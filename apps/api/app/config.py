from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central app config. Values come from environment / .env — never hardcode secrets."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://nobs:nobs@localhost:5432/nobs_ai"
    redis_url: str = "redis://localhost:6379/0"

    # "local" (default, free, but doesn't survive a redeploy on ephemeral
    # disk) or "supabase" (uploads finished artifacts to Supabase Storage —
    # see services/storage). Everything still generates to local disk first
    # either way; this only controls where the FINISHED artifact ends up.
    storage_backend: str = "local"
    local_storage_root: str = "./storage/local"
    # Folder Nobert drops downloaded YouTube Audio Library tracks into —
    # there's no public API to pull them automatically (see chat history).
    # Empty/missing folder just means videos assemble without music.
    music_library_path: str = "./storage/music"

    # --- Supabase Storage (storage_backend=supabase) ---
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    # Must already exist and be public (Storage -> New bucket -> Public
    # bucket, in the Supabase dashboard) — this doesn't create it.
    supabase_storage_bucket: str = "nobs-ai"

    cors_origins: str = "http://localhost:5173"

    # Only "anthropic" is actually implemented (services/ai/*/engine.py) —
    # any other value falls through to the same ApprovalRequiredError as
    # leaving it unset. Model defaults to claude-opus-5; override with a
    # cheaper model (e.g. claude-sonnet-5, claude-haiku-4-5) to cut cost —
    # see chat history for the per-model price comparison.
    llm_provider: str = ""
    llm_api_key: str = ""
    llm_model: str = "claude-opus-5"

    runpod_api_key: str = ""
    wan_endpoint_id: str = ""

    # "chatterbox" (default — self-hosted, free per-call but needs an
    # already-running server, so it bills for uptime not usage) or
    # "elevenlabs" (managed, usage-based, no idle cost — see
    # services/voice/elevenlabs).
    voice_provider: str = "chatterbox"
    chatterbox_api_url: str = ""
    elevenlabs_api_key: str = ""
    # JSON object mapping our voice_preset ids (services/voice/catalog.py)
    # to real ElevenLabs voice_ids, e.g. {"warm-narrator": "<voice_id>"}.
    # Only used when voice_provider=elevenlabs.
    elevenlabs_voice_map: str = "{}"

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
