import logging
from datetime import datetime, timedelta

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clock import clock
from ..datafiles import DataBundle
from ..db.models.alerts import Alert as AlertRow
from ..db.models.measurements import RadiationReading
from ..db.models.sim import SimState
from ..db.models.users import Crew
from ..deps import ApiError
from ..engine import radiation as engine
from ..engine.derived import SEP_CONSECUTIVE_READINGS
from ..engine.types import EvidenceItem, Finding
from ..link import queue
from ..schemas import RadiationPoint, RadiationSeries, RadiationStatus, SepEvent, User
from ..simulator import radiation as sim
from . import mission as mission_service
from . import pipeline
from .events import Event

log = logging.getLogger(__name__)

STORM_KEY = "storm"
SHELTER_KEY = "shelter"
SEED_HOURS = 48
SEED_STEP_MIN = 10
EARTH_SENDER = "Mission Control (NASA DONKI)"
LEVEL3_LIMIT_MGY = 250.0  # NASA 30-day limit for the blood-forming organs; the fraction is in parameters.json
FLARE_CLASS = "X5.8"
EVENT_NOTE = "GLE 74, Gannon storm (May 2024). The dose curve is synthetic; the event time is real."


def _iso(t: datetime | None) -> str | None:
    return t.isoformat() if t else None


