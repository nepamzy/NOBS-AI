from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.oauth_state import sign_oauth_state, verify_oauth_state
from app.config import settings
from app.db import get_db
from app.models.waitlist_signup import WaitlistSignup
from services.common.errors import EngineNotConfiguredError
from services.connectors.google_waitlist_oauth.adapter import GoogleWaitlistOAuth, Provider

router = APIRouter(prefix="/waitlist/oauth", tags=["waitlist"])


def _oauth_client(provider: Provider) -> GoogleWaitlistOAuth:
    redirect_uri = f"{settings.api_base_url.rstrip('/')}/waitlist/oauth/{provider}/callback"
    return GoogleWaitlistOAuth(
        client_id=settings.google_waitlist_client_id,
        client_secret=settings.google_waitlist_client_secret,
        redirect_uri=redirect_uri,
    )


def _landing_redirect(path: str) -> RedirectResponse:
    return RedirectResponse(f"{settings.landing_base_url.rstrip('/')}{path}")


@router.get("/{provider}/start")
def start_oauth(provider: Provider) -> RedirectResponse:
    """Public — the waitlist page's "Continue with Google/YouTube" buttons
    navigate the browser here directly (not a fetch), since Google's
    consent screen has to actually load. Falls back to a friendly redirect
    with ?oauth_error=not_configured rather than a raw 402 JSON error in a
    public visitor's browser when GOOGLE_WAITLIST_CLIENT_ID isn't set yet —
    same gating as every other external engine in this app, just a nicer
    failure mode for an unauthenticated page."""
    try:
        client = _oauth_client(provider)
        state = sign_oauth_state(provider)
        return RedirectResponse(client.build_authorize_url(provider, state))
    except EngineNotConfiguredError:
        return _landing_redirect("/waitlist?oauth_error=not_configured")


@router.get("/{provider}/callback")
def oauth_callback(
    provider: Provider,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if error:
        return _landing_redirect("/waitlist?oauth_error=denied")
    if not code or not state or not verify_oauth_state(state, provider):
        return _landing_redirect("/waitlist?oauth_error=failed")

    try:
        identity = _oauth_client(provider).fetch_identity(provider, code)
    except Exception:
        return _landing_redirect("/waitlist?oauth_error=failed")

    email = identity.email.strip().lower()
    existing = db.query(WaitlistSignup).filter(WaitlistSignup.email == email).one_or_none()
    if existing is None:
        signup = WaitlistSignup(
            email=email,
            name=identity.name,
            source=f"{provider}_oauth",
            youtube_channel_title=identity.youtube_channel_title,
        )
        db.add(signup)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()  # lost a race with a concurrent signup for the same email
    elif identity.youtube_channel_title and not existing.youtube_channel_title:
        existing.youtube_channel_title = identity.youtube_channel_title
        db.commit()

    return _landing_redirect("/waitlist?joined=1")
