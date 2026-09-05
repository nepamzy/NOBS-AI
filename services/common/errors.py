"""Shared error types for every engine/service adapter.

CLAUDE.md Part 1 is unconditional: no paid API call, GPU rental, or paid
inference happens without Nobert's explicit approval first. Every adapter in
this codebase (LLM, Wan, Chatterbox, Runpod) must raise
`ApprovalRequiredError` instead of making the call when that call would cost
money or provision paid infrastructure — never silently proceed.
"""

from dataclasses import dataclass


@dataclass
class CostWarning:
    """Mirrors the mandatory "PAYMENT / COST WARNING" block from CLAUDE.md
    Part 1, so every caller (API, worker, CLI) renders the same fields."""

    action: str
    service: str
    expected_cost: str
    billing_type: str
    max_expected_cost: str
    risk: str
    why_needed: str

    def render(self) -> str:
        return (
            "### PAYMENT / COST WARNING\n"
            f"Action: {self.action}\n"
            f"Service: {self.service}\n"
            f"Expected cost: {self.expected_cost}\n"
            f"Billing type: {self.billing_type}\n"
            f"Maximum expected cost for this action: {self.max_expected_cost}\n"
            f"Risk: {self.risk}\n"
            f"Why it is needed: {self.why_needed}\n"
            "Approval required: YES"
        )


class ApprovalRequiredError(RuntimeError):
    """Raised by an adapter when the requested action would spend money or
    provision paid/external infrastructure and no approval has been recorded.
    Callers (job tasks) should catch this, store `cost_warning.render()` on
    the job/video row, and stop — never retry automatically."""

    def __init__(self, cost_warning: CostWarning):
        self.cost_warning = cost_warning
        super().__init__(cost_warning.render())


class EngineNotConfiguredError(RuntimeError):
    """Raised when a required setting (API key, self-hosted endpoint URL) is
    missing. Distinct from ApprovalRequiredError: this is a setup gap, not
    necessarily a spend — e.g. a self-hosted Chatterbox URL that isn't set."""
