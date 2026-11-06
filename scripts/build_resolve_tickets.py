"""Build output/resolve_tickets.json from the working DB and the audit trail.

Run after the full Problem 9 run:  python scripts/build_resolve_tickets.py
The run ids below are the Problem 9 passes recorded in output/audit_trail.json.
"""
import json, sqlite3, collections

import os, pathlib
os.chdir(pathlib.Path(__file__).resolve().parent.parent / "output")
DB = "../data/campus_customs_new.db"
c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
tickets = {r["id"]: dict(r) for r in c.execute("select * from tickets")}
approvals = [dict(r) for r in c.execute("select * from approvals")]
balance = c.execute("select balance from cash_accounts where name='checking'").fetchone()[0]

events = json.load(open("audit_trail.json", encoding="utf-8"))
runs = collections.OrderedDict()
for e in events:
    runs.setdefault(e["run_id"], []).append(e)

FINAL = {101: "ad2ec83868b5", 102: "6e9d553b3e99", 103: "c55cefe75e4e"}
FIRST = {101: "357ce546e35e", 102: "f4ae3aa186c0", 103: "46f92c383d72"}
OUTCOME = {
    101: "Paid overdue invoice 501 ($840, human-approved) so Bulldog Print Co can ship; reorder of 1 white tee size S recorded, earliest arrival 2026-09-05. Customer reply drafted, not sent.",
    102: "Verified the rent notice against lease 1 and paid $2,400 to Elm City Properties (human-approved); lease next due rolled to 2026-10-02.",
    103: "Approved 10% bulk discount ($52.20 each, above $22 cost); 8 of 20 on hand, reorder of 12 recorded with Bulldog Print Co, earliest arrival 2026-09-05. Reply drafted, not sent.",
}

def contributions(run_ids):
    out = collections.OrderedDict()
    for rid in run_ids:
        for e in runs[rid]:
            if e["event"] == "run_end" and e["agent"] != "boss":
                o = e["detail"]["output"]
                out.setdefault(e["agent"], []).append(o["summary"])
            if e["event"] == "run_end" and e["agent"] == "boss":
                out.setdefault("boss", []).append(e["detail"]["output"]["decision"])
    return {a: v for a, v in out.items()}

result = []
for tid in (101, 102, 103):
    t = tickets[tid]
    result.append({
        "id": tid,
        "subject": t["subject"],
        "final_status": t["status"],
        "short_outcome": OUTCOME[tid],
        "agent_contributions": contributions([FIRST[tid], FINAL[tid]]),
        "human_approvals": [
            {k: a[k] for k in ("id", "kind", "ref_id", "amount", "status", "decided_by", "decided_at")}
            for a in approvals if a["ticket_id"] == tid
        ],
        "run_ids": [FIRST[tid], FINAL[tid]],
    })

doc = {
    "model": "gpt-6-luna",
    "database": "data/campus_customs_new.db",
    "starting_checking_balance": 3400.0,
    "ending_checking_balance": balance,
    "tickets": result,
}
assert balance == 3400.0 - sum(a["amount"] for a in approvals if a["status"] == "approved")
json.dump(doc, open("resolve_tickets.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print([(r["id"], r["final_status"], list(r["agent_contributions"]), len(r["human_approvals"])) for r in result], balance)
