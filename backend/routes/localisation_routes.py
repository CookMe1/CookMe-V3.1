"""
localisation_routes.py
======================
API endpoints that expose localisation data to the frontend.

GET  /api/localisation/profile          — full profile for current user
GET  /api/localisation/seasonal         — in-season produce this month
GET  /api/localisation/seasonal/{month} — in-season produce for a specific month
POST /api/localisation/check-seasonal   — check if specific ingredients are in season
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from auth import get_current_user
from localisation import (
    get_localisation_profile,
    get_seasonal_produce,
    is_in_season,
    get_seasonal_tip,
    normalise_ingredient,
)

router = APIRouter(prefix="/localisation", tags=["localisation"])


class SeasonalCheckRequest(BaseModel):
    ingredients: list[str]
    month: Optional[int] = None


@router.get("/profile")
async def get_profile(request: Request):
    """Full localisation profile for the current user's language."""
    db = request.app.state.db
    user = await get_current_user(request, db)

    lang = user.get("preferred_language", "en")
    profile = get_localisation_profile(lang)
    return profile


@router.get("/seasonal")
async def get_seasonal(request: Request, hemisphere: Optional[str] = None):
    """In-season produce for the current month."""
    db = request.app.state.db
    user = await get_current_user(request, db)

    lang = user.get("preferred_language", "en")
    month = datetime.now().month
    produce = get_seasonal_produce(lang, month, hemisphere)
    return {
        "month": month,
        "month_name": datetime(2000, month, 1).strftime("%B"),
        "hemisphere": hemisphere or ("south" if lang in {"pt"} else "north"),
        "in_season": produce,
        "count": len(produce),
    }


@router.get("/seasonal/{month}")
async def get_seasonal_month(month: int, request: Request, hemisphere: Optional[str] = None):
    """In-season produce for a specific month (1-12)."""
    db = request.app.state.db
    user = await get_current_user(request, db)

    if not 1 <= month <= 12:
        raise HTTPException(status_code=400, detail="Month must be 1-12")

    lang = user.get("preferred_language", "en")
    produce = get_seasonal_produce(lang, month, hemisphere)
    return {
        "month": month,
        "month_name": datetime(2000, month, 1).strftime("%B"),
        "in_season": produce,
    }


@router.post("/check-seasonal")
async def check_seasonal(body: SeasonalCheckRequest, request: Request):
    """
    Check which ingredients in a list are in or out of season.
    Returns per-ingredient status and tips for out-of-season items.
    """
    db = request.app.state.db
    user = await get_current_user(request, db)

    lang = user.get("preferred_language", "en")
    month = body.month or datetime.now().month

    results = []
    for ingredient in body.ingredients:
        in_season = is_in_season(ingredient, lang, month)
        tip = get_seasonal_tip(ingredient, lang, month)
        results.append({
            "ingredient": ingredient,
            "in_season": in_season,
            "tip": tip,
        })

    return {
        "month": month,
        "results": results,
        "out_of_season_count": sum(1 for r in results if not r["in_season"]),
    }


@router.get("/normalise-ingredient")
async def normalise_ingredient_endpoint(name: str, request: Request):
    """Normalise a regional ingredient name to its canonical English equivalent."""
    db = request.app.state.db
    await get_current_user(request, db)

    canonical = normalise_ingredient(name)
    return {
        "input": name,
        "canonical": canonical,
        "changed": canonical.lower() != name.lower().strip(),
    }
