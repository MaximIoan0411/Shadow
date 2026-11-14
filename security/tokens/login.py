import hashlib
import hmac
import os
import time

from tokens import create_token


TEST_ACCOUNTS = {
    "comandant":   ("cm1-shadow",   "astronaut"),
    "specialist2": ("cm2-shadow",   "astronaut"),
    "medic":       ("cm3-shadow",   "medical_officer"),
    "inginer":     ("cm4-shadow",   "astronaut"),
    "earth":       ("earth-shadow", "earth"),
}

# the lock rule is fixed in contract/security: 5 wrong passwords in 5 minutes -> locked for 60 seconds
MAX_TRIES = 5
WINDOW = 5 * 60
LOCK_TIME = 60
MAX_TRACKED = 10_000   # how many usernames we remember wrong tries for, at most

ITERATIONS = 600_000   # PBKDF2-HMAC-SHA256, the OWASP minimum


def hash_password(password, salt=None):
    """Turn a password into a salted hash. We store this, never the password."""
    if salt is None:
        salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return salt.hex() + "$" + digest.hex()


def password_ok(password, stored):
    """Check a typed password against the stored hash."""
    salt_hex, hash_hex = stored.split("$")
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                 bytes.fromhex(salt_hex), ITERATIONS)
    return hmac.compare_digest(digest.hex(), hash_hex)


USERS = {name: {"hash": hash_password(pw), "role": role}
         for name, (pw, role) in TEST_ACCOUNTS.items()}

# an unknown username is checked against this hash, so the answer takes as long as for a real account
DUMMY_HASH = hash_password(os.urandom(16).hex())

failed = {}         # username -> the moments of the recent wrong tries
locked_until = {}   # username -> the moment the lock ends


def record_failure(username, now):
    tries = [moment for moment in failed.get(username, []) if now - moment < WINDOW] + [now]
    failed[username] = tries
    if len(tries) >= MAX_TRIES:
        locked_until[username] = now + LOCK_TIME
        del failed[username]
    if len(failed) + len(locked_until) > MAX_TRACKED:
        forget_old(now)


def forget_old(now):
    """Drop the usernames whose wrong tries or locks have expired, so made-up names cannot fill the memory."""
    for name in [name for name, tries in failed.items() if now - tries[-1] >= WINDOW]:
        del failed[name]
    for name in [name for name, until in locked_until.items() if until <= now]:
        del locked_until[name]
    # still too many (a flood of new names): drop the oldest wrong-try counters, never a lock
    while failed and len(failed) + len(locked_until) > MAX_TRACKED:
        del failed[next(iter(failed))]


def login(username, password):
    now = time.monotonic()
    if now < locked_until.get(username, 0):
        raise PermissionError("Account locked. Try again in a minute.")

    user = USERS.get(username)
    correct = password_ok(password, user["hash"] if user else DUMMY_HASH)
    if user is None or not correct:
        record_failure(username, now)
        raise PermissionError("Wrong username or password.")

    failed.pop(username, None)
    locked_until.pop(username, None)
    return create_token(username, user["role"])


if __name__ == "__main__":
    token = login("medic", "cm3-shadow")
    print("medic logged in. Token starts with:", token[:40], "...")
