"""Date de exemplu pentru MOCK. Backend-ul le înlocuiește treptat cu date reale;
frontend-ul poate lucra pe ele din primul minut. Scenariul: ziua 96 din 140,
tranzit spre Marte, Specialist de misiune 2 are o alertă imunitară."""
from datetime import UTC, datetime, timedelta

from .datafiles import load_all
from .schemas import *  # noqa: F401,F403

# Textele, mediile, catalogul și pragurile vin din data/ (aceleași fișiere pe care le va citi backend-ul real).
DATA = load_all()

UTC = UTC
START = datetime(2027, 1, 10, 0, 0, tzinfo=UTC)          # ziua 1 a misiunii
NOW = datetime(2027, 4, 15, 7, 42, tzinfo=UTC)           # ziua 96, dimineața
DAY = 96


def d(day: int, h: int = 7, m: int = 0) -> datetime:
    return START + timedelta(days=day - 1, hours=h, minutes=m)


# ---------------------------------------------------------------- utilizatori și echipaj
CREW = [
    CrewMember(id="cm-1", display_name="Comandant", initials="CD", role_title="Comandant"),
    CrewMember(id="cm-2", display_name="Specialist de misiune 2", initials="S2", role_title="Specialist de misiune"),
    CrewMember(id="cm-3", display_name="Ofițer medical de bord", initials="OM", role_title="Ofițer medical", is_cmo=True),
    CrewMember(id="cm-4", display_name="Inginer de zbor", initials="IZ", role_title="Inginer de zbor"),
]
CREW_BY_ID = {c.id: c for c in CREW}

# Câte un cont pentru FIECARE astronaut (+ medicul de zbor de pe Pământ). Nu există cont comun.
USERS = {
    "comandant": User(id="u-cm-1", username="comandant", display_name="Comandant", initials="CD", role=Role.astronaut, crew_id="cm-1"),
    "specialist2": User(id="u-cm-2", username="specialist2", display_name="Specialist de misiune 2", initials="S2", role=Role.astronaut, crew_id="cm-2"),
    "medic": User(id="u-cm-3", username="medic", display_name="Ofițer medical de bord", initials="OM", role=Role.cmo, crew_id="cm-3"),
    "inginer": User(id="u-cm-4", username="inginer", display_name="Inginer de zbor", initials="IZ", role=Role.astronaut, crew_id="cm-4"),
    "earth": User(id="u-earth", username="earth", display_name="Medicul de zbor", initials="MZ", role=Role.earth, crew_id=None),
}
# Parole DE TEST, câte una pe cont. Doar pentru mock: backend-ul real ține în baza de date doar hash-ul (argon2/bcrypt),
# iar valorile de seed stau în backend/seed/users.json, nu în cod.
MOCK_PASSWORDS = {"comandant": "cm1-shadow", "specialist2": "cm2-shadow", "medic": "cm3-shadow", "inginer": "cm4-shadow", "earth": "earth-shadow"}
ACCOUNTS = [LoginAccount(username=u.username, display_name=u.display_name, initials=u.initials, role=u.role, crew_id=u.crew_id,
                         location="earth" if u.role == Role.earth else "ship") for u in USERS.values()]

# ---------------------------------------------------------------- medii (din data/environments.json)
_ENV_FIELDS = set(EnvironmentInfo.model_fields)
ENVIRONMENTS = [EnvironmentInfo(**e.model_dump(include=_ENV_FIELDS)) for e in DATA.environments.environments]
ENV_BY_ID = {e.id: e for e in ENVIRONMENTS}
DEFAULT_ENV = EnvironmentId(DATA.environments.default)

LINK = LinkStatus(environment=DEFAULT_ENV, one_way_delay_s=ENV_BY_ID[DEFAULT_ENV].one_way_delay_s,
                  one_way_delay_real_s=round(ENV_BY_ID[DEFAULT_ENV].one_way_delay_s / 60, 2),
                  window_open=True, window_closes_at=NOW + timedelta(minutes=42), next_window_at=None,
                  queued_down=0, queued_up=0)

MISSION = MissionState(name="SHADOW-1", sim_now=NOW, mission_day=DAY, total_days=140, time_scale=60,
                       environment=ENV_BY_ID[DEFAULT_ENV], link=LINK)

