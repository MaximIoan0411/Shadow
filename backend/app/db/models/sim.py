"""Starea simulatorului și contoarele, ca perechi cheie → valoare JSON.

Chei folosite:
  id:<prefix>        ultimul număr dat pentru id-urile cu acel prefix (app/ids.py)        ex. {"n": 1042}
  seq:<direction>    ultimul seq pe direcție (down / up)                                    ex. {"n": 7}
  storm              furtuna activă: {"event_id", "onset_at", "sheltered_since", "onboard_alert_at", ...}
  environment        mediul curent: {"id": "mars_transit"}
"""
from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class SimState(Base):
    __tablename__ = "sim_state"
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSON)
