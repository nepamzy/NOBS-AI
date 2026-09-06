from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central app config. Values come from environment / .env — never hardcode secrets."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://nobs:nobs@localhost:5432/nobs_ai"
    redis_url: str = "redis://localhost:6379/0"

    storage_backend: str = "local"
    local_storage_root: str = "./storage/local"

    cors_origins: str = "http://localhost:5173"

    llm_provider: str = ""
    llm_api_key: str = ""

    runpod_api_key: str = ""
    wan_endpoint_id: str = ""

    chatterbox_api_url: str = ""

    # --- Auth ---
    # Peppers PIN-code and session-token hashes so a stolen DB dump alone
    # doesn't reveal valid codes/tokens. Must be set for auth to work at all
    # (see app/bootstrap.py) — no insecure default.
    secret_key: str = ""
    # Bootstraps the one ADMIN account on first startup (see app/bootstrap.py).
    # Only used when no ADMIN user exists yet; ignored after that.
    admin_email: str = ""
    admin_password: str = ""


settings = Settings()
