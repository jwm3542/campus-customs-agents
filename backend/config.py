"""Single home for model, Portkey, paths, and token limits."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

BACKEND = Path(__file__).resolve().parent
PROJECT = BACKEND.parent
load_dotenv(PROJECT / ".env")
load_dotenv(PROJECT.parent / ".env")  # course-folder .env holds PORTKEY_API_KEY

# HW 5 rule: gpt-6-luna for every agent, nothing else.
ALLOWED_MODEL = "gpt-6-luna"
MODEL_NAME = os.getenv("OPENAI_MODEL", ALLOWED_MODEL)
if MODEL_NAME != ALLOWED_MODEL:
    raise RuntimeError(f"OPENAI_MODEL must be {ALLOWED_MODEL!r} for HW 5 (got {MODEL_NAME!r}).")

PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")

PROMPTS_DIR = BACKEND / "prompts"
OUTPUT_DIR = PROJECT / "output"
AUDIT_PATH = OUTPUT_DIR / "audit_trail.json"
MCP_SERVER_SCRIPT = PROJECT / "mcp_server" / "server.py"
DB_PATH = Path(os.getenv("CAMPUS_CUSTOMS_DB", PROJECT / "data" / "campus_customs_new.db"))

# Token guardrails (per ticket unless noted)
MAX_DELEGATIONS_PER_TICKET = 8      # total hand-offs across the whole team
MAX_DELEGATION_DEPTH = 3            # boss -> A -> B -> C, no deeper
# Usage is shared by every agent on a ticket (sub-agents add to the parent's counter),
# so these caps are per TICKET, not per agent. 8/12 per agent tripped mid-run.
REQUESTS_PER_TICKET = 40            # model calls across the whole team on one ticket
TOOL_CALLS_PER_TICKET = 60
TOTAL_TOKENS_PER_TICKET = 150_000   # Luna's reasoning tokens count here too
MAX_OUTPUT_TOKENS = 4_000           # per model response (Luna reasons before it answers; 1,200 ran out)
AUDIT_TEXT_LIMIT = 2_000            # chars kept per logged field


def require_api_key() -> str:
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set (expected in the course folder .env).")
    return key


def build_model():
    from pydantic_ai.models.openai import OpenAIResponsesModel
    from pydantic_ai.providers.openai import OpenAIProvider

    provider = OpenAIProvider(base_url=PORTKEY_BASE_URL, api_key=require_api_key())
    return OpenAIResponsesModel(MODEL_NAME, provider=provider)


def load_prompt(agent_name: str) -> str:
    return (PROMPTS_DIR / f"{agent_name}.md").read_text(encoding="utf-8").strip()
