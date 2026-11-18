import json
import logging
import re
from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timezone
from typing import List, Optional
import uuid
from models import Recipe, RecipeCreate, RecipeExtractRequest, RecipeUpdate
from auth import get_current_user
import content_filter
from schema_steps import extract_steps
import public_sharing as ps
import os
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
from cache import get_cache, set_cache, nutrition_key, url_import_key, youtube_key, recipe_fingerprint, TTL_NUTRITION, TTL_URL_IMPORT, TTL_YOUTUBE
from html_sanitiser import sanitise_html, extract_best_image
from image_optimiser import optimise_image_url

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recipes", tags=["recipes"])

# Initialize Emergent LLM
EMERGENT_KEY = os.environ.get('EMERGENT_LLM_KEY')

# Get user's own recipes only (excludes recipes hidden by current user)
@router.get("", response_model=List[Recipe])
async def get_recipes(
    request: Request,
    category: Optional[str] = None,
    cuisine: Optional[str] = None,
    search: Optional[str] = None,
    show_all: Optional[bool] = False  # For master list view
):
    db = request.app.state.db
    user = await get_current_user(request, db)
    
    # CRITICAL: Only return recipes created by this user
    query = {"user_id": user["user_id"]}
    
    # Filter out recipes hidden by this user (unless show_all is True for master list)
    if not show_all:
        query["hidden_by"] = {"$ne": user["user_id"]}
    
    if category:
        query["category"] = category
    if cuisine:
        query["cuisine"] = cuisine
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"tags": {"$regex": search, "$options": "i"}},
            {"cuisine": {"$regex": search, "$options": "i"}}
        ]
    
    # Use projection to only fetch needed fields for faster loading
    projection = {
        "_id": 0,
        "recipe_id": 1,
        "user_id": 1,
        "title": 1,
        "description": 1,
        "image": 1,
        "prep_time": 1,
        "cook_time": 1,
        "time_estimated": 1,
        "servings": 1,
        "difficulty": 1,
        "ingredients": 1,
        "steps": 1,
        "category": 1,
        "cuisine": 1,
        "tags": 1,
        "nutrition": 1,
        "likes_count": 1,
        "saves_count": 1,
        "hidden_by": 1,
        "favorited_by": 1,
        "uploader_id": 1,
        "uploader_name": 1,
        "created_at": 1,
        "updated_at": 1,
        "source_url": 1
    }
    
    recipes = await db.recipes.find(query, projection).sort("created_at", -1).to_list(100)
    
    # Add favorited flag for each recipe
    for recipe in recipes:
        recipe["is_favorited"] = user["user_id"] in recipe.get("favorited_by", [])
    
    return [ps.mask_owner(r, user["user_id"]) for r in recipes]

# Get master list of all recipes (includes hidden ones)
@router.get("/master/all")
async def get_master_recipes(request: Request, search: Optional[str] = None):
    db = request.app.state.db
    user = await get_current_user(request, db)
    
    # Shared recipes plus this person's own. Never other people's private recipes.
    query = {"$or": [*ps.SHARED["$or"], {"user_id": user["user_id"]}]}
    if search:
        query = {"$and": [query, {"$or": [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"tags": {"$regex": search, "$options": "i"}}
        ]}]}
    
    # Use projection for faster loading
    projection = {
        "_id": 0,
        "recipe_id": 1,
        "user_id": 1,
        "title": 1,
        "description": 1,
        "image": 1,
        "prep_time": 1,
        "cook_time": 1,
        "time_estimated": 1,
        "servings": 1,
        "difficulty": 1,
        "ingredients": 1,
        "steps": 1,
        "category": 1,
        "cuisine": 1,
        "tags": 1,
        "nutrition": 1,
        "likes_count": 1,
        "saves_count": 1,
        "hidden_by": 1,
        "favorited_by": 1,
        "uploader_id": 1,
        "uploader_name": 1,
        "created_at": 1,
        "updated_at": 1,
        "source_url": 1
    }
    
    recipes = await db.recipes.find(query, projection).sort("created_at", -1).to_list(200)
    
    # Add flag for whether current user has hidden this recipe
    for recipe in recipes:
        recipe["is_hidden_by_me"] = user["user_id"] in recipe.get("hidden_by", [])
        recipe["is_favorited"] = user["user_id"] in recipe.get("favorited_by", [])
    
    return recipes

# Get user's favorite recipes
@router.get("/search")
async def search_recipes(
    request: Request,
    q: Optional[str] = None,
    ingredients: Optional[str] = None,
    diet: Optional[str] = None,
    cuisine: Optional[str] = None,
    quick: bool = False,
    limit: int = 24,
    skip: int = 0,
):
    """Search the shared master recipes plus the user's own.
    q = words in title/description/tags; ingredients = comma list, ALL must appear; diet = vegetarian|vegan;
    quick = only recipes tagged quick (under ~30 min)."""
    import re as _re
    db = request.app.state.db
    user = await get_current_user(request, db)
    limit = min(max(limit, 1), 60)
    and_q = [ps.shared_or_own(user["user_id"])]
    for word in (q or "").split()[:6]:
        w = _re.escape(word)
        and_q.append({"$or": [{"title": {"$regex": w, "$options": "i"}},
                              {"description": {"$regex": w, "$options": "i"}},
                              {"tags": {"$regex": w, "$options": "i"}}]})
    for ing in [i.strip() for i in (ingredients or "").split(",") if i.strip()][:8]:
        and_q.append({"ingredients": {"$elemMatch": {"item": {"$regex": _re.escape(ing), "$options": "i"}}}})
    if diet in ("vegetarian", "vegan"):
        and_q.append({"tags": diet})
    if cuisine:
        and_q.append({"cuisine": {"$regex": "^" + _re.escape(cuisine.replace(" ", "_")) + "$", "$options": "i"}})
    if quick:
        and_q.append({"tags": "quick"})
    query = {"$and": and_q}
    proj = {"_id": 0, "recipe_id": 1, "title": 1, "description": 1, "image": 1, "prep_time": 1, "cook_time": 1, "time_estimated": 1,
            "difficulty": 1, "servings": 1, "tags": 1, "cuisine": 1, "user_id": 1}
    total = await db.recipes.count_documents(query)
    recipes = await db.recipes.find(query, proj).sort("title", 1).skip(skip).limit(limit).to_list(limit)
    return {"recipes": [ps.mask_owner(r, user["user_id"]) for r in recipes], "total": total, "has_more": skip + limit < total}


@router.get("/stats")
async def recipe_stats(request: Request):
    """Totals for the counters in the app: the shared collection, plus this person's own recipes."""
    db = request.app.state.db
    user = await get_current_user(request, db)
    total = await db.recipes.count_documents(ps.SHARED)
    mine = await db.recipes.count_documents({"user_id": user["user_id"], "hidden_by": {"$ne": user["user_id"]}})
    return {"total": total, "mine": mine}


_FEATURED_CACHE: dict = {}


@router.get("/featured")
async def get_featured_master(request: Request, count: int = 3):
    """Today's pick: random but fixed for the whole day, from the shared recipes plus the person's own, only ones with a photo.
    Other people's private recipes are never shown."""
    from datetime import date
    db = request.app.state.db
    user = await get_current_user(request, db)
    # Let the database pick (no loading of every id) and remember the pick for the day
    key = (date.today().isoformat(), user["user_id"], min(max(count, 1), 12))
    picked = _FEATURED_CACHE.get(key)
    if picked is None:
        cond = {"$and": [ps.shared_or_own(user["user_id"]), {"image": {"$regex": "^(http|/recipe-images/|data:image/)"}}]}
        rows = await db.recipes.aggregate([
            {"$match": cond}, {"$sample": {"size": key[2]}}, {"$project": {"_id": 0, "recipe_id": 1}},
        ]).to_list(key[2])
        picked = [r["recipe_id"] for r in rows]
        if len(_FEATURED_CACHE) > 5000 or any(k[0] != key[0] for k in list(_FEATURED_CACHE)[:1]):
            _FEATURED_CACHE.clear()
        _FEATURED_CACHE[key] = picked
    if not picked:
        return {"recipes": []}
    out = await db.recipes.find(
        {"recipe_id": {"$in": picked}},
        {"_id": 0, "recipe_id": 1, "title": 1, "image": 1, "prep_time": 1, "cook_time": 1, "time_estimated": 1, "servings": 1, "difficulty": 1, "description": 1},
    ).to_list(len(picked))
    out.sort(key=lambda r: picked.index(r["recipe_id"]))
    return {"recipes": out}

