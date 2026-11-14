"""Generate every key the security code needs. The keys never go into git (security/keys/* is ignored).

    python security/keys/generate_keys.py           # creates the keys that are missing
    python security/keys/generate_keys.py --env     # also prints the link key line for the backend .env
    python security/keys/generate_keys.py --force   # replaces ALL keys (old tokens and stored records stop working)

| File                         | Type     | Used for                                |
| auth.pem                     | Ed25519  | signs the login tokens                  |
| ship.pem, earth.pem          | Ed25519  | sign the ship <-> Earth packets         |
| sensor-*.pem                 | Ed25519  | sign the measurements                   |
| storage.key                  | AES-256  | encrypts the records in the database    |
| earthlink.key                | AES-256  | encrypts the ship <-> Earth packets     |
"""
import argparse
import base64
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# SHADOW_KEYS_DIR lets the tests use throwaway keys instead of the real ones
KEYS_DIR = Path(os.environ.get("SHADOW_KEYS_DIR") or Path(__file__).resolve().parent / "keys_files")

SIGNING_KEYS = ["auth", "ship", "earth", "sensor-keyboard", "sensor-checkin", "sensor-sim"]
AES_KEYS = ["storage", "earthlink"]
LINK_KEY = "earthlink"


def write_secret(path, data):
    """Write a private file that only the owner can read (0600)."""
    path.unlink(missing_ok=True)
    handle = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(handle, "wb") as f:
        f.write(data)


def generate(keys_dir=KEYS_DIR, force=False):
    """Create the missing keys (all of them with force). Returns the names of the keys it created."""
    private_dir, public_dir = keys_dir / "private", keys_dir / "public"
    private_dir.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(private_dir, 0o700)
    created = []

    for name in SIGNING_KEYS:
        private_path, public_path = private_dir / f"{name}.pem", public_dir / f"{name}.pem"
        if private_path.exists() and public_path.exists() and not force:
            continue
        key = Ed25519PrivateKey.generate()
        write_secret(private_path, key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        public_path.write_bytes(key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
        created.append(name)

    for name in AES_KEYS:
        path = private_dir / f"{name}.key"
        if path.exists() and not force:
            continue
        write_secret(path, os.urandom(32))
        created.append(name)

    return created


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate the SHADOW keys.")
    parser.add_argument("--force", action="store_true", help="replace the keys that already exist")
    parser.add_argument("--env", action="store_true", help="print the link key line for the backend .env")
    args = parser.parse_args()

    created = generate(force=args.force)
    print("Keys folder:", KEYS_DIR)
    print("Created:", ", ".join(created) if created else "nothing (all keys already exist)")
    if args.env:
        link_key = (KEYS_DIR / "private" / f"{LINK_KEY}.key").read_bytes()
        print("\nPut this in .env (never in git):")
        print("LINK_AES_KEY_B64=" + base64.b64encode(link_key).decode())
