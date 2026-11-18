"""One place that decides which AI model the app uses, and meters per-user AI use.

Switch model without code changes (Emergent -> backend environment variables):
    AI_PROVIDER=anthropic
    AI_MODEL=claude-haiku-5-5
Leave them unset to keep the current default (openai / gpt-4o-mini).
"""
import hashlib
import os
import re
import json
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException

DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL = "gpt-4o-mini"


def model_for():
    """(provider, model) for everyday AI calls."""
    provider = (os.environ.get("AI_PROVIDER") or DEFAULT_PROVIDER).strip()
    model = (os.environ.get("AI_MODEL") or DEFAULT_MODEL).strip()
    return provider, model


def daily_limit() -> int:
    try:
        return max(1, int(os.environ.get("AI_DAILY_LIMIT", "20")))
    except ValueError:
        return 20


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


async def uses_left(db, user_id: str) -> int:
    doc = await db.ai_usage.find_one({"user_id": user_id, "day": _today()})
    return max(0, daily_limit() - (doc or {}).get("count", 0))


async def spend_one(db, user_id: str) -> None:
    """Count one AI call for this person today; refuse politely when the daily allowance is used up."""
    if await uses_left(db, user_id) <= 0:
        raise HTTPException(
            status_code=429,
            detail=f"You have used today's {daily_limit()} AI requests. They reset tomorrow.",
        )
    await db.ai_usage.update_one(
        {"user_id": user_id, "day": _today()},
        {"$inc": {"count": 1}, "$set": {"updated_at": datetime.now(timezone.utc)}},
        upsert=True,
    )


def key_for(*parts) -> str:
    raw = "|".join(str(p).strip().lower() for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def parse_json(text: str):
    """Pull the JSON object out of a model reply (it may be wrapped in ```json fences)."""
    clean = re.sub(r"```json|```", "", text or "").strip()
    m = re.search(r"\{.*\}", clean, re.DOTALL)
    return json.loads(m.group() if m else clean)


async def ask_json(system: str, prompt: str, session_prefix: str = "ai"):
    """One AI call that returns parsed JSON, using the configured model."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=os.environ.get("EMERGENT_LLM_KEY"),
        session_id=f"{session_prefix}_{uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model(*model_for())
    return parse_json(await chat.send_message(UserMessage(text=prompt)))


# Shared guidance so every AI-written recipe has proper cookbook-quality method steps.
COOKING_STYLE = """Write the method like a good cookbook, for a home cook who has never made it:
- 6 to 10 numbered steps. Start with prep: preheat the oven (give both °C and °F), wash/chop, and what to have ready.
- Each step is one clear action. Always give the heat level (low / medium / medium-high / high), the time, and the pan or dish size and type.
- Give a sight, smell or touch cue for doneness, e.g. "until golden brown, about 4 minutes" or "until the sauce coats the back of a spoon".
- Say when to season and to taste, and when things can be done at the same time to save time.
- Include one short tip on the step where people most often go wrong, and finish with resting and serving.
- Use exact amounts from the ingredient list inside the steps; never invent ingredients that are not listed."""
