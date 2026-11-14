import asyncio
import logging
import os
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clock import clock
from ..datafiles import DataBundle
from ..db import repos
from ..db.models.measurements import Measurement
from ..db.models.security import Rejection as RejectionRow
from ..db.models.users import Crew
from ..ids import next_id
from ..schemas import (
    Derivation,
    IngestResult,
    MeasurementIngest,
    Parameter,
    Rejection,
    SourceRef,
    TestCase,
    TestReport,
    Verification,
)
from ..security import signing, validation
from ..security.keys import Keys
from . import pipeline
from .events import Event

log = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
TESTS_TIMEOUT_S = 120
_report: TestReport | None = None


# --------------------------------------------------------------------------- rejections


def to_schema(r: RejectionRow) -> Rejection:
    return Rejection(
        id=r.id,
        at=r.at,
        kind=r.kind,
        source=r.source,
        crew_id=r.crew_id,
        metric_key=r.metric_key,
        value=r.value,
        message=r.message,
    )


async def record_rejection(
    session: AsyncSession,
    *,
    kind: str,
    source: str,
    message: str,
    crew_id: str | None = None,
    metric_key: str | None = None,
    value: float | None = None,
) -> RejectionRow:
    row = RejectionRow(
        id=await next_id(session, "rj"),
        at=clock.now(),
        kind=kind,
        source=source,
        crew_id=crew_id,
        metric_key=metric_key,
        value=value,
        message=message,
    )
    session.add(row)
    await session.flush()
    return row


async def rejections(session: AsyncSession, limit: int) -> list[Rejection]:
    stmt = select(RejectionRow).order_by(RejectionRow.at.desc(), RejectionRow.id.desc()).limit(limit)
    return [to_schema(r) for r in (await session.scalars(stmt)).all()]


# --------------------------------------------------------------------------- ingest


def limits(data: DataBundle) -> dict[str, tuple[float, float]]:
    out = {
        i.key: (i.min, i.max)
        for i in data.checkin.indicators
        if i.input == "number" and i.min is not None and i.max is not None
    }
    out["resting_pulse_bpm"] = out.pop("pulse_bpm", validation.EXTRA_LIMITS["resting_pulse_bpm"])
    return out


def _range_text(metric: str, lim: dict[str, tuple[float, float]]) -> str:
    lo, hi = lim.get(metric) or validation.EXTRA_LIMITS.get(metric, (None, None))
    return f" (possible range {lo:g}–{hi:g})" if lo is not None else ""


async def ingest(
    session: AsyncSession, data: DataBundle, keys: Keys, body: MeasurementIngest
) -> tuple[IngestResult, list[Event]]:
    """Signature → plausibility → frozen sensor; a rejected measurement is saved as a Rejection and the answer is
    still 200 with `accepted = false`. An accepted one is saved (`source = device`) and goes through the pipeline."""
    obj = body.model_dump(mode="json")
    kind, message = None, ""
    crew_known = await session.get(Crew, body.crew_id) is not None
    if not crew_known or not signing.verify(obj, body.signature_b64, keys.device_public.get(body.device_id)):
        kind, message = "bad_signature", f"Invalid signature from {body.device_id}: the measurement was discarded."
    else:
        lim = limits(data)
        recent = await repos.recent_device_values(
            session, body.device_id, body.metric_key, validation.FROZEN_REPEATS - 1
        )
        issue = validation.check(body.metric_key, body.value, recent, lim)
        if issue is not None and issue.kind == "implausible":
            kind = "implausible"
            message = f"Impossible value: {body.value:g} {body.unit}{_range_text(body.metric_key, lim)}."
        elif issue is not None:
            kind = "frozen_sensor"
            message = f"The same value ({body.value:g}) {validation.FROZEN_REPEATS} times in a row: frozen sensor."

    if kind is not None:
        row = await record_rejection(
            session,
            kind=kind,
            source=body.device_id,
            message=message,
            crew_id=body.crew_id if crew_known else None,
            metric_key=body.metric_key,
            value=body.value,
        )
        await session.commit()
        rejection = to_schema(row)
        return IngestResult(accepted=False, rejection=rejection), [
            Event("measurement.rejected", rejection, rejection.crew_id)
        ]

    day = min(max(clock.mission_day(body.measured_at), 1), clock.mission_day())
    session.add(
        Measurement(
            crew_id=body.crew_id,
            metric_key=body.metric_key,
            value=body.value,
            unit=body.unit,
            measured_at=body.measured_at,
            mission_day=day,
            source="device",
            device_id=body.device_id,
        )
    )
    await session.flush()
    result = await pipeline.process(session, body.crew_id, {body.metric_key}, day=day, data=data)
    await session.commit()
    return IngestResult(accepted=True), result.events


