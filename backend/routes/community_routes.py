"""
community_routes.py
===================
API endpoints for the community recipe database.
"""

import random
import re
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from auth import get_current_user

router = APIRouter(prefix="/community", tags=["community"])

SEASON_KEYWORDS = {
    "spring": {"spring", "asparagus", "peas", "fresh", "light", "garden"},
    "summer": {"summer", "salad", "grilled", "fresh", "light", "citrus", "berry", "berries", "seafood"},
    "autumn": {"autumn", "fall", "pumpkin", "squash", "mushroom", "mushrooms", "comfort", "roast"},
    "winter": {"winter", "stew", "stews", "soup", "soups", "roast", "comfort", "braise", "bake", "hearty"},
}
SEASON_LABELS = {
    "spring": "Spring fresh picks",
    "summer": "Summer favourites",
    "autumn": "Autumn classics",
    "winter": "Winter comfort",
}


def current_season(today: Optional[date] = None) -> str:
    month = (today or date.today()).month
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    if month in (9, 10, 11):
        return "autumn"
    return "winter"


def recipe_matches_season(recipe: dict, season: str) -> bool:
    """Use explicit tags and descriptive text as a soft seasonal signal."""
    terms = SEASON_KEYWORDS[season]
    tags = recipe.get("tags", []) or []
    searchable = " ".join([
        str(recipe.get("title", "")),
        str(recipe.get("description", "")),
        str(recipe.get("category", "")),
        str(recipe.get("cuisine", "")),
        " ".join(str(tag) for tag in tags),
    ]).lower()
    words = set(re.findall(r"[a-z]+", searchable))
    return bool(words & terms)


@router.get("/recipes")
async def browse_community_recipes(
    request: Request,
    search: Optional[str] = None,
    cuisine: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[str] = None,
    limit: int = 24,
    skip: int = 0,
):
    db = request.app.state.db
    await get_current_user(request, db)

    query = {}
    if search:
        query["$text"] = {"$search": search}
    if cuisine:
        query["cuisine"] = cuisine.lower()
    if category:
        query["category"] = category.lower()
    if tags:
        query["tags"] = {"$in": [tag.strip().lower() for tag in tags.split(",")]}

    sort = [("score", {"$meta": "textScore"})] if search else [("likes_count", -1)]
    projection = {"_id": 0}
    if search:
        projection["score"] = {"$meta": "textScore"}

    recipes = await db.community_recipes.find(query, projection).sort(sort).skip(skip).limit(limit).to_list(limit)
    total = await db.community_recipes.count_documents(query)
    return {
        "recipes": recipes,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": (skip + limit) < total,
    }


@router.get("/recipes/featured")
async def get_featured_recipes(request: Request, count: int = 12):
    """Return a daily stable selection, preferring recipes relevant to this season."""
    db = request.app.state.db
    await get_current_user(request, db)
    count = max(1, min(count, 30))
    season = current_season()

    top = await db.community_recipes.find(
        {"steps": {"$exists": True, "$not": {"$size": 0}},
         "ingredients": {"$exists": True, "$not": {"$size": 0}}},
        {"_id": 0, "community_recipe_id": 1, "title": 1, "description": 1,
         "image": 1, "prep_time": 1, "cook_time": 1, "servings": 1,
         "difficulty": 1, "cuisine": 1, "category": 1, "tags": 1,
         "likes_count": 1, "nutrition": 1}
    ).sort("likes_count", -1).limit(200).to_list(200)

    if not top:
        return {"recipes": [], "season": season, "season_label": SEASON_LABELS[season]}

    seasonal = [recipe for recipe in top if recipe_matches_season(recipe, season)]
    candidates = seasonal if seasonal else top

    # Include the season in the seed so a new season starts a fresh rotation;
    # the date keeps selections stable during a given day.
    seed = int(date.today().strftime("%Y%m%d")) + sum(ord(char) for char in season)
    rng = random.Random(seed)
    selected = rng.sample(candidates, min(count, len(candidates)))
    return {"recipes": selected, "season": season, "season_label": SEASON_LABELS[season]}


