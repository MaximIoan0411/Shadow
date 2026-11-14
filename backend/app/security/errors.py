"""Excepțiile pe care le aruncă pachetul de securitate. Backend-ul le prinde și le transformă în erori API."""
from typing import Literal


class InvalidToken(Exception):
    """Token lipsă, malformat, expirat, cu alt algoritm decât HS256 sau revocat. Backend: 401 `unauthorized`."""


class AccountLocked(Exception):
    """Prea multe parole greșite pe acest cont. Backend: 429 `too_many_attempts`, cu `retry_after_s` în details."""

    def __init__(self, retry_after_s: int):
        super().__init__(f"cont blocat încă {retry_after_s} s")
        self.retry_after_s = retry_after_s


class SealError(Exception):
    """Un pachet nu poate fi deschis. Backend: pachetul devine `rejected`, cu `reject_reason = reason`.
    Retrimiterea (`replay`) NU o detectează sealing, ci backend-ul (unic pe direcție + seq)."""

    def __init__(self, reason: Literal["bad_signature"]):
        super().__init__(reason)
        self.reason = reason
