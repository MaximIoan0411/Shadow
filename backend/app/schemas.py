"""SHADOW — contractul de date (Pydantic v2).

SURSA DE ADEVĂR pentru toată echipa. Din acest fișier se generează openapi.yaml,
tipurile TypeScript ale frontend-ului și documentația.

Reguli:
  * Nu redenumiți și nu ștergeți câmpuri fără să anunțați echipa (vezi README, „Cum schimbăm contractul”).
  * Câmpurile noi se adaugă OPȚIONALE (cu valoare implicită), ca să nu stricați frontend-ul.
  * Toate momentele de timp sunt ISO 8601 UTC, în TIMPUL MISIUNII (SimClock), nu în timpul real.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# --------------------------------------------------------------------------- enumerări


class Role(str, Enum):
    """Rolul din JWT. Decide ce endpoint-uri sunt permise."""
    astronaut = "astronaut"  # membru al echipajului, cu contul LUI; vede doar datele lui
    cmo = "cmo"          # ofițerul medical de la bord (Crew Medical Officer)
    earth = "earth"      # medicul de zbor de pe Pământ


class Pillar(str, Enum):
    """Cei patru piloni. Fiecare are o zonă pe corpul interactiv."""
    behavioral = "behavioral"            # Tastatura  — creier
    cardio = "cardio"                    # Inima      — inimă
    immune = "immune"                    # Santinela  — sistem imunitar
    musculoskeletal = "musculoskeletal"  # Încărcarea — oase și mușchi


class AlertTopic(str, Enum):
    """Subiectul unei alerte: un pilon, radiațiile sau un semnal încrucișat."""
    behavioral = "behavioral"
    cardio = "cardio"
    immune = "immune"
    musculoskeletal = "musculoskeletal"
    radiation = "radiation"
    cross_signal = "cross_signal"


class Status(str, Enum):
    """Semaforul. În UI: ok = verde ●, watch = galben ▲, alert = roșu ■, unknown = gri."""
    ok = "ok"            # în limitele normalului personal
    watch = "watch"      # abatere mică sau scurtă, de urmărit
    alert = "alert"      # abatere peste prag
    unknown = "unknown"  # baseline-ul nu e gata sau lipsesc date


class EnvironmentId(str, Enum):
    iss = "iss"                    # stația spațială, orbită joasă
    moon_base = "moon_base"        # bază pe Lună
    mars_transit = "mars_transit"  # nava, pe drumul spre Marte
    mars_base = "mars_base"        # bază sau rover pe Marte


class Hazard(str, Enum):
    """Cele 5 pericole NASA HRP."""
    radiation = "radiation"                      # radiațiile spațiale
    isolation = "isolation"                      # izolarea și spațiul închis
    distance = "distance"                        # distanța față de Pământ
    gravity = "gravity"                          # gravitația modificată
    hostile_environment = "hostile_environment"  # mediul închis și ostil al navei


class DataSource(str, Enum):
    """De unde vine o valoare. `device` = semnată Ed25519; `manual` = tastată la check-in."""
    device = "device"        # de la un dispozitiv, semnată Ed25519
    manual = "manual"        # tastată de astronaut la check-in
    simulated = "simulated"  # generată de simulator; se afișează eticheta „date simulate”


class AlertState(str, Enum):
    active = "active"              # nouă, nimeni nu a confirmat-o
    acknowledged = "acknowledged"  # astronautul a văzut-o și lucrează la plan
    escalated = "escalated"        # urcată la nivelul 2 sau 3
    resolved = "resolved"          # închisă (rezolvată / alarmă falsă)


class Cause(str, Enum):
    individual = "individual"        # doar acest astronaut
    environmental = "environmental"  # mai mulți membri ai echipajului → probabil cabina
    unknown = "unknown"


class PacketDirection(str, Enum):
    down = "down"  # navă → Pământ
    up = "up"      # Pământ → navă


class PacketKind(str, Enum):
    alert_l3 = "alert_l3"              # alertă de nivel 3, navă → Pământ
    weekly_summary = "weekly_summary"  # rezumat aprobat de astronaut, navă → Pământ
    earth_reply = "earth_reply"        # răspunsul medicului de zbor, Pământ → navă
    donki_alert = "donki_alert"        # avertizare de furtună solară, Pământ → navă


class PacketStatus(str, Enum):
    queued = "queued"          # așteaptă fereastra de comunicare
    in_transit = "in_transit"  # pe drum (întârzierea luminii)
    delivered = "delivered"    # ajuns, decriptat, semnătură validă
    rejected = "rejected"      # semnătură invalidă / replay / decriptare eșuată


class Verification(str, Enum):
    verified = "verified"      # VERIFICAT în parameters.json
    unverified = "unverified"  # NEVERIFICAT — se afișează ca ipoteză


class Derivation(str, Enum):
    published = "published"  # valoare publicată în sursă
    derived = "derived"      # prag ales/calculat de echipă


class RejectionKind(str, Enum):
    bad_signature = "bad_signature"  # semnătura nu se verifică
    implausible = "implausible"      # valoare în afara intervalului posibil
    frozen_sensor = "frozen_sensor"  # aceeași valoare de prea multe ori la rând
    replay = "replay"                # pachet retrimis (seq deja văzut)


# --------------------------------------------------------------------------- erori


class ErrorBody(BaseModel):
    code: str = Field(description="Cod stabil, pentru logică în frontend. Lista e în README, secțiunea Erori.", examples=["forbidden"])
    message: str = Field(description="Mesaj în română, gata de afișat utilizatorului.", examples=["Nu ai acces la datele altui membru al echipajului."])
    details: dict[str, Any] | None = Field(default=None, description="Detalii opționale (ex. câmpurile invalide).")


class ErrorResponse(BaseModel):
    """Forma UNICĂ a oricărei erori (4xx/5xx)."""
    error: ErrorBody


class Ok(BaseModel):
    ok: bool = True


# --------------------------------------------------------------------------- autentificare


class User(BaseModel):
    """Un cont. FIECARE astronaut are contul lui; nu există cont comun de echipaj."""
    id: str = Field(examples=["u-cm-2"])
    username: str = Field(examples=["specialist2"])
    display_name: str = Field(examples=["Specialist de misiune 2"])
    initials: str = Field(examples=["S2"])
    role: Role
    crew_id: str | None = Field(default=None, description="Membrul de echipaj al contului. Fiecare cont de astronaut are exact unul, diferit. `null` doar pentru rolul `earth`.", examples=["cm-2"])


class LoginAccount(BaseModel):
    """Un cont afișat pe ecranul de autentificare (fără nicio dată medicală)."""
    username: str = Field(examples=["specialist2"])
    display_name: str = Field(examples=["Specialist de misiune 2"])
    initials: str = Field(examples=["S2"])
    role: Role
    crew_id: str | None = Field(default=None, examples=["cm-2"])
    location: Literal["ship", "earth"] = Field(description="Pe ce stație de lucru apare contul: la bord sau la Controlul misiunii.")


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=40, examples=["specialist2"])
    password: str = Field(min_length=1, max_length=256, description="Parola PERSONALĂ a contului. Fiecare cont are altă parolă.", examples=["<parola din seed>"])


class LoginResponse(BaseModel):
    access_token: str = Field(description="JWT legat de acest cont. Se trimite la fiecare cerere: `Authorization: Bearer <token>`.")
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Secunde reale până la expirare.", examples=[43200])
    user: User


# --------------------------------------------------------------------------- misiune, mediu, ceas


class EnvironmentInfo(BaseModel):
    id: EnvironmentId
    name: str = Field(examples=["Tranzit spre Marte"])
    one_way_delay_s: float = Field(description="Întârzierea legăturii într-un sens, în secunde de MISIUNE.", examples=[700])
    gravity_g: float = Field(description="Gravitația, în g.", examples=[0.0])
    baseline_dose_usv_h: float = Field(description="Rata de doză de fond pentru simulator, µSv/h.", examples=[65.8])
    emphasized_hazards: list[Hazard] = Field(description="Pericolele care contează cel mai mult în acest mediu.")
    description: str


class LinkStatus(BaseModel):
    """Starea legăturii cu Pământul (pasul 3)."""
    environment: EnvironmentId
    one_way_delay_s: float = Field(description="Secunde de misiune, într-un sens.", examples=[700])
    one_way_delay_real_s: float = Field(description="Aceeași întârziere în secunde REALE (delay / time_scale). Folosiți-o pentru animații.", examples=[11.7])
    window_open: bool = Field(description="Dacă fereastra de comunicare e deschisă acum.")
    window_closes_at: datetime | None = None
    next_window_at: datetime | None = Field(default=None, description="Când se redeschide fereastra, dacă e închisă.")
    queued_down: int = Field(description="Pachete care așteaptă spre Pământ.", examples=[1])
    queued_up: int = Field(description="Pachete care așteaptă spre navă.", examples=[0])


class MissionState(BaseModel):
    name: str = Field(examples=["SHADOW-1"])
    sim_now: datetime = Field(description="Ora curentă a misiunii (SimClock).")
    mission_day: int = Field(description="Ziua curentă a misiunii, de la 1.", examples=[96])
    total_days: int = Field(examples=[140])
    time_scale: float = Field(description="De câte ori merge timpul misiunii mai repede decât cel real.", examples=[60])
    environment: EnvironmentInfo
    link: LinkStatus


class ClockUpdate(BaseModel):
    """Trimiteți doar câmpul pe care vreți să-l schimbați."""
    model_config = ConfigDict(allow_inf_nan=False)  # NaN și infinit nu sunt măsurători
    time_scale: float | None = Field(default=None, ge=1, le=86400, examples=[60])
    mission_day: int | None = Field(default=None, ge=1, description="Sare ceasul la începutul acestei zile (doar pentru demo).", examples=[96])


class EnvironmentUpdate(BaseModel):
    environment: EnvironmentId


# --------------------------------------------------------------------------- echipaj


class CrewMember(BaseModel):
    id: str = Field(examples=["cm-2"])
    display_name: str = Field(examples=["Specialist de misiune 2"])
    initials: str = Field(examples=["S2"])
    role_title: str = Field(examples=["Specialist de misiune"])
    is_cmo: bool = Field(default=False, description="Dacă e ofițerul medical de la bord.")


class CrewSummary(BaseModel):
    """Un rând din lista ofițerului medical. NU conține valori medicale, doar starea generală."""
    member: CrewMember
    overall_status: Status
    active_alerts: int
    highest_level: Literal[1, 2, 3] | None = None


# --------------------------------------------------------------------------- surse


class SourceRef(BaseModel):
    """O sursă științifică. Apare lângă orice prag, text sau recomandare."""
    citation: str = Field(examples=["Alavi et al. (2022), Nature Medicine 28:175–184"])
    url: str = Field(examples=["https://www.nature.com/articles/s41591-021-01593-2"])
    verification: Verification = Verification.verified
    derivation: Derivation = Derivation.published
    evidence_strength: str | None = Field(default=None, description="puternică / moderată / slabă / analog terestru / doar animale", examples=["moderată"])


# --------------------------------------------------------------------------- valori, serii


class MetricValue(BaseModel):
    """O valoare comparată cu baseline-ul PERSONAL al astronautului."""
    key: str = Field(description="Cheie stabilă. Lista completă e în README, „Chei de metrici”.", examples=["night_pulse_bpm"])
    label: str = Field(examples=["Puls de noapte"])
    value: float | None = Field(examples=[61.0])
    unit: str = Field(examples=["bpm"])
    baseline: float | None = Field(default=None, description="Normalul personal din zbor.", examples=[54.0])
    deviation_abs: float | None = Field(default=None, description="value − baseline.", examples=[7.0])
    deviation_pct: float | None = Field(default=None, examples=[13.0])
    status: Status
    source: DataSource
    measured_at: datetime | None = None


class SeriesPoint(BaseModel):
    day: int = Field(description="Ziua misiunii.", examples=[94])
    t: datetime
    value: float | None
    status: Status | None = None


class MetricSeries(BaseModel):
    """Date pentru un grafic: valori pe zile + banda de baseline + pragul de alertă."""
    metric_key: str
    label: str
    unit: str
    baseline: float | None = Field(default=None, description="Linia orizontală a normalului personal.")
    band_low: float | None = Field(default=None, description="Marginea de jos a benzii normale.")
    band_high: float | None = Field(default=None, description="Marginea de sus a benzii normale.")
    threshold: float | None = Field(default=None, description="Pragul de alertă, dacă există.")
    threshold_label: str | None = Field(default=None, examples=["+4 bpm, 2 nopți (NightSignal)"])
    points: list[SeriesPoint]


# --------------------------------------------------------------------------- tablou de bord


class PerceptionGap(BaseModel):
    """IDEEA CENTRALĂ: diferența dintre cum se simte astronautul și ce arată datele."""
    self_reported_mood: int | None = Field(default=None, ge=1, le=5, description="Răspunsul de la check-in.")
    self_score: float | None = Field(default=None, ge=0, le=100, description="Cum spune că se simte, pe 0–100.", examples=[80])
    objective_score: float | None = Field(default=None, ge=0, le=100, description="Ce arată datele obiective, pe 0–100.", examples=[52])
    gap: float | None = Field(default=None, description="self_score − objective_score. Pozitiv = se simte mai bine decât arată datele.", examples=[28])
    status: Status
    explanation: str = Field(examples=["Spui că ești bine (4/5), dar tastezi cu 18% mai lent și pulsul de noapte a crescut."])
    contributing_signals: list[str] = Field(default_factory=list, examples=[["Tastare: −18% viteză", "Puls de noapte: +7 bpm"]])


class CrossSignal(BaseModel):
    """Trei semnale slabe independente care, împreună, cântăresc mai mult."""
    id: str
    title: str = Field(examples=["Probabil debutul unei boli"])
    pillars: list[Pillar]
    signals: list[str]
    confidence: float = Field(ge=0, le=1, examples=[0.72])
    explanation: str


class Streak(BaseModel):
    key: Literal["checkin", "split_training", "pvt"]
    label: str = Field(examples=["Check-in zilnic"])
    days: int = Field(examples=[12])
    best: int = Field(examples=[31])


class Reminder(BaseModel):
    id: str
    kind: Literal["checkin", "exercise", "pvt"]
    label: str = Field(examples=["A doua sesiune de exerciții"])
    due_at: datetime
    done: bool
    overdue: bool = Field(description="True = a trecut ora; în UI apare discret, nu ca alertă.")


class AlertBrief(BaseModel):
    id: str = Field(examples=["al-1042"])
    crew_id: str = Field(examples=["cm-2"])
    topic: AlertTopic
    level: Literal[1, 2, 3] = Field(description="1 = te descurci singur, 2 = ofițerul medical, 3 = Pământul.")
    status: Status = Field(description="Culoarea alertei (watch sau alert).")
    state: AlertState
    title: str = Field(examples=["Puls de noapte +7 bpm, 3 nopți la rând"])
    created_at: datetime


class PillarSummary(BaseModel):
    """Un pilon, pe scurt: colorează zona de pe corp."""
    pillar: Pillar
    name: str = Field(description="Numele din interfață.", examples=["Santinela"])
    body_zone: Literal["brain", "heart", "immune", "bones"] = Field(description="Zona de pe ilustrația corpului.")
    status: Status
    score: float | None = Field(default=None, ge=0, le=100, description="100 = exact ca baseline-ul personal.", examples=[64])
    headline: str = Field(examples=["Puls de noapte crescut 3 nopți la rând"])
    hazard: Hazard = Field(description="Pericolul NASA principal pentru acest pilon.")
    active_alert_id: str | None = None


class Dashboard(BaseModel):
    """Tot ce îi trebuie ecranului principal al astronautului, într-un singur apel."""
    crew: CrewMember
    as_of: datetime
    mission_day: int
    overall_status: Status
    pillars: list[PillarSummary] = Field(description="Mereu exact 4, în ordinea: behavioral, cardio, immune, musculoskeletal.")
    perception_gap: PerceptionGap
    cross_signals: list[CrossSignal]
    alerts_active_count: int
    top_alert: AlertBrief | None = Field(default=None, description="Alerta cea mai importantă, pentru banner.")
    streaks: list[Streak]
    reminders: list[Reminder]
    radiation_alert_active: bool = Field(description="True = afișați banner-ul „Mergi în adăpost”.")
    checkin_done_today: bool


class PlanStep(BaseModel):
    id: str = Field(examples=["st-1"])
    text: str = Field(examples=["Culcă-te cu o oră mai devreme în următoarele 3 nopți."])
    done: bool = False
    done_at: datetime | None = None


class PillarDetail(BaseModel):
    """Panoul care se deschide la click pe o zonă a corpului."""
    pillar: Pillar
    name: str
    body_zone: Literal["brain", "heart", "immune", "bones"]
    function_text: str = Field(description="Funcția părții corpului (cerință din brief). Max. 2 propoziții.")
    hazard: Hazard
    hazard_text: str = Field(description="Rândul „Pericolul spațial”.")
    status: Status
    score: float | None = None
    explanation: str = Field(description="Ce se întâmplă acum, în cuvinte simple.")
    metrics: list[MetricValue]
    chart: MetricSeries = Field(description="Graficul principal al pilonului.")
    plan_steps: list[PlanStep] = Field(description="Pașii planului din alerta activă. Listă goală dacă nu e nicio alertă.")
    active_alert_id: str | None = None
    recheck_at: datetime | None = Field(default=None, description="Când se verifică dacă planul a funcționat (1–3 zile).")
    sources: list[SourceRef]
    limits_text: str = Field(description="„Limite oneste” — ce NU poate spune acest pilon.")
    data_is_simulated: bool = Field(description="True = afișați eticheta „date simulate”.")


class TimelineDay(BaseModel):
    day: int
    date: datetime
    overall_status: Status
    pillars: dict[Pillar, Status]
    events: list[str] = Field(default_factory=list, description="Etichete scurte pentru derulator.", examples=[["Furtună solară"]])


class Timeline(BaseModel):
    """Date pentru derulatorul misiunii."""
    crew_id: str
    from_day: int
    to_day: int
    days: list[TimelineDay]


# --------------------------------------------------------------------------- check-in


class CheckinIndicator(BaseModel):
    """Descrierea unui câmp din check-in. Frontend-ul construiește formularul din lista asta."""
    key: str = Field(examples=["systolic_mmhg"])
    label: str = Field(examples=["Tensiunea (sistolică)"])
    unit: str = Field(examples=["mmHg"])
    input: Literal["number", "scale_1_5", "choice"]
    min: float | None = Field(default=None, description="Sub această valoare, câmpul e respins ca imposibil.")
    max: float | None = Field(default=None, description="Peste această valoare, câmpul e respins ca imposibil.")
    step: float | None = None
    choices: list[str] | None = Field(default=None, description="Doar pentru input = choice.")
    required: bool = False
    how_to_measure: str = Field(description="Coloana „Cum se măsoară”.")
    what_it_means: str = Field(description="Coloana „Ce înseamnă valoarea”.")
    why_in_space: str = Field(description="Coloana „De ce contează în spațiu”.")
    pillar: Pillar | None = None
    source: SourceRef | None = None


class CheckinSchema(BaseModel):
    indicators: list[CheckinIndicator]


class CheckinCreate(BaseModel):
    """Check-in-ul de dimineață. Doar `mood` e obligatoriu; restul pot lipsi."""
    model_config = ConfigDict(allow_inf_nan=False)  # NaN și infinit nu sunt măsurători
    mood: int = Field(ge=1, le=5, description="Starea de spirit, 1 (foarte rău) – 5 (foarte bine).", examples=[4])
    systolic_mmhg: float | None = Field(default=None, examples=[112])
    diastolic_mmhg: float | None = Field(default=None, examples=[72])
    pulse_bpm: float | None = Field(default=None, description="Puls în repaus, numărat 30 s × 2.", examples=[58])
    glucose_mg_dl: float | None = Field(default=None, description="Glicemie pe nemâncate.", examples=[92])
    temperature_c: float | None = Field(default=None, examples=[36.9])
    sleep_hours: float | None = Field(default=None, examples=[5.5])
    meals_eaten: Literal["all", "some", "none"] | None = Field(default=None, description="„Ai mâncat toate mesele de ieri?”", examples=["some"])
    note: str | None = Field(default=None, max_length=500, description="Notă liberă. Textul se salvează; ritmul tastării se trimite separat la /keystrokes/batches.")


class FieldRejection(BaseModel):
    field: str = Field(examples=["temperature_c"])
    value: Any = Field(examples=[41.9])
    reason: RejectionKind
    message: str = Field(examples=["Temperatura 41,9 °C e în afara intervalului posibil. Măsoară din nou."])


class Checkin(BaseModel):
    id: str = Field(examples=["ck-0096"])
    crew_id: str
    mission_day: int
    created_at: datetime
    values: CheckinCreate = Field(description="Valorile ACCEPTATE. Câmpurile respinse sunt `null` aici.")


class CheckinResult(BaseModel):
    checkin: Checkin
    rejected: list[FieldRejection] = Field(description="Câmpurile respinse la validare. Lista goală = totul a fost acceptat.")
    perception_gap: PerceptionGap = Field(description="Recalculat imediat după check-in.")
    alerts_created: list[AlertBrief]
    streak: Streak
    message: str = Field(description="Mesaj scurt de confirmare pentru UI.", examples=["Check-in salvat. 12 zile la rând."])


# --------------------------------------------------------------------------- tastare și PVT


class KeyEvent(BaseModel):
    """O apăsare de tastă. NU conține litera, doar timpii și clasa tastei."""
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)  # orice câmp în plus (ex. litera) → 422
    t_down_ms: float = Field(description="`performance.now()` la keydown, ms.", examples=[10234.5])
    t_up_ms: float = Field(description="`performance.now()` la keyup, ms.", examples=[10321.1])
    key_class: Literal["char", "space", "backspace", "enter", "other"] = Field(description="Clasa tastei. NICIODATĂ caracterul propriu-zis.")


class KeystrokeBatch(BaseModel):
    session_id: str = Field(description="UUID generat de frontend la începutul unei sesiuni de scris.", examples=["8b1f0c1e-6f0a-4f0e-9d53-2c1a7f1b9e10"])
    context: Literal["free_typing", "checkin_note", "ai_chat", "demo"] = Field(description="Unde a tastat.")
    events: list[KeyEvent] = Field(min_length=1, max_length=2000, description="Trimiteți loturi de max. 2000 de evenimente, la ~5 secunde.")


class KeystrokeFeatures(BaseModel):
    """Trăsăturile calculate. hold = apăsare→eliberare; flight = apăsare→apăsarea următoare."""
    hold_ms_mean: float = Field(examples=[96.4])
    hold_ms_sd: float = Field(examples=[21.3])
    flight_ms_mean: float = Field(examples=[182.0])
    flight_ms_sd: float = Field(examples=[64.9])
    backspace_rate: float = Field(description="Backspace-uri / total taste, 0–1.", examples=[0.06])
    keys_per_min: float = Field(examples=[214])
    n_keys: int = Field(examples=[380])


class KeystrokeResult(BaseModel):
    session_id: str
    features: KeystrokeFeatures
    baseline: KeystrokeFeatures | None = Field(default=None, description="`null` până când baseline-ul e gata.")
    deviation_z: dict[str, float] = Field(description="Abaterea fiecărei trăsături, în deviații standard personale.", examples=[{"hold_ms_mean": 1.9, "keys_per_min": -1.6}])
    fatigue_index: float | None = Field(default=None, ge=0, le=100, description="0 = ca baseline-ul, 100 = abatere maximă.", examples=[68])
    status: Status
    baseline_ready: bool
    baseline_sessions: int = Field(description="Câte sesiuni au intrat în baseline până acum.", examples=[9])


class KeystrokeSessionPoint(BaseModel):
    session_id: str
    at: datetime
    keys_per_min: float
    hold_ms_mean: float
    fatigue_index: float | None = None
    status: Status


class KeystrokeSummary(BaseModel):
    """Pentru barele live de tastare și comparația „ora 2 vs ora 18” din demo."""
    baseline: KeystrokeFeatures | None
    current: KeystrokeFeatures | None
    fatigue_index: float | None = None
    status: Status
    baseline_ready: bool
    sessions: list[KeystrokeSessionPoint]


class PvtTrial(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)  # NaN și infinit nu sunt măsurători
    stimulus_at_ms: float = Field(description="Când a apărut stimulul, ms de la începutul testului.")
    rt_ms: float | None = Field(default=None, description="Timpul de reacție. `null` = nu a răspuns.", examples=[287])
    false_start: bool = Field(default=False, description="A apăsat înainte de stimul.")


class PvtSubmit(BaseModel):
    started_at: datetime
    duration_s: int = Field(default=180, ge=1, le=3600, description="PVT-B durează 3 minute.")
    trials: list[PvtTrial] = Field(min_length=1, max_length=1000)


class PvtResult(BaseModel):
    id: str = Field(examples=["pvt-0031"])
    crew_id: str
    at: datetime
    n_trials: int
    mean_rt_ms: float = Field(examples=[312.5])
    mean_speed: float = Field(description="Media 1/RT în 1/s — metrica cea mai sensibilă (Basner 2011).", examples=[3.31])
    lapses: int = Field(description="Răspunsuri cu RT ≥ 355 ms.", examples=[6])
    false_starts: int
    baseline_speed: float | None = Field(default=None, examples=[3.72])
    deviation_sd: float | None = Field(default=None, description="Abaterea vitezei față de baseline, în SD. Prag derivat: −1,24.", examples=[-1.4])
    status: Status


# --------------------------------------------------------------------------- exerciții


class ExerciseSet(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)  # NaN și infinit nu sunt măsurători
    exercise: str = Field(max_length=80, examples=["genuflexiuni ARED"])
    reps: int = Field(ge=1, le=1000, examples=[10])
    load_kg: float = Field(ge=0, le=2000, examples=[85])


class ExerciseSessionCreate(BaseModel):
    kind: Literal["resistance", "aerobic"]
    started_at: datetime
    duration_min: float = Field(gt=0, le=1440, allow_inf_nan=False, examples=[40])
    sets: list[ExerciseSet] = Field(default_factory=list, max_length=200, description="Gol pentru sesiuni aerobe.")


class ExerciseSession(ExerciseSessionCreate):
    id: str = Field(examples=["ex-0211"])
    crew_id: str
    mission_day: int
    loading_score: float = Field(description="Stimulul de încărcare osoasă al sesiunii.", examples=[38])
    source: DataSource


class BoneProjection(BaseModel):
    """Estimare, NU măsurătoare: densitatea osoasă nu se poate măsura la bord."""
    current_plan_pct_month: float = Field(description="Pierderea estimată de densitate cu planul actual, % pe lună.", examples=[-0.64])
    split_plan_pct_month: float = Field(description="Aceeași estimare cu antrenamentul împărțit (ipoteză, doar pe animale).", examples=[-0.45])
    note: str


class ExerciseToday(BaseModel):
    mission_day: int
    planned_sessions: int = Field(examples=[2])
    completed_sessions: int = Field(examples=[1])
    loading_score: float = Field(ge=0, description="Scorul zilnic de încărcare.", examples=[38])
    loading_target: float = Field(examples=[80])
    split_recommended: bool
    recommendation_text: str = Field(examples=["Împarte antrenamentul de azi în două sesiuni, la câteva ore distanță."])
    streak: Streak
    sessions: list[ExerciseSession]
    projection: BoneProjection


# --------------------------------------------------------------------------- alerte, triaj, catalog


class Evidence(BaseModel):
    metric_key: str
    label: str
    value: float | None
    unit: str
    baseline: float | None = None
    deviation_text: str = Field(examples=["+7 bpm peste mediana personală, 3 nopți"])


class Recommendation(BaseModel):
    """O intrare din catalogul scris de echipă pe baza NASA. AI-ul doar o reformulează."""
    id: str = Field(description="Format: <topic>-<nivel>-<nr>, ex. `immune-2-1`.", examples=["immune-2-1"])
    topic: AlertTopic
    level: Literal[1, 2, 3]
    trigger: str = Field(description="Când se aplică.")
    action: str = Field(description="Ce are de făcut.")
    hrp_risk: str = Field(description="Riscul NASA HRP corespunzător.")
    hrp_risk_url: str
    source: SourceRef


class AlertHistoryEntry(BaseModel):
    at: datetime
    actor: str = Field(examples=["Specialist de misiune 2"])
    role: Role | None = None
    action: Literal["created", "acknowledged", "step_done", "escalated", "packet_sent", "earth_replied", "rechecked", "resolved"]
    note: str | None = None


class Alert(AlertBrief):
    """Alerta completă."""
    explanation: str = Field(description="Ce s-a observat, în cuvinte simple.")
    cause: Cause
    cause_explanation: str = Field(examples=["Doar tu ai această abatere; ceilalți membri ai echipajului sunt în limite."])
    evidence: list[Evidence]
    recommendation: Recommendation
    plan_steps: list[PlanStep]
    recheck_at: datetime | None = Field(default=None, description="Când verifică SHADOW dacă planul a funcționat.")
    packet_id: str | None = Field(default=None, description="Pachetul spre Pământ, dacă alerta a ajuns la nivelul 3.")
    earth_reply: str | None = Field(default=None, description="Răspunsul medicului de pe Pământ, după ce a sosit.")
    history: list[AlertHistoryEntry]


class StepUpdate(BaseModel):
    done: bool


class EscalateRequest(BaseModel):
    to_level: Literal[2, 3] = Field(description="2 = către ofițerul medical; 3 = către Pământ (doar rolul cmo).")
    note: str | None = Field(default=None, max_length=500)


class ResolveRequest(BaseModel):
    outcome: Literal["resolved", "false_alarm", "monitoring"]
    note: str | None = Field(default=None, max_length=500)


# --------------------------------------------------------------------------- legătura cu Pământul


class Packet(BaseModel):
    """Un mesaj din coada navă ↔ Pământ. Conținutul e criptat; aici e doar plicul."""
    id: str = Field(examples=["pk-0007"])
    seq: int = Field(description="Număr de ordine unic; blochează retrimiterea (replay).", examples=[7])
    direction: PacketDirection
    kind: PacketKind
    status: PacketStatus
    title: str = Field(description="Titlu scurt, vizibil în coadă.", examples=["Imunitar · puls de noapte +7 bpm, 3 nopți"])
    sender: str = Field(examples=["Ofițer medical de bord"])
    level: Literal[1, 2, 3] | None = None
    alert_status: Status | None = Field(default=None, description="Culoarea alertei din pachet, dacă e cazul.")
    crew_id: str | None = None
    alert_id: str | None = None
    in_reply_to: str | None = Field(default=None, description="Id-ul pachetului la care răspunde.")
    created_at: datetime
    sent_at: datetime | None = Field(default=None, description="Când a plecat (s-a deschis fereastra).")
    arrives_at: datetime | None = Field(default=None, description="Când ajunge. `sent_at + one_way_delay`.")
    delivered_at: datetime | None = None
    progress: float = Field(ge=0, le=1, description="0 = încă în coadă, 1 = ajuns. Pentru bara de progres.", examples=[0.64])
    eta_real_s: float | None = Field(default=None, description="Secunde REALE până la sosire.", examples=[4.2])
    signature_valid: bool | None = Field(default=None, description="`null` până la sosire. False = pachet respins.")
    reject_reason: RejectionKind | None = None
    size_bytes: int = Field(examples=[1840])


class PacketCrypto(BaseModel):
    cipher: str = Field(default="AES-256-GCM")
    signature_alg: str = Field(default="Ed25519")
    key_id: str = Field(examples=["ship-2026-01"])
    nonce_b64: str
    signature_b64: str


class PacketDetail(Packet):
    payload: dict[str, Any] | None = Field(default=None, description="Conținutul DECRIPTAT. Apare doar dacă pachetul e `delivered` și rolul are voie să-l citească.")
    crypto: PacketCrypto


class OutboxCreate(BaseModel):
    """Astronautul/ofițerul medical pune ceva în coada spre Pământ."""
    kind: Literal["weekly_summary", "alert_l3"] = Field(description="`alert_l3`: doar ofițerul medical, doar pentru o alertă deja escaladată la nivelul 3.")
    crew_id: str = Field(examples=["cm-2"])
    alert_id: str | None = Field(default=None, description="Obligatoriu pentru kind = alert_l3.")
    body: str | None = Field(default=None, max_length=2000, description="Text liber adăugat de expeditor.")


class EarthReplyCreate(BaseModel):
    in_reply_to: str | None = Field(default=None, description="Id-ul pachetului la care răspunde.", examples=["pk-0007"])
    crew_id: str = Field(examples=["cm-2"])
    alert_id: str | None = Field(default=None, examples=["al-1042"])
    body: str = Field(min_length=1, max_length=2000, examples=["De acord cu odihna. Temperatura de două ori pe zi."])


class CrewMessage(BaseModel):
    """Un mesaj SOSIT la bord de pe Pământ (deja decriptat și verificat)."""
    packet_id: str
    kind: Literal["earth_reply", "donki_alert"]
    sender: str = Field(examples=["Medicul de zbor"])
    body: str
    sent_at: datetime
    delivered_at: datetime
    alert_id: str | None = None
    donki_event_id: str | None = None
    read: bool = False


# --------------------------------------------------------------------------- radiații


class SepEvent(BaseModel):
    """Evenimentul real de particule solare din NASA DONKI folosit în simulator."""
    donki_id: str = Field(examples=["2024-05-11T02:10:00-SEP-001"])
    event_time: datetime = Field(description="Ora reală a evenimentului (2024).")
    sim_onset_at: datetime | None = Field(default=None, description="Când lovește în timpul misiunii simulate.")
    instrument: str = Field(examples=["GOES-P: SEISS >100 MeV"])
    flare_class: str = Field(examples=["X5.8"])
    cme_id: str = Field(examples=["2024-05-11T01:36:00-CME-001"])
    donki_url: str
    note: str = Field(examples=["GLE 74, furtuna Gannon (mai 2024)"])


class RadiationStatus(BaseModel):
    """Starea radiațiilor acum (pasul 4). Prototipul afișează totul în Sv, simplificat."""
    at: datetime
    dose_rate_usv_h: float = Field(description="Rata de doză la dozimetrul de la bord, µSv/h.", examples=[412.0])
    mean_24h_usv_h: float = Field(description="Media mobilă pe 24 h.", examples=[66.0])
    ratio: float = Field(description="dose_rate / mean_24h.", examples=[6.2])
    threshold_ratio: float = Field(default=2.0, description="Pragul de alertă (derivat de echipă).")
    alert_active: bool
    alert_id: str | None = None
    sheltered: bool
    sheltered_since: datetime | None = None
    event: SepEvent | None = Field(default=None, description="`null` dacă nu rulează nicio furtună.")
    event_dose_msv: float = Field(description="Doza acumulată de la începutul evenimentului, mSv.", examples=[1.8])
    onboard_alert_at: datetime | None = Field(default=None, description="Când a dat SHADOW alerta, din dozimetru.")
    earth_warning_arrived_at: datetime | None = Field(default=None, description="Când a sosit avertizarea DONKI de pe Pământ.")
    lead_minutes: float | None = Field(default=None, description="Cu câte minute de misiune a fost SHADOW mai rapid decât Pământul. `null` până sosește avertizarea.", examples=[31.0])
    profile_is_synthetic: bool = Field(default=True, description="Forma curbei e sintetică; ora evenimentului e reală. Afișați eticheta.")


class RadiationPoint(BaseModel):
    t: datetime
    dose_rate_usv_h: float
    mean_24h_usv_h: float
    sheltered: bool = False


class RadiationSeries(BaseModel):
    unit: str = "µSv/h"
    threshold_ratio: float = 2.0
    points: list[RadiationPoint]


class ShelterAck(BaseModel):
    sheltered: bool = Field(description="True = „Sunt în adăpost”. False = a ieșit din adăpost.")


class SepStart(BaseModel):
    event_id: str = Field(default="2024-05-11T02:10:00-SEP-001", max_length=80)
    starts_in_min: float = Field(default=0, ge=0, le=100_000, allow_inf_nan=False, description="Peste câte minute de MISIUNE începe furtuna.")


# --------------------------------------------------------------------------- medicul AI


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class AiChatRequest(BaseModel):
    crew_id: str = Field(examples=["cm-2"])
    message: str = Field(min_length=1, max_length=1000, examples=["De ce mi-a crescut pulsul de noapte?"])
    alert_id: str | None = Field(default=None, description="Dacă întrebarea e despre o alertă anume.", examples=["al-1042"])
    history: list[ChatMessage] = Field(default_factory=list, max_length=20, description="Ultimele max. 6 mesaje sunt folosite.")


class Citation(BaseModel):
    title: str = Field(examples=["NASA HRP — Risk of Altered Immune Response"])
    url: str
    snippet: str = Field(description="Fragmentul din document pe care se bazează răspunsul.")


class AiChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(description="Sursele NASA. Dacă lista e goală, afișați „fără sursă”.")
    recommendation_ids: list[str] = Field(description="Intrările din catalog pe care le reformulează răspunsul.", examples=[["immune-2-1"]])
    model: str = Field(examples=["gemma-3-4b-it-Q4_K_M"])
    latency_ms: int
    fallback: bool = Field(description="True = modelul nu a răspuns; textul vine direct din catalog.")
    disclaimer: str = Field(default="Prototip de sprijin, nu dispozitiv medical.")


class AiStatus(BaseModel):
    ready: bool
    model: str | None = None
    mode: Literal["local", "colab_simulation", "fallback", "mock"] = Field(description="Unde rulează modelul: `local` (laptopul de demo), `colab_simulation` (Colab, prezentat deschis ca simulare), `fallback` (serviciul nu răspunde; doar catalogul), `mock` (serviciul AI încă fără model). Afișați-l onest în UI.")


# --------------------------------------------------------------------------- securitate și dovezi


class AccessLogEntry(BaseModel):
    """Jurnalul de acces: doar se adaugă, fiecare intrare conține hash-ul celei dinainte."""
    id: int
    at: datetime
    actor: str = Field(examples=["Ofițer medical de bord"])
    actor_role: Role
    action: str = Field(description="login, login_failed, logout, read_dashboard, read_pillar, read_alert, escalate, read_packet, …", examples=["read_alert"])
    resource: str = Field(examples=["alerts/al-1042"])
    crew_id: str | None = None
    outcome: Literal["allowed", "denied"]
    prev_hash: str
    hash: str


class AccessLogIntegrity(BaseModel):
    """Rezultatul verificării lanțului de hash-uri al jurnalului de acces, făcută la cerere."""
    intact: bool = Field(description="`false` = o intrare a fost modificată sau ștearsă în afara aplicației.")
    entries: int = Field(description="Câte intrări are tot jurnalul (nu doar cele pe care le vede contul).", examples=[42])
    checked_at: datetime = Field(description="Când s-a făcut verificarea (timpul misiunii).")


class Rejection(BaseModel):
    """O valoare sau un pachet respins de stratul de securitate."""
    id: str = Field(examples=["rj-0003"])
    at: datetime
    kind: RejectionKind
    source: str = Field(description="Dispozitivul sau pachetul.", examples=["senzor-07"])
    crew_id: str | None = None
    metric_key: str | None = None
    value: float | None = None
    message: str = Field(examples=["Temperatură 41,9 °C · semnătură invalidă"])


class MeasurementIngest(BaseModel):
    """O măsurătoare trimisă de un dispozitiv (sau de simulator), semnată Ed25519."""
    model_config = ConfigDict(allow_inf_nan=False)  # NaN și infinit nu sunt măsurători
    device_id: str = Field(min_length=1, max_length=40, examples=["wearable-cm-2"])
    crew_id: str = Field(min_length=1, max_length=16, examples=["cm-2"])
    metric_key: str = Field(min_length=1, max_length=40, examples=["night_pulse_bpm"])
    value: float = Field(examples=[61])
    unit: str = Field(max_length=16, examples=["bpm"])
    measured_at: datetime
    signature_b64: str = Field(max_length=200, description="Ed25519 peste JSON-ul canonic al celorlalte câmpuri (chei sortate, fără spații).")


class IngestResult(BaseModel):
    accepted: bool
    rejection: Rejection | None = None


class TestCase(BaseModel):
    name: str = Field(examples=["test_nightsignal_red_after_two_nights"])
    module: str = Field(examples=["tests/test_immune.py"])
    outcome: Literal["passed", "failed", "skipped"]
    duration_ms: float


class TestReport(BaseModel):
    """Rezultatul pytest pe motorul de protocoale, pentru ecranul Evidence."""
    ran_at: datetime
    passed: int
    failed: int
    skipped: int = 0
    duration_s: float
    tests: list[TestCase]


class Parameter(BaseModel):
    """Un prag din parameters.json, cu sursa lui."""
    id: str = Field(examples=["nightsignal_red_delta_bpm"])
    topic: str = Field(examples=["imunitar"])
    name: str
    value: Any
    unit: str
    explanation: str
    is_key_threshold: bool = Field(description="True = motorul de triaj îl folosește direct.")
    source: SourceRef


# --------------------------------------------------------------------------- evenimente SSE


class MissionTick(BaseModel):
    sim_now: datetime
    mission_day: int


class SseEvent(BaseModel):
    """Plicul oricărui eveniment de pe /events. `data` depinde de `type` — vezi README, secțiunea SSE."""
    id: str = Field(examples=["ev-000123"])
    type: Literal[
        "mission.tick", "environment.changed",
        "alert.created", "alert.updated",
        "packet.sent", "packet.arrived", "packet.rejected",
        "radiation.alert", "radiation.reading", "radiation.cleared",
        "measurement.rejected", "reminder.due", "dashboard.changed",
    ]
    at: datetime
    crew_id: str | None = Field(default=None, description="Dacă evenimentul privește un singur membru.")
    data: dict[str, Any]