# ---------------------------------------------------------------- surse
SRC_ALAVI = SourceRef(citation="Alavi et al. (2022), Real-time alerting system for COVID-19 and other stress events using wearable data, Nature Medicine 28:175–184",
                      url="https://www.nature.com/articles/s41591-021-01593-2", evidence_strength="moderată")
SRC_ROONEY = SourceRef(citation="Rooney et al. (2019), Herpes Virus Reactivation in Astronauts During Spaceflight, Frontiers in Microbiology 10:16",
                       url="https://www.frontiersin.org/articles/10.3389/fmicb.2019.00016/full", evidence_strength="moderată")
SRC_IMMUNE_HRP = SourceRef(citation="NASA HRP — Risk of Altered Immune Response",
                           url="https://humanresearchroadmap.nasa.gov/Risks/?i=85", evidence_strength="puternică")
SRC_VANDONGEN = SourceRef(citation="Van Dongen et al. (2003), The cumulative cost of additional wakefulness, Sleep 26(2):117–126",
                          url="https://pubmed.ncbi.nlm.nih.gov/12683469/", evidence_strength="analog terestru")
SRC_CV = SourceRef(citation="NASA HRP — Risk of Cardiovascular Adaptations",
                   url="https://www.nasa.gov/reference/risk-of-cardiovascular-adaptations/",
                   verification=Verification.unverified, derivation=Derivation.derived, evidence_strength="slabă")
SRC_BONE = SourceRef(citation="NASA HRP (2024), Evidence Report: Risk of Bone Fracture due to Spaceflight-induced Changes to Bone",
                     url="https://humanresearchroadmap.nasa.gov/evidence/reports/Bone%20Fracture%20Evidence%20Report_07-18-2024.pdf",
                     evidence_strength="moderată")
SRC_ROBLING = SourceRef(citation="Robling et al. (2002), J Bone Miner Res 17(8):1545–1554",
                        url="https://pubmed.ncbi.nlm.nih.gov/12162508/", evidence_strength="doar animale")

# ---------------------------------------------------------------- alerte și catalog
_REC_FIELDS = set(Recommendation.model_fields)
RECOMMENDATIONS = [Recommendation(**r.model_dump(include=_REC_FIELDS)) for r in DATA.catalog.recommendations]
REC_BY_ID = {r.id: r for r in RECOMMENDATIONS}

ALERT_IMMUNE = Alert(
    id="al-1042", crew_id="cm-2", topic=AlertTopic.immune, level=2, status=Status.alert, state=AlertState.escalated,
    title="Puls de noapte +7 bpm, 3 nopți la rând", created_at=d(95, 6, 10),
    explanation="Pulsul tău de noapte e cu 7 bpm peste normalul tău de trei nopți. Asta apare des cu 2–3 zile înaintea unei infecții.",
    cause=Cause.individual, cause_explanation="Doar tu ai această abatere; ceilalți membri ai echipajului sunt în limite.",
    evidence=[
        Evidence(metric_key="night_pulse_bpm", label="Puls de noapte", value=61, unit="bpm", baseline=54, deviation_text="+7 bpm peste mediana personală, 3 nopți"),
        Evidence(metric_key="temperature_c", label="Temperatura", value=37.3, unit="°C", baseline=36.9, deviation_text="+0,4 °C față de normalul tău"),
        Evidence(metric_key="sleep_hours", label="Somn", value=5.5, unit="h", baseline=6.6, deviation_text="−1,1 h"),
    ],
    recommendation=REC_BY_ID["immune-2-1"],
    plan_steps=[
        PlanStep(id="st-1", text="Culcă-te cu o oră mai devreme în următoarele 3 nopți.", done=True, done_at=d(95, 21, 30)),
        PlanStep(id="st-2", text="Măsoară temperatura dimineața și seara.", done=False),
        PlanStep(id="st-3", text="Completează jurnalul de simptome (tuse, durere de cap, oboseală).", done=False),
    ],
    recheck_at=d(98, 7, 0), packet_id="pk-0007", earth_reply=None,
    history=[
        AlertHistoryEntry(at=d(95, 6, 10), actor="SHADOW", action="created"),
        AlertHistoryEntry(at=d(95, 7, 5), actor="Specialist de misiune 2", role=Role.astronaut, action="acknowledged"),
        AlertHistoryEntry(at=d(96, 6, 30), actor="Specialist de misiune 2", role=Role.astronaut, action="escalated", note="A treia noapte la rând."),
    ],
)
ALERT_BEHAV = Alert(
    id="al-1039", crew_id="cm-2", topic=AlertTopic.behavioral, level=1, status=Status.watch, state=AlertState.active,
    title="Tastezi cu 18% mai lent decât de obicei", created_at=d(96, 7, 20),
    explanation="Ritmul tău de tastare s-a abătut de la normalul tău, deși la check-in ai spus că te simți bine.",
    cause=Cause.individual, cause_explanation="Abaterea apare doar la tine.",
    evidence=[Evidence(metric_key="keys_per_min", label="Viteză de tastare", value=176, unit="taste/min", baseline=214, deviation_text="−18%")],
    recommendation=REC_BY_ID["behavioral-1-1"],
    plan_steps=[PlanStep(id="st-1", text="Fă testul de reacție de 3 minute."), PlanStep(id="st-2", text="Amână sarcinile critice cu 2 ore, dacă se poate.")],
    recheck_at=d(97, 7, 0), history=[AlertHistoryEntry(at=d(96, 7, 20), actor="SHADOW", action="created")],
)
ALERTS = {a.id: a for a in (ALERT_IMMUNE, ALERT_BEHAV)}


