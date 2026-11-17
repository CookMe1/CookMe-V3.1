"""
nutrition_lookup.py
===================
Free nutrition data before touching AI.

Priority chain per ingredient:
  1. Open Food Facts API  — free, no key, great UK/EU coverage, branded products
  2. Edamam Food API      — free tier 500 calls/day, natural language, generic foods
  3. AI fallback          — only when both above fail

Recipe-level nutrition = sum of all ingredients ÷ servings.

Setup:
  EDAMAM_APP_ID  = your Edamam app ID  (free at developer.edamam.com)
  EDAMAM_APP_KEY = your Edamam app key

  Both are optional — if absent, falls through to AI.
  Open Food Facts requires no key at all.
"""

import os
import re
import hashlib
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

EDAMAM_APP_ID  = os.environ.get("EDAMAM_APP_ID", "")
EDAMAM_APP_KEY = os.environ.get("EDAMAM_APP_KEY", "")

# ── Nutrient per-100g cache (in-memory, lives for process lifetime) ───────────
_ingredient_cache: dict = {}


def _cache_key(ingredient: str) -> str:
    return hashlib.sha256(ingredient.lower().strip().encode()).hexdigest()[:16]


# ── Open Food Facts ───────────────────────────────────────────────────────────

async def lookup_open_food_facts(ingredient_name: str) -> Optional[dict]:
    """
    Search Open Food Facts for an ingredient.
    Returns per-100g nutriments dict or None.
    No API key needed — completely free.
    """
    try:
        # Clean ingredient name — strip amounts
        clean = re.sub(
            r'^[\d\s./½¼¾⅓⅔⅛]+\s*(?:g|kg|ml|l|oz|lb|cup|tbsp|tsp|piece|clove|bunch|can|slice|pinch)s?\s*',
            '', ingredient_name, flags=re.IGNORECASE
        ).strip()

        if len(clean) < 2:
            return None

        params = {
            "search_terms": clean,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 1,
            "fields": "nutriments,product_name,serving_size",
            "countries_tags_en": "united-kingdom",  # UK products first
        }

        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                "https://world.openfoodfacts.org/cgi/search.pl",
                params=params,
                headers={"User-Agent": "CookMe/1.0 (recipe app)"}
            )

        if resp.status_code != 200:
            return None

        data = resp.json()
        products = data.get("products", [])
        if not products:
            return None

        nutriments = products[0].get("nutriments", {})
        if not nutriments.get("energy-kcal_100g"):
            return None

        def _n(key):
            v = nutriments.get(f"{key}_100g")
            try:
                return round(float(v), 1) if v is not None else None
            except Exception:
                return None

        return {
            "calories_per_100g": _n("energy-kcal"),
            "protein_per_100g":  _n("proteins"),
            "carbs_per_100g":    _n("carbohydrates"),
            "fat_per_100g":      _n("fat"),
            "fiber_per_100g":    _n("fiber"),
            "sugar_per_100g":    _n("sugars"),
            "sodium_per_100g":   _n("sodium"),
            "source": "openfoodfacts",
        }

    except Exception as e:
        logger.debug(f"Open Food Facts lookup failed for '{ingredient_name}': {e}")
        return None


# ── Edamam ────────────────────────────────────────────────────────────────────

async def lookup_edamam(ingredient_text: str) -> Optional[dict]:
    """
    Parse ingredient text with Edamam's Food Database API.
    Accepts natural language like "200g chicken breast" or "1 cup flour".
    Returns estimated nutrition for that specific quantity or None.
    Free tier: 500 calls/day.
    """
    if not EDAMAM_APP_ID or not EDAMAM_APP_KEY:
        return None

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.edamam.com/api/food-database/v2/parser",
                params={
                    "app_id":     EDAMAM_APP_ID,
                    "app_key":    EDAMAM_APP_KEY,
                    "ingr":       ingredient_text,
                    "nutrition-type": "cooking",
                }
            )

        if resp.status_code != 200:
            return None

        data = resp.json()
        hints = data.get("hints", [])
        if not hints:
            # Try parsed section
            parsed = data.get("parsed", [])
            if not parsed:
                return None
            food = parsed[0].get("food", {})
        else:
            food = hints[0].get("food", {})

        nutrients = food.get("nutrients", {})
        if not nutrients.get("ENERC_KCAL"):
            return None

        def _n(key):
            v = nutrients.get(key)
            try:
                return round(float(v), 1) if v is not None else None
            except Exception:
                return None

        return {
            "calories_per_100g": _n("ENERC_KCAL"),
            "protein_per_100g":  _n("PROCNT"),
            "carbs_per_100g":    _n("CHOCDF"),
            "fat_per_100g":      _n("FAT"),
            "fiber_per_100g":    _n("FIBTG"),
            "sugar_per_100g":    _n("SUGAR"),
            "sodium_per_100g":   _n("NA"),
            "source": "edamam",
        }

    except Exception as e:
        logger.debug(f"Edamam lookup failed for '{ingredient_text}': {e}")
        return None


# ── Amount parser ─────────────────────────────────────────────────────────────

