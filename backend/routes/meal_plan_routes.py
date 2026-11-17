from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import uuid
import os
import json
import re
from pydantic import BaseModel
from auth import get_current_user
from emergentintegrations.llm.chat import LlmChat, UserMessage

router = APIRouter(prefix="/meal-plans", tags=["meal-plans"])
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")


# ── Models ────────────────────────────────────────────────────────────────────

class MealSlot(BaseModel):
    recipe_id: Optional[str] = None
    recipe_title: Optional[str] = None
    recipe_image: Optional[str] = None
    custom_meal: Optional[str] = None   # free-text if no saved recipe linked


class DayPlan(BaseModel):
    date: str                           # ISO date string e.g. "2025-03-10"
    day_name: str                       # "Monday" etc.
    breakfast: Optional[MealSlot] = None
    lunch: Optional[MealSlot] = None
    dinner: Optional[MealSlot] = None


class MealPlanCreate(BaseModel):
    week_start: str                     # ISO date string for Monday of the week
    days: List[DayPlan]


class AIGenerateRequest(BaseModel):
    week_start: str
    cuisine_preferences: Optional[List[str]] = None
    dietary_restrictions: Optional[List[str]] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def week_key(week_start: str) -> str:
    """Normalise week start to YYYY-MM-DD."""
    return week_start[:10]


def build_week_days(week_start: str) -> List[dict]:
    """Return 7 day stubs starting from week_start."""
    from datetime import date
    start = date.fromisoformat(week_start[:10])
    names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return [
        {"date": (start + timedelta(days=i)).isoformat(), "day_name": names[i],
         "breakfast": None, "lunch": None, "dinner": None}
        for i in range(7)
    ]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
async def get_meal_plans(request: Request):
    """Return all meal plans for the current user, newest first."""
    db = request.app.state.db
    user = await get_current_user(request, db)
    plans = await db.meal_plans.find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).sort("week_start", -1).to_list(52)
    return plans


@router.get("/{week_start}")
async def get_meal_plan(week_start: str, request: Request):
    """Return meal plan for a specific week (creates empty one if missing)."""
    db = request.app.state.db
    user = await get_current_user(request, db)
    key = week_key(week_start)

    plan = await db.meal_plans.find_one(
        {"user_id": user["user_id"], "week_start": key}, {"_id": 0}
    )
    if not plan:
        # Return empty plan without saving
        return {
            "meal_plan_id": None,
            "user_id": user["user_id"],
            "week_start": key,
            "days": build_week_days(key),
            "created_at": None,
            "updated_at": None,
        }
    return plan


@router.put("/{week_start}")
async def save_meal_plan(week_start: str, data: MealPlanCreate, request: Request):
    """Save (upsert) a meal plan for the given week."""
    db = request.app.state.db
    user = await get_current_user(request, db)
    key = week_key(week_start)

    now = datetime.now(timezone.utc)
    days_data = [d.dict() for d in data.days]

    result = await db.meal_plans.find_one_and_update(
        {"user_id": user["user_id"], "week_start": key},
        {
            "$set": {
                "days": days_data,
                "updated_at": now,
            },
            "$setOnInsert": {
                "meal_plan_id": f"mp_{uuid.uuid4().hex[:12]}",
                "user_id": user["user_id"],
                "week_start": key,
                "created_at": now,
            },
        },
        upsert=True,
        return_document=True,
    )
    if result:
        result.pop("_id", None)
    return result or {"message": "Saved"}


@router.delete("/{week_start}")
async def delete_meal_plan(week_start: str, request: Request):
    """Delete the meal plan for a week."""
    db = request.app.state.db
    user = await get_current_user(request, db)
    await db.meal_plans.delete_one(
        {"user_id": user["user_id"], "week_start": week_key(week_start)}
    )
    return {"message": "Meal plan deleted"}