def brief(a: Alert) -> AlertBrief:
    return AlertBrief(**a.model_dump(include=set(AlertBrief.model_fields)))


# ---------------------------------------------------------------- tablou de bord
GAP = PerceptionGap(self_reported_mood=4, self_score=80, objective_score=52, gap=28, status=Status.alert,
                    explanation="Spui că ești bine (4/5), dar tastezi cu 18% mai lent și pulsul de noapte a crescut.",
                    contributing_signals=["Tastare: −18% viteză", "Puls de noapte: +7 bpm", "Somn: −1,1 h"])

PILLAR_SUMMARIES = [
    PillarSummary(pillar=Pillar.behavioral, name="Tastatura", body_zone="brain", status=Status.watch, score=71,
                  headline="Tastezi cu 18% mai lent decât de obicei", hazard=Hazard.isolation, active_alert_id="al-1039"),
    PillarSummary(pillar=Pillar.cardio, name="Inima", body_zone="heart", status=Status.ok, score=88,
                  headline="În limitele tale din zbor", hazard=Hazard.gravity),
    PillarSummary(pillar=Pillar.immune, name="Santinela", body_zone="immune", status=Status.alert, score=58,
                  headline="Puls de noapte crescut 3 nopți la rând", hazard=Hazard.hostile_environment, active_alert_id="al-1042"),
    PillarSummary(pillar=Pillar.musculoskeletal, name="Încărcarea", body_zone="bones", status=Status.ok, score=82,
                  headline="1 din 2 sesiuni făcute azi", hazard=Hazard.gravity),
]

STREAKS = [Streak(key="checkin", label="Check-in zilnic", days=12, best=31),
           Streak(key="split_training", label="Antrenament în două sesiuni", days=5, best=9),
           Streak(key="pvt", label="Test de reacție", days=3, best=14)]

REMINDERS = [Reminder(id="rm-1", kind="checkin", label="Check-in de dimineață", due_at=d(96, 7, 0), done=True, overdue=False),
             Reminder(id="rm-2", kind="pvt", label="Test de reacție (3 minute)", due_at=d(96, 9, 0), done=False, overdue=False),
             Reminder(id="rm-3", kind="exercise", label="A doua sesiune de exerciții", due_at=d(96, 16, 0), done=False, overdue=False)]

CROSS = [CrossSignal(id="xs-1", title="Probabil debutul unei boli", pillars=[Pillar.immune, Pillar.behavioral],
                     signals=["Puls de noapte: +7 bpm", "Tastare: −18% viteză", "Somn: −1,1 h"], confidence=0.72,
                     explanation="Trei semnale slabe, independente, arată în aceeași direcție.")]

DASHBOARD = Dashboard(crew=CREW_BY_ID["cm-2"], as_of=NOW, mission_day=DAY, overall_status=Status.alert,
                      pillars=PILLAR_SUMMARIES, perception_gap=GAP, cross_signals=CROSS, alerts_active_count=2,
                      top_alert=brief(ALERT_IMMUNE), streaks=STREAKS, reminders=REMINDERS,
                      radiation_alert_active=False, checkin_done_today=True)


