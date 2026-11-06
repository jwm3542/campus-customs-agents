# Campus Customs Multi-Agent Harness

Working database: `data/campus_customs_new.db` (agents read and write this copy).
Original: `data/campus_customs.db` (never modified; copy it over the working copy to reset).

---

## Shop rules (every agent and tool must follow these)

1. **Today is `desk.date_today`** (2026-08-31). Overdue status is judged against this date, never the system clock.
2. **Vendor lead times** come from `vendors.lead_days`.
3. **No shipping on unpaid bills:** a vendor won't ship new product while it has an open, unpaid invoice.
4. **Human approval for every payment.** No payment is written without a named human approver in `payments.approved_by`.
5. **A payment updates every table it touches:** the `payments` row, the `cash_accounts` balance, and the invoice status.
6. **No negative cash.** The pay tool must refuse any payment larger than the account balance.
7. **Cash only goes out.** Revenue isn't modeled, so no money comes in.
8. **Reset before every full run:** `python scripts/reset_db.py` copies the original over the working copy.
9. **No real contact.** Never email customers or call real vendors. Customer and vendor messages are drafts shown on the board only.
10. **Model:** every agent uses `gpt-6-luna` through Portkey and nothing else. It's set once via `OPENAI_MODEL`.
11. **Secrets:** `PORTKEY_API_KEY` lives in the course folder's `.env`, outside this repo. It's never committed, printed, or logged.

---

## Database tables

| Table | Fields | Why it matters to our agents |
|---|---|---|
| `desk` | `date_today`, `notes` | Defines "today" (2026-08-31), so agents can judge what's overdue or coming due without trusting the system clock. |
| `inventory` | `sku`, `name`, `size`, `qty`, `location` (PK `sku`+`size`) | Source of truth for stock by size. Order agents check here before promising anything. |
| `pricing` | `sku`, `unit_cost`, `list_price` | Margin floor for quotes and discounts; any price override has to stay above `unit_cost`. |
| `vendors` | `id`, `name`, `specialty`, `lead_days` | Who can restock or reprint, and how long it takes. Used to set delivery dates for out-of-stock items. |
| `leases` | `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes` | Fixed obligations. Rent notices link here, so the finance agent can check amount and due date. |
| `cash_accounts` | `name`, `balance`, `date` | Cash on hand ($3,400 checking). Every payment decision has to fit within this balance. |
| `payments` | `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by` | Audit log agents write to. `approved_by` is required, so no payment goes through without a named approver. Empty at start. |
| `invoices` | `id`, `vendor_id`→`vendors`, `amount`, `due_date`, `status`, `description` | Bills owed to vendors. The finance agent checks status and due date before paying. |
| `tickets` | `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`→`leases`, `invoice_id`→`invoices`, `status`, `notes`, `created_at` | The work queue. Each ticket's `type` decides which agent handles it, and its keys link to the records it needs. |

## Open tickets and their links

**101 · customer_order** (Tauhid Zaman): 1 × Bulldog Tee, size S
- `inventory` CC-TEE-WHITE / S → **qty 0** (Aisle B). Out of stock.
- `pricing` → list $28, cost $8.
- `invoice_id` 501 → `invoices` → $840 "Rush reprint CC-TEE-WHITE S", due 2026-08-28, **open and 3 days overdue**.
- `invoices.vendor_id` 1 → `vendors` → Bulldog Print Co (apparel reprint, 5 lead days).
- Takeaway: the restock is held up by an unpaid vendor bill.

**102 · rent_notice** (Elm City Properties): rent due
- `lease_id` 1 → `leases` → Chapel Street shop, $2,400, due 2026-09-02 (in 2 days).
- `cash_accounts` → checking $3,400.

**103 · price_override** (Yale AI Club): 20 × hoodie M, bulk discount
- `inventory` CC-HOOD-NAVY / M → **qty 8**, which is 12 short. (S 4, L 14, XL 6.)
- `pricing` → list $58, cost $22. Full price is $1,160 and the cost floor is $440.
- No `lease_id` or `invoice_id` link. A discount needs human sign-off.

**Cash pressure:** paying invoice 501 ($840) plus rent ($2,400) = $3,240, which leaves **$160** in checking. Agents need to prioritize, and a human needs to approve payments.

**Other observations:** Crest Mug (CC-MUG-CREST) has qty 0 and no ticket. No `customers` table exists, so requesters are free text.

---

## MCP tools (`mcp_server/server.py`)

Every agent uses these tools, and none of them reads the database directly. Each tool returns `found: false` on a miss instead of inventing data. All three are read-only. The full list after Problem 5 is further down.

| Tool | Reads table | Unlocks ticket | Why it's the right tool |
|---|---|---|---|
| `check_inventory(sku, size)` | `inventory` | **101** | The tee order turns on whether CC-TEE-WHITE size S is actually on the shelf, and this returns that exact qty (0). |
| `get_lease(lease_id)` | `leases` | **102** | The rent notice is only an email claim, so the agent has to confirm the amount ($2,400) and due date (09-02) against the lease on record before anyone pays. |
| `get_pricing(sku)` | `pricing` | **103** | A bulk discount can only be judged against list price and unit cost, and this gives the margin floor ($22) that any override must stay above. |