def _dt(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s else None


def _parse_donki(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# --------------------------------------------------------------------------- parameters


def threshold_ratio(data: DataBundle) -> float:
    return float(data.params.value("prag_alerta_sep_rata_vs_baseline"))


def shield_factor(data: DataBundle) -> float:
    without, with_shelter = data.params.value("reducere_doza_adapost_capsula")
    return with_shelter / without


def peak_multiplier(data: DataBundle) -> float:
    storm = next((e for e in data.scenario.events if e.kind == "solar_storm"), None)
    return float(storm.params.get("peak_multiplier", 6.0)) if storm else 6.0


def earth_warning_lag(data: DataBundle) -> timedelta:
    """How long after the event NASA issued its first alert (20240511-AL-006: 20 minutes)."""
    sep = data.donki.chosen_sep
    notes = getattr(sep, "sentNotifications", None) or []
    if not notes:
        return timedelta(minutes=20)
    return _parse_donki(notes[0]["messageIssueTime"]) - _parse_donki(sep.eventTime)


def sep_event(data: DataBundle, onset: datetime | None) -> SepEvent:
    sep = data.donki.chosen_sep
    return SepEvent(
        donki_id=sep.sepID,
        event_time=_parse_donki(sep.eventTime),
        sim_onset_at=onset,
        instrument=sep.instruments[0]["displayName"] if sep.instruments else "",
        flare_class=FLARE_CLASS,
        cme_id=data.donki.linked_cme[0]["activityID"] if data.donki.linked_cme else "",
        donki_url=sep.link,
        note=EVENT_NOTE,
    )


async def _baseline(session: AsyncSession, data: DataBundle) -> float:
    env_id = await mission_service.current_environment_id(session, data)
    return next(e.baseline_dose_usv_h for e in data.environments.environments if e.id.value == env_id)


# --------------------------------------------------------------------------- state


async def _get(session: AsyncSession, key: str) -> dict | None:
    row = await session.get(SimState, key)
    return dict(row.value) if row else None


async def _put(session: AsyncSession, key: str, value: dict | None) -> None:
    row = await session.get(SimState, key)
    if value is None:
        if row is not None:
            await session.delete(row)
    elif row is None:
        session.add(SimState(key=key, value=value))
    else:
        row.value = value
    await session.flush()


async def _sheltered(session: AsyncSession) -> datetime | None:
    shelter = await _get(session, SHELTER_KEY)
    return _dt(shelter.get("since")) if shelter else None


# --------------------------------------------------------------------------- readings


async def seed_readings(session: AsyncSession, data: DataBundle) -> None:
    """The quiet background of the last 48 h, so the 24-h mean exists before any storm."""
    if await session.scalar(select(RadiationReading.id).limit(1)) is not None:
        return
    base = await _baseline(session, data)
    now = clock.now()
    times = [now - timedelta(minutes=SEED_STEP_MIN * i) for i in range(SEED_HOURS * 60 // SEED_STEP_MIN, 0, -1)]
    seed = data.scenario.seed
    rates = [
        sim.dose_rate(
            t, baseline_usv_h=base, storm_onset=None, peak_multiplier=1, sheltered=False, shield_factor=1, rng_seed=seed
        )
        for t in times
    ]
    per_day = 24 * 60 // SEED_STEP_MIN
    rows = [
        {
            "t": t,
            "dose_rate_usv_h": r,
            "mean_24h_usv_h": round(engine.mean_24h(rates[max(0, i - per_day) : i + 1]), 2),
            "sheltered": False,
        }
        for i, (t, r) in enumerate(zip(times, rates, strict=True))
    ]
    await session.execute(insert(RadiationReading), rows)


async def _quiet_mean(session: AsyncSession, now: datetime, onset: datetime | None) -> float:
    end = onset if onset is not None and onset <= now else now
    stmt = select(RadiationReading.dose_rate_usv_h).where(
        RadiationReading.t >= end - timedelta(hours=24), RadiationReading.t < end
    )
    return round(engine.mean_24h(list((await session.scalars(stmt)).all())), 2)


async def _rate_now(session: AsyncSession, data: DataBundle, now: datetime, storm: dict | None) -> float:
    return sim.dose_rate(
        now,
        baseline_usv_h=await _baseline(session, data),
        storm_onset=_dt(storm["onset_at"]) if storm else None,
        peak_multiplier=peak_multiplier(data),
        sheltered=await _sheltered(session) is not None,
        shield_factor=shield_factor(data),
        rng_seed=data.scenario.seed,
    )


async def _since_onset(session: AsyncSession, onset: datetime) -> list[RadiationReading]:
    stmt = select(RadiationReading).where(RadiationReading.t >= onset).order_by(RadiationReading.t)
    return list((await session.scalars(stmt)).all())


def _dose(readings: list[RadiationReading], onset: datetime) -> float:
    return round(
        engine.event_dose_msv([((r.t - onset).total_seconds() / 3600, r.dose_rate_usv_h) for r in readings]), 3
    )


# --------------------------------------------------------------------------- status and series


async def status(session: AsyncSession, data: DataBundle, user: User | None = None) -> RadiationStatus:
    now = clock.now()
    storm = await _get(session, STORM_KEY)
    onset = _dt(storm["onset_at"]) if storm else None
    rate = await _rate_now(session, data, now, storm)
    mean = await _quiet_mean(session, now, onset)
    readings = await _since_onset(session, onset) if onset and onset <= now else []
    alert_ids = (storm or {}).get("alert_ids", {})
    mine = alert_ids.get(user.crew_id) if user and user.crew_id else None
    return RadiationStatus(
        at=now,
        dose_rate_usv_h=rate,
        mean_24h_usv_h=mean,
        ratio=round(rate / mean, 2) if mean else 0.0,
        threshold_ratio=threshold_ratio(data),
        alert_active=bool(storm and storm.get("onboard_alert_at")),
        alert_id=mine or (next(iter(alert_ids.values())) if alert_ids else None),
        sheltered=await _sheltered(session) is not None,
        sheltered_since=await _sheltered(session),
        event=sep_event(data, onset) if storm else None,
        event_dose_msv=_dose(readings, onset) if readings else 0.0,
        onboard_alert_at=_dt((storm or {}).get("onboard_alert_at")),
        earth_warning_arrived_at=_dt((storm or {}).get("earth_arrived_at")),
        lead_minutes=(storm or {}).get("lead_minutes"),
        profile_is_synthetic=True,
    )


async def alert_active(session: AsyncSession) -> bool:
    storm = await _get(session, STORM_KEY)
    return bool(storm and storm.get("onboard_alert_at"))


async def series(session: AsyncSession, hours: float, step_min: int) -> RadiationSeries:
    now = clock.now()
    stmt = (
        select(RadiationReading)
        .where(RadiationReading.t >= now - timedelta(hours=hours), RadiationReading.t <= now)
        .order_by(RadiationReading.t)
    )
    buckets: dict[int, RadiationReading] = {}
    for r in (await session.scalars(stmt)).all():
        buckets[int((r.t - now).total_seconds() // (step_min * 60))] = r
    points = [
        RadiationPoint(t=r.t, dose_rate_usv_h=r.dose_rate_usv_h, mean_24h_usv_h=r.mean_24h_usv_h, sheltered=r.sheltered)
        for _, r in sorted(buckets.items())
    ]
    return RadiationSeries(points=points)


# --------------------------------------------------------------------------- storm control


async def start_storm(
    session: AsyncSession, data: DataBundle, event_id: str, starts_in_min: float
) -> tuple[RadiationStatus, list[Event]]:
    if event_id != data.donki.chosen_sep.sepID:
        raise ApiError(404, "not_found", f"DONKI event {event_id} is not available offline.")
    onset = clock.now() + timedelta(minutes=starts_in_min)
    await _put(
        session,
        STORM_KEY,
        {
            "event_id": event_id,
            "onset_at": _iso(onset),
            "earth_due_at": _iso(onset + earth_warning_lag(data)),
            "alert_ids": {},
        },
    )
    await session.commit()
    s = await status(session, data)
    return s, [Event("radiation.reading", s)]


async def stop_storm(session: AsyncSession, data: DataBundle) -> tuple[RadiationStatus, list[Event]]:
    await _put(session, STORM_KEY, None)
    await session.commit()
    s = await status(session, data)
    return s, [Event("radiation.cleared", s)]


async def shelter(
    session: AsyncSession, data: DataBundle, sheltered: bool, user: User
) -> tuple[RadiationStatus, list[Event]]:
    await _put(session, SHELTER_KEY, {"since": _iso(clock.now())} if sheltered else None)
    await session.commit()
    s = await status(session, data, user)
    return s, [Event("radiation.reading", s)]


# --------------------------------------------------------------------------- live step


def _finding(crew_id: str, level: int, rate: float, mean: float, dose: float, day: int) -> Finding:
    ratio = rate / mean if mean else 0.0
    if level >= 3:
        title = f"Solar particle event: {dose:.1f} mSv since the onset"
        explanation = "The dose accumulated since the start of the event passed the threshold for informing Earth."
        rec = "radiation-3-1"
    else:
        title = f"Solar particle event: dose rate ×{ratio:.1f} — go to the shelter"
        explanation = (
            f"The on-board dosimeter reads {rate:.0f} µSv/h, {ratio:.1f} times the 24-h average ({mean:.0f} µSv/h), "
            f"for {SEP_CONSECUTIVE_READINGS} readings in a row. Go to the shelter and confirm in the app."
        )
        rec = "radiation-1-1"
    return Finding(
        crew_id=crew_id,
        topic="radiation",
        level=level,
        status="alert",
        title=title,
        explanation=explanation,
        evidence=(
            EvidenceItem(
                metric_key="dose_rate_usv_h",
                label="Dose rate",
                value=round(rate, 1),
                unit="µSv/h",
                baseline=round(mean, 1),
                deviation_text=f"×{ratio:.1f} vs the 24-h average",
            ),
            EvidenceItem(
                metric_key="event_dose_msv",
                label="Dose since the onset",
                value=round(dose, 3),
                unit="mSv",
                baseline=None,
                deviation_text="Synthetic dose curve; the event time is real (NASA DONKI)",
            ),
        ),
        recommendation_id=rec,
        day=day,
    )


async def _alert_crew(
    session: AsyncSession, data: DataBundle, storm: dict, level: int, rate: float, mean: float, dose: float
) -> list[Event]:
    events: list[Event] = []
    day = clock.mission_day()
    for crew_id in (await session.scalars(select(Crew.id).order_by(Crew.id))).all():
        result = await pipeline.process(
            session,
            crew_id,
            set(),
            day=day,
            data=data,
            extra_findings=[_finding(crew_id, level, rate, mean, dose, day)],
        )
        events += result.events
        alert_id = await session.scalar(
            select(AlertRow.id).where(
                AlertRow.crew_id == crew_id, AlertRow.topic == "radiation", AlertRow.state != "resolved"
            )
        )
        if alert_id:
            storm["alert_ids"][crew_id] = alert_id
    return events


async def live_step(session: AsyncSession, data: DataBundle) -> list[Event]:
    """One step of the live simulator: while a storm runs, a new dosimeter reading; after 3 readings above the
    threshold the crew alert (level 1); at the NASA alert time the DONKI warning leaves Earth as a packet; if the
    event dose passes the level-3 threshold, the alert goes to Earth. Does not commit."""
    storm = await _get(session, STORM_KEY)
    now = clock.now()
    if not storm:
        return []
    onset = _dt(storm["onset_at"])
    events: list[Event] = []
    if now >= onset:
        rate = await _rate_now(session, data, now, storm)
        mean = await _quiet_mean(session, now, onset)
        sheltered = await _sheltered(session) is not None
        session.add(RadiationReading(t=now, dose_rate_usv_h=rate, mean_24h_usv_h=mean, sheltered=sheltered))
        await session.flush()
        readings = await _since_onset(session, onset)
        dose = _dose(readings, onset)

        rates = [r.dose_rate_usv_h for r in readings]
        if not storm.get("onboard_alert_at") and engine.is_alert(
            rates, mean, threshold_ratio(data), SEP_CONSECUTIVE_READINGS
        ):
            storm["onboard_alert_at"] = _iso(now)
            events += await _alert_crew(session, data, storm, 1, rate, mean, dose)
            events.append(Event("radiation.alert", await status(session, data)))

        limit = LEVEL3_LIMIT_MGY * float(data.params.value("prag_doza_eveniment_nivel3")) / 100
        if storm.get("onboard_alert_at") and not storm.get("level3_at") and dose >= limit:
            storm["level3_at"] = _iso(now)
            events += await _alert_crew(session, data, storm, 3, rate, mean, dose)

    if not storm.get("earth_packet_id") and now >= _dt(storm["earth_due_at"]):
        packet = await queue.enqueue(
            session,
            direction="up",
            kind="donki_alert",
            title=f"NASA DONKI: solar particle event {storm['event_id']}",
            sender=EARTH_SENDER,
            payload={"event": sep_event(data, onset).model_dump(mode="json"), "issued_at": _iso(now)},
        )
        storm["earth_packet_id"] = packet.id
        storm["earth_issued_at"] = _iso(now)

    await _put(session, STORM_KEY, storm)
    if now >= onset:
        events.append(Event("radiation.reading", await status(session, data)))
    return events


async def donki_arrived(session: AsyncSession, packet_id: str) -> None:
    """Called by the link scheduler when a `donki_alert` packet is delivered: how many mission minutes SHADOW's own
    alert came before Earth's warning."""
    storm = await _get(session, STORM_KEY)
    if not storm or storm.get("earth_packet_id") != packet_id:
        return
    now = clock.now()
    storm["earth_arrived_at"] = _iso(now)
    onboard = _dt(storm.get("onboard_alert_at"))
    storm["lead_minutes"] = round((now - onboard).total_seconds() / 60, 1) if onboard else None
    await _put(session, STORM_KEY, storm)