# Rough gram conversions for common volume/count measures
VOLUME_TO_GRAMS = {
    "cup": 240, "cups": 240,
    "tbsp": 15, "tablespoon": 15, "tablespoons": 15,
    "tsp": 5, "teaspoon": 5, "teaspoons": 5,
    "ml": 1, "l": 1000,
    "fl oz": 30,
    "oz": 28, "lb": 454,
    "piece": 100, "pieces": 100,
    "clove": 5, "cloves": 5,
    "slice": 30, "slices": 30,
    "can": 400, "handful": 40,
    "bunch": 80,
}

UNICODE_FRACTIONS = {
    "½": 0.5, "¼": 0.25, "¾": 0.75,
    "⅓": 0.333, "⅔": 0.667, "⅛": 0.125,
}

def parse_amount_to_grams(amount_str: str) -> float:
    """
    Convert an ingredient amount string to approximate grams.
    Examples: "200g" → 200, "1 cup" → 240, "2 tbsp" → 30, "½" → ~50
    Returns 100 (default serving) if parsing fails.
    """
    if not amount_str:
        return 100.0

    text = amount_str.strip().lower()

    # Replace unicode fractions
    for frac, val in UNICODE_FRACTIONS.items():
        text = text.replace(frac, str(val))

    # Extract numeric value
    num_match = re.search(r'([\d.]+(?:\s*/\s*[\d.]+)?)', text)
    if not num_match:
        return 100.0

    num_str = num_match.group(1)
    try:
        if '/' in num_str:
            parts = num_str.split('/')
            quantity = float(parts[0].strip()) / float(parts[1].strip())
        else:
            quantity = float(num_str)
    except Exception:
        quantity = 1.0

    # Direct grams/kg
    if re.search(r'\d\s*g\b', text):
        return quantity
    if re.search(r'\d\s*kg\b', text):
        return quantity * 1000

    # Volume/count conversions
    for unit, grams in VOLUME_TO_GRAMS.items():
        if unit in text:
            return quantity * grams

    # Fallback: assume grams if numeric only
    return quantity if quantity >= 1 else 100.0


# ── Recipe-level nutrition calculation ───────────────────────────────────────

async def calculate_recipe_nutrition_free(
    ingredients: list,
    servings: int = 4,
) -> Optional[dict]:
    """
    Calculate recipe nutrition using free APIs.
    ingredients: list of {"item": "flour", "amount": "2 cups"} dicts
    Returns per-serving nutrition dict, or None if insufficient data.

    Falls back gracefully — if <50% of ingredients are found, returns None
    so the caller can use AI instead.
    """
    if not ingredients:
        return None

    totals = {
        "calories": 0.0,
        "protein":  0.0,
        "carbs":    0.0,
        "fat":      0.0,
        "fiber":    0.0,
        "sugar":    0.0,
        "sodium":   0.0,
    }
    found = 0

    for ing in ingredients:
        if isinstance(ing, str):
            item_name = ing
            amount_str = ""
        elif isinstance(ing, dict):
            item_name   = ing.get("item", "")
            amount_str  = ing.get("amount", "")
        else:
            continue

        if not item_name:
            continue

        # Check in-process cache
        ck = _cache_key(item_name)
        nutriments = _ingredient_cache.get(ck)

        if nutriments is None:
            # Try Open Food Facts first
            nutriments = await lookup_open_food_facts(item_name)
            # Try Edamam if OFF failed
            if nutriments is None:
                ingredient_text = f"{amount_str} {item_name}".strip()
                nutriments = await lookup_edamam(ingredient_text)

            if nutriments:
                _ingredient_cache[ck] = nutriments
            else:
                _ingredient_cache[ck] = {}  # mark as not found

        if not nutriments:
            continue

        grams = parse_amount_to_grams(amount_str)
        ratio = grams / 100.0

        totals["calories"] += (nutriments.get("calories_per_100g") or 0) * ratio
        totals["protein"]  += (nutriments.get("protein_per_100g")  or 0) * ratio
        totals["carbs"]    += (nutriments.get("carbs_per_100g")    or 0) * ratio
        totals["fat"]      += (nutriments.get("fat_per_100g")      or 0) * ratio
        totals["fiber"]    += (nutriments.get("fiber_per_100g")    or 0) * ratio
        totals["sugar"]    += (nutriments.get("sugar_per_100g")    or 0) * ratio
        totals["sodium"]   += (nutriments.get("sodium_per_100g")   or 0) * ratio
        found += 1

    # Only return if we found data for at least half the ingredients
    if found < len(ingredients) * 0.5:
        logger.info(f"Nutrition: only {found}/{len(ingredients)} ingredients found, falling back to AI")
        return None

    servings = max(1, servings)
    return {
        "calories": round(totals["calories"] / servings),
        "protein":  round(totals["protein"]  / servings, 1),
        "carbs":    round(totals["carbs"]    / servings, 1),
        "fat":      round(totals["fat"]      / servings, 1),
        "fiber":    round(totals["fiber"]    / servings, 1),
        "sugar":    round(totals["sugar"]    / servings, 1),
        "sodium":   round(totals["sodium"]   / servings),
        "source":   "api",
    }
