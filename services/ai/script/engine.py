"""Script engine: Research (optional) + Topic -> structured, scene-by-scene
script (CLAUDE.md Part 3). Every scene carries narration, visual_prompt,
duration, and transition — never a flat text blob.

Same gate as the research engine: no LLM call happens without a configured
provider and Nobert's approval. Only "anthropic" is actually implemented.
"""

from dataclasses import dataclass, field

from pydantic import BaseModel

from services.ai.research.engine import ResearchResult
from services.common.errors import ApprovalRequiredError, CostWarning, EngineNotConfiguredError

_MAX_OUTPUT_TOKENS = 4096


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


class _SceneModel(BaseModel):
    order: int
    narration: str
    visual_prompt: str
    duration_seconds: int
    transition: str


class _ScriptDraftModel(BaseModel):
    title: str
    hook: str
    estimated_duration_seconds: int
    word_count: int
    scenes: list[_SceneModel]


class _SceneRegenerateModel(BaseModel):
    narration: str
    visual_prompt: str


def _require_configured(llm_provider: str, llm_api_key: str) -> None:
    if llm_provider and llm_api_key and llm_provider != "anthropic":
        raise EngineNotConfiguredError(
            f"LLM_PROVIDER={llm_provider!r} is not implemented — only "
            "'anthropic' is wired up so far."
        )


class ScriptEngine:
    def __init__(self, llm_provider: str, llm_api_key: str, llm_model: str = "claude-opus-5"):
        self._llm_provider = llm_provider
        self._llm_api_key = llm_api_key
        self._llm_model = llm_model

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
                    service="Anthropic API (unconfigured)",
                    expected_cost="COST UNKNOWN — no LLM_PROVIDER/LLM_API_KEY set",
                    billing_type="per token",
                    max_expected_cost="A full script (~15-25 scenes) is "
                    "several thousand output tokens — under $0.50 at "
                    "current Claude pricing for most models, re-verify "
                    "before relying on this figure",
                    risk="Low",
                    why_needed="Script stage requires an LLM call to turn the "
                    "topic (and research, if enabled) into scene-structured "
                    "narration + visual prompts.",
                )
            )
        _require_configured(self._llm_provider, self._llm_api_key)

        import anthropic

        client = anthropic.Anthropic(api_key=self._llm_api_key)
        research_context = ""
        if research is not None:
            research_context = (
                "\n\nUse this research:\n"
                f"Key facts: {research.key_facts}\n"
                f"Statistics: {research.statistics}\n"
                f"Interesting findings: {research.interesting_findings}\n"
                f"Story opportunities: {research.story_opportunities}"
            )
        response = client.messages.parse(
            model=self._llm_model,
            max_tokens=_MAX_OUTPUT_TOKENS,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Write a YouTube video script for topic: {topic!r}, "
                        f"targeting about {target_duration_seconds} seconds "
                        "of narration. Break it into numbered scenes, each "
                        "5-12 seconds of narration with its own visual_prompt "
                        "(a text-to-video generation prompt describing what "
                        "should appear on screen) and a transition "
                        "('cut', 'fade', or 'dissolve')." + research_context
                    ),
                }
            ],
            output_format=_ScriptDraftModel,
        )
        parsed = response.parsed_output
        return ScriptDraft(
            title=parsed.title,
            hook=parsed.hook,
            estimated_duration_seconds=parsed.estimated_duration_seconds,
            word_count=parsed.word_count,
            scenes=[
                SceneDraft(
                    order=s.order,
                    narration=s.narration,
                    visual_prompt=s.visual_prompt,
                    duration_seconds=s.duration_seconds,
                    transition=s.transition,
                )
                for s in parsed.scenes
            ],
        )

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
                    service="Anthropic API (unconfigured)",
                    expected_cost="COST UNKNOWN — no LLM_PROVIDER/LLM_API_KEY set",
                    billing_type="per token",
                    max_expected_cost="A single scene rewrite is a few "
                    "hundred tokens — a fraction of a cent at current "
                    "Claude pricing, re-verify before relying on this figure",
                    risk="Low",
                    why_needed="Regenerating a scene requires an LLM call to "
                    "rewrite its narration and visual prompt.",
                )
            )
        _require_configured(self._llm_provider, self._llm_api_key)

        import anthropic

        client = anthropic.Anthropic(api_key=self._llm_api_key)
        instruction_note = f" Instructions: {instructions}" if instructions else ""
        response = client.messages.parse(
            model=self._llm_model,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"For a YouTube video about {topic!r}, rewrite scene "
                        f"{scene.order} (currently narration={scene.narration!r}, "
                        f"visual_prompt={scene.visual_prompt!r}, "
                        f"~{scene.duration_seconds}s).{instruction_note} Keep "
                        "it roughly the same length."
                    ),
                }
            ],
            output_format=_SceneRegenerateModel,
        )
        parsed = response.parsed_output
        return SceneDraft(
            order=scene.order,
            narration=parsed.narration,
            visual_prompt=parsed.visual_prompt,
            duration_seconds=scene.duration_seconds,
            transition=scene.transition,
        )
