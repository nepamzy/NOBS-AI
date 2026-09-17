"""Shared engine constructors for anything outside the pipeline job (e.g. a
router doing a one-off scene regeneration) that needs the same
config-gated engines the worker uses."""

from app.config import settings
from services.ai.script.engine import ScriptEngine


def get_script_engine() -> ScriptEngine:
    return ScriptEngine(settings.llm_provider, settings.llm_api_key, settings.llm_model)