# --------------------------------------------------------------------------- evidence: thresholds


def parameters(data: DataBundle, topic: str | None, key_only: bool) -> list[Parameter]:
    key_ids = data.params.key_threshold_ids()
    out = []
    for pillar_topic, pillar in data.params.piloni.items():
        if topic is not None and pillar_topic != topic:
            continue
        for p in pillar.parametri:
            if key_only and p.id not in key_ids:
                continue
            url = p.sursa.url or (f"https://doi.org/{p.sursa.doi}" if p.sursa.doi else "")
            out.append(
                Parameter(
                    id=p.id,
                    topic=pillar_topic,
                    name=p.nume,
                    value=p.valoare,
                    unit=p.unitate,
                    explanation=p.explicatie,
                    is_key_threshold=p.id in key_ids,
                    source=SourceRef(
                        citation=p.sursa.citare,
                        url=url,
                        verification=Verification.verified if p.status == "VERIFICAT" else Verification.unverified,
                        derivation=Derivation.derived if p.derivare == "derivat" else Derivation.published,
                        evidence_strength=p.forta_dovezii,
                    ),
                )
            )
    return out


# --------------------------------------------------------------------------- evidence: tests


def parse_junit(xml_text: str, ran_at, duration_s: float) -> TestReport:
    root = ET.fromstring(xml_text)
    tests = []
    for case in root.iter("testcase"):
        outcome = "passed"
        if case.find("failure") is not None or case.find("error") is not None:
            outcome = "failed"
        elif case.find("skipped") is not None:
            outcome = "skipped"
        module = case.get("classname", "").replace(".", "/") + ".py"
        tests.append(
            TestCase(
                name=case.get("name", ""),
                module=module,
                outcome=outcome,
                duration_ms=round(float(case.get("time", 0) or 0) * 1000, 1),
            )
        )
    count = {o: sum(1 for t in tests if t.outcome == o) for o in ("passed", "failed", "skipped")}
    return TestReport(
        ran_at=ran_at,
        passed=count["passed"],
        failed=count["failed"],
        skipped=count["skipped"],
        duration_s=round(duration_s, 2),
        tests=tests,
    )


def _run_pytest() -> tuple[str, float]:
    """In a worker thread: runs the engine tests into a junit file, reads it and deletes it (all in the same thread,
    so a cancelled caller can never remove the file while pytest still writes it)."""
    fd, name = tempfile.mkstemp(prefix="shadow-engine-", suffix=".xml")
    os.close(fd)
    junit = Path(name)
    started = time.perf_counter()
    try:
        subprocess.run(
            [sys.executable, "-m", "pytest", "tests/engine", "-q", "-p", "no:cacheprovider", f"--junitxml={junit}"],
            cwd=BACKEND_DIR,
            capture_output=True,
            timeout=TESTS_TIMEOUT_S,
            check=False,
        )
        return junit.read_text(encoding="utf-8"), time.perf_counter() - started
    finally:
        junit.unlink(missing_ok=True)


async def run_engine_tests() -> TestReport | None:
    """Runs the engine tests (in a thread, so the event loop keeps going) and keeps the report."""
    global _report
    try:
        xml_text, duration = await asyncio.to_thread(_run_pytest)
        _report = parse_junit(xml_text, clock.now(), duration)
    except Exception:
        log.exception("could not run the engine tests for the Evidence screen")
        return None
    return _report


def test_report() -> TestReport:
    return _report or TestReport(ran_at=clock.now(), passed=0, failed=0, skipped=0, duration_s=0.0, tests=[])
