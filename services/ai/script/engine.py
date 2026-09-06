"""Script engine: Research (optional) + Topic -> structured, scene-by-scene
script (CLAUDE.md Part 3). Every scene carries narration, visual_prompt,
duration, and transition — never a flat text blob.

Same gate as the research engine: no LLM call happens without a configured
provider and Nobert's approval.
"""

from dataclasses import dataclass, field

from services.ai.research.engine import ResearchResult
from services.common.errors import ApprovalRequiredError, CostWarning


@dataclass
class SceneDraft:
    order: int
    narration: str
    visual_prompt: str
    duration_seconds: int
    transition: str = "cut"


@dataclass
class ScriptDraft:
    title: str
    hook: str
    estimated_duration_seconds: int
    word_count: int
    scenes: list[SceneDraft] = field(default_factory=list)


class ScriptEngine:
    def __init__(self, llm_provider: str, llm_api_key: str):
        self._llm_provider = llm_provider
        self._llm_api_key = llm_api_key

    def generate(
        self,
        topic: str,
        target_duration_seconds: int,
        research: ResearchResult | None = None,
    ) -> ScriptDraft:
        if not self._llm_provider or not self._llm_api_key:
            raise ApprovalRequiredError(
                CostWarning(
                    action=f"Generate script for topic: {topic!r} "
                    f"({target_duration_seconds}s target)",
                    service="LLM provider (unconfigured)",
                    expected_cost="COST UNKNOWN — no LLM_PROVIDER/LLM_API_KEY set",
                    billing_type="per token (assumed)",
                    max_expected_cost="Unknown until provider is chosen",
                    risk="Unknown",
                    why_needed="Script stage requires an LLM call to turn the "
                    "topic (and research, if enabled) into scene-structured "
                    "narration + visual prompts.",
                )
            )
        raise NotImplementedError("LLM-backed script generation not yet implemented")

    def regenerate_scene(
        self,
        topic: str,
        scene: SceneDraft,
        instructions: str = "",
    ) -> SceneDraft:
        """The "Regenerate" action on a single storyboard scene (CLAUDE.md:
        Regenerate / Edit / Approve) — re-runs just that scene's narration +
        visual_prompt through the LLM rather than the whole script. Same gate
        as generate(): no call happens without a configured provider."""
        if not self._llm_provider or not self._llm_api_key:
            raise ApprovalRequiredError(
                CostWarning(
                    action=f"Regenerate scene {scene.order} for topic: {topic!r}",
                    service="LLM provider (unconfigured)",
                    expected_cost="COST UNKNOWN — no LLM_PROVIDER/LLM_API_KEY set",
                    billing_type="per token (assumed)",
                    max_expected_cost="Unknown until provider is chosen",
                    risk="Unknown",
                    why_needed="Regenerating a scene requires an LLM call to "
                    "rewrite its narration and visual prompt.",
                )
            )
        raise NotImplementedError("LLM-backed scene regeneration not yet implemented")
