import logging
logger = logging.getLogger(__name__)
from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid
import os
import json
import re
import hashlib
from pydantic import BaseModel
from auth import get_current_user
from emergentintegrations.llm.chat import LlmChat, UserMessage
from cache import get_cache, set_cache
from localisation import normalise_ingredient

router = APIRouter(prefix="/pantry", tags=["pantry"])
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")


# ── Models ────────────────────────────────────────────────────────────────────

class PantryItemCreate(BaseModel):
    name: str
    category: str = "Other"
    amount: Optional[str] = "1"
    quantity: Optional[int] = None
    unit: Optional[str] = None
    in_stock: bool = True


class MealSuggestionRequest(BaseModel):
    match_type: str = "all"
    extra_ingredients: int = 0


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("")
async def get_pantry_items(request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    items = await db.pantry_items.find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).to_list(500)
    return items


@router.post("")
async def add_pantry_item(item_data: PantryItemCreate, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)

    amount = item_data.amount or "1"
    if item_data.quantity is not None:
        amount = f"{item_data.quantity} {item_data.unit}".strip() if item_data.unit else str(item_data.quantity)

    item_doc = {
        "item_id": f"item_{uuid.uuid4().hex[:12]}",
        "user_id": user["user_id"],
        "name": item_data.name,
        "category": item_data.category,
        "amount": amount,
        "in_stock": item_data.in_stock,
        "created_at": datetime.now(timezone.utc),
    }
    await db.pantry_items.insert_one(item_doc)
    item_doc.pop("_id", None)
    return item_doc


