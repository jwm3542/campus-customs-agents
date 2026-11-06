# Campus Customs Multi-Agent Operations (HW 5)

Five PydanticAI agents (Boss, Inventory, Accounting, Facilities, Customer Service) work the Campus Customs ticket desk. They use one FastMCP server over a SQLite shop database, a FastAPI backend, and a React dashboard where a human watches the agents and signs every payment.

- **Model:** `gpt-6-luna` only, routed through Portkey. `backend/config.py` refuses to start with any other model.
- **No real contact:** no customers are emailed and no real vendors are called. Agents write drafts only.
- **Human approval:** agents can only *request* a payment. Cash moves only when a human clicks **Approve & pay** on the board, and a payment that would take checking negative is refused.

## Layout

```
HW 5/
├── AI_prompts.md            # every prompt, problem by problem
├── .env.example             # variable names only (real key lives in an untracked .env)
├── .mcp.json                # registers the MCP server for Claude Code
├── data/
│   ├── campus_customs.db        # original, never modified
│   └── campus_customs_new.db    # working copy the agents update
├── mcp_server/              # FastMCP server: the only way to touch the database
├── backend/                 # FastAPI routes + the 5-agent team + prompts/
├── frontend/                # React + Vite + TypeScript ops desk
├── scripts/
│   ├── reset_db.py              # restore the working copy from the original
│   └── build_resolve_tickets.py # rebuild output/resolve_tickets.json
└── output/
    ├── harness.md               # tables, MCP tools, agents, routes, dashboard, safety
    ├── mcp_smoke.json           # Problem 4 tool tests
    ├── desk_tickets.html        # plan vs actual per ticket, Cash, Reflection
    ├── design.md                # dashboard design choices
    ├── resolve_tickets.json     # outcome, agent contributions, approvals per ticket
    ├── resolved_board.html      # board screenshots (screens/)
    └── audit_trail.json         # every agent step from the real runs
```

## Run it

Commands below are for Windows (Git Bash or PowerShell). On macOS/Linux, use `.venv/bin/` instead of `.venv/Scripts/`.

### 0. Setup (once)

```bash
git clone https://github.com/jwm3542/campus-customs-agents.git
cd campus-customs-agents
python -m venv .venv
.venv/Scripts/pip install -r backend/requirements.txt
cp .env.example .env          # then paste your own PORTKEY_API_KEY into .env
```

`.env` is git-ignored. The real key is never in this repo.

### 1. Copy the original DB to the working copy (clean run)

`data/campus_customs.db` is the untouched original. `data/campus_customs_new.db` is the working copy the agents change. The working copy in this repo holds the **finished** run (checking = $160). For a clean run, copy the original over it:

```bash
python scripts/reset_db.py    # same as: cp data/campus_customs.db data/campus_customs_new.db
```

Checking should now read **$3,400.00**.

### 2. Start the MCP server

The backend launches `mcp_server/server.py` itself over stdio, so for a normal run you skip this step. To start it on its own (for example, to test the tools from Claude Code, which reads `.mcp.json`):

```bash
.venv/Scripts/python mcp_server/server.py
```

It's the only code that touches the database.

### 3. Start the FastAPI backend

```bash
cd backend
../.venv/Scripts/python -m uvicorn main:app --port 8000
```

### 4. Start the React board (second terminal)

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

### 5. Full three-ticket run

1. **Reset the DB first** (step 1), with the backend stopped, so the run starts at $3,400.
2. Start the backend and the board.
3. For 101, 102, then 103: pick the ticket on the rail and hit **▶ Start the band**.
4. Sign each check under **Sign here** (type your name, then **Approve & pay**). No cash moves without that click.
5. Run each ticket again so the Boss confirms the payment and marks it resolved.
6. Expected end balance: **$160.00**.

## Result of the full run (Problem 9)

| Ticket | Outcome | Cash |
|---|---|---|
| Start | after reset | $3,400.00 |
| 101 Bulldog tee | invoice 501 paid (human-approved), reorder recorded, **resolved** | −$840.00 |
| 102 Rent due | lease 1 rent paid (human-approved), **resolved** | −$2,400.00 |
| 103 Hoodie discount | 10% off at $52.20 (above $22 cost), reorder recorded, **resolved** | $0.00 |
| End | matches `cash_accounts` | **$160.00** |
