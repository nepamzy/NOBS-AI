from fastapi import APIRouter

from app.schemas.payment import TokenPackageRead
from services.payments.packages import TOKEN_PACKAGES

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/packages", response_model=list[TokenPackageRead])
def list_packages() -> list[TokenPackageRead]:
    """Display only — prices are placeholders (see services/payments/packages.py).
    No checkout is wired here; buying a package isn't possible yet."""
    return [
        TokenPackageRead(id=p.id, name=p.name, tokens=p.tokens, price_usd=p.price_usd)
        for p in TOKEN_PACKAGES
    ]
