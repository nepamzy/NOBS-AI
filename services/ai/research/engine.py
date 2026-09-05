"""Research engine: Topic -> structured research (CLAUDE.md Part 3).

Output shape (stored on the Research model, not a text blob):
key_facts, statistics, interesting_findings, counterarguments,
story_opportunities, plus a ResearchSource row per citation.

No LLM provider is wired in yet. Calling `run()` raises ApprovalRequiredError
until an LLM_PROVIDER + LLM_API_KEY are configured *and* Nobert has approved
the per-call cost — this file is the single place that gate has to hold.
"""

from dataclasses import dataclass, field

from services.common.errors import ApprovalRequiredError, CostWarning


@dataclass
class ResearchResult:
    topic: str
    key_facts: list[str] = field(default_factory=list)
    statistics: list[str] = field(default_factory=list)
    interesting_findings: list[str] = field(default_factory=list)
    counterarguments: list[str] = field(default_factory=list)
    story_opportunities: list[str] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)  # [{"url", "title", "excerpt"}]


class ResearchEngine:
    def __init__(self, llm_provider: str, llm_api_key: str):
        self._llm_provider = llm_provider
        self._llm_api_key = llm_api_key

    def run(self, topic: str) -> ResearchResult:
        if not self._llm_provider or not self._llm_api_key:
            raise ApprovalRequiredError(
                CostWarning(
                    action=f"Run research engine for topic: {topic!r}",
                    service="LLM provider (unconfigured)",
                    expected_cost="COST UNKNOWN — no LLM_PROVIDER/LLM_API_KEY set",
                    billing_type="per token (assumed)",
                    max_expected_cost="Unknown until provider is chosen",
                    risk="Unknown",
                    why_needed="Research stage requires an LLM call to gather "
                    "key facts, statistics, and story angles for the topic.",
                )
            )
        # Real implementation goes here once a provider is chosen and
        # approved. Deliberately not implemented further: this line is
        # unreachable while llm_api_key stays empty.
        raise NotImplementedError("LLM-backed research call not yet implemented")
