"""SHADOW — contractul dintre backend și folderul data/.

Formatul fiecărui fișier din data/, ca modele Pydantic. Backend-ul (și mock-ul) încarcă totul cu `load_all()`
la pornire; un fișier invalid oprește pornirea, cu mesaj clar. Din aceste modele se generează JSON Schema în
contract/data/schemas/ (scripts/build_docs.py), iar scripts/validate_data.py verifică fișierele.

Reguli:
  * Schimbările de FORMAT (câmp nou obligatoriu, câmp redenumit) se anunță: strică încărcarea.
  * Schimbările de CONȚINUT (un text, un prag cu sursa lui) se pot face oricând.
  * Unde se poate, modelele refolosesc modelele contractului API (schemas.py), ca datele să ajungă la frontend
    fără conversii.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .schemas import AlertTopic, CheckinIndicator, EnvironmentInfo, Hazard, Pillar, Recommendation, SourceRef

# --------------------------------------------------------------------------- parameters.json (din research)


class ParamSource(BaseModel):
    model_config = ConfigDict(extra="allow")
    citare: str
    doi: str | None = None
    url: str | None = None


class Param(BaseModel):
    """Un parametru. `valoare` poate fi număr, text, listă, dicționar sau null — motorul citește doar pragurile cheie."""
    model_config = ConfigDict(extra="allow")
    id: str
    nume: str
    valoare: Any
    unitate: str
    explicatie: str
    status: Literal["VERIFICAT", "NEVERIFICAT"]
    derivare: Literal["publicat", "derivat"]
    nota_derivare: str = ""
    forta_dovezii: str
    relativ_la_baseline: bool = False
    verificat_cum: str = ""
    sursa: ParamSource
    surse_suplimentare: list[Any] = Field(default_factory=list)


class HrpRisk(BaseModel):
    nume: str
    url: str


class ParamRecommendation(BaseModel):
    model_config = ConfigDict(extra="allow")
    nivel: Literal["1_singur", "2_ofiter_medical", "3_pamant"]
    declansator: str
    actiune: str
    risc_hrp: str
    risc_hrp_url: str
    status: Literal["VERIFICAT", "NEVERIFICAT"]
    sursa: ParamSource
    nota: str | None = None


class ParamPillar(BaseModel):
    titlu: str
    riscuri_hrp: list[HrpRisk]
    parametri: list[Param]
    recomandari: list[ParamRecommendation]


class ParametersFile(BaseModel):
    """data/parameters.json — pragurile, fiecare cu sursa lui."""
    model_config = ConfigDict(extra="allow")
    meta: dict[str, Any]
    praguri_cheie_triaj: dict[str, list[str]] = Field(description="Pe subiect: id-urile pragurilor folosite direct de motor.")
    piloni: dict[str, ParamPillar]
    eveniment_sep_simulator: dict[str, Any]
    corecturi_plan: dict[str, Any] = Field(default_factory=dict)
    note_dovezi_slabe: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _key_thresholds_exist(self) -> ParametersFile:
        ids = {p.id for pil in self.piloni.values() for p in pil.parametri}
        missing = [i for lst in self.praguri_cheie_triaj.values() for i in lst if i not in ids]
        if missing:
            raise ValueError(f"praguri_cheie_triaj conține id-uri inexistente: {missing}")
        return self

    def by_id(self) -> dict[str, Param]:
        return {p.id: p for pil in self.piloni.values() for p in pil.parametri}

    def value(self, param_id: str) -> Any:
        """Valoarea unui parametru. Aruncă KeyError dacă nu există (preferabil la pornire, nu în demo)."""
        return self.by_id()[param_id].valoare

    def key_threshold_ids(self) -> set[str]:
        return {i for lst in self.praguri_cheie_triaj.values() for i in lst}


# --------------------------------------------------------------------------- environments.json


class EnvironmentEntry(EnvironmentInfo):
    """Un mediu. Câmpurile din EnvironmentInfo ajung direct la frontend; restul sunt doar pentru backend."""
    delay_range_s: tuple[float, float] | None = Field(default=None, description="Intervalul real al întârzierii într-un sens (Marte: 3–22 min). `one_way_delay_s` e valoarea folosită în demo.")
    dose_source_param: str | None = Field(default=None, description="Id-ul din parameters.json de unde vine doza de fond.")
    sources: list[SourceRef] = Field(default_factory=list)


class EnvironmentsFile(BaseModel):
    """data/environments.json — cele 4 medii ale comutatorului."""
    default: str = Field(description="Id-ul mediului la pornire.")
    environments: list[EnvironmentEntry]

    @model_validator(mode="after")
    def _default_exists(self) -> EnvironmentsFile:
        if self.default not in {e.id.value for e in self.environments}:
            raise ValueError(f"default = {self.default} nu e în listă")
        return self


# --------------------------------------------------------------------------- texts/checkin_indicators.json


class CheckinIndicatorsFile(BaseModel):
    """data/texts/checkin_indicators.json — câmpurile check-in-ului. `min`/`max` = limitele FIZIC posibile."""
    indicators: list[CheckinIndicator]

    @model_validator(mode="after")
    def _mood_first(self) -> CheckinIndicatorsFile:
        keys = [i.key for i in self.indicators]
        if len(keys) != len(set(keys)):
            raise ValueError("chei duplicate în indicators")
        if "mood" not in keys:
            raise ValueError("lipsește indicatorul obligatoriu `mood`")
        return self


# --------------------------------------------------------------------------- texts/body_functions.json


class BodyFunction(BaseModel):
    """Textele panoului unei zone a corpului (cerință din brief: funcția părții corpului)."""
    pillar: Pillar
    name: str = Field(examples=["Santinela"])
    body_zone: Literal["brain", "heart", "immune", "bones"]
    function_text: str = Field(description="Max. 2 propoziții.")
    hazard: Hazard
    hazard_text: str
    limits_text: str
    sources: list[SourceRef] = Field(default_factory=list)


class BodyFunctionsFile(BaseModel):
    """data/texts/body_functions.json — exact 4 intrări, câte una pe pilon."""
    pillars: list[BodyFunction]

    @model_validator(mode="after")
    def _all_four(self) -> BodyFunctionsFile:
        got = sorted(p.pillar.value for p in self.pillars)
        if got != sorted(x.value for x in Pillar):
            raise ValueError(f"trebuie exact câte o intrare pe pilon; am găsit {got}")
        return self


# --------------------------------------------------------------------------- catalog/recommendations.json


class CatalogEntry(Recommendation):
    """O recomandare din catalog. Câmpurile din Recommendation ajung la frontend; `steps` și `recheck_days`
    le folosește backend-ul ca să construiască planul alertei."""
    steps: list[str] | None = Field(default=None, description="Pașii planului (2–4). Lipsă = backend-ul împarte `action` în propoziții.")
    recheck_days: int = Field(default=2, ge=1, le=3, description="După câte zile se reverifică alerta.")
    note: str | None = None


class CatalogFile(BaseModel):
    """data/catalog/recommendations.json."""
    recommendations: list[CatalogEntry]

    @model_validator(mode="after")
    def _ids(self) -> CatalogFile:
        ids = [r.id for r in self.recommendations]
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            raise ValueError(f"id-uri duplicate: {sorted(dup)}")
        for r in self.recommendations:
            topic, level, _ = r.id.rsplit("-", 2)
            if topic != r.topic.value or int(level) != r.level:
                raise ValueError(f"{r.id}: id-ul trebuie să fie <topic>-<nivel>-<nr>")
        return self

    def by_id(self) -> dict[str, CatalogEntry]:
        return {r.id: r for r in self.recommendations}

    def first(self, topic: AlertTopic, level: int) -> CatalogEntry:
        return next(r for r in self.recommendations if r.topic == topic and r.level == level)


# --------------------------------------------------------------------------- scenario/scenario.json


ScenarioKind = Literal["poor_sleep", "skipped_exercise", "infection_onset", "keystroke_slowdown",
                       "solar_storm", "cardio_deconditioning"]


class ScenarioEvent(BaseModel):
    days: tuple[int, int] = Field(description="Prima și ultima zi, inclusiv.")
    crew: Literal["all"] | list[str] | str = Field(description="`all`, un crew_id sau o listă.")
    kind: ScenarioKind
    params: dict[str, Any] = Field(default_factory=dict, description="Mărimea efectului, specifică fiecărui `kind`.")
    note: str = ""


class ScenarioFile(BaseModel):
    """data/scenario/scenario.json — ce se întâmplă în fiecare zi a misiunii simulate."""
    seed: int
    total_days: int = 140
    start: datetime = Field(description="Ora 00:00 a zilei 1, UTC.")
    start_day: int = Field(default=96, description="Ziua în care pornește ceasul live; zilele de dinainte se generează la pornire.")
    start_time: str = Field(default="07:00", pattern=r"^\d{2}:\d{2}$")
    environment: str = Field(default="mars_transit")
    crew_baselines: dict[str, dict[str, float]] = Field(description="Pe crew_id: normalul personal pe fiecare cheie de metrică.")
    events: list[ScenarioEvent]

    @model_validator(mode="after")
    def _days(self) -> ScenarioFile:
        if not 1 <= self.start_day <= self.total_days:
            raise ValueError("start_day în afara misiunii")
        for e in self.events:
            a, b = e.days
            if not (1 <= a <= b <= self.total_days):
                raise ValueError(f"eveniment {e.kind}: zilele {e.days} în afara misiunii")
            crews = [e.crew] if isinstance(e.crew, str) and e.crew != "all" else (e.crew if isinstance(e.crew, list) else [])
            for c in crews:
                if c not in self.crew_baselines:
                    raise ValueError(f"eveniment {e.kind}: membrul {c} nu are baseline")
        return self


# --------------------------------------------------------------------------- donki/donki_sep_event.json (din research)


class DonkiSep(BaseModel):
    model_config = ConfigDict(extra="allow")
    sepID: str
    eventTime: str
    link: str
    instruments: list[dict[str, Any]]


class DonkiFile(BaseModel):
    """data/donki/donki_sep_event.json — evenimentul real NASA DONKI (11 mai 2024)."""
    model_config = ConfigDict(extra="allow")
    source: str
    chosen_sep: DonkiSep
    linked_cme: list[dict[str, Any]] = Field(default_factory=list)


# --------------------------------------------------------------------------- încărcarea


FILES: dict[str, tuple[str, type[BaseModel]]] = {
    "params": ("parameters.json", ParametersFile),
    "environments": ("environments.json", EnvironmentsFile),
    "checkin": ("texts/checkin_indicators.json", CheckinIndicatorsFile),
    "body": ("texts/body_functions.json", BodyFunctionsFile),
    "catalog": ("catalog/recommendations.json", CatalogFile),
    "scenario": ("scenario/scenario.json", ScenarioFile),
    "donki": ("donki/donki_sep_event.json", DonkiFile),
}


class DataError(RuntimeError):
    pass


class DataBundle(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    params: ParametersFile
    environments: EnvironmentsFile
    checkin: CheckinIndicatorsFile
    body: BodyFunctionsFile
    catalog: CatalogFile
    scenario: ScenarioFile
    donki: DonkiFile


def default_data_dir() -> Path:
    """DATA_DIR din mediu, altfel ../data față de backend/ (adică data/ din rădăcina repo-ului)."""
    env = os.environ.get("DATA_DIR")
    if env:
        p = Path(env)
        return p if p.is_absolute() else (Path(__file__).resolve().parents[1] / p).resolve()
    return Path(__file__).resolve().parents[2] / "data"


def load_all(data_dir: Path | str | None = None) -> DataBundle:
    """Încarcă și validează toate fișierele. Aruncă DataError cu TOATE problemele găsite, nu doar prima."""
    root = Path(data_dir) if data_dir else default_data_dir()
    loaded, problems = {}, []
    for key, (rel, model) in FILES.items():
        path = root / rel
        try:
            loaded[key] = model.model_validate(json.loads(path.read_text(encoding="utf-8")))
        except FileNotFoundError:
            problems.append(f"{rel}: lipsește (căutat în {root})")
        except json.JSONDecodeError as e:
            problems.append(f"{rel}: JSON invalid la rândul {e.lineno}: {e.msg}")
        except ValidationError as e:
            for err in e.errors()[:10]:
                where = ".".join(str(x) for x in err["loc"]) or "(fișier)"
                problems.append(f"{rel}: {where}: {err['msg']}")
    if problems:
        raise DataError("Fișierele din data/ nu respectă contractul:\n  - " + "\n  - ".join(problems))
    bundle = DataBundle(**loaded)
    _cross_checks(bundle)
    return bundle


def _cross_checks(b: DataBundle) -> None:
    problems = []
    for e in b.environments.environments:
        if e.dose_source_param and e.dose_source_param not in b.params.by_id():
            problems.append(f"environments.json: {e.id.value}.dose_source_param = {e.dose_source_param} nu există în parameters.json")
    if b.scenario.environment not in {e.id.value for e in b.environments.environments}:
        problems.append(f"scenario.json: environment = {b.scenario.environment} nu există în environments.json")
    for kind in ("solar_storm",):
        for ev in b.scenario.events:
            if ev.kind == kind and ev.params.get("event_id") not in (None, b.donki.chosen_sep.sepID):
                problems.append(f"scenario.json: furtuna folosește {ev.params.get('event_id')}, dar fișierul DONKI are {b.donki.chosen_sep.sepID}")
    if problems:
        raise DataError("Fișierele din data/ nu se potrivesc între ele:\n  - " + "\n  - ".join(problems))