---

## Agent team (Problem 5): `backend/`

Built with PydanticAI. Every agent runs on `gpt-6-luna` through Portkey (`backend/config.py` refuses any other model). Each agent's prompt is in `backend/prompts/<agent>.md`, data types are in `backend/models.py`, and the team, its loops, and delegation are in `backend/agents.py`.

**Full connectivity:** every agent has a `delegate(to, task)` tool that can reach any other agent. Each agent only sees the MCP tools its job needs (least privilege), and no agent can see a tool that moves money.

| Agent | Job | MCP tools it can call | Output |
|---|---|---|---|
| **boss** | Reads each ticket, routes work, makes the final call, records it on the ticket | `get_shop_date`, `list_open_tickets`, `get_ticket`, `update_ticket`, `list_payments` | `TicketDecision` |
| **inventory** | Stock by SKU and size, shortfalls, which vendor restocks and when, blocked vendors | `get_shop_date`, `check_inventory`, `get_pricing`, `list_vendors`, `get_invoice` | `SpecialistReport` |
| **accounting** | Cash, invoices, margins, priorities; queues payments for human approval | `get_shop_date`, `get_cash_balance`, `get_invoice`, `get_lease`, `get_pricing`, `list_payments`, `request_payment` | `SpecialistReport` |
| **facilities** | Leases and rent; checks notices against the lease on record | `get_shop_date`, `get_lease`, `get_ticket` | `SpecialistReport` |
| **customer_service** | Drafts customer replies (`DRAFT — not sent`) from confirmed facts only | `get_shop_date`, `get_ticket`, `check_inventory`, `get_pricing` | `SpecialistReport` (with `draft_message`) |

