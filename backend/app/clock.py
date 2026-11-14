"""SimClock: SINGURA sursă de timp din aplicație. TASK T02.

Nicăieri în cod nu apare datetime.now(). Timpul misiunii = start_sim + (timp_real_scurs × scale).
Ziua 1 începe la scenario.start (2027-01-10T00:00Z). Misiunea pornește în ziua 96, la 07:00.
Timpul real se măsoară cu time.monotonic() (nu sare dacă se schimbă ora sistemului).
"""

import time as _time
from datetime import UTC, datetime, time, timedelta


def _offset(time_hhmm: str) -> timedelta:
    t = time.fromisoformat(time_hhmm)
    return timedelta(hours=t.hour, minutes=t.minute)


def _check_scale(scale: float) -> float:
    if scale <= 0:
        raise ValueError(f"scale must be > 0, got {scale}")
    return float(scale)


class SimClock:
    def __init__(self) -> None:
        self._mission_start: datetime | None = None
        self._real0: float = 0.0
        self._sim0: datetime | None = None
        self._scale: float = 1.0
        self._frozen: datetime | None = None

    def _require_started(self) -> datetime:
        if self._mission_start is None or self._sim0 is None:
            raise RuntimeError("SimClock not started: call clock.start(...) first")
        return self._mission_start

    def start(self, *, mission_start: datetime, day: int, time_hhmm: str, scale: float) -> None:
        """Pornește ceasul la ziua `day`, ora `time_hhmm` ("07:00"), cu viteza `scale`."""
        if mission_start.tzinfo is None:
            raise ValueError("mission_start must be timezone-aware (UTC)")
        self._mission_start = mission_start.astimezone(UTC)
        self._scale = _check_scale(scale)
        self._frozen = None
        self._sim0 = self.day_start(day) + _offset(time_hhmm)
        self._real0 = _time.monotonic()

    def now(self) -> datetime:
        """Timpul misiunii, cu tzinfo=UTC."""
        self._require_started()
        if self._frozen is not None:
            return self._frozen
        return self._sim0 + timedelta(seconds=(_time.monotonic() - self._real0) * self._scale)

    def mission_day(self, at: datetime | None = None) -> int:
        """Ziua misiunii (de la 1) pentru `at` sau pentru acum."""
        start = self._require_started()
        return ((at or self.now()) - start).days + 1

    def day_start(self, day: int) -> datetime:
        """Ora 00:00 a zilei `day`."""
        if self._mission_start is None:  # start() îl cheamă înainte să existe _sim0
            raise RuntimeError("SimClock not started: call clock.start(...) first")
        return self._mission_start + timedelta(days=day - 1)

    @property
    def scale(self) -> float:
        return self._scale

    def set_scale(self, scale: float) -> None:
        """Schimbă viteza fără să sară timpul: ora curentă rămâne aceeași."""
        scale = _check_scale(scale)
        self._sim0 = self.now()
        self._real0 = _time.monotonic()
        self._scale = scale

    def jump_to_day(self, day: int, time_hhmm: str = "07:00") -> None:
        """Doar înainte (ValueError înapoi). Generarea zilelor lipsă o face services/demo.py (T33)."""
        current = self.mission_day()
        if day <= current:
            raise ValueError(f"jump_to_day only moves forward: day {day} <= current day {current}")
        self._sim0 = self.day_start(day) + _offset(time_hhmm)
        self._real0 = _time.monotonic()
        if self._frozen is not None:  # înghețat (teste): rămâne înghețat, dar la noua oră
            self._frozen = self._sim0

    def real_seconds(self, mission_seconds: float) -> float:
        """Pentru câmpurile *_real_s din contract: mission_seconds / scale."""
        return mission_seconds / self._scale

    def freeze(self, at: datetime) -> None:
        """Doar pentru teste: ceasul stă pe loc la `at` până la următorul start()."""
        self._require_started()
        if at.tzinfo is None:
            raise ValueError("freeze(at) needs a timezone-aware datetime (UTC)")
        self._frozen = at.astimezone(UTC)
        self._sim0 = self._frozen
        self._real0 = _time.monotonic()


clock = SimClock()
