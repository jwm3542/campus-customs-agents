"""The Campus Customs agent team.

Five PydanticAI agents (boss, inventory, accounting, facilities,
customer_service). Every agent gets:
  - its prompt from backend/prompts/<name>.md
  - a filtered view of the ONE shared MCP server (no second shop-tools layer)
  - a `delegate` tool that can reach ANY other agent (full connectivity)
Each agent loop step is appended to output/audit_trail.json.
"""

from __future__ import annotations

import os
import sys
import uuid
from dataclasses import dataclass, field
from typing import Any, get_args

from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport
from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import RetryPromptPart, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.settings import ModelSettings
from pydantic_ai.usage import RunUsage, UsageLimits

import audit
from config import (
    DB_PATH,
    MAX_DELEGATION_DEPTH,
    MAX_DELEGATIONS_PER_TICKET,
    MAX_OUTPUT_TOKENS,
    MCP_SERVER_SCRIPT,
    MODEL_NAME,
    REQUESTS_PER_TICKET,
    TOOL_CALLS_PER_TICKET,
    TOTAL_TOKENS_PER_TICKET,
    build_model,
    load_prompt,
)
from models import AgentName, SpecialistReport, TicketDecision

AGENT_NAMES: tuple[str, ...] = get_args(AgentName)

# Tools that move money. Never shown to any agent; only the human approval path calls them.
HUMAN_ONLY_TOOLS = {"approve_payment", "reject_payment"}

# Which MCP tools each agent may see (least privilege). All are on the shared MCP server.
AGENT_TOOLS: dict[str, set[str]] = {
    "boss": {"get_shop_date", "list_open_tickets", "get_ticket", "update_ticket", "list_payments"},
    "inventory": {"get_shop_date", "check_inventory", "get_pricing", "list_vendors", "get_invoice"},
    "accounting": {
        "get_shop_date", "get_cash_balance", "get_invoice", "get_lease",
        "get_pricing", "list_payments", "request_payment",
    },
    "facilities": {"get_shop_date", "get_lease", "get_ticket"},
    "customer_service": {"get_shop_date", "get_ticket", "check_inventory", "get_pricing"},
}
assert all(not (tools & HUMAN_ONLY_TOOLS) for tools in AGENT_TOOLS.values())


def mcp_env(db_path: str | os.PathLike | None = None) -> dict[str, str]:
    """Environment for the MCP subprocess: the normal env minus secrets it never needs."""
    env = {k: v for k, v in os.environ.items() if "API_KEY" not in k.upper()}
    env["CAMPUS_CUSTOMS_DB"] = str(db_path or DB_PATH)
    return env


def build_mcp_toolset(db_path: str | os.PathLike | None = None) -> MCPToolset:
    """Stdio connection to mcp_server/server.py, the same server .mcp.json registers."""
    transport = PythonStdioTransport(MCP_SERVER_SCRIPT, env=mcp_env(db_path), python_cmd=sys.executable)
    return MCPToolset(Client(transport))


@dataclass
class TeamDeps:
    """Shared state for every agent working one ticket."""

    team: "Team"
    run_id: str
    ticket_id: int | None
    agent: str = "boss"
    chain: list[str] = field(default_factory=lambda: ["boss"])
    counter: dict[str, int] = field(default_factory=lambda: {"delegations": 0})

    def child(self, agent: str) -> "TeamDeps":
        return TeamDeps(self.team, self.run_id, self.ticket_id, agent, [*self.chain, agent], self.counter)


async def delegate(ctx: RunContext[TeamDeps], to: AgentName, task: str) -> dict[str, Any]:
    """Hand a self-contained task to another Campus Customs agent and get its report back.

    Args:
        to: boss, inventory, accounting, facilities, or customer_service.
        task: Everything they need: ticket id, sku/size/qty, lease or invoice id, and what to return.
    """
    deps = ctx.deps
    base = dict(run_id=deps.run_id, ticket_id=deps.ticket_id, agent=deps.agent,
                depth=len(deps.chain) - 1, chain=deps.chain, step=0, model=MODEL_NAME)

    refusal = None
    if to == deps.agent:
        refusal = "You can't delegate to yourself."
    elif to in deps.chain:
        refusal = f"{to} is already working on this chain ({' -> '.join(deps.chain)}); answer with what you have."
    elif len(deps.chain) > MAX_DELEGATION_DEPTH:
        refusal = "Delegation depth limit reached; answer with what you have."
    elif deps.counter["delegations"] >= MAX_DELEGATIONS_PER_TICKET:
        refusal = "Ticket delegation budget used up; answer with what you have."
    if refusal:
        await audit.record(**base, event="delegate_refused", detail={"to": to, "task": task, "reason": refusal})
        return {"status": "refused", "reason": refusal}

    deps.counter["delegations"] += 1
    await audit.record(**base, event="delegate", detail={"to": to, "task": task})
    report = await deps.team.run_agent(to, task, deps.child(to), usage=ctx.usage)
    return {"status": "ok", "report": report.model_dump()}


