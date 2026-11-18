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


def _qty_of(amount) -> Optional[float]:
    """Leading number of an amount like '0', '2 kg', '1/2 cup'. None when there is no number."""
    m = re.match(r"^\s*(\d+(?:\.\d+)?)", str(amount or ""))
    return float(m.group(1)) if m else None


async def _restock_if_empty(db, request: Request, name: str, amount, in_stock: bool) -> bool:
    """A pantry item at zero is out of stock and goes straight onto the shopping list."""
    q = _qty_of(amount)
    if (q is not None and q <= 0) or not in_stock:
        from routes.shopping_routes import add_items_to_shopping_list, AddItemsRequest
        await add_items_to_shopping_list(AddItemsRequest(items=[name]), request)
        return True
    return False


@router.post("")
async def add_pantry_item(item_data: PantryItemCreate, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)

    amount = item_data.amount or "1"
    if item_data.quantity is not None:
        amount = f"{item_data.quantity} {item_data.unit}".strip() if item_data.unit else str(item_data.quantity)

    q = _qty_of(amount)
    if q is not None and q <= 0:
        item_data.in_stock = False
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
    item_doc["added_to_shopping_list"] = await _restock_if_empty(db, request, item_data.name, amount, item_data.in_stock)
    return item_doc


@router.put("/{item_id}")
async def update_pantry_item(item_id: str, item_data: dict, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    item_data = {k: v for k, v in item_data.items() if k not in ("item_id", "user_id", "_id")}
    if "amount" in item_data:
        q = _qty_of(item_data["amount"])
        if q is not None:
            item_data["in_stock"] = q > 0
    result = await db.pantry_items.update_one(
        {"item_id": item_id, "user_id": user["user_id"]},
        {"$set": item_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    added = False
    if item_data.get("in_stock") is False:
        doc = await db.pantry_items.find_one({"item_id": item_id, "user_id": user["user_id"]}, {"_id": 0})
        if doc:
            added = await _restock_if_empty(db, request, doc["name"], doc.get("amount"), False)
    return {"message": "Item updated", "added_to_shopping_list": added}


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



# ── Fuzzy matching for the shared master recipes ──────────────
_STAPLES = {"salt", "water", "pepper", "black pepper", "oil", "olive oil", "vegetable oil", "cooking oil", "ice"}
_NOISE = {"fresh", "chopped", "large", "small", "medium", "ground", "dried", "finely", "sliced", "diced", "minced",
          "boneless", "skinless", "whole", "frozen", "canned", "to", "taste", "of", "and", "or", "the", "a", "cut", "into",
          "pieces", "plus", "extra", "for", "serving", "optional", "cup", "cups", "tbsp", "tsp", "g", "kg", "ml"}


def _tokens(name: str) -> frozenset:
    words = re.findall(r"[a-z]+", normalise_ingredient(name.lower()))
    return frozenset(w.rstrip("s") if len(w) > 3 else w for w in words if w not in _NOISE)


# A general pantry word also covers its common specific forms in recipes.
_GROUPS = {
    "pasta": ["spaghetti", "penne", "fusilli", "linguine", "fettuccine", "tagliatelle", "macaroni", "rigatoni", "lasagne", "lasagna", "farfalle", "orzo"],
    "rice": ["basmati", "jasmine", "arborio", "risotto"],
    "cheese": ["cheddar", "mozzarella", "parmesan", "feta", "halloumi", "gruyere", "ricotta", "mascarpone", "pecorino", "gouda", "brie", "parmigiano"],
    "mince": ["ground beef", "ground pork", "ground lamb", "ground turkey"],
    "beef": ["steak", "brisket", "sirloin", "ribeye"],
    "chicken": ["drumstick", "thigh", "wing"],
    "bread": ["baguette", "ciabatta", "sourdough", "bun", "roll", "pitta", "pita"],
    "beans": ["chickpea", "kidney bean", "black bean", "cannellini", "lentil", "haricot", "butter bean"],
    "pepper": ["bell pepper", "capsicum"],
    "tomato": ["passata", "tomatoes"],
    "potato": ["potatoes", "new potato"],
    "milk": ["cream", "buttermilk"],
    "egg": ["eggs"],
}


def _pantry_groups(pantry_names):
    """One group per pantry item: its own words plus any specific forms it stands for."""
    groups = []
    for n in pantry_names:
        base = _tokens(n)
        if not base:
            continue
        g = [base]
        for word, alts in _GROUPS.items():
            if word in {w.rstrip("s") for w in base} or word in base:
                g += [t for t in (_tokens(a) for a in alts) if t]
        groups.append(g)
    return groups


def _score_master(recipe_ings, pantry_token_sets, match_type, extra):
    """Word-level match: pantry 'chicken' covers 'chicken breast'; salt/water/oil count as always on hand."""
    names = []
    for ing in recipe_ings:
        n = ing.get("item", ing.get("name", "")) if isinstance(ing, dict) else str(ing)
        if n and n.strip():
            names.append(n.strip())
    if not names:
        return False, 0, 0, 0, 0
    matched = 0
    used = set()   # which of the person's pantry items this recipe actually uses
    for n in names:
        if n.lower() in _STAPLES:
            matched += 1
            continue
        t = _tokens(n)
        hit = [i for i, grp in enumerate(pantry_token_sets) if t and any(p <= t or t <= p for p in grp)]
        if hit:
            matched += 1
            used.update(hit)
    total = len(names)
    missing = total - matched
    pct = round(matched / total * 100)
    if match_type == "all":
        ok = missing <= extra
    elif match_type == "most":
        ok = pct >= 70 or missing <= extra
    else:
        ok = pct >= 30
    real = matched - sum(1 for n in names if n.lower() in _STAPLES)
    # with 2+ pantry items, a recipe has to use at least 2 of them (a 1-item omelette is not a "match" for chicken+rice+onion)
    enough = len(used) >= min(2, len(pantry_token_sets))
    return (ok and real > 0 and enough), pct, matched, missing, len(used)

# ── Suggest meal ──────────────────────────────────────────────────────────────

@router.post("/suggest-meal")
async def suggest_meal(suggestion_request: MealSuggestionRequest, request: Request):
    """
    Priority order (cheapest first):
      1. User's saved recipes  — pure Python, always free
      1b. Shared master recipes — pure Python, always free
      2. Community recipe DB   — MongoDB query, always free
      3. AI generation         — only when there are < 3 matches in total, cached 1 hour
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
    from ingredient_dictionary import to_english as _to_english
    pantry_names_normalised = [normalise_ingredient(_to_english(n) or n) for n in pantry_names]
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

    # 1b. Shared master recipes — pure Python, free
    master_matches = []
    try:
        pantry_token_sets = _pantry_groups(pantry_lookup)
        async for recipe in db.recipes.find(
            {"$or": [{"user_id": "system_seeder"}, {"visibility": "public"}]},
            {"_id": 0, "recipe_id": 1, "title": 1, "description": 1, "image": 1, "prep_time": 1, "cook_time": 1,
             "difficulty": 1, "servings": 1, "ingredients": 1, "tags": 1},
        ):
            ok, pct, matched, missing, used = _score_master(recipe.get("ingredients", []), pantry_token_sets, mt, extra)
            if ok:
                master_matches.append({
                    "recipe_id": recipe["recipe_id"],
                    "title": recipe.get("title"),
                    "description": recipe.get("description", ""),
                    "image": recipe.get("image") or "",
                    "prep_time": recipe.get("prep_time", ""),
                    "cook_time": recipe.get("cook_time", ""),
                    "difficulty": recipe.get("difficulty", "Medium"),
                    "servings": recipe.get("servings", 4),
                    "match_percentage": pct,
                    "matched_ingredients": matched,
                    "total_ingredients": matched + missing,
                    "missing_ingredients": missing,
                    "source": "master",
                    "pantry_items_used": used,
                    "ingredients": recipe.get("ingredients", []),
                    "tags": recipe.get("tags", []),
                })
        master_matches.sort(key=lambda x: (-x["pantry_items_used"], -x["match_percentage"], x["missing_ingredients"]))
        master_matches = master_matches[:8]
    except Exception as e:
        logger.info(f"Master recipe search error: {e}")

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
    if (len(matched_saved) + len(master_matches) + len(community_matches)) < 3:
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
        "saved_recipe_matches": matched_saved[:5] + master_matches,
        "community_recipe_matches": community_matches,
        "ai_suggestions": ai_suggestions,
        "match_criteria": {"type": mt, "extra_ingredients_allowed": extra},
    }
