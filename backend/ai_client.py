"""One place that decides which AI model the app uses, and meters per-user AI use.

Switch model without code changes (Emergent -> backend environment variables):
    AI_PROVIDER=anthropic
    AI_MODEL=claude-haiku-5-5
Unset = Claude Haiku 5.5. At startup verify_model() tests it once and, if it does not answer,
switches the whole app to openai / gpt-4o-mini by itself. To force the old model: AI_PROVIDER=openai, AI_MODEL=gpt-4o-mini.
Limits per person per day: AI_DAILY_LIMIT (big actions, default 3) and AI_SWAP_LIMIT (ingredient swaps, default 4).
"""
import hashlib
import os
import re
import json
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException

DEFAULT_PROVIDER = "anthropic"
DEFAULT_MODEL = "claude-haiku-5-5"
FALLBACK_PROVIDER = "openai"
FALLBACK_MODEL = "gpt-4o-mini"


def model_for():
    """(provider, model) for everyday AI calls."""
    provider = (os.environ.get("AI_PROVIDER") or DEFAULT_PROVIDER).strip()
    model = (os.environ.get("AI_MODEL") or DEFAULT_MODEL).strip()
    return provider, model


def _int_env(name: str, default: int) -> int:
    try:
        return max(0, int(os.environ.get(name, str(default))))
    except ValueError:
        return default


def daily_limit() -> int:
    """Big AI actions per person per day (new recipe ideas, recipe conversions)."""
    return _int_env("AI_DAILY_LIMIT", 3)


def swap_limit() -> int:
    """Ingredient swaps per person per day (about a tenth the cost of a big action)."""
    return _int_env("AI_SWAP_LIMIT", 4)


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _field(kind: str) -> str:
    return "swap_count" if kind == "swap" else "count"


def _limit(kind: str) -> int:
    return swap_limit() if kind == "swap" else daily_limit()


async def uses_left(db, user_id: str, kind: str = "big") -> int:
    doc = await db.ai_usage.find_one({"user_id": user_id, "day": _today()})
    return max(0, _limit(kind) - (doc or {}).get(_field(kind), 0))


async def spend_one(db, user_id: str, kind: str = "big") -> None:
    """Count one AI call for this person today; refuse politely when the daily allowance is used up."""
    if await uses_left(db, user_id, kind) <= 0:
        what = "ingredient swaps" if kind == "swap" else "AI recipe requests"
        raise HTTPException(
            status_code=429,
            detail=f"You have used today's {_limit(kind)} {what}. They reset tomorrow.",
        )
    await db.ai_usage.update_one(
        {"user_id": user_id, "day": _today()},
        {"$inc": {_field(kind): 1}, "$set": {"updated_at": datetime.now(timezone.utc)}},
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


async def verify_model() -> str:
    """Run once at startup: if the chosen model does not answer, fall back to GPT-4o mini for this run
    so a wrong model name can never break recipe imports and the other AI features."""
    import logging
    log = logging.getLogger(__name__)
    provider, model = model_for()
    if (provider, model) == (FALLBACK_PROVIDER, FALLBACK_MODEL) or not os.environ.get("EMERGENT_LLM_KEY"):
        return f"{provider}/{model}"
    try:
        data = await ask_json("Return only valid JSON.", 'Reply with exactly {"ok": true}', "verify")
        if data.get("ok"):
            log.info(f"AI model in use: {provider}/{model}")
            return f"{provider}/{model}"
        raise ValueError("unexpected reply")
    except Exception as e:
        log.warning(f"AI model {provider}/{model} failed its startup check ({e}); using {FALLBACK_PROVIDER}/{FALLBACK_MODEL}")
        os.environ["AI_PROVIDER"], os.environ["AI_MODEL"] = FALLBACK_PROVIDER, FALLBACK_MODEL
        return f"{FALLBACK_PROVIDER}/{FALLBACK_MODEL}"
