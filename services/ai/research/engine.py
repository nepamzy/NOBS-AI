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

from dataclasses import dataclass, field

from pydantic import BaseModel

from services.common.errors import ApprovalRequiredError, CostWarning, EngineNotConfiguredError

_MAX_OUTPUT_TOKENS = 4096


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
        response = client.messages.parse(
            model=self._llm_model,
            max_tokens=_MAX_OUTPUT_TOKENS,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Research this YouTube video topic: {topic!r}. Provide "
                        "key facts, relevant statistics, interesting findings, "
                        "counterarguments/nuance worth acknowledging, and "
                        "story angle opportunities. For sources, name real "
                        "references you're aware of (they are not fetched "
                        "live — flag anything you're unsure is still "
                        "accurate)."
                    ),
                }
            ],
            output_format=_ResearchResultModel,
        )
        parsed = response.parsed_output
        return ResearchResult(
            topic=topic,
            key_facts=parsed.key_facts,
            statistics=parsed.statistics,
            interesting_findings=parsed.interesting_findings,
            counterarguments=parsed.counterarguments,
            story_opportunities=parsed.story_opportunities,
            sources=[s.model_dump() for s in parsed.sources],
        )
