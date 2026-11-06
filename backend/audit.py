"""Append-only audit trail at output/audit_trail.json (a JSON array; never wiped)."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import AUDIT_PATH, AUDIT_TEXT_LIMIT
from models import AuditEvent

_lock = asyncio.Lock()


def clip(value: Any, limit: int = AUDIT_TEXT_LIMIT) -> Any:
    """Keep audit entries readable and small; never hold secrets (none pass through here)."""
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + f"... [+{len(value) - limit} chars]"
    if isinstance(value, dict):
        return {k: clip(v, limit) for k, v in value.items()}
    if isinstance(value, list):
        return [clip(v, limit) for v in value]
    return value


def _append(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    events: list = []
    if path.exists() and path.stat().st_size:
        events = json.loads(path.read_text(encoding="utf-8"))
    events.append(entry)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(events, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


async def record(**fields: Any) -> None:
    fields.setdefault("ts", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    fields["detail"] = clip(fields.get("detail", {}))
    entry = AuditEvent(**fields).model_dump()
    async with _lock:
        _append(AUDIT_PATH, entry)
