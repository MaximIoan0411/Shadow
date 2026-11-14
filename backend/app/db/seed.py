"""Seed-ul de la pornire. TASK T06 (echipaj + conturi) și T11 (istoricul).

ATENȚIE: fără relații ORM între tabele, ordinea inserărilor în același flush NU e garantată. Inserați echipajul,
faceți `await session.flush()`, apoi restul.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from ..datafiles import DataBundle


async def seed_crew_and_users(session: AsyncSession, users_json_path: str) -> None:
    """Citește backend/seed/users.json; creează crew (4) și users (5). Parolele prin
    `await asyncio.to_thread(passwords.hash, test_password)`. Nu salvează niciodată parola în clar."""
    raise NotImplementedError("T06")


async def seed_history(session: AsyncSession, data: DataBundle, until_day: int) -> None:
    """Zilele 1..until_day din simulator/scenario.py → measurements, checkins, exercise_sessions (+ radiation_readings
    pentru ultimele 48 h). Generarea în memorie (asyncio.to_thread), apoi session.add_all(...)."""
    raise NotImplementedError("T11")
