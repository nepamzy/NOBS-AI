"""Signs/verifies the OAuth "state" param for the public waitlist sign-in
(app/routers/waitlist_oauth.py) — stdlib-only HMAC, same style as
app/auth/security.py, rather than a server-side session store or a new
dependency for something this small. Guards against a forged callback
(CSRF on the OAuth redirect), not against anything account-sensitive —
this flow only ever reads a verified email for lead capture."""

import base64
import hashlib
import hmac
import time

from app.config import settings

_STATE_TTL_SECONDS = 600  # 10 minutes is plenty to click through Google's consent screen


def _require_secret_key() -> str:
    if not settings.secret_key:
        raise RuntimeError("SECRET_KEY is not set — required to sign OAuth state.")
    return settings.secret_key


def _signature(payload: str) -> str:
    digest = hmac.new(_require_secret_key().encode(), payload.encode(), hashlib.sha256)
    return digest.hexdigest()[:16]


def sign_oauth_state(provider: str) -> str:
    expiry = int(time.time()) + _STATE_TTL_SECONDS
    payload = f"{provider}:{expiry}"
    return base64.urlsafe_b64encode(f"{payload}:{_signature(payload)}".encode()).decode()


def verify_oauth_state(state: str, expected_provider: str) -> bool:
    try:
        decoded = base64.urlsafe_b64decode(state.encode()).decode()
        provider, expiry_str, signature = decoded.rsplit(":", 2)
    except (ValueError, UnicodeDecodeError):
        return False
    if provider != expected_provider or int(expiry_str) < time.time():
        return False
    return hmac.compare_digest(signature, _signature(f"{provider}:{expiry_str}"))
