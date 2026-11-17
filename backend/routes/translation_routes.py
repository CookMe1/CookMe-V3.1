import logging
logger = logging.getLogger(__name__)
"""
translation_routes.py
=====================
Handles recipe translation and user language preference.

Translation priority:
  1. English — no-op, return immediately
  2. DeepL Free API — covers 23 of 28 supported languages, 500k chars/month free
  3. AI fallback — for Arabic, Hindi, Thai, Vietnamese, Hebrew, Catalan

DeepL language codes differ slightly from ISO 639-1:
  - Portuguese → PT-PT (European) or PT-BR (Brazilian)
  - Chinese → ZH (simplified)
  - English target → EN-GB

Endpoints:
  POST /api/translate/recipe       — translate a full recipe
  PUT  /api/translate/language     — save user preferred language
  GET  /api/translate/languages    — list supported languages
"""

import os
import re
import json
import uuid
import hashlib
import httpx
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from auth import get_current_user
from emergentintegrations.llm.chat import LlmChat, UserMessage
from cache import get_cache, set_cache

router = APIRouter(prefix="/translate", tags=["translation"])

EMERGENT_KEY   = os.environ.get("EMERGENT_LLM_KEY")
DEEPL_API_KEY  = os.environ.get("DEEPL_API_KEY", "")
# Free tier keys end with :fx and use api-free.deepl.com; Pro uses api.deepl.com
DEEPL_BASE_URL = "https://api-free.deepl.com" if DEEPL_API_KEY.endswith(":fx") \
                 else "https://api.deepl.com"

TTL_TRANSLATION = 90  # days

# ── Language catalogue ────────────────────────────────────────────────────────

SUPPORTED_LANGUAGES = [
    {"code": "en", "name": "English",    "native": "English",            "flag": "🇬🇧", "deepl": "EN-GB"},
    {"code": "es", "name": "Spanish",    "native": "Español",            "flag": "🇪🇸", "deepl": "ES"},
    {"code": "fr", "name": "French",     "native": "Français",           "flag": "🇫🇷", "deepl": "FR"},
    {"code": "de", "name": "German",     "native": "Deutsch",            "flag": "🇩🇪", "deepl": "DE"},
    {"code": "it", "name": "Italian",    "native": "Italiano",           "flag": "🇮🇹", "deepl": "IT"},
    {"code": "pt", "name": "Portuguese", "native": "Português",          "flag": "🇵🇹", "deepl": "PT-PT"},
    {"code": "nl", "name": "Dutch",      "native": "Nederlands",         "flag": "🇳🇱", "deepl": "NL"},
    {"code": "pl", "name": "Polish",     "native": "Polski",             "flag": "🇵🇱", "deepl": "PL"},
    {"code": "ru", "name": "Russian",    "native": "Русский",            "flag": "🇷🇺", "deepl": "RU"},
    {"code": "zh", "name": "Chinese",    "native": "中文",                "flag": "🇨🇳", "deepl": "ZH"},
    {"code": "ja", "name": "Japanese",   "native": "日本語",              "flag": "🇯🇵", "deepl": "JA"},
    {"code": "ko", "name": "Korean",     "native": "한국어",              "flag": "🇰🇷", "deepl": "KO"},
    {"code": "ar", "name": "Arabic",     "native": "العربية",            "flag": "🇸🇦", "deepl": None},   # AI only
    {"code": "hi", "name": "Hindi",      "native": "हिन्दी",             "flag": "🇮🇳", "deepl": None},   # AI only
    {"code": "tr", "name": "Turkish",    "native": "Türkçe",             "flag": "🇹🇷", "deepl": "TR"},
    {"code": "sv", "name": "Swedish",    "native": "Svenska",            "flag": "🇸🇪", "deepl": "SV"},
    {"code": "da", "name": "Danish",     "native": "Dansk",              "flag": "🇩🇰", "deepl": "DA"},
    {"code": "no", "name": "Norwegian",  "native": "Norsk",              "flag": "🇳🇴", "deepl": "NB"},
    {"code": "fi", "name": "Finnish",    "native": "Suomi",              "flag": "🇫🇮", "deepl": "FI"},
    {"code": "el", "name": "Greek",      "native": "Ελληνικά",           "flag": "🇬🇷", "deepl": "EL"},
    {"code": "he", "name": "Hebrew",     "native": "עברית",              "flag": "🇮🇱", "deepl": None},   # AI only
    {"code": "th", "name": "Thai",       "native": "ภาษาไทย",           "flag": "🇹🇭", "deepl": None},   # AI only
    {"code": "vi", "name": "Vietnamese", "native": "Tiếng Việt",        "flag": "🇻🇳", "deepl": None},   # AI only
    {"code": "id", "name": "Indonesian", "native": "Bahasa Indonesia",   "flag": "🇮🇩", "deepl": "ID"},
    {"code": "ro", "name": "Romanian",   "native": "Română",             "flag": "🇷🇴", "deepl": "RO"},
    {"code": "uk", "name": "Ukrainian",  "native": "Українська",         "flag": "🇺🇦", "deepl": "UK"},
    {"code": "cs", "name": "Czech",      "native": "Čeština",            "flag": "🇨🇿", "deepl": "CS"},
    {"code": "hu", "name": "Hungarian",  "native": "Magyar",             "flag": "🇭🇺", "deepl": "HU"},
    {"code": "ca", "name": "Catalan",    "native": "Català",             "flag": "🏴", "deepl": None},   # AI only
]