def series(key, label, unit, base, vals, lo=None, hi=None, thr=None, thr_label=None) -> MetricSeries:
    n = len(vals)
    return MetricSeries(metric_key=key, label=label, unit=unit, baseline=base, band_low=lo, band_high=hi,
                        threshold=thr, threshold_label=thr_label,
                        points=[SeriesPoint(day=DAY - n + 1 + i, t=d(DAY - n + 1 + i, 6), value=v,
                                            status=(Status.alert if thr is not None and v is not None and v >= thr else Status.ok))
                                for i, v in enumerate(vals)])


PILLAR_DETAILS = {
    Pillar.behavioral: PillarDetail(
        pillar=Pillar.behavioral, name="Tastatura", body_zone="brain",
        function_text="Creierul coordonează atenția, memoria, deciziile și reacțiile rapide. În spațiu, somnul scurt și izolarea îi pot scădea performanța fără ca astronautul să observe.",
        hazard=Hazard.isolation, hazard_text="Izolarea și programul neregulat: somnul scurt scade atenția fără să-ți dai seama.",
        status=Status.watch, score=71, explanation="Tastezi mai lent și ții tastele apăsate mai mult decât de obicei.",
        metrics=[MetricValue(key="keys_per_min", label="Viteză de tastare", value=176, unit="taste/min", baseline=214, deviation_abs=-38, deviation_pct=-18, status=Status.watch, source=DataSource.device, measured_at=d(96, 7, 18)),
                 MetricValue(key="hold_ms_mean", label="Timp de apăsare", value=112, unit="ms", baseline=96, deviation_abs=16, deviation_pct=17, status=Status.watch, source=DataSource.device, measured_at=d(96, 7, 18)),
                 MetricValue(key="pvt_mean_speed", label="Viteză de reacție (PVT-B)", value=3.31, unit="1/s", baseline=3.72, deviation_abs=-0.41, deviation_pct=-11, status=Status.watch, source=DataSource.device, measured_at=d(95, 9, 5))],
        chart=series("keys_per_min", "Viteză de tastare", "taste/min", 214, [216, 211, 209, 213, 205, 198, 190, 184, 180, 176], lo=198, hi=230),
        plan_steps=ALERT_BEHAV.plan_steps, active_alert_id="al-1039", recheck_at=d(97, 7), sources=[SRC_VANDONGEN],
        limits_text="Tastarea ca semnal de oboseală are dovezi puține (un studiu mic). Nu citim niciodată ce scrii, doar ritmul.",
        data_is_simulated=False),
    Pillar.cardio: PillarDetail(
        pillar=Pillar.cardio, name="Inima", body_zone="heart",
        function_text="Inima pompează sângele care duce oxigen și nutrienți în tot corpul. În microgravitație fluidele urcă spre cap, iar la revenire pot apărea amețeli la ridicare.",
        hazard=Hazard.gravity, hazard_text="Gravitația modificată: inima lucrează mai puțin și se decondiționează.",
        status=Status.ok, score=88, explanation="Valorile tale sunt în limitele normalului tău din zbor.",
        metrics=[MetricValue(key="systolic_mmhg", label="Tensiune sistolică", value=112, unit="mmHg", baseline=110, deviation_abs=2, deviation_pct=2, status=Status.ok, source=DataSource.manual, measured_at=d(96, 7, 2)),
                 MetricValue(key="resting_pulse_bpm", label="Puls în repaus", value=58, unit="bpm", baseline=57, deviation_abs=1, deviation_pct=2, status=Status.ok, source=DataSource.manual, measured_at=d(96, 7, 2)),
                 MetricValue(key="landing_readiness", label="Pregătire pentru revenire", value=88, unit="/100", baseline=100, deviation_abs=-12, deviation_pct=-12, status=Status.ok, source=DataSource.simulated)],
        chart=series("landing_readiness", "Pregătire pentru revenire", "/100", 100, [93, 92, 92, 91, 90, 90, 89, 89, 88, 88], lo=80, hi=100),
        plan_steps=[], sources=[SRC_CV],
        limits_text="Pragurile nu sunt publicate pentru astronauți; sunt derivate. Comparăm cu normalul din zbor, nu cu cel de pe Pământ.",
        data_is_simulated=True),
    Pillar.immune: PillarDetail(
        pillar=Pillar.immune, name="Santinela", body_zone="immune",
        function_text="Sistemul imunitar apără corpul de virusuri, bacterii și celule anormale. În zbor, stresul, somnul perturbat și radiațiile îl dereglează.",
        hazard=Hazard.hostile_environment, hazard_text="Radiațiile și mediul închis: stresul și spațiul comun slăbesc apărarea organismului.",
        status=Status.alert, score=58, explanation="Pulsul tău de noapte e peste normalul tău de trei nopți la rând.",
        metrics=[MetricValue(key="night_pulse_bpm", label="Puls de noapte", value=61, unit="bpm", baseline=54, deviation_abs=7, deviation_pct=13, status=Status.alert, source=DataSource.simulated, measured_at=d(96, 6)),
                 MetricValue(key="temperature_c", label="Temperatura", value=37.3, unit="°C", baseline=36.9, deviation_abs=0.4, deviation_pct=1.1, status=Status.watch, source=DataSource.manual, measured_at=d(96, 7, 2)),
                 MetricValue(key="sleep_hours", label="Somn", value=5.5, unit="h", baseline=6.6, deviation_abs=-1.1, deviation_pct=-17, status=Status.watch, source=DataSource.manual, measured_at=d(96, 7, 2)),
                 MetricValue(key="stress_index", label="Indice de stres", value=64, unit="/100", baseline=40, deviation_abs=24, deviation_pct=60, status=Status.watch, source=DataSource.simulated)],
        chart=series("night_pulse_bpm", "Puls de noapte", "bpm", 54, [54, 53, 55, 54, 54, 55, 56, 60, 61, 61], lo=51, hi=57, thr=58, thr_label="+4 bpm, 2 nopți (NightSignal)"),
        plan_steps=ALERT_IMMUNE.plan_steps, active_alert_id="al-1042", recheck_at=d(98, 7), sources=[SRC_ALAVI, SRC_ROONEY, SRC_IMMUNE_HRP],
        limits_text="Algoritmul nu distinge tipul de infecție și poate da alarme false. A fost validat pe civili, nu pe astronauți.",
        data_is_simulated=True),
    Pillar.musculoskeletal: PillarDetail(
        pillar=Pillar.musculoskeletal, name="Încărcarea", body_zone="bones",
        function_text="Oasele susțin corpul, iar mușchii produc mișcarea; ambele se mențin prin încărcare. Fără gravitație și fără exerciții, oasele portante pierd 1–1,5% din densitate pe lună.",
        hazard=Hazard.gravity, hazard_text="Gravitația modificată: fără greutatea corpului, oasele și mușchii pierd masă.",
        status=Status.ok, score=82, explanation="Ai făcut o sesiune din două. A doua, la câteva ore distanță, ajută mai mult oasele.",
        metrics=[MetricValue(key="loading_score", label="Încărcare azi", value=38, unit="/80", baseline=80, deviation_abs=-42, deviation_pct=-52, status=Status.ok, source=DataSource.simulated),
                 MetricValue(key="strength_pct", label="Forță față de început", value=96, unit="%", baseline=100, deviation_abs=-4, deviation_pct=-4, status=Status.ok, source=DataSource.simulated)],
        chart=series("loading_score", "Scor zilnic de încărcare", "", 80, [78, 81, 80, 62, 79, 83, 80, 81, 77, 38], lo=64, hi=96),
        plan_steps=[], sources=[SRC_BONE, SRC_ROBLING],
        limits_text="Efectul împărțirii în sesiuni e demonstrat doar pe animale. Densitatea osoasă e estimată, nu măsurată.",
        data_is_simulated=True),
}