@router.get("/recipes/similar")
async def get_similar_recipes(
    request: Request,
    recipe_id: Optional[str] = None,
    cuisine: Optional[str] = None,
    ingredient_names: Optional[str] = None,
    limit: int = 6,
):
    db = request.app.state.db
    await get_current_user(request, db)

    if recipe_id:
        source = await db.recipes.find_one({"recipe_id": recipe_id}, {"_id": 0})
        if source:
            names = []
            for ingredient in source.get("ingredients", []):
                name = ingredient.get("item", "") if isinstance(ingredient, dict) else str(ingredient)
                clean = re.sub(r"^[\d\s./½¼¾⅓⅔]+\s*(?:cup|tbsp|tsp|oz|lb|g|kg|ml)s?\s*", "", name, flags=re.I).strip()
                if clean:
                    names.append(clean.lower())
            cuisine = cuisine or source.get("cuisine", "")
            ingredient_names = ",".join(names[:8])

    if not ingredient_names and not cuisine:
        raise HTTPException(status_code=400, detail="Provide recipe_id, cuisine, or ingredient_names")

    query = {}
    if ingredient_names:
        query["ingredient_names"] = {"$in": [name.strip() for name in ingredient_names.split(",") if name.strip()]}
    if cuisine:
        query["cuisine"] = cuisine.lower()
    if recipe_id:
        query["community_recipe_id"] = {"$ne": recipe_id}

    similar = await db.community_recipes.find(
        query,
        {"_id": 0, "community_recipe_id": 1, "title": 1, "description": 1,
         "image": 1, "prep_time": 1, "cook_time": 1, "servings": 1,
         "difficulty": 1, "cuisine": 1, "tags": 1, "nutrition": 1,
         "ingredient_names": 1}
    ).limit(limit * 3).to_list(limit * 3)

    if ingredient_names:
        names_set = {name.strip() for name in ingredient_names.split(",")}
        for recipe in similar:
            recipe["_match_score"] = len(set(recipe.get("ingredient_names", [])) & names_set)
        similar.sort(key=lambda recipe: recipe.get("_match_score", 0), reverse=True)
        for recipe in similar:
            recipe.pop("_match_score", None)
            recipe.pop("ingredient_names", None)

    return {"recipes": similar[:limit]}


@router.get("/recipes/{community_recipe_id}")
async def get_community_recipe(community_recipe_id: str, request: Request):
    db = request.app.state.db
    await get_current_user(request, db)
    recipe = await db.community_recipes.find_one({"community_recipe_id": community_recipe_id}, {"_id": 0})
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


@router.post("/recipes/{community_recipe_id}/like")
async def like_community_recipe(community_recipe_id: str, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    existing = await db.community_likes.find_one({
        "user_id": user["user_id"],
        "community_recipe_id": community_recipe_id,
    })
    if existing:
        await db.community_likes.delete_one({"_id": existing["_id"]})
        await db.community_recipes.update_one({"community_recipe_id": community_recipe_id}, {"$inc": {"likes_count": -1}})
        return {"liked": False}

    await db.community_likes.insert_one({
        "user_id": user["user_id"],
        "community_recipe_id": community_recipe_id,
        "created_at": datetime.now(timezone.utc),
    })
    await db.community_recipes.update_one({"community_recipe_id": community_recipe_id}, {"$inc": {"likes_count": 1}})
    return {"liked": True}


@router.post("/recipes/{community_recipe_id}/save")
async def save_community_recipe(community_recipe_id: str, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    community_recipe = await db.community_recipes.find_one({"community_recipe_id": community_recipe_id}, {"_id": 0})
    if not community_recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    existing = await db.recipes.find_one({"user_id": user["user_id"], "source_community_id": community_recipe_id})
    if existing:
        return {"saved": True, "recipe_id": existing["recipe_id"], "already_existed": True}

    now = datetime.now(timezone.utc)
    recipe_id = f"recipe_{uuid.uuid4().hex[:12]}"
    recipe_doc = {
        "recipe_id": recipe_id,
        "user_id": user["user_id"],
        "title": community_recipe["title"],
        "description": community_recipe.get("description", ""),
        "image": community_recipe.get("image", ""),
        "prep_time": community_recipe.get("prep_time", ""),
        "cook_time": community_recipe.get("cook_time", ""),
        "servings": community_recipe.get("servings", 4),
        "difficulty": community_recipe.get("difficulty", "Medium"),
        "ingredients": community_recipe.get("ingredients", []),
        "steps": community_recipe.get("steps", []),
        "tags": community_recipe.get("tags", []),
        "category": community_recipe.get("category"),
        "cuisine": community_recipe.get("cuisine"),
        "nutrition": community_recipe.get("nutrition"),
        "source_url": community_recipe.get("source_url", ""),
        "source_community_id": community_recipe_id,
        "attribution": community_recipe.get("attribution", ""),
        "likes_count": 0,
        "saves_count": 0,
        "hidden_by": [],
        "favorited_by": [],
        "gallery_images": [],
        "uploader_id": user["user_id"],
        "uploader_name": user.get("name", "Anonymous"),
        "created_at": now,
        "updated_at": now,
    }
    await db.recipes.insert_one(recipe_doc)
    await db.users.update_one({"user_id": user["user_id"]}, {"$inc": {"recipes_count": 1}})
    return {"saved": True, "recipe_id": recipe_id, "already_existed": False}