LANG_MAP = {l["code"]: l for l in SUPPORTED_LANGUAGES}


# ── Models ────────────────────────────────────────────────────────────────────

class RecipeTranslateRequest(BaseModel):
    recipe_id:            Optional[str] = None
    title:                str
    description:          Optional[str] = ""
    ingredients:          list
    steps:                list
    tags:                 Optional[list] = []
    target_language:      str   # ISO 639-1
    target_language_name: str


class LanguagePreferenceRequest(BaseModel):
    language_code: str
    language_name: str


# ── DeepL translation ─────────────────────────────────────────────────────────

async def translate_via_deepl(texts: list[str], target_deepl_code: str) -> list[str]:
    """
    Translate a list of strings using the DeepL Free API.
    Returns translated strings in the same order.
    Raises on failure so caller can fall back to AI.
    """
    if not DEEPL_API_KEY:
        raise ValueError("DEEPL_API_KEY not set")

    # Filter empty strings but keep index mapping
    indices = [i for i, t in enumerate(texts) if t and t.strip()]
    non_empty = [texts[i] for i in indices]

    if not non_empty:
        return texts

    payload = {
        "text": non_empty,
        "target_lang": target_deepl_code,
        "preserve_formatting": True,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{DEEPL_BASE_URL}/v2/translate",
            headers={
                "Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if resp.status_code == 456:
        raise RuntimeError("DeepL quota exceeded this month — falling back to AI")
    if resp.status_code != 200:
        raise RuntimeError(f"DeepL returned {resp.status_code}: {resp.text[:200]}")

    translations = resp.json().get("translations", [])
    result = list(texts)  # copy
    for idx, translated in zip(indices, translations):
        result[idx] = translated.get("text", texts[idx])
    return result


async def translate_recipe_with_deepl(
    body: "RecipeTranslateRequest",
    deepl_code: str,
) -> dict:
    """
    Translate a recipe using DeepL. Sends all text fields in one batched call.
    """
    # Flatten all translatable strings with position markers
    title       = body.title or ""
    description = body.description or ""

    # Ingredients: translate the 'item' field of each ingredient
    ing_items  = [i.get("item", "") if isinstance(i, dict) else str(i)
                  for i in (body.ingredients or [])]
    # Steps: translate each step string
    step_texts = [s if isinstance(s, str) else s.get("text", str(s))
                  for s in (body.steps or [])]
    # Tags
    tag_texts  = [str(t) for t in (body.tags or [])]

    # Batch everything into one API call
    batch = [title, description] + ing_items + step_texts + tag_texts
    translated = await translate_via_deepl(batch, deepl_code)

    # Unpack results
    t_title       = translated[0]
    t_description = translated[1]
    offset = 2

    t_ing_items = translated[offset: offset + len(ing_items)]
    offset += len(ing_items)

    t_steps = translated[offset: offset + len(step_texts)]
    offset += len(step_texts)

    t_tags = translated[offset: offset + len(tag_texts)]

    # Rebuild ingredients with translated item names
    t_ingredients = []
    for original, t_item in zip(body.ingredients or [], t_ing_items):
        if isinstance(original, dict):
            t_ingredients.append({**original, "item": t_item})
        else:
            t_ingredients.append({"item": t_item, "amount": ""})

    # Rebuild steps
    t_step_list = []
    for original, t_text in zip(body.steps or [], t_steps):
        if isinstance(original, str):
            t_step_list.append(t_text)
        elif isinstance(original, dict):
            t_step_list.append({**original, "text": t_text})
        else:
            t_step_list.append(t_text)

    return {
        "title":       t_title,
        "description": t_description,
        "ingredients": t_ingredients,
        "steps":       t_step_list,
        "tags":        t_tags,
        "translated":  True,
        "engine":      "deepl",
    }


# ── AI translation fallback ───────────────────────────────────────────────────

async def translate_recipe_with_ai(body: "RecipeTranslateRequest") -> dict:
    """AI translation for languages DeepL doesn't support."""
    lang_name = body.target_language_name
    ingredients_text = json.dumps(body.ingredients, ensure_ascii=False)
    steps_text       = json.dumps(body.steps, ensure_ascii=False)
    tags_text        = json.dumps(body.tags or [], ensure_ascii=False)

    prompt = f"""Translate this recipe into {lang_name}.
Preserve all measurements exactly. Use standard {lang_name} culinary terms.
Return ONLY valid JSON with no markdown:
{{
  "title": "translated title",
  "description": "translated description",
  "ingredients": [translated ingredients array — same structure as input],
  "steps": [translated steps array],
  "tags": [translated tags array]
}}

Input:
Title: {body.title}
Description: {body.description}
Ingredients: {ingredients_text}
Steps: {steps_text}
Tags: {tags_text}"""

    chat = LlmChat(
        api_key=EMERGENT_KEY,
        session_id=f"translate_{uuid.uuid4().hex[:8]}",
        system_message=f"You are a professional culinary translator. Translate recipes into {lang_name} accurately and naturally. Return only valid JSON.",
    ).with_model("openai", "gpt-5.2")

    response_text = await chat.send_message(UserMessage(text=prompt))
    clean = re.sub(r"```json|```", "", response_text).strip()
    match = re.search(r"\{.*\}", clean, re.DOTALL)
    translated = json.loads(match.group() if match else clean)

    return {
        "title":       translated.get("title",       body.title),
        "description": translated.get("description", body.description),
        "ingredients": translated.get("ingredients", body.ingredients),
        "steps":       translated.get("steps",       body.steps),
        "tags":        translated.get("tags",        body.tags),
        "translated":  True,
        "engine":      "ai",
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/languages")
async def get_languages():
    return {"languages": SUPPORTED_LANGUAGES}


@router.put("/language")
async def set_language_preference(body: LanguagePreferenceRequest, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)

    if body.language_code not in LANG_MAP:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {body.language_code}")

    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {
            "preferred_language":      body.language_code,
            "preferred_language_name": body.language_name,
        }}
    )
    return {"message": "Language preference saved", "language": body.language_code}


@router.post("/recipe")
async def translate_recipe(body: RecipeTranslateRequest, request: Request):
    """
    Translate a full recipe.
    Priority: cache → DeepL (free, 23 languages) → AI (5 languages) → original
    """
    db = request.app.state.db
    await get_current_user(request, db)

    # English — return immediately
    if body.target_language == "en":
        return {
            "title":       body.title,
            "description": body.description,
            "ingredients": body.ingredients,
            "steps":       body.steps,
            "tags":        body.tags,
            "translated":  False,
        }

    lang_info = LANG_MAP.get(body.target_language)
    if not lang_info:
        raise HTTPException(status_code=400, detail=f"Unsupported language: {body.target_language}")

    # Build cache key
    if body.recipe_id:
        cache_key = f"translation:{body.recipe_id}:{body.target_language}"
    else:
        content_hash = hashlib.sha256(
            (body.title + str(body.ingredients)).encode()
        ).hexdigest()[:20]
        cache_key = f"translation:{content_hash}:{body.target_language}"

    # Check cache
    cached = await get_cache(db, cache_key)
    if cached:
        cached["translated"]  = True
        cached["from_cache"]  = True
        return cached

    # Translate
    deepl_code = lang_info.get("deepl")
    result = None

    if deepl_code and DEEPL_API_KEY:
        try:
            result = await translate_recipe_with_deepl(body, deepl_code)
        except Exception as e:
            logger.info(f"DeepL failed ({e}), falling back to AI")

    if result is None:
        # AI fallback — for unsupported languages or DeepL failure
        result = await translate_recipe_with_ai(body)

    result["from_cache"] = False

    # Cache for 90 days
    await set_cache(db, cache_key, result, ttl_days=TTL_TRANSLATION)

    # Also persist translation into the recipe document if recipe_id provided
    if body.recipe_id:
        translation_field = f"translations.{body.target_language}"
        await db.recipes.update_one(
            {"recipe_id": body.recipe_id},
            {"$set": {translation_field: {
                "title":          result["title"],
                "description":    result["description"],
                "ingredients":    result["ingredients"],
                "steps":          result["steps"],
                "tags":           result["tags"],
                "engine":         result.get("engine", "unknown"),
                "translated_at":  datetime.now(timezone.utc).isoformat(),
            }}}
        )

    return result