# textele panourilor vin din data/texts/body_functions.json
for _b in DATA.body.pillars:
    PILLAR_DETAILS[_b.pillar] = PILLAR_DETAILS[_b.pillar].model_copy(update=dict(
        name=_b.name, body_zone=_b.body_zone, function_text=_b.function_text, hazard=_b.hazard,
        hazard_text=_b.hazard_text, limits_text=_b.limits_text, sources=_b.sources or PILLAR_DETAILS[_b.pillar].sources))
for _p in PILLAR_SUMMARIES:
    _p.name = PILLAR_DETAILS[_p.pillar].name


def timeline(from_day: int, to_day: int) -> Timeline:
    days = []
    for n in range(from_day, to_day + 1):
        imm = Status.alert if 94 <= n <= 99 else (Status.watch if n in (93, 100) else Status.ok)
        beh = Status.watch if n in (40, 41, 95, 96, 97) else Status.ok
        card = Status.watch if 110 <= n <= 118 else Status.ok
        mus = Status.watch if n in (61, 62) else Status.ok
        allp = {Pillar.behavioral: beh, Pillar.cardio: card, Pillar.immune: imm, Pillar.musculoskeletal: mus}
        overall = Status.alert if Status.alert in allp.values() else (Status.watch if Status.watch in allp.values() else Status.ok)
        days.append(TimelineDay(day=n, date=d(n, 0), overall_status=overall, pillars=allp,
                                events=(["Furtună solară"] if n == 97 else [])))
    return Timeline(crew_id="cm-2", from_day=from_day, to_day=to_day, days=days)


