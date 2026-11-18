"""AI helpers on a recipe: ingredient swaps and dietary conversion.

Both use the configured everyday model (see ai_client.py), are cached so a repeat question costs nothing,
and count against each person's daily AI allowance only when the AI actually runs.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

import public_sharing as ps
from ai_client import ask_json, spend_one, uses_left, key_for, daily_limit, swap_limit, COOKING_STYLE
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
    diet: Optional[str] = None            # one diet (older clients)
    diets: Optional[List[str]] = None     # several at once: one AI call instead of one per diet


# Ticking "vegan" already covers these, so they are dropped from a combination.
_IMPLIED = {"vegan": {"vegetarian", "dairy-free"}}


def normalise_diets(diets) -> List[str]:
    """Unique, valid, sorted; anything a ticked diet already covers is removed (vegan covers vegetarian and dairy-free)."""
    wanted = {str(d).strip().lower() for d in (diets or []) if str(d).strip()}
    bad = wanted - set(DIETS)
    if bad:
        raise HTTPException(status_code=400, detail="Unknown diet")
    for d in list(wanted):
        wanted -= _IMPLIED.get(d, set())
    return sorted(wanted)


class CookedRequest(BaseModel):
    recipe_id: str


@router.get("/usage")
async def ai_usage(request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    return {
        "left_today": await uses_left(db, user["user_id"]), "daily_limit": daily_limit(),
        "swaps_left_today": await uses_left(db, user["user_id"], "swap"), "swap_limit": swap_limit(),
    }


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
        return {**cached, "cached": True, "left_today": await uses_left(db, user["user_id"], "swap")}

    await spend_one(db, user["user_id"], "swap")
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
    return {**result, "cached": False, "left_today": await uses_left(db, user["user_id"], "swap")}


@router.post("/convert-recipe")
async def convert_recipe(body: ConvertRequest, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    diets = normalise_diets(body.diets if body.diets else [body.diet] if body.diet else [])
    if not diets:
        raise HTTPException(status_code=400, detail="Pick at least one diet")
    diet = "+".join(diets)
    diet_text = " and ".join(DIETS[d] for d in diets)

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
    prompt = f"""Convert this recipe so it is {diet_text}. Every ingredient must satisfy all of these at once. Keep it tasting as close to the original as possible.
Replace only what must change, keep amounts sensible, and update the method where a swap changes cooking (times, heat, technique).

Title: {recipe.get('title')}
Servings: {recipe.get('servings', 4)}
Ingredients:
{chr(10).join('- ' + i for i in ings)}
Method:
{chr(10).join(f'{n + 1}. {t}' for n, t in enumerate(steps))}

{COOKING_STYLE}

Return ONLY JSON:
{{"title":"new title, e.g. {' '.join(d.title() for d in diets)} {recipe.get('title')}",
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
        "title": str(data.get("title") or f"{' '.join(d.title() for d in diets)} {recipe.get('title')}")[:150],
        "diet": diet,
        "diets": diets,
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


@router.post("/cooked")
async def mark_cooked(body: CookedRequest, request: Request):
    """Someone finished cooking a recipe. If it is an AI-made recipe, it goes to the admin review queue."""
    db = request.app.state.db
    user = await get_current_user(request, db)
    recipe = await db.recipes.find_one({"recipe_id": body.recipe_id}, {"_id": 0, "recipe_id": 1, "ai_generated": 1, "user_id": 1, "ai_review": 1})
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    await db.recipe_cooks.update_one(
        {"recipe_id": body.recipe_id, "user_id": user["user_id"]},
        {"$set": {"cooked_at": datetime.now(timezone.utc)}, "$inc": {"times": 1}},
        upsert=True,
    )
    queued = False
    if recipe.get("ai_generated") and recipe.get("user_id") != "system_seeder" and not recipe.get("ai_review"):
        await db.recipes.update_one(
            {"recipe_id": body.recipe_id, "ai_review": {"$exists": False}},
            {"$set": {"ai_review": "pending", "ai_review_at": datetime.now(timezone.utc)}},
        )
        queued = True
    return {"ok": True, "sent_for_review": queued}


@router.get("/image/{image_id}")
async def get_image(image_id: str, request: Request):
    """Photos added to approved AI recipes, kept in our own database (never hotlinked)."""
    from fastapi import Response
    db = request.app.state.db
    doc = await db.images.find_one({"image_id": image_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return Response(content=bytes(doc["data"]), media_type=doc.get("content_type", "image/jpeg"),
                    headers={"Cache-Control": "public, max-age=2592000"})