@router.put("/{item_id}")
async def update_pantry_item(item_id: str, item_data: dict, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    result = await db.pantry_items.update_one(
        {"item_id": item_id, "user_id": user["user_id"]},
        {"$set": item_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item updated"}


@router.delete("/{item_id}")
async def delete_pantry_item(item_id: str, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    result = await db.pantry_items.delete_one(
        {"item_id": item_id, "user_id": user["user_id"]}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"message": "Item deleted"}


# ── Helper ────────────────────────────────────────────────────────────────────

def _score(recipe_ing_names, pantry_names, match_type, extra):
    """Returns (should_include, match_pct, matched_count, missing_count)."""
    recipe_set = set(recipe_ing_names)
    pantry_set = set(pantry_names)
    matched = recipe_set & pantry_set
    total = len(recipe_set) or 1
    pct = round(len(matched) / total * 100)
    missing = total - len(matched)
    if match_type == "all":
        ok = missing <= extra
    elif match_type == "most":
        ok = pct >= 70 or missing <= extra
    else:
        ok = len(matched) > 0
    return (ok and len(matched) > 0), pct, len(matched), missing


# ── Suggest meal ──────────────────────────────────────────────────────────────

@router.post("/suggest-meal")
async def suggest_meal(suggestion_request: MealSuggestionRequest, request: Request):
    """
    Priority order (cheapest first):
      1. User's saved recipes  — pure Python, always free
      2. Community recipe DB   — MongoDB query, always free
      3. AI generation         — only when DB has < 3 matches, cached 1 hour
    """
    db = request.app.state.db
    user = await get_current_user(request, db)

    pantry_items = await db.pantry_items.find(
        {"user_id": user["user_id"], "in_stock": True}, {"_id": 0}
    ).to_list(100)

    if not pantry_items:
        raise HTTPException(status_code=400, detail="Your pantry is empty. Add some ingredients first!")

    pantry_names = [item["name"].lower() for item in pantry_items]
    # Normalise regional names to canonical English (courgette→zucchini etc.)
    pantry_names_normalised = [normalise_ingredient(n) for n in pantry_names]
    # Use union of both — original names AND normalised for maximum match coverage
    pantry_lookup = list(set(pantry_names + pantry_names_normalised))
    mt = suggestion_request.match_type
    extra = suggestion_request.extra_ingredients

    # 1. User's saved recipes
    saved_recipes = await db.recipes.find(
        {"user_id": user["user_id"], "hidden_by": {"$ne": user["user_id"]}},
        {"_id": 0}
    ).to_list(200)

    matched_saved = []
    for recipe in saved_recipes:
        ings = recipe.get("ingredients", [])
        if not ings:
            continue
        ing_names = []
        for ing in ings:
            n = ing.get("item", ing.get("name", "")).lower() if isinstance(ing, dict) else str(ing).lower()
            if n:
                ing_names.append(n)
        if not ing_names:
            continue
        # Normalise ingredient names for matching
        ing_names_normalised = [normalise_ingredient(n) for n in ing_names]
        ok, pct, matched, missing = _score(ing_names_normalised, pantry_lookup, mt, extra)
        if ok:
            matched_saved.append({
                "recipe_id": recipe.get("recipe_id"),
                "title": recipe.get("title"),
                "description": recipe.get("description", ""),
                "image": recipe.get("image", ""),
                "prep_time": recipe.get("prep_time", ""),
                "cook_time": recipe.get("cook_time", ""),
                "difficulty": recipe.get("difficulty", "Medium"),
                "servings": recipe.get("servings", 4),
                "match_percentage": pct,
                "matched_ingredients": matched,
                "total_ingredients": len(ing_names),
                "missing_ingredients": missing,
                "source": "saved",
                "ingredients": ings,
                "tags": recipe.get("tags", []),
            })
    matched_saved.sort(key=lambda x: x["match_percentage"], reverse=True)

    # 2. Community recipe DB
    community_matches = []
    try:
        cursor = db.community_recipes.find(
            {"ingredient_names": {"$in": pantry_lookup}},
            {"_id": 0, "community_recipe_id": 1, "title": 1, "description": 1,
             "image": 1, "prep_time": 1, "cook_time": 1, "difficulty": 1,
             "servings": 1, "ingredient_names": 1, "ingredients": 1,
             "tags": 1, "cuisine": 1}
        ).limit(50)
        async for recipe in cursor:
            ok, pct, matched, missing = _score(
                recipe.get("ingredient_names", []), pantry_lookup, mt, extra
            )
            if ok:
                community_matches.append({
                    "recipe_id": recipe["community_recipe_id"],
                    "title": recipe["title"],
                    "description": recipe.get("description", ""),
                    "image": recipe.get("image", ""),
                    "prep_time": recipe.get("prep_time", ""),
                    "cook_time": recipe.get("cook_time", ""),
                    "difficulty": recipe.get("difficulty", "Medium"),
                    "servings": recipe.get("servings", 4),
                    "match_percentage": pct,
                    "matched_ingredients": matched,
                    "total_ingredients": len(recipe.get("ingredient_names", [])),
                    "missing_ingredients": missing,
                    "source": "community",
                    "ingredients": recipe.get("ingredients", []),
                    "tags": recipe.get("tags", []),
                })
        community_matches.sort(key=lambda x: x["match_percentage"], reverse=True)
        community_matches = community_matches[:5]
    except Exception as e:
        logger.info(f"Community search error: {e}")

    # 3. AI — only if not enough DB results
    ai_suggestions = []
    if (len(matched_saved) + len(community_matches)) < 3:
        fingerprint = hashlib.sha256(
            ("|".join(sorted(pantry_names)) + f"|{mt}|{extra}").encode()
        ).hexdigest()[:24]
        ai_cache_key = f"meal_suggest:{user['user_id']}:{fingerprint}"

        cached = await get_cache(db, ai_cache_key)
        if cached:
            ai_suggestions = cached
        else:
            try:
                chat = LlmChat(
                    api_key=EMERGENT_KEY,
                    session_id=f"meal_suggest_{uuid.uuid4().hex[:8]}",
                    system_message="You are a creative chef assistant. Suggest practical, delicious recipes based on available ingredients.",
                ).with_model("openai", "gpt-4o-mini")

                if mt == "all":
                    match_instruction = "Only suggest recipes that primarily use the available ingredients."
                elif mt == "most":
                    match_instruction = "Suggest recipes where at least 70% of ingredients are available."
                else:
                    match_instruction = "Suggest creative recipes that use at least some of the available ingredients."

                extra_context = f"\nThe user is willing to buy up to {extra} additional ingredients." if extra > 0 else ""

                prompt = f"""Based on these pantry ingredients: {', '.join(pantry_names)}

{match_instruction}{extra_context}

Suggest 3 different meal ideas that can be made with these ingredients.

Return ONLY valid JSON:
{{
  "suggestions": [
    {{
      "title": "Recipe Name",
      "description": "Brief appetizing description (1-2 sentences)",
      "prep_time": "15 min",
      "cook_time": "30 min",
      "difficulty": "Easy/Medium/Hard",
      "servings": 4,
      "ingredients": [{{"item": "ingredient name", "amount": "1 cup"}}],
      "steps": ["Step 1 instruction", "Step 2 instruction", "Step 3 instruction"],
      "matched_ingredients": ["list of pantry items used"],
      "additional_ingredients_needed": ["list of items not in pantry, if any"],
      "tags": ["Dinner", "Quick", "Healthy"]
    }}
  ]
}}

Make the recipes practical and delicious. Include clear, actionable steps."""

                response_text = await chat.send_message(UserMessage(text=prompt))
                m = re.search(r"\{.*\}", response_text, re.DOTALL)
                if m:
                    ai_data = json.loads(m.group())
                    ai_suggestions = ai_data.get("suggestions", [])
                    for idx, s in enumerate(ai_suggestions):
                        s["source"] = "ai"
                        s["recipe_id"] = f"ai_suggestion_{idx}"
                        matched_list = s.get("matched_ingredients", [])
                        additional = s.get("additional_ingredients_needed", [])
                        total = len(matched_list) + len(additional)
                        s["match_percentage"] = round(len(matched_list) / total * 100) if total > 0 else 100
                        s["matched_count"] = len(matched_list)
                        s["missing_count"] = len(additional)

                # Cache for 1 hour
                await set_cache(db, ai_cache_key, ai_suggestions, ttl_days=0)
                await db.ai_cache.update_one(
                    {"key": ai_cache_key},
                    {"$set": {"expires_at": datetime.now(timezone.utc) + timedelta(hours=1)}}
                )

            except Exception as e:
                logger.info(f"AI suggestion error: {e}")

    return {
        "pantry_items": pantry_names,
        "saved_recipe_matches": matched_saved[:5],
        "community_recipe_matches": community_matches,
        "ai_suggestions": ai_suggestions,
        "match_criteria": {"type": mt, "extra_ingredients_allowed": extra},
    }
