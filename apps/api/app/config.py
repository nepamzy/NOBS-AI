from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central app config. Values come from environment / .env — never hardcode secrets."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://nobs:nobs@localhost:5432/nobs_ai"
    redis_url: str = "redis://localhost:6379/0"

    storage_backend: str = "local"
    local_storage_root: str = "./storage/local"

    llm_provider: str = ""
    llm_api_key: str = ""

    runpod_api_key: str = ""
    wan_endpoint_id: str = ""

    chatterbox_api_url: str = ""


settings = Settings()