# ---------------------------------------------------------------- check-in
CHECKIN_SCHEMA = CheckinSchema(indicators=DATA.checkin.indicators)   # din data/texts/checkin_indicators.json

CHECKIN_VALUES = CheckinCreate(mood=4, systolic_mmhg=112, diastolic_mmhg=72, pulse_bpm=58, glucose_mg_dl=92,
                               temperature_c=37.3, sleep_hours=5.5, meals_eaten="some", note=None)
CHECKIN = Checkin(id="ck-0096", crew_id="cm-2", mission_day=DAY, created_at=d(96, 7, 2), values=CHECKIN_VALUES)

# ---------------------------------------------------------------- tastare, PVT
KS_BASE = KeystrokeFeatures(hold_ms_mean=96.4, hold_ms_sd=21.3, flight_ms_mean=182.0, flight_ms_sd=64.9, backspace_rate=0.06, keys_per_min=214, n_keys=5200)
KS_NOW = KeystrokeFeatures(hold_ms_mean=112.0, hold_ms_sd=27.8, flight_ms_mean=221.5, flight_ms_sd=88.0, backspace_rate=0.07, keys_per_min=176, n_keys=380)
KS_SUMMARY = KeystrokeSummary(baseline=KS_BASE, current=KS_NOW, fatigue_index=68, status=Status.watch, baseline_ready=True,
                              sessions=[KeystrokeSessionPoint(session_id=f"s-{i}", at=d(96 - (5 - i), 7, 15), keys_per_min=v, hold_ms_mean=h, fatigue_index=f,
                                                              status=Status.watch if f >= 50 else Status.ok)
                                        for i, (v, h, f) in enumerate([(213, 97, 6), (205, 99, 18), (198, 102, 31), (184, 108, 55), (180, 110, 61), (176, 112, 68)])])
PVT = PvtResult(id="pvt-0031", crew_id="cm-2", at=d(95, 9, 5), n_trials=48, mean_rt_ms=312.5, mean_speed=3.31, lapses=6, false_starts=1,
                baseline_speed=3.72, deviation_sd=-1.4, status=Status.watch)

# ---------------------------------------------------------------- exerciții
EX_SESSION = ExerciseSession(id="ex-0211", crew_id="cm-2", mission_day=DAY, kind="resistance", started_at=d(96, 8, 30), duration_min=40,
                             sets=[ExerciseSet(exercise="genuflexiuni ARED", reps=10, load_kg=85), ExerciseSet(exercise="îndreptări ARED", reps=8, load_kg=95)],
                             loading_score=38, source=DataSource.simulated)
EX_TODAY = ExerciseToday(mission_day=DAY, planned_sessions=2, completed_sessions=1, loading_score=38, loading_target=80, split_recommended=True,
                         recommendation_text="Împarte antrenamentul de azi în două sesiuni, la câteva ore distanță.",
                         streak=STREAKS[1], sessions=[EX_SESSION],
                         projection=BoneProjection(current_plan_pct_month=-0.64, split_plan_pct_month=-0.45,
                                                   note="Estimare. Efectul împărțirii e demonstrat doar pe animale (Robling 2002)."))

