"""Parolele: în baza de date stă doar hash-ul. Fiecare astronaut are parola lui.

ATENȚIE, backend: ambele funcții sunt LENTE intenționat. Din cod asincron se apelează cu
`await asyncio.to_thread(passwords.verify, parola, hash_salvat)`.
"""
import base64
import hashlib
import hmac
import os

PROVIZORIU: tuple[str, ...] = ('hash', 'verify')
"""Funcțiile al căror corp e încă provizoriu. Echipa de securitate scoate numele pe măsură ce le termină."""

# PROVIZORIU: scrypt din biblioteca standard. Securitatea îl înlocuiește cu argon2id (pachetul argon2-cffi);
# formatul șirului întors se schimbă, dar semnăturile rămân.
_N, _R, _P = 2**14, 8, 1


def hash(password: str) -> str:  # noqa: A001 - numele face parte din contract
    """Întoarce hash-ul parolei, cu sare aleatoare inclusă, gata de salvat în `users.password_hash`."""
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def verify(password: str, stored: str) -> bool:
    """True dacă parola corespunde hash-ului. Durează la fel indiferent unde diferă (comparare în timp constant)."""
    try:
        _, salt_b64, dk_b64 = stored.split("$")
    except ValueError:
        return False
    dk = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt_b64), n=_N, r=_R, p=_P)
    return hmac.compare_digest(dk, base64.b64decode(dk_b64))


DUMMY_HASH = hash("parola-inexistenta")
"""Pentru utilizatori inexistenți: backend-ul verifică totuși o parolă, ca răspunsul să dureze la fel."""
