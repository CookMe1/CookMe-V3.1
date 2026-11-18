"""Make sure every recipe has a decent description, whether it was imported, typed in, or came with the library.

weak description  -> short AI-written one (gpt-4o-mini, about 0.02 cents) -> if the AI is unavailable, a plain
                     sentence built from the ingredients (master_enrich.make_description).
Decent descriptions written by the person or the source site are never touched.
"""
import asyncio
import logging
import os
import re
import uuid

from master_enrich import GENERIC_DESC, make_description

logger = logging.getLogger(__name__)
MIN_LEN = 40
_JUNK = re.compile(r"(https?://|www\.|<[a-z/][^>]*>|subscribe|follow (?:us|me)|click here|instagram|facebook|tiktok|youtube|"
                   r"link in (?:bio|description)|#\w+.*#\w+|©|all rights reserved|\bjoin\b.*\bnewsletter)", re.I)
_AI_TELLS = re.compile(r"(as an ai|i cannot|i can't|here is|here's a|sure[,!]|description:)", re.I)


def description_is_weak(description, title: str = "") -> bool:
    d = re.sub(r"\s+", " ", str(description or "")).strip()
    if len(d) < MIN_LEN:
        return True
    if title and d.lower().rstrip(".") == title.lower().rstrip("."):
        return True
    if GENERIC_DESC.match(d) or re.match(r"^A [A-Za-z ]{0,25}dish (?:made with|from our recipe collection)", d):
        return True
    return bool(_JUNK.search(d))


def _clean(text: str) -> str:
    t = re.sub(r"\s+", " ", str(text or "")).strip().strip('"“”\'')
    return t


async def _ask_llm(recipe: dict) -> str:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise RuntimeError("no LLM key")
    ings = []
    for i in (recipe.get("ingredients") or [])[:10]:
        ings.append((i.get("item") if isinstance(i, dict) else str(i)) or "")
    steps = " ".join(str(s) for s in (recipe.get("steps") or [])[:3])[:500]
    prompt = (f"Title: {recipe.get('title', '')}\nCuisine: {recipe.get('cuisine') or 'not stated'}\n"
              f"Main ingredients: {', '.join(x for x in ings if x)}\nMethod (start): {steps}\n\n"
              "Write a description of this dish for a recipe app: 1 or 2 sentences, 25 to 45 words, British English, "
              "appetising but honest. Only mention things supported by the title, ingredients or method. "
              "No emoji, no exclamation marks, no brand names, do not start with the dish title or the word 'Delicious'. "
              "Reply with the description only.")
    chat = LlmChat(api_key=key, session_id=f"desc_{uuid.uuid4().hex[:8]}",
                   system_message="You write short, accurate, appetising recipe descriptions.").with_model("openai", "gpt-4o-mini")
    return await asyncio.wait_for(chat.send_message(UserMessage(text=prompt)), timeout=15)


async def improved_description(recipe: dict, use_ai: bool = True):
    """-> (description, source) where source is 'ai' or 'auto'."""
    if use_ai:
        try:
            text = _clean(await _ask_llm(recipe))
            if MIN_LEN <= len(text) <= 320 and not _AI_TELLS.search(text) and not _JUNK.search(text):
                return text, "ai"
        except Exception as e:
            logger.info("description AI skipped: %s", e)
    return make_description(recipe), "auto"
