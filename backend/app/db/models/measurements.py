"""Datele astronauților: măsurători, check-in-uri, tastare, teste de reacție, exerciții, radiații.

Toate datele-oră sunt TIMP DE MISIUNE (clock.now()). Fiecare tabel cu date ale unui om are crew_id + mission_day.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, UTCDateTime


class Measurement(Base):
    """TABEL LUNG: o valoare pe rând. Pulsul de noapte, HRV, temperatura de la senzor, scorurile pe zi
    (landing_readiness, stress_index, loading_score…). metric_key = cheile din contract/api (secțiunea 3)."""

    __tablename__ = "measurements"
    __table_args__ = (Index("ix_meas_crew_metric_day", "crew_id", "metric_key", "mission_day"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crew_id: Mapped[str] = mapped_column(ForeignKey("crew.id"))
    metric_key: Mapped[str] = mapped_column(String(40))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(16))
    measured_at: Mapped[datetime] = mapped_column(UTCDateTime)
    mission_day: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(12))                     # device | manual | simulated
    device_id: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Checkin(Base):
    """Check-in-ul de dimineață. UNUL pe zi de misiune (al doilea îl înlocuiește). Câmpurile respinse sunt NULL,
    iar motivele stau în `rejected` (listă de FieldRejection, ca JSON)."""

    __tablename__ = "checkins"
    __table_args__ = (UniqueConstraint("crew_id", "mission_day", name="uq_checkin_crew_day"),)
    id: Mapped[str] = mapped_column(String(16), primary_key=True)        # "ck-0096"
    crew_id: Mapped[str] = mapped_column(ForeignKey("crew.id"), index=True)
    mission_day: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    mood: Mapped[int] = mapped_column(Integer)                           # 1..5
    systolic_mmhg: Mapped[float | None] = mapped_column(Float, nullable=True)
    diastolic_mmhg: Mapped[float | None] = mapped_column(Float, nullable=True)
    pulse_bpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    glucose_mg_dl: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    meals_eaten: Mapped[str | None] = mapped_column(String(8), nullable=True)   # all | some | none
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(12), default="manual")   # manual | simulated (istoricul)
    rejected: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


class KeystrokeSession(Base):
    """O sesiune de tastare: loturile cu același session_id se ADUNĂ aici. FĂRĂ caractere, doar sume de timpi.
    Acumulatorii (sum, sumsq) permit medii și deviații corecte când vin loturi noi; câmpurile *_mean/*_sd sunt
    recalculate din ei la fiecare lot."""

    __tablename__ = "keystroke_sessions"
    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    crew_id: Mapped[str] = mapped_column(ForeignKey("crew.id"), index=True)
    context: Mapped[str] = mapped_column(String(16))                   # free_typing | checkin_note | ai_chat | demo
    started_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
    mission_day: Mapped[int] = mapped_column(Integer)
    # acumulatori
    n_keys: Mapped[int] = mapped_column(Integer, default=0)
    hold_sum: Mapped[float] = mapped_column(Float, default=0.0)
    hold_sumsq: Mapped[float] = mapped_column(Float, default=0.0)
    flight_n: Mapped[int] = mapped_column(Integer, default=0)
    flight_sum: Mapped[float] = mapped_column(Float, default=0.0)
    flight_sumsq: Mapped[float] = mapped_column(Float, default=0.0)
    backspaces: Mapped[int] = mapped_column(Integer, default=0)
    active_ms: Mapped[float] = mapped_column(Float, default=0.0)       # timp de tastare, fără pauzele > 2 s
    last_down_ms: Mapped[float | None] = mapped_column(Float, nullable=True)   # pentru flight între loturi
    # derivate (KeystrokeFeatures din contract)
    hold_ms_mean: Mapped[float] = mapped_column(Float, default=0.0)
    hold_ms_sd: Mapped[float] = mapped_column(Float, default=0.0)
    flight_ms_mean: Mapped[float] = mapped_column(Float, default=0.0)
    flight_ms_sd: Mapped[float] = mapped_column(Float, default=0.0)
    backspace_rate: Mapped[float] = mapped_column(Float, default=0.0)
    keys_per_min: Mapped[float] = mapped_column(Float, default=0.0)
    fatigue_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(8), default="unknown")
    is_baseline: Mapped[bool] = mapped_column(Boolean, default=False)  # intră în baseline-ul contului


class PvtResult(Base):
    """Un test de reacție PVT-B (3 minute). Primele 2–3 sunt antrenament (is_practice) și nu intră în baseline."""

    __tablename__ = "pvt_results"
    id: Mapped[str] = mapped_column(String(16), primary_key=True)        # "pvt-0031"
    crew_id: Mapped[str] = mapped_column(ForeignKey("crew.id"), index=True)
    at: Mapped[datetime] = mapped_column(UTCDateTime)
    mission_day: Mapped[int] = mapped_column(Integer)
    n_trials: Mapped[int] = mapped_column(Integer)
    mean_rt_ms: Mapped[float] = mapped_column(Float)
    mean_speed: Mapped[float] = mapped_column(Float)                     # media 1/RT, în 1/s
    lapses: Mapped[int] = mapped_column(Integer)                         # RT ≥ 355 ms
    false_starts: Mapped[int] = mapped_column(Integer)
    is_practice: Mapped[bool] = mapped_column(Boolean, default=False)
    baseline_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    deviation_sd: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(8))


class ExerciseSession(Base):
    """O sesiune de exerciții. `sets` = listă de ExerciseSet (exercise, reps, load_kg), ca JSON."""

    __tablename__ = "exercise_sessions"
    __table_args__ = (Index("ix_ex_crew_day", "crew_id", "mission_day"),)
    id: Mapped[str] = mapped_column(String(16), primary_key=True)        # "ex-0211"
    crew_id: Mapped[str] = mapped_column(ForeignKey("crew.id"))
    mission_day: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(12))                        # resistance | aerobic
    started_at: Mapped[datetime] = mapped_column(UTCDateTime)
    duration_min: Mapped[float] = mapped_column(Float)
    sets: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    loading_score: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(12))


class RadiationReading(Base):
    """O citire a dozimetrului de la bord. O singură serie pentru toată nava."""

    __tablename__ = "radiation_readings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    t: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    dose_rate_usv_h: Mapped[float] = mapped_column(Float)
    mean_24h_usv_h: Mapped[float] = mapped_column(Float)
    sheltered: Mapped[bool] = mapped_column(Boolean, default=False)
