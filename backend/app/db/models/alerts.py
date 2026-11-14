"""Alertele, pașii planului și istoricul lor.

Regula: cel mult O alertă deschisă (state != resolved) pe (crew_id, topic); o constatare nouă o actualizează.
Relațiile au lazy="raise": încărcați-le explicit cu selectinload(Alert.steps), selectinload(Alert.history).
"""
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base, UTCDateTime


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (Index("ix_alert_crew_topic_state", "crew_id", "topic", "state"),)
    id: Mapped[str] = mapped_column(String(16), primary_key=True)        # "al-1042"
    crew_id: Mapped[str] = mapped_column(ForeignKey("crew.id"))
    topic: Mapped[str] = mapped_column(String(20))                       # AlertTopic
    level: Mapped[int] = mapped_column(Integer)                          # 1 | 2 | 3
    status: Mapped[str] = mapped_column(String(8))                       # watch | alert
    state: Mapped[str] = mapped_column(String(14))                       # active | acknowledged | escalated | resolved
    title: Mapped[str] = mapped_column(String(160))
    explanation: Mapped[str] = mapped_column(Text)
    cause: Mapped[str] = mapped_column(String(14), default="unknown")    # individual | environmental | unknown
    cause_explanation: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)   # listă de Evidence
    recommendation_id: Mapped[str] = mapped_column(String(32))           # din data/catalog/recommendations.json
    recheck_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    packet_id: Mapped[str | None] = mapped_column(String(16), nullable=True)
    earth_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
    mission_day: Mapped[int] = mapped_column(Integer)

    steps: Mapped[list["PlanStep"]] = relationship(back_populates="alert", lazy="raise", cascade="all, delete-orphan",
                                                   order_by="PlanStep.position")
    history: Mapped[list["AlertHistory"]] = relationship(back_populates="alert", lazy="raise", cascade="all, delete-orphan",
                                                         order_by="AlertHistory.id")


class PlanStep(Base):
    """Un pas din planul alertei. `step_id` ("st-1") e unic doar în alerta lui (așa apare în contract)."""

    __tablename__ = "plan_steps"
    __table_args__ = (UniqueConstraint("alert_id", "step_id", name="uq_step_in_alert"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(ForeignKey("alerts.id", ondelete="CASCADE"))
    step_id: Mapped[str] = mapped_column(String(8))
    position: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    done_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    alert: Mapped[Alert] = relationship(back_populates="steps", lazy="raise")


class AlertHistory(Base):
    __tablename__ = "alert_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(ForeignKey("alerts.id", ondelete="CASCADE"), index=True)
    at: Mapped[datetime] = mapped_column(UTCDateTime)
    actor: Mapped[str] = mapped_column(String(80))                       # display_name sau "SHADOW"
    role: Mapped[str | None] = mapped_column(String(12), nullable=True)
    action: Mapped[str] = mapped_column(String(16))                      # created | acknowledged | step_done | escalated | packet_sent | earth_replied | rechecked | resolved
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    alert: Mapped[Alert] = relationship(back_populates="history", lazy="raise")
