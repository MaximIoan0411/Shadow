"""Parolele: în baza de date stă doar hash-ul. Fiecare astronaut are parola lui.

ATENȚIE, backend: ambele funcții sunt LENTE intenționat. Din cod asincron se apelează cu
`await asyncio.to_thread(passwords.verify, parola, hash_salvat)`.
"""
from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error, InvalidHashError

PROVIZORIU: tuple[str, ...] = ()
"""Funcțiile al căror corp e încă provizoriu. Echipa de securitate scoate numele pe măsură ce le termină."""

MAX_PASSWORD_CHARS = 256
"""O parolă mai lungă e refuzată înainte de hash, ca nimeni să nu țină serverul ocupat cu megabytes de text."""

# argon2id, cu parametrii recomandați de bibliotecă (RFC 9106): 64 MiB, 3 treceri, 4 fire
_hasher = PasswordHasher()


def hash(password: str) -> str:  # noqa: A001 - numele face parte din contract
    """Întoarce hash-ul parolei, cu sare aleatoare inclusă, gata de salvat în `users.password_hash`."""
    return _hasher.hash(password)


def verify(password: str, stored: str) -> bool:
    """True dacă parola corespunde hash-ului. Durează la fel indiferent unde diferă (comparare în timp constant)."""
    if len(password) > MAX_PASSWORD_CHARS:
        return False
    try:
        return _hasher.verify(stored, password)
    except (Argon2Error, InvalidHashError):
        return False


DUMMY_HASH = hash("parola-inexistenta")
"""Pentru utilizatori inexistenți: backend-ul verifică totuși o parolă, ca răspunsul să dureze la fel."""
