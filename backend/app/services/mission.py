from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clock import clock
from ..datafiles import DataBundle, EnvironmentEntry
from ..db.models.link import Packet
from ..db.models.sim import SimState
from ..deps import ApiError
from ..schemas import EnvironmentId, EnvironmentInfo, LinkStatus, MissionState
from .events import Event

MISSION_NAME = "SHADOW-1"
ENV_KEY = "environment"
_ENV_FIELDS = set(EnvironmentInfo.model_fields)


def environment_info(entry: EnvironmentEntry) -> EnvironmentInfo:
    return EnvironmentInfo(**entry.model_dump(include=_ENV_FIELDS))


def environments(data: DataBundle) -> list[EnvironmentInfo]:
    return [environment_info(e) for e in data.environments.environments]


def _entry(data: DataBundle, env_id: str) -> EnvironmentEntry:
    return next(e for e in data.environments.environments if e.id.value == env_id)


async def init_environment(session: AsyncSession, data: DataBundle) -> None:
    if await session.get(SimState, ENV_KEY) is None:
        session.add(SimState(key=ENV_KEY, value={"id": data.environments.default}))
        await session.flush()


async def current_environment_id(session: AsyncSession, data: DataBundle) -> str:
    row = await session.get(SimState, ENV_KEY)
    return row.value["id"] if row else data.environments.default


async def _queued(session: AsyncSession, direction: str) -> int:
    stmt = select(func.count()).select_from(Packet).where(Packet.direction == direction, Packet.status == "queued")
    return await session.scalar(stmt) or 0


async def state(session: AsyncSession, data: DataBundle) -> MissionState:
    env = _entry(data, await current_environment_id(session, data))
    link = LinkStatus(
        environment=env.id,
        one_way_delay_s=env.one_way_delay_s,
        one_way_delay_real_s=round(clock.real_seconds(env.one_way_delay_s), 2),
        window_open=True,
        window_closes_at=None,
        next_window_at=None,
        queued_down=await _queued(session, "down"),
        queued_up=await _queued(session, "up"),
    )
    return MissionState(
        name=MISSION_NAME,
        sim_now=clock.now(),
        mission_day=clock.mission_day(),
        total_days=data.scenario.total_days,
        time_scale=clock.scale,
        environment=environment_info(env),
        link=link,
    )


async def set_environment(
    session: AsyncSession, data: DataBundle, env_id: EnvironmentId
) -> tuple[MissionState, list[Event]]:
    row = await session.get(SimState, ENV_KEY)
    if row is None:
        session.add(SimState(key=ENV_KEY, value={"id": env_id.value}))
    else:
        row.value = {"id": env_id.value}
    await session.commit()
    new_state = await state(session, data)
    return new_state, [Event("environment.changed", new_state)]


async def set_clock(
    session: AsyncSession, data: DataBundle, *, time_scale: float | None, mission_day: int | None
) -> MissionState:
    current = clock.mission_day()
    total = data.scenario.total_days
    if mission_day is not None and mission_day < current:
        raise ApiError(
            409,
            "invalid_state",
            f"The clock cannot go backwards (current day: {current}). Use /sim/reset.",
        )
    if mission_day is not None and mission_day > total:
        raise ApiError(
            422,
            "validation_error",
            f"The mission has {total} days.",
            {"fields": [{"field": "mission_day", "problem": "after the end of the mission"}]},
        )
    if time_scale is not None:
        clock.set_scale(time_scale)
    if mission_day is not None and mission_day > current:
        clock.jump_to_day(mission_day, data.scenario.start_time)
    return await state(session, data)


async def mission_ticker() -> None:
    raise NotImplementedError("T22")
