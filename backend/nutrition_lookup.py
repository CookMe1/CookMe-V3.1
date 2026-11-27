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

# ── Local USDA table (public domain, built by scripts/build_usda_table.py) ─────
import json as _json
from pathlib import Path as _Path

_USDA_FILE = _Path(__file__).resolve().parent.parent / "data" / "nutrition_usda.json"
_USDA = None          # list of foods, or [] when the file is missing
_USDA_TOKENS = None
_USDA_NOISE = {"raw", "fresh", "cooked", "chopped", "sliced", "diced", "minced", "large", "small", "medium", "whole", "ground",
               "dried", "finely", "a", "of", "the", "and", "or", "to", "taste", "for", "pinch", "optional", "boneless", "skinless"}


def _stem(w: str) -> str:
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("es") and w[-3] in "sxz":
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def _toks(text: str) -> list:
    return [_stem(w) for w in re.findall(r"[a-z]+", text.lower()) if w not in _USDA_NOISE]


# Common staples whose everyday names differ from USDA's wording. Used only when the USDA entry exists in the table.
_USDA_OVERRIDES = {
    "flour": "Wheat flour, white, all-purpose", "plain flour": "Wheat flour, white, all-purpose",
    "all purpose flour": "Wheat flour, white, all-purpose", "self raising flour": "Wheat flour, white, self-rising",
    "bread flour": "Wheat flour, white, bread", "wholemeal flour": "Wheat flour, whole-grain",
    "sugar": "Sugars, granulated", "caster sugar": "Sugars, granulated", "white sugar": "Sugars, granulated",
    "brown sugar": "Sugars, brown", "icing sugar": "Sugars, powdered", "powdered sugar": "Sugars, powdered",
    "butter": "Butter, salted", "unsalted butter": "Butter, without salt", "milk": "Milk, whole",
    "whole milk": "Milk, whole", "skimmed milk": "Milk, nonfat", "double cream": "Cream, fluid, heavy whipping",
    "heavy cream": "Cream, fluid, heavy whipping", "single cream": "Cream, fluid, light", "egg": "Egg, whole, raw, fresh",
    "eggs": "Egg, whole, raw, fresh", "water": "Water, bottled", "salt": "Salt, table", "honey": "Honey",
    "olive oil": "Oil, olive", "vegetable oil": "Oil, vegetable", "sunflower oil": "Oil, sunflower",
    "rice": "Rice, white, long-grain, regular, raw", "pasta": "Pasta, dry, enriched", "spaghetti": "Pasta, dry, enriched",
    "potato": "Potatoes, flesh and skin, raw", "potatoes": "Potatoes, flesh and skin, raw", "onion": "Onions, raw",
    "onions": "Onions, raw", "garlic": "Garlic, raw", "tomato": "Tomatoes, red, ripe, raw", "tomatoes": "Tomatoes, red, ripe, raw",
    "cheddar": "Cheese, cheddar", "cheddar cheese": "Cheese, cheddar", "parmesan": "Cheese, parmesan, hard",
    "chicken breast": "Chicken, broilers or fryers, breast, meat only, raw", "chicken": "Chicken, broilers or fryers, meat only, raw",
}


def _load_usda():
    global _USDA, _USDA_TOKENS
    if _USDA is not None:
        return
    try:
        _USDA = _json.load(open(_USDA_FILE, encoding="utf-8"))
    except Exception:
        _USDA = []
    _USDA_TOKENS = [(set(_toks(f["n"])), _toks(f["n"]), f) for f in _USDA]


def lookup_usda_local(ingredient_name: str) -> Optional[dict]:
    """Best USDA match for an ingredient name, as per-100g values. None if no table or no confident match."""
    _load_usda()
    if not _USDA:
        return None
    q = _toks(re.sub(r"\(.*?\)", " ", ingredient_name))
    if not q:
        return None
    qset = set(q)
    wanted = _USDA_OVERRIDES.get(" ".join(re.findall(r"[a-z]+", ingredient_name.lower())).replace("-", " "))
    if wanted:
        for f in _USDA:
            if f["n"].lower().startswith(wanted.lower()):
                return _usda_result(f)
    best, best_score = None, None
    for tset, tlist, f in _USDA_TOKENS:
        if not qset <= tset:
            continue
        # prefer: description starts with the query's last word (the food itself), plain/raw entries, short names
        head = 0 if tlist and (tlist[0] == q[-1] or tlist[0] == q[0]) else 1
        raw = 0 if "raw" in f["n"].lower() else 1
        score = (head, raw, len(tlist))
        if best_score is None or score < best_score:
            best, best_score = f, score
    if not best and len(q) > 1:
        # Fallback: the food itself (last word) as the start of the USDA name, e.g. "unsalted butter" -> "Butter, ..."
        for tset, tlist, f in _USDA_TOKENS:
            if tlist and tlist[0] == q[-1]:
                score = (0 if "raw" in f["n"].lower() else 1, len(tlist))
                if best_score is None or score < best_score:
                    best, best_score = f, score
    if not best:
        return None
    return _usda_result(best)


def _usda_result(best: dict) -> dict:
    return {
        "calories_per_100g": best["calories"], "protein_per_100g": best["protein"], "carbs_per_100g": best["carbs"],
        "fat_per_100g": best["fat"], "fiber_per_100g": best["fiber"], "sugar_per_100g": best["sugar"],
        "sodium_per_100g": best["sodium"], "matched_food": best["n"],
    }


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
            "sodium_per_100g":   (_n("sodium") or 0) * 1000 if _n("sodium") is not None else None,  # OFF is grams -> mg
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

from amounts import parse_amount_to_grams, adjust_cups, split_ingredient, fry_factor  # noqa: E402  (whole-word units, per-item weights), adjust_cups


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
        if not str(amount_str or "").strip():            # "2 tbsp olive oil" written as one line
            _a, _n = split_ingredient(item_name)
            if _a and _n:
                amount_str, item_name = _a, _n

        # Non-English names (e.g. "pollo", "Zwiebel") -> English via our own dictionary before looking them up
        try:
            from ingredient_dictionary import to_english
            item_name = to_english(item_name) or item_name
        except Exception:
            pass

        # Check in-process cache
        ck = _cache_key(item_name)
        nutriments = _ingredient_cache.get(ck)

        if nutriments is None:
            # 1) Local USDA table (free, instant, offline)
            nutriments = lookup_usda_local(item_name)
            # 2) Open Food Facts
            if nutriments is None:
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

        grams = parse_amount_to_grams(amount_str, item_name)
        grams, factor = adjust_cups(amount_str, item_name, grams, servings)
        factor *= fry_factor(item_name, grams, servings)
        ratio = grams / 100.0 * factor

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
        "source":   "usda" if _USDA else "api",
        "calc_v":   4,
    }
