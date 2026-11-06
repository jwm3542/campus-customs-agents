"""Data types shared by the agent team, the audit trail, and (later) the API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
TicketStatus = Literal["open", "in_progress", "waiting_approval", "resolved", "blocked"]


class SpecialistReport(BaseModel):
    """What a specialist hands back to whoever delegated to it."""

    agent: AgentName
    summary: str = Field(description="One or two sentences answering the task.")
    facts: list[str] = Field(default_factory=list, description="Facts taken from tool results only.")
    actions_taken: list[str] = Field(default_factory=list, description="Writes made, e.g. approval ids queued.")
    blockers: list[str] = Field(default_factory=list)
    draft_message: str | None = Field(default=None, description="Customer draft (customer_service only).")


class ApprovalQueued(BaseModel):
    approval_id: int
    kind: Literal["invoice", "rent"]
    ref_id: int
    amount: float
    reason: str


class TicketDecision(BaseModel):
    """The Boss's final call on one ticket."""

    ticket_id: int
    decision: str = Field(description="The final call in one or two sentences.")
    agents_used: list[AgentName] = Field(default_factory=list)
    approvals_queued: list[ApprovalQueued] = Field(default_factory=list)
    customer_draft: str | None = None
    blockers: list[str] = Field(default_factory=list)
    final_status: TicketStatus


class AuditEvent(BaseModel):
    """One line in output/audit_trail.json: a single step of an agent loop."""

    ts: str
    run_id: str
    ticket_id: int | None
    agent: AgentName
    depth: int
    chain: list[AgentName]
    step: int
    event: Literal[
        "run_start", "model_response", "tool_result",
        "delegate", "delegate_refused", "run_end", "error",
    ]
    model: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)
    usage: dict[str, int] | None = None
