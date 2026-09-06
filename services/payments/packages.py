"""Token package catalog — display only, no real checkout wired yet.

Prices here are GUESSED placeholders (explicitly requested — "let's just
guess all the pricing" — rather than waiting on real Paystack/Flutterwave
API keys or a settled per-video cost floor). Adjust freely; nothing reads
these numbers for billing since no payment provider is connected. Once
real infra costs (Chatterbox + video generation) are settled and a
provider is chosen, these should be revisited against an actual cost
floor rather than left as guesses.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenPackage:
    id: str
    name: str
    tokens: int
    price_usd: float


TOKEN_PACKAGES: list[TokenPackage] = [
    TokenPackage(id="starter", name="Starter", tokens=5, price_usd=5.0),
    TokenPackage(id="creator", name="Creator", tokens=15, price_usd=12.0),
    TokenPackage(id="pro", name="Pro", tokens=40, price_usd=28.0),
]
