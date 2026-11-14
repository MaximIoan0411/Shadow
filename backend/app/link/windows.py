"""Ferestrele de comunicare și întârzierea pe mediu. TASK T24."""
from datetime import datetime


def window_open(at: datetime, environment_id: str) -> bool:
    """Prototip: fereastra e mereu deschisă, în afară de conjuncția solară (mars_*), dacă e simulată."""
    raise NotImplementedError("T24")


def one_way_delay_s(environment_id: str, environments: dict[str, float]) -> float:
    """Întârzierea într-un sens, în secunde de misiune, din data/environments.json."""
    raise NotImplementedError("T24")
