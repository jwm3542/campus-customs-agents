"""Campus Customs backend: FastAPI routes for the React dashboard.

Start from the backend folder:
    uvicorn main:app --reload --port 8000

Every shop fact and every database write goes through the campus-customs MCP
server (one stdio connection held for the app's lifetime). The only exception
is /api/reset, which copies the untouched original database file over the
working copy.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field

import agents
from config import AUDIT_PATH, DB_PATH, MCP_SERVER_SCRIPT, MODEL_NAME, PROJECT

ORIGINAL_DB = PROJECT / "data" / "campus_customs.db"


# ------------------------------------------------------------------ MCP link


class ShopMCP:
    """One long-lived stdio connection to the MCP server, shared by all routes."""

    def __init__(self) -> None:
        self.client = Client(
            PythonStdioTransport(
                MCP_SERVER_SCRIPT,
                env=agents.mcp_env(DB_PATH),
                python_cmd=sys.executable,
            )
        )
        self.lock = asyncio.Lock()

    async def call(self, tool: str, **args: Any) -> dict:
        async with self.lock:
            try:
                result = await self.client.call_tool(tool, args)
            except ToolError as exc:
                raise HTTPException(status_code=502, detail=f"MCP tool {tool} failed: {exc}") from exc
        return result.structured_content or {}


shop = ShopMCP()

# Background agent runs: ticket_id -> status record. One run at a time keeps tokens in check.
RUNS: dict[int, dict[str, Any]] = {}
run_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with shop.client:
        yield


app = FastAPI(title="Campus Customs Ops API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# -------------------------------------------------------------------- models


class ApproveBody(BaseModel):
    approved_by: str = Field(min_length=1, description="Name of the human approving the payment.")


class RejectBody(BaseModel):
    rejected_by: str = Field(min_length=1)
    reason: str = Field(min_length=1)


# -------------------------------------------------------------------- routes


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True, "model": MODEL_NAME, "database": DB_PATH.name}


@app.get("/api/tickets")
async def list_tickets() -> dict:
    """All tickets with status, plus a simple open/resolved flag for the board."""
    data = await shop.call("list_tickets")
    tickets = data.get("tickets", [])
    for t in tickets:
        t["is_resolved"] = t["status"] == "resolved"
        t["run"] = RUNS.get(t["id"])
    return {"tickets": tickets}


async def _run_in_background(ticket_id: int) -> None:
    record = RUNS[ticket_id]
    async with run_lock:
        record.update(status="running", started_at=_now())
        try:
            decision = await agents.run_ticket(ticket_id)
            record.update(status="done", decision=decision.model_dump())
        except Exception as exc:  # surfaced to the board, also logged in the audit trail
            record.update(status="error", error=f"{type(exc).__name__}: {exc}")
        record["finished_at"] = _now()


@app.post("/api/tickets/{ticket_id}/run", status_code=202)
async def run_ticket(ticket_id: int) -> dict:
    """Start the agent team on one ticket. Poll /api/runs or /api/events for progress."""
    found = await shop.call("get_ticket", ticket_id=ticket_id)
    if not found.get("found"):
        raise HTTPException(status_code=404, detail=f"No ticket {ticket_id}.")
    if any(r["status"] in ("queued", "running") for r in RUNS.values()):
        raise HTTPException(status_code=409, detail="An agent run is already in progress.")
    RUNS[ticket_id] = {"ticket_id": ticket_id, "status": "queued", "queued_at": _now()}
    asyncio.create_task(_run_in_background(ticket_id))
    return RUNS[ticket_id]


@app.get("/api/runs")
async def list_runs() -> dict:
    return {"runs": list(RUNS.values())}


@app.get("/api/events")
async def recent_events(
    limit: int = Query(50, ge=1, le=500),
    ticket_id: int | None = None,
) -> dict:
    """Most recent audit-trail events: what each agent said and which tools it used."""
    if not AUDIT_PATH.exists() or not AUDIT_PATH.stat().st_size:
        return {"events": []}
    events = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    if ticket_id is not None:
        events = [e for e in events if e.get("ticket_id") == ticket_id]
    out = []
    for e in events[-limit:]:
        d = e.get("detail", {})
        out.append({
            "ts": e["ts"], "run_id": e["run_id"], "ticket_id": e["ticket_id"], "agent": e["agent"],
            "depth": e["depth"], "event": e["event"],
            "said": d.get("text") or d.get("task") or d.get("reason"),
            "tools": [c["tool"] for c in d.get("tool_calls", [])] or [r["tool"] for r in d.get("results", [])],
            "to": d.get("to"),
            "detail": d,
            "usage": e.get("usage"),
        })
    return {"events": out}


@app.get("/api/approvals")
async def approvals() -> dict:
    """The approval queue (pending first) plus the payments ledger."""
    data = await shop.call("list_payments")
    queue = sorted(data.get("approvals", []), key=lambda a: (a["status"] != "pending", a["id"]))
    return {"approvals": queue, "payments": data.get("payments", [])}


@app.post("/api/approvals/{approval_id}/approve")
async def approve(approval_id: int, body: ApproveBody) -> dict:
    """HUMAN click. The only route that moves cash. The MCP tool refuses a negative balance."""
    result = await shop.call("approve_payment", approval_id=approval_id, approved_by=body.approved_by)
    if not result.get("ok"):
        raise HTTPException(status_code=409, detail=result.get("message", "Refused."))
    return result


@app.post("/api/approvals/{approval_id}/reject")
async def reject(approval_id: int, body: RejectBody) -> dict:
    result = await shop.call(
        "reject_payment", approval_id=approval_id, rejected_by=body.rejected_by, reason=body.reason
    )
    if not result.get("ok"):
        raise HTTPException(status_code=409, detail=result.get("message", "Refused."))
    return result


@app.get("/api/cash")
async def cash() -> dict:
    """Current checking balance from cash_accounts, plus what's waiting on approval."""
    data = await shop.call("get_cash_balance")
    checking = next((a for a in data.get("accounts", []) if a["name"] == "checking"), None)
    if not checking:
        raise HTTPException(status_code=404, detail="No checking account.")
    pending = data.get("pending_approval_total", 0)
    return {**checking, "pending_approval_total": pending, "balance_if_all_approved": checking["balance"] - pending}


@app.post("/api/reset")
async def reset() -> dict:
    """Copy the untouched original over the working database. The audit trail is kept."""
    if any(r["status"] in ("queued", "running") for r in RUNS.values()):
        raise HTTPException(status_code=409, detail="Can't reset while an agent run is in progress.")
    if not ORIGINAL_DB.exists():
        raise HTTPException(status_code=500, detail="Original database missing.")
    async with shop.lock:
        shutil.copyfile(ORIGINAL_DB, DB_PATH)
    RUNS.clear()
    return {"ok": True, "message": f"Reset {DB_PATH.name} from {ORIGINAL_DB.name}.", "at": _now()}