# ---------------------------------------------------------------- pachete
CRYPTO = PacketCrypto(key_id="ship-2026-01", nonce_b64="q83vEjRWeJCrze8S", signature_b64="MEUCIQDc...trunchiat...")
PACKETS = [
    PacketDetail(id="pk-0007", seq=7, direction=PacketDirection.down, kind=PacketKind.alert_l3, status=PacketStatus.in_transit,
                 title="Imunitar · puls de noapte +7 bpm, 3 nopți", sender="Ofițer medical de bord", level=3, alert_status=Status.alert,
                 crew_id="cm-2", alert_id="al-1042", created_at=d(96, 7, 30), sent_at=d(96, 7, 35), arrives_at=d(96, 7, 46, ) + timedelta(seconds=40),
                 progress=0.64, eta_real_s=4.2, signature_valid=None, size_bytes=1840, payload=None, crypto=CRYPTO),
    PacketDetail(id="pk-0006", seq=6, direction=PacketDirection.down, kind=PacketKind.weekly_summary, status=PacketStatus.delivered,
                 title="Rezumat săptămânal aprobat de astronaut", sender="Specialist de misiune 2", crew_id="cm-2",
                 created_at=d(95, 9, 20), sent_at=d(95, 9, 29), arrives_at=d(95, 9, 41), delivered_at=d(95, 9, 41),
                 progress=1, eta_real_s=0, signature_valid=True, size_bytes=2310,
                 payload={"summary": "Săptămâna 13: somn mediu 6,1 h, 6 check-in-uri din 7, nicio alertă de nivel 3."}, crypto=CRYPTO),
    PacketDetail(id="pk-0005", seq=5, direction=PacketDirection.down, kind=PacketKind.alert_l3, status=PacketStatus.rejected,
                 title="Temperatură 41,9 °C · senzor 07", sender="necunoscut", created_at=d(95, 3, 12), sent_at=d(95, 3, 12),
                 arrives_at=d(95, 3, 24), progress=1, eta_real_s=0, signature_valid=False, reject_reason=RejectionKind.bad_signature,
                 size_bytes=612, payload=None, crypto=CRYPTO),
]
PACKET_BY_ID = {p.id: p for p in PACKETS}

MESSAGES = [CrewMessage(packet_id="pk-0004", kind="earth_reply", sender="Medicul de zbor",
                        body="Am primit rezumatul. Continuați planul de somn; revenim la următoarea fereastră.",
                        sent_at=d(94, 12, 0), delivered_at=d(94, 12, 12), read=True)]

# ---------------------------------------------------------------- radiații
_sep = DATA.donki.chosen_sep
SEP = SepEvent(donki_id=_sep.sepID, event_time=datetime.fromisoformat(_sep.eventTime.replace("Z", "+00:00")), sim_onset_at=None,
               instrument=_sep.instruments[0]["displayName"], flare_class="X5.8",
               cme_id=(DATA.donki.linked_cme[0]["activityID"] if DATA.donki.linked_cme else ""),
               donki_url=_sep.link, note="GLE 74, furtuna Gannon (mai 2024)")
RAD_QUIET = RadiationStatus(at=NOW, dose_rate_usv_h=66.4, mean_24h_usv_h=65.8, ratio=1.01, alert_active=False, sheltered=False, event=None, event_dose_msv=0)
RAD_STORM = RadiationStatus(at=NOW, dose_rate_usv_h=412.0, mean_24h_usv_h=66.0, ratio=6.24, alert_active=True, alert_id="al-1050",
                            sheltered=True, sheltered_since=NOW - timedelta(minutes=4),
                            event=SEP.model_copy(update={"sim_onset_at": NOW - timedelta(minutes=9)}), event_dose_msv=0.05,
                            onboard_alert_at=NOW - timedelta(minutes=7), earth_warning_arrived_at=None, lead_minutes=None)

# ---------------------------------------------------------------- AI, securitate, dovezi
AI_ANSWER = AiChatResponse(
    answer="Pulsul tău de noapte e cu 7 bpm peste normalul tău de trei nopți. Corpul face asta des când luptă cu o infecție, înainte să apară simptome. "
           "Recomandarea e să anunți ofițerul medical, să-ți protejezi somnul și să măsori temperatura de două ori pe zi.",
    citations=[Citation(title="Alavi et al. (2022), Nature Medicine", url="https://www.nature.com/articles/s41591-021-01593-2",
                        snippet="Alerta roșie: puls de repaus nocturn cu cel puțin 4 bpm peste baseline, două nopți consecutive."),
               Citation(title="NASA HRP — Risk of Altered Immune Response", url="https://humanresearchroadmap.nasa.gov/Risks/?i=85",
                        snippet="Stresul zborului, somnul perturbat și radiațiile dereglează sistemul imunitar.")],
    recommendation_ids=["immune-2-1"], model="gemma-3-4b-it-Q4_K_M", latency_ms=2140, fallback=False)

