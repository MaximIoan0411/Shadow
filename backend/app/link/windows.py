from datetime import datetime


def window_open(at: datetime, environment_id: str) -> bool:
    """Prototype: the communication window is always open (solar conjunction is not simulated)."""
    return True


def one_way_delay_s(environment_id: str, environments: dict[str, float]) -> float:
    """One-way delay in mission seconds, from data/environments.json (`environments` = id → one_way_delay_s)."""
    return float(environments[environment_id])
