from pydantic import BaseModel


class TokenPackageRead(BaseModel):
    id: str
    name: str
    tokens: int
    price_usd: float