**Audit trail:** `output/audit_trail.json` is append-only and never wiped. Every agent loop step is logged, with run id, ticket, agent, delegation chain and depth, step number, model, the event type, and token usage. The event types are `run_start` (the task), `model_response` (the model's text plus every tool call with its arguments), `tool_result` (what each tool returned, plus any retries), `delegate`, `delegate_refused` (with the reason), `run_end` (the final structured output and total usage), and `error`.

## MCP tools (full list after Problem 5)

| Tool | Table(s) | Who can call it |
|---|---|---|
| `get_shop_date` | `desk` | all agents |
| `list_tickets` | `tickets` | backend `/api/tickets` (not given to agents) |
| `list_open_tickets` | `tickets` | boss |
| `get_ticket` | `tickets` | boss, facilities, customer_service |
| `check_inventory` | `inventory` | inventory, customer_service |
| `get_pricing` | `pricing` | inventory, accounting, customer_service |
| `list_vendors` | `vendors`, `invoices` | inventory |
| `get_invoice` | `invoices`, `vendors`, `desk` | inventory, accounting |
| `get_lease` | `leases` | accounting, facilities |
| `get_cash_balance` | `cash_accounts`, `approvals` | accounting |
| `list_payments` | `payments`, `approvals` | boss, accounting |
| `request_payment` (write, no money moves) | `approvals`, `tickets` | accounting |
| `update_ticket` (write) | `tickets` | boss |
| `approve_payment` (**human only**) | `payments`, `cash_accounts`, `invoices`/`leases`, `approvals` | nobody but a human |
| `reject_payment` (**human only**) | `approvals` | nobody but a human |

## Safety

**Guardrails for real customers and real money**
- **Humans hold the checkbook.** Agents can only *request* payments. `approve_payment` and `reject_payment` are hidden from every agent, require a named human, and are logged in `payments.approved_by`.
- **Amounts come from the database, not the model.** `request_payment` looks up the bill itself, so an agent can't inflate or invent an amount.
- **No overdraft, double payment, or duplicates.** Requests are refused if cash minus pending approvals can't cover them, if the bill is already paid, or if the same bill is already pending. Payment is refused again if the balance would go negative at approval time.
- **Verify before paying.** Facilities checks every emailed notice against the lease on record, because spoofed rent and invoice emails are a classic fraud.
- **Least privilege.** Each agent only sees the tools its role needs, so Customer Service can't touch cash and Inventory can't queue payments.
- **No real outbound contact.** Customer messages are drafts marked `DRAFT — not sent`, and no tool emails customers or contacts vendors.
- **No invented facts.** Tools return `found: false` instead of guessing, and prompts forbid filling gaps.
- **Reorders move no cash.** We don't have a purchase-order tool. When a vendor `can_ship`, the Boss records the reorder (vendor, SKU, size, qty, earliest arrival) in the ticket note, and the vendor invoices after it ships.
- **Discount floor.** No price goes below `unit_cost`, and a human signs off on any override.
- **Full audit.** Every step, tool argument, tool result, and delegation is appended to `output/audit_trail.json`.
- **Secrets stay out.** `PORTKEY_API_KEY` is loaded from the course folder's `.env`, never committed or logged.
- **Clean slate.** `scripts/reset_db.py` runs before every full run.

**Token limits** (in `backend/config.py`)
- One model only: `gpt-6-luna`. Any other value fails at startup.
- At most 8 delegations per ticket, at most 3 levels deep, no delegating to yourself, and no loops back to an agent already in the chain.
- At most 40 model requests and 60 tool calls per ticket, counted across the whole team. Sub-agents share the ticket's usage counter.
- 150,000 total tokens per ticket, shared across every agent working it. Luna's reasoning tokens count here too.
- 4,000 output tokens per model response.
- Why these numbers: the first live run hit the old 1,200-token cap, because Luna reasons before it answers. The old per-agent 8-request cap also tripped, because sub-agents add to the parent's counter. Both were fixed in Problem 9.
- Audit fields are clipped to 2,000 characters.

---

## Backend routes (Problem 7): `backend/main.py`

Start it from `backend/` with `uvicorn main:app --reload --port 8000`, which serves `http://localhost:8000`. Every route reaches the shop through the MCP server except reset, which copies the original database file.

- `GET  http://localhost:8000/api/health`: confirms the server is up, the model (`gpt-6-luna`), and which database file it's using.
- `GET  http://localhost:8000/api/tickets`: all 3 tickets with status, an `is_resolved` flag, and the latest agent run for each.
- `POST http://localhost:8000/api/tickets/{id}/run`: starts the agent team on one ticket in the background (202). Only one run at a time.
- `GET  http://localhost:8000/api/runs`: status of each agent run (queued, running, done, or error) and the Boss's final decision.
- `GET  http://localhost:8000/api/events?limit=50&ticket_id=101`: recent audit-trail events, showing which agent spoke, what it said, which tools it used, and who it delegated to.
- `GET  http://localhost:8000/api/approvals`: the payment approval queue (pending first) and the payments ledger.
- `POST http://localhost:8000/api/approvals/{id}/approve` with body `{"approved_by": "name"}`: a **human** approves. This is the only route that moves cash; it writes `payments`, debits checking, and marks the bill paid, and it refuses a negative balance.
- `POST http://localhost:8000/api/approvals/{id}/reject` with body `{"rejected_by": "name", "reason": "..."}`: a human declines a request. No money moves.
- `GET  http://localhost:8000/api/cash`: the checking balance from `cash_accounts`, plus pending approvals and the balance if all of them were approved.
- `POST http://localhost:8000/api/reset`: copies `campus_customs.db` over the working copy for a fresh run. It's blocked while an agent run is in progress, and the audit trail is kept.

---

## Dashboard (Problem 8): `frontend/`

React + Vite + TypeScript at `http://localhost:5173`. Start it with `npm install`, then `npm run dev` in `frontend/`. It calls the API at `http://localhost:8000` (override with `VITE_API_URL`). The backend CORS allows `localhost:5173` and `127.0.0.1:5173`. Full design notes are in `output/design.md`.

- **The rail:** the 3 tickets as order slips with status stamps (Open, On stage, Needs your OK, Resolved). Click one to pick it.
- **The stage:** **▶ Start the band** calls `POST /api/tickets/{id}/run`. The 5 agents stand in a band lineup with VU meters and a live status line, and the **Live set** feed shows each step from `/api/events`, indented by delegation depth.
- **Sign here:** pending approvals show as checks. A human types their name, then clicks Approve & pay or Reject (`/api/approvals/{id}/approve|reject`). Buttons stay disabled until a name is entered.
- **Register:** the checking balance from `/api/cash`. It rolls down when a payment is approved and shows what's pending.
- **Liner notes:** the Boss's call plus a short summary for each agent. Customer messages are tagged *Draft · not sent*.
- **Amp knob:** 3 (1938 big band) → 5 (1956 rockabilly) → 7 (1975 shop) → 11 (1984 metal). Only the look changes.
- **Banner:** "No customer is emailed and no real vendor is called. Money moves only when a human signs."

## Full run (Problem 9)

| | |
|---|---|
| Start after reset | $3,400.00 |
| 101 Bulldog tee | Invoice 501 paid, −$840 (approval #1, Jared Miller). Reorder of 1 recorded. **resolved** |
| 102 Rent due | Lease 1 rent paid, −$2,400 (approval #2, Jared Miller). Next due 2026-10-02. **resolved** |
| 103 Hoodie discount | 10% off at $52.20, above the $22 cost. Reorder of 12 recorded, $0. **resolved** |
| End | **$160.00**, matching `cash_accounts` in `campus_customs_new.db` |

Each ticket took two passes: a first pass that queued payments or got blocked, the human signatures on the board, then a second pass that confirmed the payments and closed the ticket. Outputs: `desk_tickets.html` (Actual and Cash tabs), `resolve_tickets.json`, `resolved_board.html` (with `screens/`), and `audit_trail.json`, which holds every real run, including the two early 101 attempts that crashed.
