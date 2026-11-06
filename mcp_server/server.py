"""Campus Customs MCP server.

The single shared tool layer for every HW 5 agent and the backend. Tools only
report what is in the working database; they never fill in or guess values.

Tool groups
- Read tools: any agent may call these.
- Agent write tools: request_payment, update_ticket. Agents can propose and
  record, but cannot move money.
- Human-only tools (HUMAN_ONLY_TOOLS): approve_payment, reject_payment. These
  are filtered out of every agent's toolset by the backend and are only called
  from the human approval path.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from fastmcp import FastMCP

DB_PATH = Path(
    os.getenv(
        "CAMPUS_CUSTOMS_DB",
        Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db",
    )
)

HUMAN_ONLY_TOOLS = {"approve_payment", "reject_payment"}
TICKET_STATUSES = {"open", "in_progress", "waiting_approval", "resolved", "blocked"}

mcp = FastMCP("campus-customs")


@contextmanager
def _db():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        _ensure_approvals(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_approvals(conn: sqlite3.Connection) -> None:
    """Approval queue for payments. Lives in the working DB; a reset removes it."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY,
            kind TEXT NOT NULL CHECK (kind IN ('invoice', 'rent')),
            ref_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            account TEXT NOT NULL,
            reason TEXT NOT NULL,
            requested_by TEXT NOT NULL,
            ticket_id INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            decided_by TEXT,
            decided_at TEXT,
            created_at TEXT NOT NULL
        )"""
    )


def _rows(conn, sql: str, params: tuple = ()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _today(conn) -> str:
    return conn.execute("SELECT date_today FROM desk").fetchone()["date_today"]


# --------------------------------------------------------------------- reads


@mcp.tool
def get_shop_date() -> dict:
    """Return the shop's 'today' (desk.date_today) and desk notes.

    Always use this date, never the real clock, to judge what is due or overdue.
    """
    with _db() as conn:
        rows = _rows(conn, "SELECT date_today, notes FROM desk")
    if not rows:
        return {"found": False, "message": "Desk table is empty."}
    return {"found": True, "desk": rows[0]}


@mcp.tool
def list_open_tickets() -> dict:
    """List every ticket whose status is not 'resolved', oldest first, from the tickets table."""
    with _db() as conn:
        rows = _rows(conn, "SELECT * FROM tickets WHERE status != 'resolved' ORDER BY created_at")
    return {"found": bool(rows), "count": len(rows), "tickets": rows}


@mcp.tool
def list_tickets() -> dict:
    """List every ticket (any status), by id, with type, requester, subject, and status."""
    with _db() as conn:
        rows = _rows(
            conn,
            "SELECT id, type, requester, subject, sku, size, qty, lease_id, invoice_id, status, notes, created_at "
            "FROM tickets ORDER BY id",
        )
    return {"found": bool(rows), "count": len(rows), "tickets": rows}


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Return one ticket (type, requester, sku/size/qty, linked lease or invoice, status, notes)."""
    with _db() as conn:
        rows = _rows(conn, "SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    if not rows:
        return {"found": False, "ticket_id": ticket_id, "message": "No ticket with that id."}
    return {"found": True, "ticket": rows[0]}


@mcp.tool
def check_inventory(sku: str, size: str | None = None) -> dict:
    """Look up on-hand stock for a SKU from the inventory table.

    Pass a size (e.g. "S", "M", "OS") for one row, or omit it for every size.
    Returns found=False if the SKU/size is not in the database.
    """
    with _db() as conn:
        if size:
            rows = _rows(
                conn,
                "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
                (sku, size),
            )
        else:
            rows = _rows(
                conn,
                "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? ORDER BY size",
                (sku,),
            )
    if not rows:
        return {"found": False, "sku": sku, "size": size, "message": "No matching inventory row."}
    return {"found": True, "rows": rows}


@mcp.tool
def get_pricing(sku: str) -> dict:
    """Look up unit cost and list price for a SKU from the pricing table.

    unit_cost is the floor for any discount. Returns found=False if the SKU has no price.
    """
    with _db() as conn:
        rows = _rows(conn, "SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku,))
    if not rows:
        return {"found": False, "sku": sku, "message": "No pricing row for that SKU."}
    return {"found": True, "pricing": rows[0]}


@mcp.tool
def list_vendors() -> dict:
    """List vendors with specialty and lead_days, plus each vendor's open (unpaid) invoices.

    A vendor with open invoices will not ship new product until they are paid.
    """
    with _db() as conn:
        vendors = _rows(conn, "SELECT id, name, specialty, lead_days FROM vendors ORDER BY id")
        for v in vendors:
            v["open_invoices"] = _rows(
                conn,
                "SELECT id, amount, due_date FROM invoices WHERE vendor_id = ? AND status = 'open'",
                (v["id"],),
            )
            v["can_ship"] = not v["open_invoices"]
    return {"found": bool(vendors), "vendors": vendors}


@mcp.tool
def get_invoice(invoice_id: int) -> dict:
    """Return one invoice with its vendor, and whether it is overdue as of the shop date."""
    with _db() as conn:
        rows = _rows(
            conn,
            """SELECT i.id, i.vendor_id, v.name AS vendor_name, i.amount, i.due_date,
                      i.status, i.description
               FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?""",
            (invoice_id,),
        )
        today = _today(conn)
    if not rows:
        return {"found": False, "invoice_id": invoice_id, "message": "No invoice with that id."}
    inv = rows[0]
    inv["overdue"] = inv["status"] == "open" and inv["due_date"] < today
    if inv["overdue"]:
        inv["days_overdue"] = (date.fromisoformat(today) - date.fromisoformat(inv["due_date"])).days
    return {"found": True, "shop_date": today, "invoice": inv}


@mcp.tool
def get_lease(lease_id: int) -> dict:
    """Look up a lease (space, landlord, monthly rent, next due date) from the leases table.

    Returns found=False if the lease id is not in the database.
    """
    with _db() as conn:
        rows = _rows(
            conn,
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?",
            (lease_id,),
        )
    if not rows:
        return {"found": False, "lease_id": lease_id, "message": "No lease with that id."}
    return {"found": True, "lease": rows[0]}


@mcp.tool
def get_cash_balance() -> dict:
    """Return cash account balances, plus the total of payments still awaiting human approval.

    Cash only goes out in this shop; no revenue comes in.
    """
    with _db() as conn:
        accounts = _rows(conn, "SELECT name, balance, date FROM cash_accounts")
        pending = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS t FROM approvals WHERE status = 'pending'"
        ).fetchone()["t"]
    return {"found": bool(accounts), "accounts": accounts, "pending_approval_total": pending}


@mcp.tool
def list_payments() -> dict:
    """Return the payments ledger and the approval queue (pending, approved, rejected)."""
    with _db() as conn:
        payments = _rows(conn, "SELECT * FROM payments ORDER BY id")
        approvals = _rows(conn, "SELECT * FROM approvals ORDER BY id")
    return {"payments": payments, "approvals": approvals}


# --------------------------------------------------------------- agent writes


@mcp.tool
def request_payment(
    kind: str,
    ref_id: int,
    reason: str,
    requested_by: str,
    ticket_id: int | None = None,
    account: str = "checking",
) -> dict:
    """Queue a payment for HUMAN approval. This does NOT move money.

    kind: 'invoice' (ref_id = invoices.id) or 'rent' (ref_id = leases.id).
    The amount is taken from the database, never from the caller. Refuses if the
    bill is unknown or already paid, if the same bill is already pending, or if
    the account cannot cover it alongside other pending requests.
    """
    if kind not in ("invoice", "rent"):
        return {"ok": False, "message": "kind must be 'invoice' or 'rent'."}
    with _db() as conn:
        if kind == "invoice":
            row = conn.execute("SELECT amount, status FROM invoices WHERE id = ?", (ref_id,)).fetchone()
            if not row:
                return {"ok": False, "message": f"No invoice {ref_id}."}
            if row["status"] != "open":
                return {"ok": False, "message": f"Invoice {ref_id} is already {row['status']}."}
            amount = row["amount"]
        else:
            row = conn.execute("SELECT monthly_rent FROM leases WHERE id = ?", (ref_id,)).fetchone()
            if not row:
                return {"ok": False, "message": f"No lease {ref_id}."}
            amount = row["monthly_rent"]

        dup = conn.execute(
            "SELECT id FROM approvals WHERE kind = ? AND ref_id = ? AND status = 'pending'",
            (kind, ref_id),
        ).fetchone()
        if dup:
            return {"ok": False, "message": f"Already pending as approval {dup['id']}."}

        acct = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (account,)).fetchone()
        if not acct:
            return {"ok": False, "message": f"No cash account '{account}'."}
        pending = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS t FROM approvals WHERE status = 'pending' AND account = ?",
            (account,),
        ).fetchone()["t"]
        if pending + amount > acct["balance"]:
            return {
                "ok": False,
                "message": "Refused: not enough cash for this plus already-pending requests.",
                "balance": acct["balance"],
                "pending_total": pending,
                "requested": amount,
            }

        cur = conn.execute(
            """INSERT INTO approvals (kind, ref_id, amount, account, reason, requested_by,
                                      ticket_id, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
            (kind, ref_id, amount, account, reason, requested_by, ticket_id, _today(conn)),
        )
        if ticket_id is not None:
            conn.execute(
                "UPDATE tickets SET status = 'waiting_approval' WHERE id = ? AND status != 'resolved'",
                (ticket_id,),
            )
    return {
        "ok": True,
        "approval_id": cur.lastrowid,
        "amount": amount,
        "status": "pending",
        "message": "Queued for human approval. No money has moved.",
    }


@mcp.tool
def update_ticket(ticket_id: int, status: str, note: str) -> dict:
    """Set a ticket's status and append a note. Status: open, in_progress, waiting_approval, resolved, blocked."""
    if status not in TICKET_STATUSES:
        return {"ok": False, "message": f"status must be one of {sorted(TICKET_STATUSES)}."}
    with _db() as conn:
        row = conn.execute("SELECT notes FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if not row:
            return {"ok": False, "message": f"No ticket {ticket_id}."}
        notes = f"{row['notes'] or ''}\n[{_today(conn)}] {note}".strip()
        conn.execute("UPDATE tickets SET status = ?, notes = ? WHERE id = ?", (status, notes, ticket_id))
    return {"ok": True, "ticket_id": ticket_id, "status": status}


# ---------------------------------------------------------- human-only writes


@mcp.tool
def approve_payment(approval_id: int, approved_by: str) -> dict:
    """HUMAN ONLY. Pay a pending approval: write payments, debit cash, mark the bill paid.

    Refuses if the approver name is blank, the request is not pending, or the
    balance would go negative.
    """
    if not approved_by or not approved_by.strip():
        return {"ok": False, "message": "A human approver name is required."}
    with _db() as conn:
        a = conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        if not a:
            return {"ok": False, "message": f"No approval {approval_id}."}
        if a["status"] != "pending":
            return {"ok": False, "message": f"Approval {approval_id} is already {a['status']}."}
        acct = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (a["account"],)).fetchone()
        if not acct or acct["balance"] < a["amount"]:
            return {
                "ok": False,
                "message": "Refused: payment would make the balance negative.",
                "balance": acct["balance"] if acct else None,
                "amount": a["amount"],
            }
        today = _today(conn)
        new_balance = acct["balance"] - a["amount"]
        cur = conn.execute(
            """INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (a["kind"], a["ref_id"], a["amount"], a["account"], today, approved_by.strip()),
        )
        conn.execute(
            "UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?",
            (new_balance, today, a["account"]),
        )
        if a["kind"] == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (a["ref_id"],))
        else:
            conn.execute(
                "UPDATE leases SET next_due = date(next_due, '+1 month') WHERE id = ?",
                (a["ref_id"],),
            )
        conn.execute(
            "UPDATE approvals SET status = 'approved', decided_by = ?, decided_at = ? WHERE id = ?",
            (approved_by.strip(), today, approval_id),
        )
    return {"ok": True, "payment_id": cur.lastrowid, "amount": a["amount"], "new_balance": new_balance}


@mcp.tool
def reject_payment(approval_id: int, rejected_by: str, reason: str) -> dict:
    """HUMAN ONLY. Reject a pending approval; no money moves."""
    if not rejected_by or not rejected_by.strip():
        return {"ok": False, "message": "A human name is required."}
    with _db() as conn:
        a = conn.execute("SELECT status FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        if not a:
            return {"ok": False, "message": f"No approval {approval_id}."}
        if a["status"] != "pending":
            return {"ok": False, "message": f"Approval {approval_id} is already {a['status']}."}
        conn.execute(
            "UPDATE approvals SET status = 'rejected', decided_by = ?, decided_at = ?, reason = reason || ? WHERE id = ?",
            (rejected_by.strip(), _today(conn), f" | rejected: {reason}", approval_id),
        )
    return {"ok": True, "approval_id": approval_id, "status": "rejected"}


if __name__ == "__main__":
    mcp.run(show_banner=False)
