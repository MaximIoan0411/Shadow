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

MAX_TRIES = 5          
LOCK_TIME = 3 * 60     


def hash_password(password, salt=None):
    """Turn a password into a salted hash. We store this, never the password."""
    if salt is None:
        salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200_000)
    return salt.hex() + "$" + digest.hex()


def password_ok(password, stored):
    """Check a typed password against the stored hash."""
    salt_hex, hash_hex = stored.split("$")
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(),
                                 bytes.fromhex(salt_hex), 200_000)
    return hmac.compare_digest(digest.hex(), hash_hex)


USERS = {name: {"hash": hash_password(pw), "role": role}
         for name, (pw, role) in TEST_ACCOUNTS.items()}

failed = {}        
locked_until = {}  


def login(username, password):
    if time.time() < locked_until.get(username, 0):
        raise PermissionError("Account locked. Try again in a few minutes.")

    user = USERS.get(username)
    if user is None or not password_ok(password, user["hash"]):
        failed[username] = failed.get(username, 0) + 1
        if failed[username] >= MAX_TRIES:
            locked_until[username] = time.time() + LOCK_TIME
            failed[username] = 0
        raise PermissionError("Wrong username or password.")

    failed[username] = 0
    return create_token(username, user["role"])


if __name__ == "__main__":
    token = login("medic", "cm3-shadow")
    print("medic logged in. Token starts with:", token[:40], "...")