class Team:
    """Builds the five agents around one shared MCP toolset."""

    def __init__(self, mcp_toolset: MCPToolset, model=None):
        self.mcp = mcp_toolset
        model = model or build_model()
        settings = ModelSettings(max_tokens=MAX_OUTPUT_TOKENS)
        self.agents: dict[str, Agent] = {}
        for name in AGENT_NAMES:
            allowed = AGENT_TOOLS[name]
            view = mcp_toolset.filtered(
                lambda _ctx, td, allowed=allowed: td.name in allowed and td.name not in HUMAN_ONLY_TOOLS
            )
            self.agents[name] = Agent(
                model,
                name=name,
                deps_type=TeamDeps,
                output_type=TicketDecision if name == "boss" else SpecialistReport,
                instructions=load_prompt(name),
                toolsets=[view],
                tools=[delegate],
                model_settings=settings,
            )

    async def run_agent(self, name: str, task: str, deps: TeamDeps, usage: RunUsage | None = None):
        """One agent loop, with every step appended to the audit trail."""
        agent = self.agents[name]
        base = dict(run_id=deps.run_id, ticket_id=deps.ticket_id, agent=name,
                    depth=len(deps.chain) - 1, chain=deps.chain, model=MODEL_NAME)
        limits = UsageLimits(
            request_limit=REQUESTS_PER_TICKET,
            tool_calls_limit=TOOL_CALLS_PER_TICKET,
            total_tokens_limit=TOTAL_TOKENS_PER_TICKET,
        )
        step = 0
        await audit.record(**base, step=step, event="run_start", detail={"task": task})
        try:
            async with agent.iter(task, deps=deps, usage=usage, usage_limits=limits) as run:
                async for node in run:
                    step += 1
                    if Agent.is_call_tools_node(node):
                        resp = node.model_response
                        u = resp.usage
                        await audit.record(
                            **base, step=step, event="model_response",
                            detail={
                                "text": " ".join(p.content for p in resp.parts if isinstance(p, TextPart)),
                                "tool_calls": [
                                    {"tool": p.tool_name, "args": p.args_as_dict(), "call_id": p.tool_call_id}
                                    for p in resp.parts if isinstance(p, ToolCallPart)
                                ],
                            },
                            usage={"input_tokens": u.input_tokens, "output_tokens": u.output_tokens},
                        )
                    elif Agent.is_model_request_node(node):
                        results = [
                            {"tool": p.tool_name, "call_id": p.tool_call_id, "result": p.model_response_str()}
                            for p in node.request.parts if isinstance(p, ToolReturnPart)
                        ]
                        retries = [
                            {"tool": p.tool_name, "error": str(p.content)}
                            for p in node.request.parts if isinstance(p, RetryPromptPart)
                        ]
                        if results or retries:
                            await audit.record(**base, step=step, event="tool_result",
                                               detail={"results": results, "retries": retries})
                output = run.result.output
                total = run.usage
        except Exception as exc:
            await audit.record(**base, step=step + 1, event="error",
                               detail={"type": type(exc).__name__, "message": str(exc)})
            raise
        await audit.record(
            **base, step=step + 1, event="run_end", detail={"output": output.model_dump()},
            usage={"requests": total.requests, "input_tokens": total.input_tokens,
                   "output_tokens": total.output_tokens},
        )
        return output


async def run_ticket(ticket_id: int, model=None, db_path=None) -> TicketDecision:
    """Have the Boss work one ticket end to end. Opens one MCP connection for the whole team."""
    toolset = build_mcp_toolset(db_path)
    async with toolset:
        team = Team(toolset, model=model)
        deps = TeamDeps(team=team, run_id=uuid.uuid4().hex[:12], ticket_id=ticket_id)
        task = f"Work ticket {ticket_id}. Start with get_shop_date and get_ticket, then make the final call."
        return await team.run_agent("boss", task, deps)
