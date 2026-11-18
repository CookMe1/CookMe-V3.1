"""AI helpers on a recipe: ingredient swaps and dietary conversion.

Both use the configured everyday model (see ai_client.py), are cached so a repeat question costs nothing,
and count against each person's daily AI allowance only when the AI actually runs.
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

import public_sharing as ps
from ai_client import ask_json, spend_one, uses_left, key_for, daily_limit, COOKING_STYLE
from auth import get_current_user
from cache import get_cache, set_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])

DIETS = {
    "vegan": "vegan (no meat, fish, dairy, eggs or honey)",
    "vegetarian": "vegetarian (no meat or fish)",
    "gluten-free": "gluten-free (no wheat, barley, rye or regular oats; check stock cubes, sauces and pasta)",
    "dairy-free": "dairy-free (no milk, butter, cream, cheese or yoghurt)",
    "low-carb": "low-carb (cut or replace sugar, flour, rice, pasta, potatoes and bread)",
    "nut-free": "nut-free (no nuts or nut oils or nut-based products)",
}
CACHE_DAYS = 90


class SubstituteRequest(BaseModel):
    ingredient: str
    recipe_title: Optional[str] = None
    diet: Optional[str] = None


class ConvertRequest(BaseModel):
    recipe_id: str
    diet: str


@router.get("/usage")
async def ai_usage(request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    return {"left_today": await uses_left(db, user["user_id"]), "daily_limit": daily_limit()}


@router.post("/substitutes")
async def substitutes(body: SubstituteRequest, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    name = (body.ingredient or "").strip()[:120]
    if not name:
        raise HTTPException(status_code=400, detail="Which ingredient?")
    diet = (body.diet or "").strip().lower()
    if diet and diet not in DIETS:
        raise HTTPException(status_code=400, detail="Unknown diet")

    cache_key = f"ai_sub:{key_for(name, diet)}"
    cached = await get_cache(db, cache_key)
    if cached:
        return {**cached, "cached": True, "left_today": await uses_left(db, user["user_id"])}

    await spend_one(db, user["user_id"])
    prompt = f"""Suggest up to 4 good substitutes for "{name}" in home cooking{' for this recipe: ' + body.recipe_title if body.recipe_title else ''}.
{('Every substitute must be ' + DIETS[diet] + '.') if diet else ''}
Say how much to use compared with the original and how it changes the dish. Most common and easiest-to-find first.
Return ONLY JSON: {{"substitutes":[{{"item":"name","amount":"e.g. 1:1, or 3/4 cup per 1 cup","note":"one short sentence on taste/texture or any change to the method"}}]}}"""
    try:
        data = await ask_json("You are a practical home-cooking expert. Return only valid JSON.", prompt, "sub")
        subs = [s for s in (data.get("substitutes") or []) if isinstance(s, dict) and s.get("item")][:4]
    except Exception as e:
        logger.info(f"substitute error: {e}")
        raise HTTPException(status_code=502, detail="The AI could not answer right now. Please try again.")
    result = {"ingredient": name, "substitutes": subs}
    await set_cache(db, cache_key, result, ttl_days=CACHE_DAYS)
    return {**result, "cached": False, "left_today": await uses_left(db, user["user_id"])}


@router.post("/convert-recipe")
async def convert_recipe(body: ConvertRequest, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    diet = (body.diet or "").strip().lower()
    if diet not in DIETS:
        raise HTTPException(status_code=400, detail="Unknown diet")

    recipe = await db.recipes.find_one(
        {"recipe_id": body.recipe_id, **ps.shared_or_own(user["user_id"])}, {"_id": 0}
    )
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    cache_key = f"ai_conv:{key_for(body.recipe_id, diet)}"
    cached = await get_cache(db, cache_key)
    if cached:
        return {**cached, "cached": True, "left_today": await uses_left(db, user["user_id"])}

    await spend_one(db, user["user_id"])
    ings = [
        f"{(i.get('amount') or '').strip()} {(i.get('item') or '').strip()}".strip() if isinstance(i, dict) else str(i)
        for i in recipe.get("ingredients", [])
    ]
    steps = [s.get("text", "") if isinstance(s, dict) else str(s) for s in recipe.get("steps", [])]
    prompt = f"""Convert this recipe so it is {DIETS[diet]}. Keep it tasting as close to the original as possible.
Replace only what must change, keep amounts sensible, and update the method where a swap changes cooking (times, heat, technique).

Title: {recipe.get('title')}
Servings: {recipe.get('servings', 4)}
Ingredients:
{chr(10).join('- ' + i for i in ings)}
Method:
{chr(10).join(f'{n + 1}. {t}' for n, t in enumerate(steps))}

{COOKING_STYLE}

Return ONLY JSON:
{{"title":"new title, e.g. Vegan {recipe.get('title')}",
  "ingredients":[{{"item":"name","amount":"1 cup","category":"Produce"}}],
  "steps":["..."],
  "changes":["short list of what was swapped and why, e.g. Butter -> olive oil (1:1)"]}}"""
    try:
        data = await ask_json("You are an expert recipe developer. Return only valid JSON.", prompt, "conv")
        if not data.get("ingredients") or not data.get("steps"):
            raise ValueError("incomplete recipe")
    except Exception as e:
        logger.info(f"convert error: {e}")
        raise HTTPException(status_code=502, detail="The AI could not convert this recipe right now. Please try again.")

    result = {
        "title": str(data.get("title") or f"{diet.title()} {recipe.get('title')}")[:150],
        "diet": diet,
        "ingredients": data["ingredients"],
        "steps": data["steps"],
        "changes": data.get("changes") or [],
        "servings": recipe.get("servings", 4),
        "prep_time": recipe.get("prep_time", ""),
        "cook_time": recipe.get("cook_time", ""),
        "image": recipe.get("image", ""),
        "source_recipe_id": body.recipe_id,
    }
    await set_cache(db, cache_key, result, ttl_days=CACHE_DAYS)
    return {**result, "cached": False, "left_today": await uses_left(db, user["user_id"])}