ACCESS_LOG = [
    AccessLogEntry(id=1, at=d(96, 6, 31), actor="Ofițer medical de bord", actor_role=Role.cmo, action="read_alert", resource="alerts/al-1042",
                   crew_id="cm-2", outcome="allowed", prev_hash="0" * 16, hash="9f2c41d07ab3e5c8"),
    AccessLogEntry(id=2, at=d(96, 6, 40), actor="Comandant", actor_role=Role.astronaut, action="read_dashboard", resource="crew/cm-2/dashboard",
                   crew_id="cm-2", outcome="denied", prev_hash="9f2c41d07ab3e5c8", hash="1b77e0aa52c9d4f3"),
]
REJECTIONS = [Rejection(id="rj-0003", at=d(95, 3, 12), kind=RejectionKind.bad_signature, source="senzor-07", crew_id=None,
                        metric_key="temperature_c", value=41.9, message="Temperatură 41,9 °C · semnătură invalidă"),
              Rejection(id="rj-0002", at=d(93, 14, 0), kind=RejectionKind.frozen_sensor, source="wearable-cm-4", crew_id="cm-4",
                        metric_key="night_pulse_bpm", value=57.0, message="Aceeași valoare 240 de citiri la rând: senzor înghețat")]
TEST_REPORT = TestReport(ran_at=d(96, 0, 5), passed=3, failed=0, duration_s=1.42, tests=[
    TestCase(name="test_nightsignal_red_after_two_nights", module="tests/test_immune.py", outcome="passed", duration_ms=12.1),
    TestCase(name="test_sep_alert_at_2x_mean", module="tests/test_radiation.py", outcome="passed", duration_ms=8.4),
    TestCase(name="test_packet_with_bad_signature_is_rejected", module="tests/test_link.py", outcome="passed", duration_ms=21.7)])
_KEY_IDS = DATA.params.key_threshold_ids()
PARAMETERS = [
    Parameter(id=prm.id, topic=topic, name=prm.nume, value=prm.valoare, unit=prm.unitate, explanation=prm.explicatie,
              is_key_threshold=prm.id in _KEY_IDS,
              source=SourceRef(citation=prm.sursa.citare,
                               url=prm.sursa.url or (f"https://doi.org/{prm.sursa.doi}" if prm.sursa.doi else ""),
                               verification=Verification.verified if prm.status == "VERIFICAT" else Verification.unverified,
                               derivation=Derivation.derived if prm.derivare == "derivat" else Derivation.published,
                               evidence_strength=prm.forta_dovezii))
    for topic, pil in DATA.params.piloni.items() for prm in pil.parametri
]


# ---------------------------------------------------------------- date pe membru de echipaj
# Scenariul are abateri doar la cm-2. Ceilalți membri primesc aceleași structuri, cu totul „în limite”,
# ca fiecare cont să-și vadă PROPRIILE date după autentificare.
def dashboard_for(crew_id: str) -> Dashboard:
    if crew_id == "cm-2":
        return DASHBOARD
    return DASHBOARD.model_copy(update=dict(
        crew=CREW_BY_ID[crew_id], overall_status=Status.ok,
        pillars=[p.model_copy(update=dict(status=Status.ok, score=92, headline="În limitele tale din zbor", active_alert_id=None)) for p in PILLAR_SUMMARIES],
        perception_gap=PerceptionGap(self_reported_mood=4, self_score=80, objective_score=84, gap=-4, status=Status.ok,
                                     explanation="Cum te simți se potrivește cu ce arată datele.", contributing_signals=[]),
        cross_signals=[], alerts_active_count=0, top_alert=None))


def pillar_for(crew_id: str, pillar: Pillar) -> PillarDetail:
    d_ = PILLAR_DETAILS[pillar]
    if crew_id == "cm-2":
        return d_
    flat = d_.chart.model_copy(update=dict(threshold=None, points=[pt.model_copy(update=dict(value=d_.chart.baseline, status=Status.ok)) for pt in d_.chart.points]))
    return d_.model_copy(update=dict(
        status=Status.ok, score=92, explanation="Valorile tale sunt în limitele normalului tău din zbor.",
        metrics=[m.model_copy(update=dict(value=m.baseline, deviation_abs=0, deviation_pct=0, status=Status.ok)) for m in d_.metrics],
        chart=flat, plan_steps=[], active_alert_id=None, recheck_at=None))
