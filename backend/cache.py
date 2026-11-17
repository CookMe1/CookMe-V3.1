"""
cache.py — MongoDB-backed AI result cache
==========================================
Stores AI responses so identical requests are never repeated.

Collections used:
  - ai_cache          : general key/value cache with TTL
  - ingredient_aisles : permanent ingredient → aisle lookup table

Usage:
    from cache import get_cache, set_cache, get_aisle, set_aisle

All functions accept the db object from app.state.db.
"""

import re
import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from urllib.parse import urlparse, parse_qs, urlencode


# ── TTL constants (in days) ───────────────────────────────────────────────────
TTL_NUTRITION   = 3650  # 10 years — calorie counts never change
TTL_URL_IMPORT  = 30    # recipe content is stable; bump from 7 to 30 days
TTL_YOUTUBE     = 30    # YouTube metadata
TTL_UNIT_CONV   = 3650  # unit conversions never change
TTL_MEAL_PLAN   = 1     # AI meal plans — regenerate daily


# ── URL normalisation (optimisation #4) ──────────────────────────────────────

# UTM and tracking params to strip before caching
_STRIP_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'utm_id', 'fbclid', 'gclid', 'ref', 'source', 'src', 'mc_cid', 'mc_eid',
    '_ga', 'igshid', 'epik', 'pp', 'feature', 'si', 'via',
}

def normalise_url(url: str) -> str:
    """
    Normalise a recipe URL for consistent cache key generation.
    Strips tracking params, www prefix, trailing slashes, fragments.
    Example:
      https://www.allrecipes.com/recipe/123/?utm_source=email&fbclid=xyz
      → allrecipes.com/recipe/123
    """
    try:
        parsed = urlparse(url.strip())
        # Strip www prefix
        host = parsed.netloc.lower()
        if host.startswith('www.'):
            host = host[4:]
        # Strip tracking query params
        qs = parse_qs(parsed.query, keep_blank_values=False)
        clean_qs = {k: v for k, v in qs.items() if k.lower() not in _STRIP_PARAMS}
        clean_query = urlencode(clean_qs, doseq=True)
        # Strip trailing slash from path, lowercase path
        path = parsed.path.rstrip('/')
        clean = f"{host}{path}"
        if clean_query:
            clean += f"?{clean_query}"
        return clean.lower()
    except Exception:
        return url.strip().rstrip('/').lower()


# ── Key builders ──────────────────────────────────────────────────────────────

def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:24]


def nutrition_key(ingredients: list, servings: int) -> str:
    canonical = json.dumps(ingredients, sort_keys=True) + f"|{servings}"
    return f"nutrition:{_hash(canonical)}"


def url_import_key(url: str) -> str:
    """Cache key using normalised URL — strips tracking params, www, trailing slashes."""
    return f"url_import:{_hash(normalise_url(url))}"


def youtube_key(video_id: str) -> str:
    return f"youtube:{video_id}"


def recipe_fingerprint(title: str, domain: str) -> str:
    """
    Fingerprint for deduplication check (optimisation #5).
    Normalises title to detect near-duplicates before importing.
    """
    clean_title = re.sub(r'[^a-z0-9 ]', '', title.lower())
    clean_title = re.sub(r'\s+', ' ', clean_title).strip()
    return _hash(f"{domain}:{clean_title}")


# ── Generic cache get/set ─────────────────────────────────────────────────────

async def get_cache(db, key: str) -> Optional[Any]:
    doc = await db.ai_cache.find_one({"key": key})
    if not doc:
        return None
    if doc.get("expires_at") and doc["expires_at"] < datetime.now(timezone.utc):
        await db.ai_cache.delete_one({"key": key})
        return None
    return doc.get("value")


