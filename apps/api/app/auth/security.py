"""Password hashing, session tokens, and PIN codes. Stdlib-only (hashlib +
secrets) — no new dependency for something this security-sensitive; PBKDF2
via hashlib is a well-understood, NIST-approved KDF.

Session tokens and PIN codes are both high-entropy values *we* generate
(never a user-chosen secret), so they're hashed with a fast keyed hash
(HMAC-SHA256, peppered with SECRET_KEY) for exact-match lookup rather than a
slow KDF — resistance comes from their entropy, not the hash's cost. Only
passwords (user-chosen, low-entropy-prone) get the slow PBKDF2 treatment.
"""

import hashlib
import hmac
import secrets

from app.config import settings

_PBKDF2_ITERATIONS = 260_000  # matches Django's current default


def _require_secret_key() -> str:
    if not settings.secret_key:
        raise RuntimeError(
            "SECRET_KEY is not set — required for auth (session tokens, PIN "
            "hashing). Set it in .env before using signup/login."
        )
    return settings.secret_key


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations_str, salt_hex, digest_hex = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, AttributeError):
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations_str))
    return hmac.compare_digest(candidate, expected)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def generate_pin_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_lookup_value(value: str) -> str:
    """Deterministic, peppered hash for exact-match lookup of a session
    token or PIN code — never used for passwords."""
    key = _require_secret_key().encode()
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()