@router.post("/generate")
async def generate_ai_meal_plan(data: AIGenerateRequest, request: Request):
    """
    AI-generate a full week meal plan based on:
    - User's pantry items
    - Their saved recipes
    - Optional cuisine preferences / dietary restrictions
    """
    db = request.app.state.db
    user = await get_current_user(request, db)
    key = week_key(data.week_start)

    # Gather pantry
    pantry_items = await db.pantry_items.find(
        {"user_id": user["user_id"], "in_stock": True}, {"_id": 0}
    ).to_list(100)
    pantry_names = [p["name"] for p in pantry_items]

    # Gather saved recipes (titles only for context)
    saved = await db.recipes.find(
        {"user_id": user["user_id"]}, {"_id": 0, "title": 1, "recipe_id": 1, "cuisine": 1, "category": 1}
    ).to_list(50)
    saved_titles = [r["title"] for r in saved]

    # ── 1) Free path: build the week from tagged recipes (master list + the user's own) ──
    try:
        from meal_plan_builder import build_plan
        pool = await db.recipes.find(
            {"$or": [{"user_id": "system_seeder"}, {"visibility": "public"}, {"user_id": user["user_id"], "hidden_by": {"$ne": user["user_id"]}}]},
            {"_id": 0, "recipe_id": 1, "title": 1, "image": 1, "tags": 1, "cuisine": 1, "category": 1, "ingredients": 1},
        ).to_list(3000)
        built = build_plan(key, pool, pantry_names, data.cuisine_preferences or [], data.dietary_restrictions or [], seed=uuid.uuid4().hex)
        if built:
            days, notes = built
            now = datetime.now(timezone.utc)
            await db.meal_plans.find_one_and_update(
                {"user_id": user["user_id"], "week_start": key},
                {"$set": {"days": days, "updated_at": now},
                 "$setOnInsert": {"meal_plan_id": f"mp_{uuid.uuid4().hex[:12]}", "user_id": user["user_id"],
                                  "week_start": key, "created_at": now}},
                upsert=True,
            )
            return {"week_start": key, "days": days, "source": "recipes", "notes": notes}
    except Exception as e:
        import logging
        logging.getLogger(__name__).info(f"Recipe-based meal plan failed, using AI: {e}")

    # ── 2) AI fallback (custom requests, e.g. gluten-free, or too few recipes) ──
    # Build prompt
    prefs = ", ".join(data.cuisine_preferences) if data.cuisine_preferences else "any cuisine"
    restrictions = ", ".join(data.dietary_restrictions) if data.dietary_restrictions else "none"

    prompt = f"""Create a 7-day meal plan (Monday–Sunday) starting {key}.

Pantry available: {", ".join(pantry_names) if pantry_names else "not specified"}
User's saved recipes: {", ".join(saved_titles[:20]) if saved_titles else "none yet"}
Cuisine preferences: {prefs}
Dietary restrictions: {restrictions}

Return ONLY valid JSON — no markdown, no backticks:
{{
  "days": [
    {{
      "date": "YYYY-MM-DD",
      "day_name": "Monday",
      "breakfast": {{"custom_meal": "meal name"}},
      "lunch": {{"custom_meal": "meal name"}},
      "dinner": {{"custom_meal": "meal name"}}
    }}
  ]
}}

Use 7 entries (Monday through Sunday). Vary the meals, keep them practical."""

    try:
        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"mealplan_{uuid.uuid4().hex[:8]}",
            system_message="You are a meal planning assistant. Return only valid JSON.",
        ).with_model("openai", "gpt-4o-mini")

        response_text = await chat.send_message(UserMessage(text=prompt))
        clean = re.sub(r"```json|```", "", response_text).strip()
        parsed = json.loads(clean)
        days = parsed.get("days", [])

        # Link to saved recipes where names match
        saved_map = {r["title"].lower(): r for r in saved}
        for day in days:
            for slot in ["breakfast", "lunch", "dinner"]:
                meal = day.get(slot)
                if meal and meal.get("custom_meal"):
                    match = saved_map.get(meal["custom_meal"].lower())
                    if match:
                        meal["recipe_id"] = match["recipe_id"]
                        meal["recipe_title"] = match["title"]

        # Save to DB
        now = datetime.now(timezone.utc)
        await db.meal_plans.find_one_and_update(
            {"user_id": user["user_id"], "week_start": key},
            {
                "$set": {"days": days, "updated_at": now},
                "$setOnInsert": {
                    "meal_plan_id": f"mp_{uuid.uuid4().hex[:12]}",
                    "user_id": user["user_id"],
                    "week_start": key,
                    "created_at": now,
                },
            },
            upsert=True,
        )

        return {"week_start": key, "days": days}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")
