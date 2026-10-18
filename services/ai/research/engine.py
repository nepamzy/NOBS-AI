"""Research engine: Topic -> structured research (CLAUDE.md Part 3).

Output shape (stored on the Research model, not a text blob):
key_facts, statistics, interesting_findings, counterarguments,
story_opportunities, plus a ResearchSource row per citation.

Calling `run()` raises ApprovalRequiredError until an LLM_PROVIDER +
LLM_API_KEY are configured *and* Nobert has approved the per-call cost —
this file is the single place that gate has to hold. Only "anthropic" is
actually implemented; any other provider string is treated as unconfigured.

No live web search: this asks the model directly, relying on its training
knowledge. `sources` are therefore the model's best recollection of
relevant references, not fetched/verified URLs — treat them as starting
points to check, not as confirmed citations, until a web-search-backed
version replaces this.
"""

import json
from dataclasses import dataclass, field

from pydantic import BaseModel, ValidationError

from services.common.errors import ApprovalRequiredError, CostWarning, EngineNotConfiguredError

# Research is a structured reply with several lists plus source excerpts; 4096
# tokens was too tight and a cut-off reply is invalid JSON. Give it room and
# retry once with an explicit reason instead of failing on the first miss.
_MAX_OUTPUT_TOKENS = 8192
_MAX_ATTEMPTS = 2


class ResearchOutputError(RuntimeError):
    """The model replied, but not with usable research. Raised so the stage
    fails with the reason shown on the video page, not a silent crash."""


def _prompt(topic: str) -> str:
    return (
        f"Research this YouTube video topic: {topic!r}. Cover key facts, relevant "
        "statistics, interesting findings, counterarguments or nuance worth "
        "acknowledging, and story angle opportunities. For sources, name real "
        "references you're aware of (they are not fetched live; flag anything "
        "you're unsure is still accurate).\n\n"
        "Reply with ONLY one JSON object, no text before or after it, with keys: "
        "key_facts, statistics, interesting_findings, counterarguments, "
        "story_opportunities (each a list of strings), and sources (a list of "
        "objects with url, title, excerpt)."
    )


def _parse_json_object(text: str) -> dict:
    """Tolerates a code fence or a sentence around the JSON object."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in the reply")
    return json.loads(text[start : end + 1])


@dataclass
class ResearchResult:
    topic: str
    key_facts: list[str] = field(default_factory=list)
    statistics: list[str] = field(default_factory=list)
    interesting_findings: list[str] = field(default_factory=list)
    counterarguments: list[str] = field(default_factory=list)
    story_opportunities: list[str] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)  # [{"url", "title", "excerpt"}]


class _ResearchSourceModel(BaseModel):
    url: str
    title: str
    excerpt: str


class _ResearchResultModel(BaseModel):
    key_facts: list[str]
    statistics: list[str]
    interesting_findings: list[str]
    counterarguments: list[str]
    story_opportunities: list[str]
    sources: list[_ResearchSourceModel]


class ResearchEngine:
    def __init__(self, llm_provider: str, llm_api_key: str, llm_model: str = "claude-opus-5"):
        self._llm_provider = llm_provider
        self._llm_api_key = llm_api_key
        self._llm_model = llm_model

    def run(self, topic: str) -> ResearchResult:
        if not self._llm_provider or not self._llm_api_key:
            raise ApprovalRequiredError(
                CostWarning(
                    action=f"Run research engine for topic: {topic!r}",
                    service="Anthropic API (unconfigured)",
                    expected_cost="COST UNKNOWN — no LLM_PROVIDER/LLM_API_KEY set",
                    billing_type="per token",
                    max_expected_cost="A single research call is a few "
                    "thousand tokens — well under $0.10 at current Claude "
                    "pricing, but re-verify before relying on this figure",
                    risk="Low",
                    why_needed="Research stage requires an LLM call to gather "
                    "key facts, statistics, and story angles for the topic.",
                )
            )
        if self._llm_provider != "anthropic":
            raise EngineNotConfiguredError(
                f"LLM_PROVIDER={self._llm_provider!r} is not implemented — "
                "only 'anthropic' is wired up so far."
            )

        import anthropic

        client = anthropic.Anthropic(api_key=self._llm_api_key)
        problem = ""
        for _ in range(_MAX_ATTEMPTS):
            message = client.messages.create(
                model=self._llm_model,
                max_tokens=_MAX_OUTPUT_TOKENS,
                messages=[{"role": "user", "content": _prompt(topic)}],
            )
            text = "".join(
                block.text for block in message.content if getattr(block, "type", "") == "text"
            )
            if message.stop_reason == "max_tokens":
                problem = f"reply was cut off at {_MAX_OUTPUT_TOKENS} tokens"
                continue
            try:
                parsed = _ResearchResultModel.model_validate(_parse_json_object(text))
            except (ValueError, ValidationError) as exc:
                problem = (
                    f"reply was not the expected research JSON ({type(exc).__name__}); "
                    f"it starts with: {text[:160]!r}"
                )
                continue
            return ResearchResult(
                topic=topic,
                key_facts=parsed.key_facts,
                statistics=parsed.statistics,
                interesting_findings=parsed.interesting_findings,
                counterarguments=parsed.counterarguments,
                story_opportunities=parsed.story_opportunities,
                sources=[s.model_dump() for s in parsed.sources],
            )
        raise ResearchOutputError(f"Research failed after {_MAX_ATTEMPTS} attempts: {problem}")
