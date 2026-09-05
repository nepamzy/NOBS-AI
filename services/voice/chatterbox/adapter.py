"""Chatterbox adapter (MIT license, self-hosted, OpenAI-compatible API —
see CLAUDE.md Part 4). Self-hosting Chatterbox itself is free, but running
it means a server (local GPU/CPU or a rented one) must already exist, and
starting *paid* compute for it is gated by CLAUDE.md Part 1 just like Wan.

This adapter makes no network call until CHATTERBOX_API_URL points at a
server Nobert has actually started and approved.
"""

from services.common.errors import ApprovalRequiredError, CostWarning
from services.voice.engine import VoiceEngine, VoiceoverResult


class ChatterboxEngine(VoiceEngine):
    def __init__(self, api_url: str):
        self._api_url = api_url

    def synthesize(self, text: str, voice_preset: str, output_path: str) -> VoiceoverResult:
        if not self._api_url:
            raise ApprovalRequiredError(
                CostWarning(
                    action="Synthesize voiceover via Chatterbox",
                    service="Chatterbox (self-hosted)",
                    expected_cost="Free if self-hosted on already-running "
                    "hardware; COST UNKNOWN if it requires renting a GPU",
                    billing_type="unknown",
                    max_expected_cost="Unknown until a Chatterbox server is running",
                    risk="Unknown",
                    why_needed="No CHATTERBOX_API_URL is configured — a "
                    "Chatterbox server must be started (locally or rented) "
                    "and approved before voice synthesis can run.",
                )
            )
        # Real call to the self-hosted OpenAI-compatible endpoint goes here.
        raise NotImplementedError("Chatterbox HTTP call not yet implemented")
