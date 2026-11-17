"""Script engine: Research (optional) + Topic -> structured, scene-by-scene
script (CLAUDE.md Part 3). Every scene carries narration, visual_prompt,
duration, and transition — never a flat text blob.

Same gate as the research engine: no LLM call happens without a configured
provider and Nobert's approval. Only "anthropic" is actually implemented.
"""

import math
from dataclasses import dataclass, field

from pydantic import BaseModel

from services.ai.parsing import parsed_or_raise
from services.ai.research.engine import ResearchResult
from services.common.errors import ApprovalRequiredError, CostWarning, EngineNotConfiguredError

# How big a reply a script needs. The old fixed 4096-token cap cut off any
# script of more than a couple of minutes mid-answer (a 15-minute video is
# ~110 scenes), which then could not be read at all — and was billed anyway.
_SECONDS_PER_SCENE = 8
_TOKENS_PER_SCENE = 220  # narration + visual prompt + fields, with room to spare
_BASE_TOKENS = 1200  # title, hook, structure
_MIN_TOKENS = 4096
_MAX_TOKENS = 16000  # one reply; stays under the SDK's limit for non-streaming requests
_SCENES_PER_PART = 60  # longer scripts are written in several parts
_MAX_PARTS = 6
_MARGIN = 1.15


class ScriptLengthError(RuntimeError):
    """The requested video is longer than a script can be written for."""


def _plan(target_seconds: int) -> tuple[int, int]:
    """(number of parts, max_tokens for each reply)."""
    scenes = max(1, math.ceil(target_seconds / _SECONDS_PER_SCENE))
    parts = math.ceil(scenes / _SCENES_PER_PART)
    if parts > _MAX_PARTS:
        longest = _MAX_PARTS * _SCENES_PER_PART * _SECONDS_PER_SCENE // 60
        raise ScriptLengthError(
            f"A {target_seconds // 60}-minute script is too long to write in one go. "
            f"Choose {longest} minutes or less."
        )
    per_part = math.ceil(scenes / parts * _MARGIN)
    tokens = min(_MAX_TOKENS, max(_MIN_TOKENS, _BASE_TOKENS + _TOKENS_PER_SCENE * per_part))
    return parts, tokens


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


class _ScriptPartModel(BaseModel):
    """A continuation: just the next scenes of a script already begun."""

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
        lessons: str = "",
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

        parts, max_tokens = _plan(target_duration_seconds)
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
        lessons_context = ""
        if lessons:
            lessons_context = (
                "\n\nNotes from Nobert on past videos in this project — "
                f"apply them to this one:\n{lessons}"
            )
        context = research_context + lessons_context
        part_seconds = round(target_duration_seconds / parts)

        title = hook = ""
        claimed: tuple[int, int] = (0, 0)
        scenes: list[SceneDraft] = []
        for part in range(1, parts + 1):
            if part == 1:
                prompt = (
                    f"Write a YouTube video script for topic: {topic!r}, "
                    f"targeting about {part_seconds} seconds "
                    "of narration. Break it into numbered scenes, each "
                    "5-12 seconds of narration (for a target under 30 seconds, "
                    "use one or two scenes) with its own visual_prompt "
                    "(a text-to-video generation prompt describing what "
                    "should appear on screen) and a transition "
                    "('cut', 'fade', or 'dissolve')."
                )
                if parts > 1:
                    prompt += (
                        f" This is part 1 of {parts} of a longer "
                        f"({target_duration_seconds} second) video: write the title, the hook "
                        "and the opening scenes, and do NOT wrap the story up — the next "
                        "part continues it."
                    )
                prompt += context
                response = client.messages.parse(
                    model=self._llm_model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                    output_format=_ScriptDraftModel,
                )
                parsed = parsed_or_raise(response, "the script")
                title, hook = parsed.title, parsed.hook
                claimed = (parsed.estimated_duration_seconds, parsed.word_count)
            else:
                last = " | ".join(s.narration for s in scenes[-3:])
                final = part == parts
                prompt = (
                    f"Continue the YouTube video script for topic: {topic!r}, titled "
                    f"{title!r}. Hook so far: {hook!r}. The script so far ends with these "
                    f"scenes: {last!r}. Write part {part} of {parts}: about {part_seconds} "
                    "seconds of narration as numbered scenes of 5-12 seconds each, with a "
                    "visual_prompt (a text-to-video generation prompt) and a transition "
                    "('cut', 'fade', or 'dissolve') for every scene. Continue the story "
                    "seamlessly, without repeating what was already said. "
                    + (
                        "This is the FINAL part: bring the video to a satisfying ending."
                        if final
                        else "Do NOT wrap the story up — another part follows."
                    )
                    + context
                )
                response = client.messages.parse(
                    model=self._llm_model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                    output_format=_ScriptPartModel,
                )
                parsed = parsed_or_raise(response, f"part {part} of the script")

            scenes.extend(
                SceneDraft(
                    order=0,
                    narration=sc.narration,
                    visual_prompt=sc.visual_prompt,
                    duration_seconds=sc.duration_seconds,
                    transition=sc.transition,
                )
                for sc in parsed.scenes
            )

        for number, scene in enumerate(scenes, start=1):
            scene.order = number  # one continuous numbering across all parts

        # Measured from the scenes themselves, not the model's own claim.
        estimated = sum(sc.duration_seconds for sc in scenes) or claimed[0]
        words = sum(len(sc.narration.split()) for sc in scenes) or claimed[1]
        return ScriptDraft(
            title=title,
            hook=hook,
            estimated_duration_seconds=estimated,
            word_count=words,
            scenes=scenes,
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
        parsed = parsed_or_raise(response, "the rewritten scene")
        return SceneDraft(
            order=scene.order,
            narration=parsed.narration,
            visual_prompt=parsed.visual_prompt,
            duration_seconds=scene.duration_seconds,
            transition=scene.transition,
        )
