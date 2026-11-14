"""SimClock: SINGURA sursă de timp din aplicație. TASK T02.

Nicăieri în cod nu apare datetime.now(). Timpul misiunii = start_sim + (timp_real_scurs × scale).
Ziua 1 începe la scenario.start (2027-01-10T00:00Z). Misiunea pornește în ziua 96, la 07:00.
"""
from datetime import datetime


class SimClock:
    def start(self, *, mission_start: datetime, day: int, time_hhmm: str, scale: float) -> None:
        """Pornește ceasul la ziua `day`, ora `time_hhmm` ("07:00"), cu viteza `scale`."""
        raise NotImplementedError("T02")

    def now(self) -> datetime:
        """Timpul misiunii, cu tzinfo=UTC."""
        raise NotImplementedError("T02")

    def mission_day(self, at: datetime | None = None) -> int:
        """Ziua misiunii (de la 1) pentru `at` sau pentru acum."""
        raise NotImplementedError("T02")

    def day_start(self, day: int) -> datetime:
        """Ora 00:00 a zilei `day`."""
        raise NotImplementedError("T02")

    @property
    def scale(self) -> float:
        raise NotImplementedError("T02")

    def set_scale(self, scale: float) -> None:
        """Schimbă viteza fără să sară timpul: ora curentă rămâne aceeași."""
        raise NotImplementedError("T02")

    def jump_to_day(self, day: int, time_hhmm: str = "07:00") -> None:
        """Doar înainte (ValueError înapoi). Generarea zilelor lipsă o face services/demo.py (T33)."""
        raise NotImplementedError("T02")

    def real_seconds(self, mission_seconds: float) -> float:
        """Pentru câmpurile *_real_s din contract: mission_seconds / scale."""
        raise NotImplementedError("T02")

    def freeze(self, at: datetime) -> None:
        """Doar pentru teste: ceasul stă pe loc la `at` până la următorul start()."""
        raise NotImplementedError("T02")


clock = SimClock()