async def set_cache(db, key: str, value: Any, ttl_days: int = 30) -> None:
    expires = datetime.now(timezone.utc) + timedelta(days=ttl_days)
    await db.ai_cache.update_one(
        {"key": key},
        {"$set": {
            "key": key,
            "value": value,
            "expires_at": expires,
            "cached_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )


# ── Ingredient aisle lookup (permanent, no TTL) ───────────────────────────────

AISLE_LOOKUP = {
    # Produce
    "tomato": "Produce", "tomatoes": "Produce", "onion": "Produce", "onions": "Produce",
    "garlic": "Produce", "potato": "Produce", "potatoes": "Produce", "carrot": "Produce",
    "carrots": "Produce", "celery": "Produce", "bell pepper": "Produce", "lettuce": "Produce",
    "spinach": "Produce", "broccoli": "Produce", "mushroom": "Produce", "mushrooms": "Produce",
    "cucumber": "Produce", "zucchini": "Produce", "courgette": "Produce", "eggplant": "Produce",
    "aubergine": "Produce", "cabbage": "Produce", "cauliflower": "Produce", "kale": "Produce",
    "leek": "Produce", "leeks": "Produce", "avocado": "Produce", "lemon": "Produce",
    "lemons": "Produce", "lime": "Produce", "limes": "Produce", "orange": "Produce",
    "apple": "Produce", "banana": "Produce", "berries": "Produce", "strawberries": "Produce",
    "blueberries": "Produce", "mango": "Produce", "ginger": "Produce", "basil": "Produce",
    "cilantro": "Produce", "coriander": "Produce", "parsley": "Produce", "mint": "Produce",
    "rosemary": "Produce", "thyme": "Produce", "green onion": "Produce", "scallion": "Produce",
    "shallot": "Produce", "shallots": "Produce", "chives": "Produce", "sweet potato": "Produce",
    "pumpkin": "Produce", "squash": "Produce", "asparagus": "Produce", "peas": "Produce",
    "corn": "Produce", "green beans": "Produce", "beets": "Produce", "beetroot": "Produce",
    # Dairy & Eggs
    "milk": "Dairy", "butter": "Dairy", "egg": "Dairy", "eggs": "Dairy", "cheese": "Dairy",
    "cheddar": "Dairy", "parmesan": "Dairy", "mozzarella": "Dairy", "feta": "Dairy",
    "cream cheese": "Dairy", "cream": "Dairy", "heavy cream": "Dairy", "sour cream": "Dairy",
    "yogurt": "Dairy", "greek yogurt": "Dairy", "ricotta": "Dairy", "cottage cheese": "Dairy",
    "whipping cream": "Dairy", "half and half": "Dairy", "crème fraîche": "Dairy",
    # Meat
    "chicken": "Meat", "chicken breast": "Meat", "chicken thigh": "Meat", "ground beef": "Meat",
    "beef": "Meat", "steak": "Meat", "pork": "Meat", "bacon": "Meat", "ham": "Meat",
    "sausage": "Meat", "turkey": "Meat", "lamb": "Meat", "duck": "Meat", "prosciutto": "Meat",
    "pancetta": "Meat", "salami": "Meat", "chorizo": "Meat", "mince": "Meat",
    # Seafood
    "salmon": "Seafood", "shrimp": "Seafood", "prawns": "Seafood", "tuna": "Seafood",
    "cod": "Seafood", "tilapia": "Seafood", "mussels": "Seafood", "clams": "Seafood",
    "scallops": "Seafood", "crab": "Seafood", "lobster": "Seafood", "calamari": "Seafood",
    "squid": "Seafood", "anchovies": "Seafood", "sardines": "Seafood", "fish": "Seafood",
    # Grains / Pasta
    "rice": "Grains", "pasta": "Grains", "spaghetti": "Grains", "penne": "Grains",
    "noodles": "Grains", "bread": "Bakery", "sourdough": "Bakery", "tortilla": "Grains",
    "pita": "Bakery", "quinoa": "Grains", "couscous": "Grains", "oats": "Grains",
    "barley": "Grains", "breadcrumbs": "Grains", "panko": "Grains",
    # Canned & Jarred
    "tomato sauce": "Canned", "diced tomatoes": "Canned", "canned tomatoes": "Canned",
    "tomato paste": "Canned", "chickpeas": "Canned", "black beans": "Canned",
    "kidney beans": "Canned", "lentils": "Canned", "coconut milk": "Canned",
    "broth": "Canned", "stock": "Canned", "chicken broth": "Canned", "beef broth": "Canned",
    # Spices
    "salt": "Spices", "pepper": "Spices", "black pepper": "Spices", "cumin": "Spices",
    "paprika": "Spices", "turmeric": "Spices", "cinnamon": "Spices", "oregano": "Spices",
    "chili flakes": "Spices", "red pepper flakes": "Spices", "cayenne": "Spices",
    "bay leaf": "Spices", "bay leaves": "Spices", "nutmeg": "Spices", "cardamom": "Spices",
    "coriander powder": "Spices", "garam masala": "Spices", "curry powder": "Spices",
    "garlic powder": "Spices", "onion powder": "Spices", "chili powder": "Spices",
    # Oils & Condiments
    "olive oil": "Oils", "vegetable oil": "Oils", "coconut oil": "Oils", "sesame oil": "Oils",
    "soy sauce": "Condiments", "fish sauce": "Condiments", "worcestershire": "Condiments",
    "hot sauce": "Condiments", "ketchup": "Condiments", "mustard": "Condiments",
    "mayonnaise": "Condiments", "vinegar": "Condiments", "balsamic": "Condiments",
    "honey": "Condiments", "maple syrup": "Condiments", "sriracha": "Condiments",
    "tahini": "Condiments", "hoisin sauce": "Condiments", "oyster sauce": "Condiments",
    # Baking
    "flour": "Baking", "sugar": "Baking", "brown sugar": "Baking", "baking powder": "Baking",
    "baking soda": "Baking", "yeast": "Baking", "vanilla": "Baking", "cocoa powder": "Baking",
    "chocolate": "Baking", "cornstarch": "Baking", "powdered sugar": "Baking",
    "almond flour": "Baking", "vegetable shortening": "Baking",
    # Frozen
    "frozen peas": "Frozen", "frozen corn": "Frozen", "frozen spinach": "Frozen",
    "ice cream": "Frozen", "frozen berries": "Frozen",
    # Beverages
    "water": "Beverages", "wine": "Beverages", "beer": "Beverages",
    "chicken stock": "Beverages", "vegetable stock": "Beverages",
}


def lookup_aisle(ingredient_name: str) -> Optional[str]:
    key = ingredient_name.lower().strip()
    if key in AISLE_LOOKUP:
        return AISLE_LOOKUP[key]
    for known, aisle in AISLE_LOOKUP.items():
        if known in key:
            return aisle
    return None


async def get_aisle(db, ingredient_name: str) -> Optional[str]:
    aisle = lookup_aisle(ingredient_name)
    if aisle:
        return aisle
    key = f"aisle:{_hash(ingredient_name.lower().strip())}"
    cached = await db.ai_cache.find_one({"key": key})
    if cached:
        return cached.get("value")
    return None


async def set_aisle(db, ingredient_name: str, aisle: str) -> None:
    key = f"aisle:{_hash(ingredient_name.lower().strip())}"
    await db.ai_cache.update_one(
        {"key": key},
        {"$set": {
            "key": key,
            "value": aisle,
            "ingredient": ingredient_name.lower().strip(),
            "cached_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )


async def create_cache_indexes(db) -> None:
    await db.ai_cache.create_index("key", unique=True)
    await db.ai_cache.create_index("expires_at", expireAfterSeconds=0)
    await db.ai_cache.create_index("ingredient")
    # Deduplication index
    await db.recipes.create_index("import_fingerprint", sparse=True)