@router.get("/favorites")
async def get_favorite_recipes(request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    
    # Use projection for faster loading
    projection = {
        "_id": 0,
        "recipe_id": 1,
        "user_id": 1,
        "title": 1,
        "description": 1,
        "image": 1,
        "prep_time": 1,
        "cook_time": 1,
        "time_estimated": 1,
        "servings": 1,
        "difficulty": 1,
        "ingredients": 1,
        "steps": 1,
        "category": 1,
        "cuisine": 1,
        "tags": 1,
        "nutrition": 1,
        "likes_count": 1,
        "saves_count": 1,
        "hidden_by": 1,
        "favorited_by": 1,
        "uploader_id": 1,
        "uploader_name": 1,
        "created_at": 1,
        "updated_at": 1,
        "source_url": 1
    }
    
    # Find recipes that have this user in favorited_by array
    recipes = await db.recipes.find(
        {"favorited_by": user["user_id"]},
        projection
    ).sort("created_at", -1).to_list(100)
    
    # Add favorited flag
    for recipe in recipes:
        recipe["is_favorited"] = True
        recipe["is_hidden_by_me"] = user["user_id"] in recipe.get("hidden_by", [])
    
    return recipes

# Get available categories and cuisines
@router.get("/filters/options")
async def get_filter_options(request: Request):
    db = request.app.state.db
    await get_current_user(request, db)  # Verify authenticated
    
    # Predefined categories
    categories = [
        {"value": "quick", "label": "Quick & Easy"},
        {"value": "budget", "label": "Budget Friendly"},
        {"value": "student", "label": "Student Meals"},
        {"value": "instapot", "label": "Instant Pot"},
        {"value": "airfryer", "label": "Air Fryer"},
        {"value": "healthy", "label": "Healthy"},
        {"value": "comfort", "label": "Comfort Food"},
        {"value": "dessert", "label": "Desserts"}
    ]
    
    # Predefined cuisines (countries)
    cuisines = [
        {"value": "american", "label": "American"},
        {"value": "italian", "label": "Italian"},
        {"value": "mexican", "label": "Mexican"},
        {"value": "indian", "label": "Indian"},
        {"value": "chinese", "label": "Chinese"},
        {"value": "japanese", "label": "Japanese"},
        {"value": "thai", "label": "Thai"},
        {"value": "french", "label": "French"},
        {"value": "mediterranean", "label": "Mediterranean"},
        {"value": "korean", "label": "Korean"},
        {"value": "vietnamese", "label": "Vietnamese"},
        {"value": "greek", "label": "Greek"},
        {"value": "spanish", "label": "Spanish"},
        {"value": "middle_eastern", "label": "Middle Eastern"},
        {"value": "british", "label": "British"},
        {"value": "caribbean", "label": "Caribbean"},
        {"value": "african", "label": "African"},
        {"value": "german", "label": "German"}
    ]
    
    return {"categories": categories, "cuisines": cuisines}

# Get recipe gallery images (must be before /{recipe_id} route)
@router.get("/{recipe_id}/gallery")
async def get_gallery_images(recipe_id: str, request: Request):
    db = request.app.state.db
    await get_current_user(request, db)  # Verify authenticated
    
    # First check if recipe exists
    recipe = await db.recipes.find_one({"recipe_id": recipe_id})
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    return {"images": recipe.get("gallery_images", [])}

# Get recipe by ID
@router.get("/{recipe_id}", response_model=Recipe)
async def get_recipe(recipe_id: str, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    
    recipe = await db.recipes.find_one({"recipe_id": recipe_id}, {"_id": 0})
    # Private recipes can only be opened by their owner
    if not recipe or not (recipe.get("user_id") in ("system_seeder", user["user_id"]) or recipe.get("visibility") == "public"):
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    return ps.mask_owner(recipe, user["user_id"])


# ── Edit your own recipe ──────────────────────────────────────────────────────

async def _own_recipe(db, user, recipe_id):
    recipe = await db.recipes.find_one({"recipe_id": recipe_id, "user_id": user["user_id"]}, {"_id": 0})
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.put("/{recipe_id}", response_model=Recipe)
async def update_recipe(recipe_id: str, changes: RecipeUpdate, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    recipe = await _own_recipe(db, user, recipe_id)
    fields = {k: v for k, v in changes.dict().items() if v is not None}
    if not fields:
        return recipe
    fields["updated_at"] = datetime.now(timezone.utc)
    recipe.update(fields)
    # Editing a public recipe puts it back through the checks; if it no longer passes it goes back to private
    if recipe.get("visibility") == "public":
        issues = await ps.full_check(db, recipe)
        if issues:
            fields.update({"visibility": "private", "publish_status": "needs_changes", "publish_issues": issues})
            recipe.update(fields)
    await db.recipes.update_one({"recipe_id": recipe_id}, {"$set": fields})
    return recipe


# ── Making a recipe public ────────────────────────────────────────────────────

@router.get("/terms/public-sharing")
async def public_sharing_terms(request: Request):
    await get_current_user(request, request.app.state.db)
    return {"version": ps.TERMS_VERSION, "text": ps.CONSENT_TEXT}


@router.get("/{recipe_id}/publish-check")
async def publish_check(recipe_id: str, request: Request):
    """What still needs fixing before this recipe can go public (nothing is changed)."""
    db = request.app.state.db
    user = await get_current_user(request, db)
    recipe = await _own_recipe(db, user, recipe_id)
    issues = await ps.full_check(db, recipe)
    return {"ready": not issues, "issues": issues, "visibility": recipe.get("visibility") or "private",
            "publish_status": recipe.get("publish_status")}


@router.post("/{recipe_id}/publish")
async def publish_recipe(recipe_id: str, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    body = await request.json()
    recipe = await _own_recipe(db, user, recipe_id)
    if recipe.get("publish_status") == "under_review":
        raise HTTPException(status_code=403, detail="This recipe was reported and is being reviewed, so it can't be made public right now")
    if body.get("consent") is not True or body.get("terms_version") != ps.TERMS_VERSION:
        raise HTTPException(status_code=400, detail="You need to agree to the sharing terms to make a recipe public")
    issues = await ps.full_check(db, recipe)
    caption = re.sub(r"\s+", " ", str(body.get("caption") or "")).strip()
    if len(caption) > 200:
        raise HTTPException(status_code=400, detail="Keep your note under 200 characters")
    for p in content_filter.problems(caption)[:1]:
        issues.append({"field": "caption", "message": "Your note: " + p["message"]})
    now = datetime.now(timezone.utc)
    if issues:
        await db.recipes.update_one({"recipe_id": recipe_id}, {"$set": {
            "visibility": "private", "publish_status": "needs_changes", "publish_issues": issues, "updated_at": now}})
        return {"status": "needs_changes", "issues": issues}
    # Passed: keep the proof of consent, then publish
    await db.recipe_consents.insert_one({
        "user_id": user["user_id"], "recipe_id": recipe_id, "terms_version": ps.TERMS_VERSION,
        "consent_text_sha256": ps.CONSENT_HASH, "show_name": bool(body.get("show_name", True)), "consented_at": now, "action": "publish"})
    author = (user.get("name") or "").strip() if body.get("show_name", True) else ""
    try:
        from recipe_tagger import auto_tag
        auto = auto_tag(recipe)
        tags, cuisine = auto["tags"], recipe.get("cuisine") or auto["cuisine"]
    except Exception:
        tags, cuisine = recipe.get("tags", []), recipe.get("cuisine")
    await db.recipes.update_one({"recipe_id": recipe_id}, {"$set": {
        "visibility": "public", "publish_status": "public", "publish_issues": [], "public_since": now,
        "public_author": author or "CookMe community", "share_caption": caption or None, "tags": tags, "cuisine": cuisine, "updated_at": now}})
    return {"status": "public", "issues": []}


@router.post("/{recipe_id}/unpublish")
async def unpublish_recipe(recipe_id: str, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    await _own_recipe(db, user, recipe_id)
    now = datetime.now(timezone.utc)
    await db.recipes.update_one({"recipe_id": recipe_id}, {"$set": {
        "visibility": "private", "publish_status": None, "publish_issues": [], "updated_at": now}})
    await db.recipe_consents.insert_one({"user_id": user["user_id"], "recipe_id": recipe_id, "action": "unpublish", "consented_at": now})
    return {"status": "private"}

# Soft delete recipe (hide from user's view but keep in master database)
@router.delete("/{recipe_id}")
async def delete_recipe(recipe_id: str, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    
    recipe = await db.recipes.find_one({"recipe_id": recipe_id})
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    if recipe.get("user_id") == user["user_id"]:
        # Your own recipe: really delete it (and the comments on it), not just hide it
        await db.recipes.delete_one({"recipe_id": recipe_id})
        await db.comments.delete_many({"recipe_id": recipe_id})
        return {"message": "Recipe removed from your collection", "recipe_id": recipe_id, "deleted": True}

    # Shared / master recipe: only hide it for this person
    await db.recipes.update_one(
        {"recipe_id": recipe_id},
        {"$addToSet": {"hidden_by": user["user_id"]}}
    )

    return {"message": "Recipe removed from your collection", "recipe_id": recipe_id}

# Restore a hidden recipe back to user's view
@router.post("/{recipe_id}/restore")
async def restore_recipe(recipe_id: str, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    
    recipe = await db.recipes.find_one({"recipe_id": recipe_id})
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    # Remove user from hidden_by list
    await db.recipes.update_one(
        {"recipe_id": recipe_id},
        {"$pull": {"hidden_by": user["user_id"]}}
    )
    
    return {"message": "Recipe restored to your collection", "recipe_id": recipe_id}

# Create recipe
@router.post("", response_model=Recipe)
async def create_recipe(recipe_data: RecipeCreate, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    
    # Note: Content moderation for images should be done at upload time
    # with proper image analysis API, not text-based LLM checks
    
    recipe_id = f"recipe_{uuid.uuid4().hex[:12]}"

    # Automatic free tagging: cooking type, vegetarian/vegan, cuisine (keeps anything the user/importer already set)
    payload = recipe_data.dict()
    try:
        from recipe_tagger import auto_tag
        auto = auto_tag(payload)
        payload["tags"] = auto["tags"]
        if not payload.get("cuisine") and auto["cuisine"]:
            payload["cuisine"] = auto["cuisine"]
    except Exception as e:
        logger.info(f"auto-tag skipped: {e}")

    # Every recipe gets a decent description: keep a good one, otherwise write one (AI, or a plain fallback)
    try:
        from description_quality import description_is_weak, improved_description
        if description_is_weak(payload.get("description"), payload.get("title", "")):
            payload["description"], src = await improved_description(payload)
            payload["description_auto"] = True
            payload["description_source"] = src
    except Exception as e:
        logger.info(f"description check skipped: {e}")

    recipe_doc = {
        "recipe_id": recipe_id,
        "user_id": user["user_id"],
        **payload,
        "uploader_id": user["user_id"],
        "uploader_name": user.get("name", "Anonymous"),
        "likes_count": 0,
        "saves_count": 0,
        "hidden_by": [],
        "favorited_by": [],
        "gallery_images": [],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    await db.recipes.insert_one(recipe_doc)
    
    # Increment user's recipe count
    await db.users.update_one(
        {"user_id": user["user_id"]},
        {"$inc": {"recipes_count": 1}}
    )
    
    recipe_doc.pop("_id", None)
    return recipe_doc

# Helper function to extract recipe data from WPRM (WordPress Recipe Maker) format
def _extract_json_ld_recipe(html: str) -> dict | None:
    """
    Extract a complete recipe from schema.org JSON-LD — zero AI cost.
    Also extracts NutritionInformation if present (free nutrition data).
    Returns None if no valid Recipe schema found.
    """
    import json as _json
    json_ld_blocks = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE
    )
    for block in json_ld_blocks:
        try:
            cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', block.strip())
            data = _json.loads(cleaned)
            items = data if isinstance(data, list) else data.get("@graph", [data])
            if not isinstance(items, list):
                items = [items]
            for item in items:
                if not isinstance(item, dict):
                    continue
                t = item.get("@type", "")
                is_recipe = (
                    (isinstance(t, str) and t.lower() == "recipe") or
                    (isinstance(t, list) and any(x.lower() == "recipe" for x in t if isinstance(x, str)))
                )
                if not is_recipe:
                    continue

                # ── Core fields ───────────────────────────────────────────────
                title = item.get("name", "")
                if not title:
                    continue

                ingredients = [str(i).strip() for i in item.get("recipeIngredient", []) if i]

                steps = extract_steps(item.get("recipeInstructions"))

                # Image
                imgs = item.get("image", "")
                if isinstance(imgs, list):
                    imgs = imgs[0]
                if isinstance(imgs, dict):
                    imgs = imgs.get("url", "")
                image = str(imgs) if imgs else ""

                # Times
                def _dur(iso):
                    if not iso:
                        return ""
                    h = re.search(r'(\d+)H', iso)
                    m = re.search(r'(\d+)M', iso)
                    parts = []
                    if h: parts.append(f"{h.group(1)}h")
                    if m: parts.append(f"{m.group(1)}m")
                    return " ".join(parts)

                servings_raw = item.get("recipeYield", 4)
                if isinstance(servings_raw, str):
                    sm = re.search(r'\d+', servings_raw)
                    servings = int(sm.group()) if sm else 4
                else:
                    servings = int(servings_raw) if servings_raw else 4

                # ── Nutrition (free if site publishes it) ─────────────────────
                nutrition = None
                n = item.get("nutrition", {})
                if isinstance(n, dict):
                    def _num(val):
                        if val is None:
                            return None
                        try:
                            return round(float(re.search(r'[\d.]+', str(val)).group()))
                        except Exception:
                            return None

                    cal = _num(n.get("calories"))
                    if cal:
                        nutrition = {
                            "calories": cal,
                            "protein":  _num(n.get("proteinContent")),
                            "carbs":    _num(n.get("carbohydrateContent")),
                            "fat":      _num(n.get("fatContent")),
                            "fiber":    _num(n.get("fiberContent")),
                            "sugar":    _num(n.get("sugarContent")),
                            "sodium":   _num(n.get("sodiumContent")),
                        }

                # ── Tags / cuisine ────────────────────────────────────────────
                tags = []
                for field in ("recipeCategory", "recipeCuisine", "keywords"):
                    val = item.get(field, "")
                    if isinstance(val, list):
                        tags.extend(val)
                    elif isinstance(val, str) and val:
                        tags.extend([v.strip() for v in val.split(",")])

                result = {
                    "title":       title,
                    "description": item.get("description", ""),
                    "image":       image,
                    "prep_time":   _dur(item.get("prepTime")),
                    "cook_time":   _dur(item.get("cookTime")),
                    "servings":    servings,
                    "difficulty":  "Medium",
                    "ingredients": [{"item": i, "amount": ""} for i in ingredients],
                    "steps":       steps,
                    "tags":        list(set(t for t in tags if t)),
                    "nutrition":   nutrition,  # free if site provides it
                    "source_url":  item.get("url", ""),
                    "confidence":  "high",
                    "confidence_score": 1.0,
                }
                if ingredients and steps:
                    return result
        except Exception:
            continue
    return None


def extract_wprm_recipe(html_content: str) -> dict:
    import re
    from html import unescape
    
    recipe_data = {"ingredients": [], "steps": []}
    
    # Match each li element with wprm-recipe-ingredient class
    li_pattern = r'<li[^>]*class="wprm-recipe-ingredient"[^>]*>(.*?)</li>'
    
    for li_match in re.finditer(li_pattern, html_content, re.DOTALL):
        li_content = li_match.group(1)
        
        # Extract amount
        amount_match = re.search(r'<span class="wprm-recipe-ingredient-amount">([^<]*)</span>', li_content)
        amount = unescape(amount_match.group(1).strip()) if amount_match else ""
        
        # Extract unit
        unit_match = re.search(r'<span class="wprm-recipe-ingredient-unit">([^<]*)</span>', li_content)
        unit = unescape(unit_match.group(1).strip()) if unit_match else ""
        
        # Extract name (may have link inside)
        name_match = re.search(r'<span class="wprm-recipe-ingredient-name"[^>]*>(?:<a[^>]*>)?([^<]+)', li_content)
        name = unescape(name_match.group(1).strip()) if name_match else ""
        
        # Extract notes
        notes_match = re.search(r'<span class="wprm-recipe-ingredient-notes[^"]*">([^<]*)</span>', li_content)
        notes = unescape(notes_match.group(1).strip()) if notes_match else ""
        
        full_amount = f"{amount} {unit}".strip()
        full_name = f"{name} ({notes})" if notes else name
        
        if full_name:
            recipe_data["ingredients"].append({"item": full_name, "amount": full_amount})
    
    # Extract instructions from WPRM format
    instruction_pattern = r'<div class="wprm-recipe-instruction-text"[^>]*>(?:<span[^>]*>)?([^<]+)(?:</span>)?</div>'
    
    for match in re.finditer(instruction_pattern, html_content, re.DOTALL | re.IGNORECASE):
        step = unescape(match.group(1).strip())
        if step:
            recipe_data["steps"].append(step)
    
    return recipe_data


# Extract recipe from photo or URL
@router.post("/extract")
async def extract_recipe(extract_data: RecipeExtractRequest, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    
    try:
        if extract_data.image_urls:
            raise HTTPException(status_code=400, detail="Image extraction not yet supported with current LLM")
            
        elif extract_data.recipe_url:
            import httpx
            import json

            # ── Cache check (normalised URL — strips UTM params etc) ──────────
            cache_key = url_import_key(extract_data.recipe_url)
            cached = await get_cache(db, cache_key)
            if cached:
                return cached

            # Scrape URL content
            # Soft-paywall domains get Googlebot UA + Google referer to trigger
            # "first click free" — they publish full JSON-LD for Google indexing
            _SOFT_PAYWALL = {
                'cooking.nytimes.com', 'nytimes.com',
                'washingtonpost.com',
                'theguardian.com', 'guardian.com',
                'bonappetit.com', 'epicurious.com',
                'telegraph.co.uk', 'ottolenghi.co.uk',
                'latimes.com', 'delish.com', 'food52.com',
                'seriouseats.com', 'esquire.com',
                'menshealth.com', 'womenshealthmag.com',
                'prevention.com', 'countryliving.com',
                'goodhousekeeping.com',
                'homecookingshow.in',
            }
            _fetch_domain = extract_data.recipe_url.lower().split('/')[2].replace('www.', '')
            _fetch_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            if any(d in _fetch_domain for d in _SOFT_PAYWALL):
                _fetch_headers['User-Agent'] = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
                _fetch_headers['Referer'] = 'https://www.google.com/'

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as http_client:
                response = await http_client.get(extract_data.recipe_url, headers=_fetch_headers)
                page_content = response.text

            # ── Try JSON-LD first (free, no AI) ──────────────────────────────
            from urllib.parse import urlparse as _urlparse
            domain = _urlparse(extract_data.recipe_url).netloc.replace('www.', '')
            json_ld_data = _extract_json_ld_recipe(page_content)
            if json_ld_data:
                recipe_data = json_ld_data
                # ── Deduplication check (optimisation #5) ────────────────────
                if recipe_data.get("title"):
                    fp = recipe_fingerprint(recipe_data["title"], domain)
                    existing = await db.recipes.find_one(
                        {"user_id": user["user_id"], "import_fingerprint": fp},
                        {"_id": 0, "recipe_id": 1, "title": 1}
                    )
                    if existing:
                        recipe_data["_duplicate"] = True
                        recipe_data["_existing_recipe_id"] = existing["recipe_id"]
                    else:
                        recipe_data["import_fingerprint"] = fp
                if recipe_data.get("image"):
                    _, recipe_data["image"] = await optimise_image_url(recipe_data["image"])
                await set_cache(db, cache_key, recipe_data, ttl_days=TTL_URL_IMPORT)
                return recipe_data

            # ── Sanitise HTML — remove nav/ads/footer before AI ──────────────
            extracted_image = extract_best_image(page_content, extract_data.recipe_url)
            sanitised_text, fallback_image = sanitise_html(
                page_content, base_url=extract_data.recipe_url, max_chars=3500
            )
            extracted_image = extracted_image or fallback_image

            import logging
            logging.getLogger(__name__).info(
                f"Sanitised: {len(page_content):,} → {len(sanitised_text):,} chars"
            )

            # ── WPRM structured data hint ─────────────────────────────────────
            wprm_data = extract_wprm_recipe(page_content)
            wprm_hint = ""
            if wprm_data["ingredients"]:
                wprm_hint = f"\n\nFound structured ingredients:\n{json.dumps(wprm_data['ingredients'][:10], indent=2)}"
            if wprm_data["steps"]:
                wprm_hint += f"\n\nFound structured steps:\n{json.dumps(wprm_data['steps'][:5], indent=2)}"

            # Extract from sanitised content using LLM
            chat = LlmChat(
                api_key=EMERGENT_KEY,
                session_id=f"extract_{uuid.uuid4().hex[:8]}",
                system_message="You are a recipe extraction assistant. Extract recipe information and return ONLY valid JSON."
            ).with_model("openai", "gpt-4o-mini")

            prompt = f"""Extract the recipe from this content and provide ONLY a JSON response:
{{
  "title": "Recipe name",
  "description": "Brief description",
  "prep_time": "15 min",
  "cook_time": "30 min",
  "servings": 4,
  "difficulty": "Easy",
  "ingredients": [{{"item": "ingredient name", "amount": "1 cup", "category": "Produce"}}],
  "steps": ["Step 1 text", "Step 2 text"],
  "tags": ["tag1", "tag2"]
}}
{wprm_hint}

Content:
{sanitised_text}"""

            msg = UserMessage(text=prompt)
            response_text = await chat.send_message(msg)

            # Parse JSON response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                recipe_data = json.loads(json_match.group())
            else:
                recipe_data = json.loads(response_text)

            # Use WPRM data if more complete
            if wprm_data["ingredients"] and len(wprm_data["ingredients"]) > len(recipe_data.get("ingredients", [])):
                recipe_data["ingredients"] = wprm_data["ingredients"]
            if wprm_data["steps"] and len(wprm_data["steps"]) > len(recipe_data.get("steps", [])):
                recipe_data["steps"] = wprm_data["steps"]

            # Set and optimise image
            if not recipe_data.get("image"):
                recipe_data["image"] = extracted_image
            if recipe_data.get("image"):
                _, recipe_data["image"] = await optimise_image_url(recipe_data["image"])

            # ── Save to cache ─────────────────────────────────────────────────
            await set_cache(db, cache_key, recipe_data, ttl_days=TTL_URL_IMPORT)
                
        else:
            raise HTTPException(status_code=400, detail="Either image_urls or recipe_url required")
        
        return recipe_data
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract recipe: {str(e)}")

# Analyze photo - detect if recipe or ingredients using vision model
@router.post("/analyze-photo")
async def analyze_photo(request: Request):
    db = request.app.state.db
    await get_current_user(request, db)
    
    body = await request.json()
    image_data = body.get("image_data")
    
    if not image_data:
        raise HTTPException(status_code=400, detail="Image data required")
    
    try:
        import json
        import re
        
        # Keep the original image data to return with the result
        original_image = image_data
        
        # Extract base64 data from data URL if present
        if image_data.startswith('data:'):
            # Extract the base64 portion after the comma
            base64_data = image_data.split(',')[1] if ',' in image_data else image_data
        else:
            base64_data = image_data
        
        # Initialize vision-capable model
        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"photo_{uuid.uuid4().hex[:8]}",
            system_message="You are a cooking assistant that analyzes food photos. You can read text from images including recipe cards, cookbook pages, and handwritten recipes. Extract all visible text accurately."
        ).with_model("openai", "gpt-4o-mini")
        
        target_lang = str(body.get("language") or "English")[:30]
        lang_rule = (
            f"\n\nLANGUAGE: Write the title, description, ingredient names and steps in {target_lang}. "
            f"If the text in the image is in another language, translate it into {target_lang} (keep the numbers and units). "
            "Keep the JSON keys exactly as shown below in English.\n"
        )
        prompt = lang_rule + """Carefully analyze this image. Look for ANY text visible in the image.

If you see a RECIPE (written recipe, cookbook page, recipe card, screenshot of a recipe):
- READ ALL THE TEXT carefully including the title, ingredients list, and cooking instructions
- Extract every ingredient with its exact amount as written
- Extract every step/instruction as written

If you see INGREDIENTS (raw ingredients, groceries, pantry items without a recipe):
- Identify all visible food items
- Suggest dishes that could be made

If you see a PHOTO OF FOOD/DISH (a cooked dish, plated food, meal):
- Identify what the dish is
- Create a recipe for that dish

Return ONLY valid JSON in one of these formats:

For RECIPE (when you see written recipe text):
{
  "type": "recipe",
  "title": "Exact Recipe Title from image",
  "description": "Brief description based on the recipe",
  "prep_time": "as written or estimate",
  "cook_time": "as written or estimate",
  "servings": number as written or 4,
  "difficulty": "Easy/Medium/Hard based on steps",
  "ingredients": [{"item": "exact ingredient name", "amount": "exact amount as written"}],
  "steps": ["Exact step 1 as written", "Exact step 2 as written"],
  "is_food_photo": false
}

For FOOD PHOTO (when you see a cooked dish):
{
  "type": "recipe",
  "title": "Name of the dish",
  "description": "Description of what you see",
  "prep_time": "estimate",
  "cook_time": "estimate",
  "servings": 4,
  "difficulty": "Medium",
  "ingredients": [{"item": "ingredient", "amount": "amount"}],
  "steps": ["Step 1", "Step 2"],
  "is_food_photo": true
}

For INGREDIENTS (when you see raw food items without a recipe):
{
  "type": "ingredients",
  "ingredients": ["ingredient1", "ingredient2"],
  "suggestions": [
    {"name": "Dish Name 1", "description": "Brief description"},
    {"name": "Dish Name 2", "description": "Brief description"}
  ]
}

IMPORTANT: Read the actual text in the image carefully. Do not make up recipes - extract what you actually see written.

TRANSLATION: If any text is in a language OTHER than English (Spanish, French, Chinese, Japanese, Korean, German, Italian, Portuguese, Arabic, Hindi, etc.):
- Translate ALL text to English
- Keep ingredient names clear and recognizable
- For each ingredient, also provide the original language name in parentheses if helpful
- Ensure recipe steps are in clear English"""
        
        # Create message with image attachment for vision analysis
        image_content = ImageContent(image_base64=base64_data)
        msg = UserMessage(text=prompt, file_contents=[image_content])
        
        response_text = await chat.send_message(msg)
        
        # Parse JSON response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(response_text)
        
        # For recipe type, include the uploaded image as the recipe image
        # This way the food photo becomes the card image
        if result.get("type") == "recipe":
            result["uploaded_image"] = original_image
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze photo: {str(e)}")


# Validate image quality before AI analysis (balanced - reject only clearly unusable images)
@router.post("/validate-image")
async def validate_image_quality(request: Request):
    db = request.app.state.db
    await get_current_user(request, db)
    
    body = await request.json()
    image_data = body.get("image_data")
    
    if not image_data:
        raise HTTPException(status_code=400, detail="Image data required")
    
    try:
        
        # Extract base64 data from data URL if present
        if image_data.startswith('data:'):
            base64_data = image_data.split(',')[1] if ',' in image_data else image_data
        else:
            base64_data = image_data
        
        # Use vision model to assess image quality
        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"validate_{uuid.uuid4().hex[:8]}",
            system_message="You are an image quality assessor for a cooking app. Be practical - accept most reasonable photos."
        ).with_model("openai", "gpt-4o-mini")
        
        prompt = """Evaluate this image for a cooking/recipe app. The image could be:
- A photo of ingredients/groceries/food items
- A recipe card or cookbook page with text
- A cooked dish or meal
- A screenshot of a recipe

ACCEPT the image if:
- Food items or ingredients are visible and identifiable (even without labels)
- Text is reasonably readable (doesn't need to be perfect)
- The overall image is usable for recipe/ingredient recognition
- Lighting is adequate to see the main content

REJECT the image ONLY if:
- Image is extremely blurry where nothing is identifiable
- Image is almost completely dark (can't see anything)
- Image is completely washed out/overexposed
- Image is corrupted or mostly blank
- Content is so out of focus that items cannot be identified at all

Be LENIENT - if you can reasonably identify food items or read most text, ACCEPT it.
Photos of ingredients on a counter, in a fridge, or groceries should be ACCEPTED.

Respond with EXACTLY one of these formats:
ACCEPT
or
REJECT: <short reason>

Only reject truly unusable images."""

        image_content = ImageContent(image_base64=base64_data)
        msg = UserMessage(text=prompt, file_contents=[image_content])
        
        response_text = await chat.send_message(msg)
        response_text = response_text.strip()
        
        # Parse response
        if response_text.upper().startswith('ACCEPT'):
            return {"status": "ACCEPT", "reason": None}
        elif response_text.upper().startswith('REJECT'):
            # Extract reason after "REJECT:"
            reason = response_text[7:].strip() if len(response_text) > 7 else "Image quality is not sufficient"
            # Remove leading colon if present
            reason = reason.lstrip(':').strip()
            return {"status": "REJECT", "reason": reason}
        else:
            # If response is unclear, accept the image (fail-open)
            return {"status": "ACCEPT", "reason": None}
            
    except Exception as e:
        # If validation fails, log error but allow image through (fail-open for user experience)
        logger.info(f"Image validation error: {str(e)}")
        return {"status": "ACCEPT", "reason": None}


# Translate ingredient names to English with suggestions
@router.post("/translate-ingredient")
async def translate_ingredient(request: Request):
    db = request.app.state.db
    await get_current_user(request, db)
    
    body = await request.json()
    ingredient_name = body.get("name", "")
    
    if not ingredient_name:
        raise HTTPException(status_code=400, detail="Ingredient name required")

    # Our own dictionary first (free, instant). AI is only used for words it doesn't know.
    from ingredient_dictionary import lookup as _dict_lookup, alternatives as _dict_alts, LANGS as _LANGS
    from cache import lookup_aisle as _lookup_aisle
    hit = _dict_lookup(ingredient_name)
    if hit:
        english = hit["concept"]["en"]
        return {
            "original": ingredient_name,
            "detected_language": _LANGS.get(hit["language"], "English"),
            "english_name": english,
            "alternatives": _dict_alts(hit["concept"], exclude_lang=hit["language"]),
            "category": _lookup_aisle(english) or "Other",
            "description": "",
            "source": "dictionary",
        }

    try:
        import json
        import re
        
        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"translate_{uuid.uuid4().hex[:8]}",
            system_message="You are a culinary translator expert who knows food ingredients in all languages."
        ).with_model("openai", "gpt-4o-mini")
        
        prompt = f"""Translate this ingredient name to English and provide alternative names/spellings.

Ingredient: "{ingredient_name}"

Return ONLY valid JSON in this format:
{{
  "original": "the original input",
  "detected_language": "detected language name or 'English'",
  "english_name": "best English translation/name",
  "alternatives": ["alternative spelling 1", "alternative name 2", "common variation 3"],
  "category": "Produce/Dairy/Meat/Seafood/Grains/Spices/Oils/Baking/Canned/Other",
  "description": "brief description of the ingredient"
}}

Provide 3-5 alternative names/spellings that users might search for.
If already in English, provide common variations and spellings."""

        msg = UserMessage(text=prompt)
        response_text = await chat.send_message(msg)
        
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(response_text)
        
        return result
    except Exception:
        # Return basic response on error
        return {
            "original": ingredient_name,
            "detected_language": "Unknown",
            "english_name": ingredient_name,
            "alternatives": [],
            "category": "Other",
            "description": ""
        }


# Generate AI image for a recipe
@router.post("/generate-image")
async def generate_recipe_image(request: Request):
    db = request.app.state.db
    await get_current_user(request, db)
    # AI image generation costs credits per image; off unless ENABLE_AI_IMAGES=1 is set.
    if os.environ.get("ENABLE_AI_IMAGES") != "1":
        return {"success": False, "image": None, "disabled": True}
    
    body = await request.json()
    title = body.get("title", "")
    description = body.get("description", "")
    
    if not title:
        raise HTTPException(status_code=400, detail="Recipe title required")
    
    try:
        
        # Use Gemini Nano Banana for image generation
        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"imggen_{uuid.uuid4().hex[:8]}",
            system_message="You are a food photography expert."
        ).with_model("gemini", "gemini-3-pro-image-preview").with_params(modalities=["image", "text"])
        
        prompt = f"""Generate a beautiful, appetizing food photography image of: {title}

Description: {description}

The image should be:
- Professional food photography style
- Well-lit and appetizing
- Showing the finished dish plated beautifully
- High quality and realistic"""

        msg = UserMessage(text=prompt)
        text_response, images = await chat.send_message_multimodal_response(msg)
        
        if images and len(images) > 0:
            # Return the first generated image as base64
            image_data = images[0].get('data', '')
            mime_type = images[0].get('mime_type', 'image/png')
            return {
                "success": True,
                "image": f"data:{mime_type};base64,{image_data}"
            }
        else:
            return {
                "success": False,
                "error": "No image generated"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate image: {str(e)}")


# Get recipes by category
# Dishes that suit an air fryer when the method says oven / grill / deep-fry (shown with the real air-fryer recipes)
_AF_FOODS = r"\b(wings?|drumsticks?|chicken (?:thighs?|breasts?|tenders?|nuggets?|strips?|legs?)|fries|chips|wedges|(?:roast(?:ed)?|jacket|baked) potato(?:es)?|salmon|cod|haddock|fish (?:fillets?|fingers?|cakes?)|prawns?|falafel|samosas?|spring rolls?|schnitzel|meatballs?|sausages?|burgers?|halloumi|cauliflower|broccoli|brussels|bacon|kievs?|croquettes?|bhajis?|pakoras?)\b"
_AF_METHOD = r"\b(oven|roast|bake|baked|grill|broil|deep[- ]?fr(?:y|ied)|crisp)\b"
_AF_NOT = r"\b(soups?|stews?|casseroles?|curry|cakes?|pudding|pies?|bread|dough|risotto|pasta|smoothie|ice cream|jam|sauce|shanks?|tagines?|stir[- ]?fry|noodles?|salad|wraps?|omelette|tortilla|gratin|tempura|mash(?:ed)?|loaf|empanadas?|chowder|kofta|kebabs?|pizzas?|dips?|polenta|coleslaw|marsala|hash)\b|[^\x00-\x7F]"


@router.get("/type/{cooking_type}")
async def get_recipes_by_cooking_type(cooking_type: str, request: Request, limit: int = 60, skip: int = 0):
    """Shared master recipes for a cooking type: quick, student, budget, instapot, airfryer."""
    db = request.app.state.db
    user = await get_current_user(request, db)
    tags = {"quick": ["quick"], "student": ["student"], "budget": ["budget"],
            "instapot": ["instant pot", "pressure cooker", "slow cooker", "one pot"], "airfryer": ["air fryer", "airfryer"]}.get(cooking_type)
    if not tags:
        raise HTTPException(status_code=404, detail="Unknown cooking type")
    limit = max(1, min(limit, 200))
    tagged = {"tags": {"$regex": "^(" + "|".join(re.escape(t) for t in tags) + ")$", "$options": "i"}}
    if cooking_type == "student":
        # Student meals: the budget-friendly ones that are also simple (few ingredients)
        q = {"$and": [ps.SHARED, tagged, {"$expr": {"$lte": [{"$size": {"$ifNull": ["$ingredients", []]}}, 9]}}]}
    elif cooking_type == "airfryer":
        # Real air-fryer recipes first, then everyday dishes that convert well from the oven
        q = {"$and": [ps.SHARED, {"$or": [tagged, {"$and": [
            {"title": {"$regex": _AF_FOODS, "$options": "i"}},
            {"title": {"$not": {"$regex": _AF_NOT, "$options": "i"}}},
            {"category": {"$ne": "dessert"}},
            {"steps": {"$elemMatch": {"$regex": _AF_METHOD, "$options": "i"}}},
        ]}]}]}
    else:
        q = {"$and": [ps.SHARED, tagged]}
    sort = [("title", 1)]
    recipes = await db.recipes.find(q, {"_id": 0}).sort(sort).skip(max(skip, 0)).limit(limit).to_list(limit)
    if cooking_type == "airfryer":
        for r in recipes:
            r["air_fryer_convertible"] = not any(str(t).lower() in ("air fryer", "airfryer") for t in (r.get("tags") or []))
        recipes.sort(key=lambda r: (r["air_fryer_convertible"], r.get("title", "")))
    return {"recipes": [ps.mask_owner(r, user["user_id"]) for r in recipes], "total": await db.recipes.count_documents(q)}

@router.get("/category/{category}")
async def get_recipes_by_category(category: str, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    
    recipes = await db.recipes.find({"$and": [ps.shared_or_own(user["user_id"]), {"category": category}]}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return recipes

# Like/Unlike recipe
@router.post("/{recipe_id}/like")
async def toggle_like_recipe(recipe_id: str, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    
    # Check if already liked
    like = await db.recipe_likes.find_one({
        "user_id": user["user_id"],
        "recipe_id": recipe_id
    })
    
    if like:
        # Unlike
        await db.recipe_likes.delete_one({"_id": like["_id"]})
        await db.recipes.update_one(
            {"recipe_id": recipe_id},
            {"$inc": {"likes_count": -1}}
        )
        return {"liked": False}
    else:
        # Like
        await db.recipe_likes.insert_one({
            "user_id": user["user_id"],
            "recipe_id": recipe_id,
            "created_at": datetime.now(timezone.utc)
        })
        await db.recipes.update_one(
            {"recipe_id": recipe_id},
            {"$inc": {"likes_count": 1}}
        )
        return {"liked": True}

# Save/Unsave recipe (Favorites functionality)
@router.post("/{recipe_id}/save")
async def toggle_save_recipe(recipe_id: str, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    
    # Check if already saved/favorited
    recipe = await db.recipes.find_one({"recipe_id": recipe_id})
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    is_favorited = user["user_id"] in recipe.get("favorited_by", [])
    
    if is_favorited:
        # Remove from favorites
        await db.recipes.update_one(
            {"recipe_id": recipe_id},
            {
                "$pull": {"favorited_by": user["user_id"]},
                "$inc": {"saves_count": -1}
            }
        )
        # Also remove from recipe_saves collection for backwards compatibility
        await db.recipe_saves.delete_one({
            "user_id": user["user_id"],
            "recipe_id": recipe_id
        })
        return {"saved": False}
    else:
        # Add to favorites
        await db.recipes.update_one(
            {"recipe_id": recipe_id},
            {
                "$addToSet": {"favorited_by": user["user_id"]},
                "$inc": {"saves_count": 1}
            }
        )
        # Also save to recipe_saves collection for backwards compatibility
        await db.recipe_saves.update_one(
            {"user_id": user["user_id"], "recipe_id": recipe_id},
            {"$set": {
                "user_id": user["user_id"],
                "recipe_id": recipe_id,
                "created_at": datetime.now(timezone.utc)
            }},
            upsert=True
        )
        return {"saved": True}


# Extract recipe from Facebook/Instagram using og:meta tags
@router.post("/extract-social")
async def extract_from_social(request: Request):
    """
    Extract recipe from any social media URL.
    Supports: Facebook, Instagram (fallback), TikTok, Pinterest, Twitter/X, Reddit.
    Uses HTML sanitisation to strip noise before AI, and optimises the image.
    """
    db = request.app.state.db
    await get_current_user(request, db)

    body = await request.json()
    url = body.get("url")
    platform = body.get("platform", "unknown")

    if not url:
        raise HTTPException(status_code=400, detail="URL required")

    import httpx
    import json

    # ── Platform-specific User-Agents ─────────────────────────────────────────
    # Using crawler UAs gets us OG meta tags without JS rendering
    PLATFORM_UA = {
        "facebook":  "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
        "instagram": "facebookexternalhit/1.1",
        "tiktok":    "Twitterbot/1.0",
        "pinterest": "Mozilla/5.0 (compatible; Pinterestbot/1.0; +https://www.pinterest.com/bot.html)",
        "twitter":   "Twitterbot/1.0",
        "reddit":    "Mozilla/5.0 (compatible; RedditBot/1.0)",
    }
    ua = PLATFORM_UA.get(platform.lower(),
         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        async with httpx.AsyncClient(
            timeout=30.0, follow_redirects=True, headers=headers
        ) as http_client:
            response = await http_client.get(url)
            html_content = response.text
            final_url = str(response.url)

        # ── Login / block detection ────────────────────────────────────────────
        if response.status_code >= 400:
            raise HTTPException(
                status_code=403,
                detail=f"This {platform} post cannot be accessed. It may be private or deleted."
            )

        login_signals = [
            '/login' in final_url, 'login.php' in final_url,
            'Log in to Facebook' in html_content,
            'Log in to Instagram' in html_content,
            'Log in to TikTok' in html_content,
            'You must log in' in html_content,
            'Sign in' in html_content and len(html_content) < 5000,
        ]
        if any(login_signals):
            raise HTTPException(
                status_code=403,
                detail=f"This {platform} post requires login. Please make sure it is set to Public."
            )

        # ── Sanitise HTML — strip nav/ads/footer ──────────────────────────────
        sanitised_text, extracted_image = sanitise_html(
            html_content, base_url=url, max_chars=3000
        )

        # Extract OG data for title/description/image
        og_title_m = re.search(
            r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']',
            html_content, re.IGNORECASE
        )
        og_desc_m = re.search(
            r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']',
            html_content, re.IGNORECASE
        )
        og_img_m = re.search(
            r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
            html_content, re.IGNORECASE
        )
        og_site_m = re.search(
            r'<meta[^>]*property=["\']og:site_name["\'][^>]*content=["\']([^"\']+)["\']',
            html_content, re.IGNORECASE
        )

        from html import unescape
        og_title = unescape(og_title_m.group(1)) if og_title_m else ""
        og_desc  = unescape(og_desc_m.group(1))  if og_desc_m  else ""
        og_image = og_img_m.group(1)              if og_img_m  else ""
        og_site  = unescape(og_site_m.group(1))   if og_site_m  else platform.capitalize()

        # Pinterest-specific: description tag often has recipe text
        if platform.lower() == "pinterest" and not og_desc:
            pin_desc_m = re.search(
                r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']',
                html_content, re.IGNORECASE
            )
            if pin_desc_m:
                og_desc = unescape(pin_desc_m.group(1))

        # Reddit: JSON-LD often has full post text
        if platform.lower() == "reddit":
            reddit_ld = re.search(
                r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                html_content, re.DOTALL | re.IGNORECASE
            )
            if reddit_ld:
                try:
                    ld_data = json.loads(reddit_ld.group(1))
                    if isinstance(ld_data, dict) and ld_data.get("articleBody"):
                        og_desc = ld_data["articleBody"][:2000]
                except Exception:
                    pass

        # Build content for AI — prefer sanitised text over OG description alone
        content_for_ai = sanitised_text or f"{og_title}\n{og_desc}"
        if not content_for_ai.strip():
            raise HTTPException(
                status_code=400,
                detail=f"No content found in this {platform} post. It may be private or contain only video/images."
            )

        image_url = og_image or extracted_image

        # ── AI extraction ──────────────────────────────────────────────────────
        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"social_{uuid.uuid4().hex[:8]}",
            system_message="You are a recipe extraction assistant. Extract recipe details from social media content. Return ONLY valid JSON."
        ).with_model("openai", "gpt-4o-mini")

        prompt = f"""Extract a recipe from this {platform} post.
If ingredients and steps are present, use them exactly.
If only a dish name is mentioned, create a standard recipe for it.

PLATFORM: {platform}
SITE: {og_site}
URL: {url}

CONTENT:
{content_for_ai[:3000]}

Return ONLY valid JSON:
{{
  "title": "Recipe name",
  "description": "Brief description",
  "prep_time": "estimated time",
  "cook_time": "estimated time",
  "servings": 4,
  "difficulty": "Easy/Medium/Hard",
  "ingredients": [{{"item": "ingredient", "amount": "amount"}}],
  "steps": ["Step 1", "Step 2"],
  "tags": ["{platform}", "Social Import"],
  "source": "{og_site}",
  "source_url": "{url}"
}}"""

        response_text = await chat.send_message(UserMessage(text=prompt))
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        recipe_data = json.loads(json_match.group() if json_match else response_text)

        # Set and optimise image
        if not recipe_data.get("image"):
            recipe_data["image"] = image_url
        if recipe_data.get("image"):
            _, recipe_data["image"] = await optimise_image_url(recipe_data["image"])

        return recipe_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to extract from {platform}: {str(e)}"
        )


# Extract recipe from YouTube video
@router.post("/extract-youtube")
async def extract_from_youtube(request: Request):
    db = request.app.state.db
    await get_current_user(request, db)
    
    body = await request.json()
    youtube_url = body.get("youtube_url")
    
    if not youtube_url:
        raise HTTPException(status_code=400, detail="YouTube URL required")
    
    try:
        # Extract video ID
        import re
        import httpx
        import json
        from html import unescape
        
        video_id_match = re.search(r'(?:v=|youtu\.be/|/shorts/)([a-zA-Z0-9_-]{11})', youtube_url)
        if not video_id_match:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        
        video_id = video_id_match.group(1)

        # ── Cache check ───────────────────────────────────────────────────────
        yt_cache_key = youtube_key(video_id)
        cached = await get_cache(db, yt_cache_key)
        if cached:
            return cached

        video_title = ""
        video_author = ""
        video_description = ""
        video_thumbnail = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=headers) as http_client:
            # Method 1: Try oEmbed API
            try:
                oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
                oembed_response = await http_client.get(oembed_url)
                if oembed_response.status_code == 200:
                    oembed_data = oembed_response.json()
                    video_title = oembed_data.get("title", "")
                    video_author = oembed_data.get("author_name", "")
                    if oembed_data.get("thumbnail_url"):
                        video_thumbnail = oembed_data.get("thumbnail_url")
            except Exception:
                pass
            
            # Method 2: Scrape page for more info (og:tags and description)
            try:
                page_response = await http_client.get(f"https://www.youtube.com/watch?v={video_id}")
                page_content = page_response.text
                
                # Extract title from og:title if not found
                if not video_title:
                    title_match = re.search(r'<meta property="og:title" content="([^"]+)"', page_content)
                    if title_match:
                        video_title = unescape(title_match.group(1))
                
                # Extract description
                desc_match = re.search(r'<meta name="description" content="([^"]+)"', page_content)
                if desc_match:
                    video_description = unescape(desc_match.group(1))
                
                # Try to get og:image for better thumbnail
                og_img_match = re.search(r'<meta property="og:image" content="([^"]+)"', page_content)
                if og_img_match:
                    video_thumbnail = og_img_match.group(1)
                
                # Extract author if not found
                if not video_author:
                    author_match = re.search(r'"author":"([^"]+)"', page_content)
                    if author_match:
                        video_author = unescape(author_match.group(1))
                        
            except Exception as e:
                logger.warning(f"Warning: Could not fetch YouTube page: {e}")
        
        # If we still don't have a title, use video ID
        if not video_title:
            video_title = f"Recipe from YouTube ({video_id})"
        
        # Use LLM to extract recipe from video metadata
        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"youtube_{uuid.uuid4().hex[:8]}",
            system_message="You are a recipe extraction assistant. Extract recipe details from cooking video information. Create a complete recipe based on the video title."
        ).with_model("openai", "gpt-4o-mini")
        
        prompt = f"""Extract a recipe from this YouTube cooking video:

VIDEO TITLE: {video_title}
VIDEO AUTHOR: {video_author}
VIDEO DESCRIPTION: {video_description[:1000] if video_description else 'Not available'}
VIDEO URL: {youtube_url}

Based on the video title and description, create a complete recipe. If the video is about a specific dish, provide accurate ingredients and steps for that dish.

Return ONLY valid JSON:
{{
  "title": "{video_title}",
  "description": "Brief description based on the video",
  "prep_time": "estimated prep time",
  "cook_time": "estimated cook time",
  "servings": 4,
  "difficulty": "Easy/Medium/Hard",
  "ingredients": [{{"item": "ingredient name", "amount": "amount"}}],
  "steps": ["Step 1", "Step 2"],
  "tags": ["YouTube", "Video Recipe"],
  "source": "YouTube",
  "video_url": "{youtube_url}",
  "author": "{video_author}",
  "image": "{video_thumbnail}"
}}"""
        
        msg = UserMessage(text=prompt)
        response_text = await chat.send_message(msg)
        
        # Parse JSON
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            recipe_data = json.loads(json_match.group())
        else:
            recipe_data = json.loads(response_text)
        
        # Ensure image is set
        if not recipe_data.get("image"):
            recipe_data["image"] = video_thumbnail

        # Optimise thumbnail image
        if recipe_data.get("image"):
            _, recipe_data["image"] = await optimise_image_url(recipe_data["image"])

        # ── Save to cache ─────────────────────────────────────────────────────
        await set_cache(db, yt_cache_key, recipe_data, ttl_days=TTL_YOUTUBE)

        return recipe_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract recipe from video: {str(e)}")


# Calculate nutrition for a recipe
@router.post("/calculate-nutrition")
async def calculate_nutrition(request: Request):
    """
    Lazy nutrition calculation — called only when user opens a recipe.

    Priority:
      0. Already on recipe document (JSON-LD or prior calc)  — free
      1. AI cache (permanent 10yr TTL)                        — free
      2. Open Food Facts + Edamam APIs                        — free
      3. AI fallback (gpt-4o-mini)                            — ~$0.0003/call
    """
    db = request.app.state.db
    await get_current_user(request, db)

    body        = await request.json()
    ingredients = body.get("ingredients", [])
    servings    = body.get("servings", 4)
    recipe_id   = body.get("recipe_id")

    if not ingredients:
        raise HTTPException(status_code=400, detail="Ingredients required")

    # ── 0. Already on recipe document ────────────────────────────────────────
    if recipe_id:
        recipe_doc = await db.recipes.find_one(
            {"recipe_id": recipe_id, "nutrition": {"$exists": True, "$ne": None}},
            {"_id": 0, "nutrition": 1}
        )
        stored = (recipe_doc or {}).get("nutrition")
        # Values the site published (no "source") or calculated with the fixed parser (calc_v 2) are kept;
        # older calculated values were wrong for many recipes and get recalculated.
        if stored and (not stored.get("source") or stored.get("calc_v") == 2 or stored.get("source") == "ai"):
            return stored

    # ── 1. Check AI cache ─────────────────────────────────────────────────────
    cache_key = nutrition_key(ingredients, servings)
    cached = await get_cache(db, cache_key)
    if cached:
        if recipe_id:
            await db.recipes.update_one(
                {"recipe_id": recipe_id},
                {"$set": {"nutrition": cached}}
            )
        return cached

    # ── 2. Try free nutrition APIs (Open Food Facts + Edamam) ─────────────────
    from nutrition_lookup import calculate_recipe_nutrition_free
    free_nutrition = await calculate_recipe_nutrition_free(ingredients, servings)
    if free_nutrition:
        await set_cache(db, cache_key, free_nutrition, ttl_days=TTL_NUTRITION)
        if recipe_id:
            await db.recipes.update_one(
                {"recipe_id": recipe_id},
                {"$set": {"nutrition": free_nutrition, "updated_at": datetime.now(timezone.utc)}}
            )
        return free_nutrition

    # ── 3. AI fallback (only when free APIs insufficient) ─────────────────────
    try:
        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"nutrition_{uuid.uuid4().hex[:8]}",
            system_message="You are a nutrition calculation assistant. Provide accurate nutritional estimates."
        ).with_model("openai", "gpt-4o-mini")

        ingredients_text = ", ".join([
            f"{i.get('amount', '')} {i.get('item', i)}" for i in ingredients
        ])

        prompt = f"""Calculate nutritional info per serving for this recipe ({servings} servings).
Ingredients: {ingredients_text}
Return ONLY valid JSON:
{{"calories": 450, "protein": 25, "carbs": 45, "fat": 18, "fiber": 6, "sugar": 8, "sodium": 800}}"""

        response_text = await chat.send_message(UserMessage(text=prompt))
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        nutrition_data = json.loads(json_match.group() if json_match else response_text)
        nutrition_data["source"] = "ai"

        await set_cache(db, cache_key, nutrition_data, ttl_days=TTL_NUTRITION)
        if recipe_id:
            await db.recipes.update_one(
                {"recipe_id": recipe_id},
                {"$set": {"nutrition": nutrition_data, "updated_at": datetime.now(timezone.utc)}}
            )

        return nutrition_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate nutrition: {str(e)}")


# AI Recipe Suggestions based on pantry
@router.post("/suggestions/pantry")
async def get_pantry_suggestions(request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    
    # Get user's pantry items
    pantry_items = await db.pantry_items.find(
        {"user_id": user["user_id"], "in_stock": True},
        {"_id": 0}
    ).to_list(100)
    
    if not pantry_items:
        raise HTTPException(status_code=400, detail="No pantry items found")
    
    ingredients_list = [item["name"] for item in pantry_items]
    
    # Use LLM to suggest recipes
    try:
        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"suggestions_{user['user_id']}",
            system_message="You are a creative recipe suggestion assistant. Provide recipes in JSON format."
        ).with_model("openai", "gpt-4o-mini")
        
        prompt = f"""Based on these pantry ingredients: {', '.join(ingredients_list)}, suggest 3 recipes I can make. 
        
Return ONLY valid JSON in this format:
{{
  "recipes": [
    {{
      "title": "Recipe Name",
      "description": "Brief description",
      "prep_time": "15 min",
      "cook_time": "20 min",
      "difficulty": "Easy",
      "ingredients_used": ["ingredient1", "ingredient2"]
    }}
  ]
}}"""
        
        msg = UserMessage(text=prompt)
        response_text = await chat.send_message(msg)
        
        # Parse JSON
        import json
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            suggestions = json.loads(json_match.group())
        else:
            suggestions = json.loads(response_text)
            
        return suggestions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate suggestions: {str(e)}")



# Upload image to recipe gallery
@router.post("/{recipe_id}/gallery")
async def upload_gallery_image(recipe_id: str, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    
    body = await request.json()
    image_data = body.get("image_data")
    
    if not image_data:
        raise HTTPException(status_code=400, detail="Image data required")
    
    # Check recipe exists
    recipe = await db.recipes.find_one({"recipe_id": recipe_id})
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    # Create gallery image entry
    gallery_entry = {
        "image_id": f"img_{uuid.uuid4().hex[:12]}",
        "user_id": user["user_id"],
        "user_name": user.get("name", "Anonymous"),
        "image_url": image_data,
        "uploaded_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Add to recipe gallery (persists even if user deletes recipe from their view)
    await db.recipes.update_one(
        {"recipe_id": recipe_id},
        {"$push": {"gallery_images": gallery_entry}}
    )
    
    return {"message": "Image uploaded to gallery", "image": gallery_entry}

# Delete image from gallery (only by uploader)
@router.delete("/{recipe_id}/gallery/{image_id}")
async def delete_gallery_image(recipe_id: str, image_id: str, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    
    # Remove image only if user is the uploader
    result = await db.recipes.update_one(
        {"recipe_id": recipe_id},
        {"$pull": {"gallery_images": {"image_id": image_id, "user_id": user["user_id"]}}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Image not found or you don't have permission to delete")
    
    return {"message": "Image deleted from gallery"}
