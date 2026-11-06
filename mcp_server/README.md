# Campus Customs MCP Server

A FastMCP server that gives every HW 5 agent, and the backend, one shared set of tools for the Campus Customs database. Agents never touch SQL or the database file directly. They call these tools, which return only what's in the database: `found: false` or `ok: false` when there's no match, never a guess.

**Database:** `data/campus_customs_new.db`, the working copy. The original `data/campus_customs.db` is never modified, and `python scripts/reset_db.py` restores the working copy from it. You can override the path with the `CAMPUS_CUSTOMS_DB` environment variable.

## Tools

### Read tools (any agent)
| Tool | Reads | Purpose |
|---|---|---|
| `get_shop_date()` | `desk` | The shop's "today". All overdue logic uses it |
| `list_tickets()` | `tickets` | Every ticket with its status (used by the dashboard) |
| `list_open_tickets()` | `tickets` | Every ticket not yet resolved |
| `get_ticket(ticket_id)` | `tickets` | One ticket with its links |
| `check_inventory(sku, size=None)` | `inventory` | On-hand qty and location |
| `get_pricing(sku)` | `pricing` | Unit cost (discount floor) and list price |
| `list_vendors()` | `vendors`, `invoices` | Specialty, lead days, open invoices, `can_ship` |
| `get_invoice(invoice_id)` | `invoices`, `vendors`, `desk` | Invoice, vendor, overdue flag and days |
| `get_lease(lease_id)` | `leases` | Space, landlord, rent, next due date |
| `get_cash_balance()` | `cash_accounts`, `approvals` | Balance plus the total pending approval |
| `list_payments()` | `payments`, `approvals` | Ledger and approval queue |

### Agent write tools (no money moves)
| Tool | Writes | Purpose |
|---|---|---|
| `request_payment(kind, ref_id, reason, requested_by, ticket_id)` | `approvals`, `tickets` | Queues an invoice or rent payment for **human approval**. The amount comes from the database. It refuses unknown or paid bills, duplicates, and anything that cash plus pending requests can't cover |
| `update_ticket(ticket_id, status, note)` | `tickets` | Sets the status and appends a dated note |

### Human-only tools (hidden from every agent)
| Tool | Writes | Purpose |
|---|---|---|
| `approve_payment(approval_id, approved_by)` | `payments`, `cash_accounts`, `invoices` or `leases`, `approvals` | Pays an approved request. It needs a human name, refuses if the balance would go negative, and updates every related table |
| `reject_payment(approval_id, rejected_by, reason)` | `approvals` | Declines a request. No money moves |

The `approvals` table is created by this server in the working database. A reset removes it.

## Run

```bash
pip install -r mcp_server/requirements.txt
python mcp_server/server.py
```

It's registered for Claude Code in `.mcp.json`. The backend launches the same script over stdio.
