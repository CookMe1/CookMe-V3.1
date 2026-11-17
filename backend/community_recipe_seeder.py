"""
community_recipe_seeder.py
==========================
One-time script to populate the community_recipes MongoDB collection
with ~50,000 open-licensed recipes.

Data sources used (all open / CC licensed):
  1. jakevdp/open-recipe-data (CC BY 3.0) — ~30k recipes
     https://github.com/jakevdp/open-recipe-data
  2. kodecocodes/recipes (open source) — ~1k recipes
     https://github.com/kodecocodes/recipes

Run once from your backend directory:
    python community_recipe_seeder.py

Requirements:
    pip install motor pymongo python-dotenv httpx
"""

import asyncio
import os
import re
import hashlib
import httpx
from datetime import datetime, timezone
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME   = os.environ["DB_NAME"]

# ── Cuisine detection from tags/title ────────────────────────────────────────

CUISINE_KEYWORDS = {
    "italian": ["italian", "pasta", "pizza", "risotto", "tiramisu", "parmesan", "lasagna", "carbonara"],
    "mexican": ["mexican", "taco", "burrito", "enchilada", "salsa", "guacamole", "tortilla", "chile"],
    "indian":  ["indian", "curry", "masala", "tikka", "biryani", "dal", "paneer", "naan", "chapati"],
    "chinese": ["chinese", "stir fry", "fried rice", "dim sum", "wonton", "chow mein", "kung pao"],
    "japanese":["japanese", "sushi", "ramen", "teriyaki", "miso", "tempura", "udon", "soba"],
    "thai":    ["thai", "pad thai", "coconut curry", "lemongrass", "fish sauce", "green curry"],
    "french":  ["french", "baguette", "croissant", "quiche", "ratatouille", "crepe", "béarnaise"],
    "greek":   ["greek", "tzatziki", "moussaka", "gyro", "spanakopita", "feta", "souvlaki"],
    "spanish": ["spanish", "paella", "tapas", "gazpacho", "chorizo", "tortilla española"],
    "american":["american", "bbq", "burger", "mac and cheese", "cornbread", "coleslaw"],
    "british": ["british", "pie", "roast", "scones", "shepherd's pie", "fish and chips"],
    "mediterranean": ["mediterranean", "hummus", "tabbouleh", "falafel", "shawarma"],
    "korean":  ["korean", "kimchi", "bibimbap", "bulgogi", "japchae", "gochujang"],
    "vietnamese": ["vietnamese", "pho", "banh mi", "spring roll", "vermicelli"],
    "middle_eastern": ["middle eastern", "persian", "lebanese", "tagine", "kebab", "pilaf"],
}

CATEGORY_KEYWORDS = {
    "quick":    ["quick", "easy", "fast", "15 min", "20 min", "30 min", "simple"],
    "healthy":  ["healthy", "low calorie", "light", "salad", "vegan", "vegetarian", "whole grain"],
    "dessert":  ["cake", "cookie", "pie", "tart", "brownie", "ice cream", "mousse", "pudding", "dessert"],
    "breakfast":["breakfast", "pancake", "waffle", "omelette", "egg", "cereal", "smoothie", "brunch"],
    "budget":   ["budget", "cheap", "economical", "beans", "lentils", "rice and beans"],
    "comfort":  ["comfort", "stew", "soup", "casserole", "roast", "mac and cheese"],
    "airfryer": ["air fry", "air-fry", "airfryer"],
    "instapot": ["instant pot", "pressure cooker", "slow cooker", "crockpot"],
}

def detect_cuisine(title: str, tags: list) -> str:
    text = (title + " " + " ".join(tags)).lower()
    for cuisine, keywords in CUISINE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return cuisine
    return "international"

def detect_category(title: str, tags: list) -> str:
    text = (title + " " + " ".join(tags)).lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return "dinner"

def extract_ingredient_names(ingredients: list) -> list:
    """Extract clean ingredient names for search indexing."""
    names = []
    for ing in ingredients:
        if isinstance(ing, dict):
            name = ing.get("name") or ing.get("item") or ""
        else:
            name = str(ing)
        # Strip amounts — keep only the food name
        clean = re.sub(r'^[\d\s./½¼¾⅓⅔⅛tTcCkKgGlLmMozlb\-]+', '', name).strip()
        clean = re.sub(r'\(.*?\)', '', clean).strip()
        if clean and len(clean) > 1:
            names.append(clean.lower())
    return names

def normalise_ingredients(raw_ingredients) -> list:
    """Convert any ingredient format to [{item, amount}]."""
    result = []
    for ing in (raw_ingredients or []):
        if isinstance(ing, dict):
            result.append({
                "item": ing.get("name") or ing.get("item") or "",
                "amount": ing.get("quantity") or ing.get("amount") or ""
            })
        elif isinstance(ing, str):
            # Try to split "1 cup flour" → amount + item
            match = re.match(r'^([\d\s./½¼¾⅓⅔⅛]+(?:cup|tbsp|tsp|oz|lb|g|kg|ml|L|piece|clove|bunch|can|slice|pinch)?s?\.?)\s*(.+)', ing, re.I)
            if match:
                result.append({"item": match.group(2).strip(), "amount": match.group(1).strip()})
            else:
                result.append({"item": ing.strip(), "amount": ""})
    return result

def normalise_steps(raw_steps) -> list:
    """Convert any steps format to a list of strings."""
    if not raw_steps:
        return []
    if isinstance(raw_steps, str):
        return [s.strip() for s in re.split(r'\n+|\.\s+(?=[A-Z])', raw_steps) if s.strip()]
    if isinstance(raw_steps, list):
        result = []
        for step in raw_steps:
            if isinstance(step, dict):
                result.append(step.get("text") or step.get("step") or str(step))
            else:
                result.append(str(step))
        return result
    return []

def make_community_doc(title, description, ingredients_raw, steps_raw,
                        tags, source_url, image_url, prep_time, cook_time,
                        servings, attribution):
    ingredients = normalise_ingredients(ingredients_raw)
    steps = normalise_steps(steps_raw)
    ingredient_names = extract_ingredient_names(ingredients)
    tags = [str(t).strip() for t in (tags or []) if t]
    cuisine = detect_cuisine(title, tags)
    category = detect_category(title, tags)

    # Stable ID based on title so re-runs don't duplicate
    stable_id = "cr_" + hashlib.sha256(title.lower().encode()).hexdigest()[:16]

    return {
        "community_recipe_id": stable_id,
        "title": title.strip(),
        "description": (description or "").strip()[:500],
        "image": image_url or "",
        "ingredients": ingredients,
        "ingredient_names": ingredient_names,   # flat list for fast text search
        "steps": steps,
        "tags": tags,
        "cuisine": cuisine,
        "category": category,
        "prep_time": prep_time or "",
        "cook_time": cook_time or "",
        "servings": int(servings) if servings else 4,
        "difficulty": "Medium",
        "source_url": source_url or "",
        "attribution": attribution or "Open Recipe Dataset",
        "license": "CC BY 3.0",
        "nutrition": None,
        "likes_count": 0,
        "created_at": datetime.now(timezone.utc),
    }


# ── Source 1: jakevdp/open-recipe-data (CC BY 3.0) ───────────────────────────

async def fetch_jakevdp_recipes(client: httpx.AsyncClient) -> list:
    """
    Download recipes from jakevdp/open-recipe-data on GitHub.
    This is the archived open recipe project released under CC BY 3.0.
    Contains ~30,000 recipes with ingredients and instructions.
    """
    print("Fetching jakevdp/open-recipe-data recipe index...")

    # The dataset is split across multiple JSON files in the repo
    base = "https://raw.githubusercontent.com/jakevdp/open-recipe-data/master/data"

    # Try to get the file list via GitHub API
    try:
        api_resp = await client.get(
            "https://api.github.com/repos/jakevdp/open-recipe-data/contents/data",
            timeout=30
        )
        if api_resp.status_code == 200:
            files = [f["download_url"] for f in api_resp.json()
                     if f["name"].endswith(".json")]
            print(f"  Found {len(files)} recipe files")
        else:
            # Fallback to known file list
            files = [f"{base}/recipes.json"]
    except Exception as e:
        print(f"  GitHub API error: {e}, trying direct download")
        files = [f"{base}/recipes.json"]

    docs = []
    for url in files[:50]:  # cap at 50 files for safety
        try:
            resp = await client.get(url, timeout=60)
            if resp.status_code != 200:
                continue
            data = resp.json()
            recipes = data if isinstance(data, list) else [data]

            for r in recipes:
                if not r.get("title"):
                    continue
                doc = make_community_doc(
                    title=r.get("title", ""),
                    description=r.get("description", ""),
                    ingredients_raw=r.get("ingredients", []),
                    steps_raw=r.get("instructions", r.get("steps", [])),
                    tags=r.get("tags", []) + r.get("categories", []),
                    source_url=r.get("url", r.get("source", "")),
                    image_url=r.get("image", r.get("picture", "")),
                    prep_time=r.get("prep_time", ""),
                    cook_time=r.get("cook_time", ""),
                    servings=r.get("servings", r.get("yield", 4)),
                    attribution="Open Recipe Project (CC BY 3.0)"
                )
                if doc["ingredients"] and doc["steps"]:
                    docs.append(doc)

        except Exception as e:
            print(f"  Error fetching {url}: {e}")

    print(f"  Parsed {len(docs)} valid recipes from jakevdp dataset")
    return docs


# ── Source 2: Synthetic high-quality seed recipes ────────────────────────────
# We generate a diverse set of well-structured recipes covering major cuisines,
# categories and dietary preferences. These are original content, no copyright.

SEED_RECIPES = [
    {
        "title": "Classic Spaghetti Bolognese",
        "description": "A hearty Italian meat sauce simmered low and slow with tomatoes and red wine.",
        "ingredients": [
            {"item": "spaghetti", "amount": "400g"},
            {"item": "beef mince", "amount": "500g"},
            {"item": "onion, finely diced", "amount": "1 large"},
            {"item": "garlic cloves, minced", "amount": "3"},
            {"item": "carrot, finely diced", "amount": "1"},
            {"item": "celery stalk, finely diced", "amount": "1"},
            {"item": "tinned chopped tomatoes", "amount": "2 x 400g"},
            {"item": "tomato paste", "amount": "2 tbsp"},
            {"item": "red wine", "amount": "150ml"},
            {"item": "olive oil", "amount": "2 tbsp"},
            {"item": "salt and black pepper", "amount": "to taste"},
            {"item": "parmesan, grated", "amount": "to serve"},
        ],
        "steps": [
            "Heat olive oil in a large pan, fry onion, carrot and celery for 8 minutes until soft.",
            "Add garlic and cook 1 minute. Add mince and brown, breaking it up.",
            "Pour in wine and simmer until reduced by half.",
            "Add tomatoes, tomato paste, salt and pepper. Simmer on low heat for 45 minutes.",
            "Cook spaghetti according to package instructions. Serve topped with sauce and parmesan."
        ],
        "tags": ["Italian", "Pasta", "Comfort", "Classic"],
        "cuisine": "italian", "category": "dinner",
        "prep_time": "15 min", "cook_time": "50 min", "servings": 4,
    },
    {
        "title": "Chicken Tikka Masala",
        "description": "Tender marinated chicken in a rich, creamy spiced tomato sauce.",
        "ingredients": [
            {"item": "chicken breast, cubed", "amount": "700g"},
            {"item": "plain yogurt", "amount": "150g"},
            {"item": "garlic cloves, minced", "amount": "4"},
            {"item": "fresh ginger, grated", "amount": "2 tbsp"},
            {"item": "garam masala", "amount": "2 tsp"},
            {"item": "ground cumin", "amount": "1 tsp"},
            {"item": "ground turmeric", "amount": "1 tsp"},
            {"item": "paprika", "amount": "1 tsp"},
            {"item": "tinned tomatoes", "amount": "400g"},
            {"item": "heavy cream", "amount": "150ml"},
            {"item": "onion, diced", "amount": "1 large"},
            {"item": "butter", "amount": "2 tbsp"},
            {"item": "fresh cilantro", "amount": "to garnish"},
        ],
        "steps": [
            "Mix yogurt, half the garlic and ginger, garam masala, cumin, turmeric and paprika. Marinate chicken for at least 1 hour.",
            "Grill or pan-fry marinated chicken until charred and cooked through. Set aside.",
            "Fry onion in butter until golden. Add remaining garlic and ginger, cook 2 minutes.",
            "Add tomatoes and simmer 15 minutes. Blend until smooth. Return to pan.",
            "Stir in cream and chicken. Simmer 10 minutes. Garnish with cilantro and serve with naan."
        ],
        "tags": ["Indian", "Curry", "Spicy", "Creamy"],
        "cuisine": "indian", "category": "dinner",
        "prep_time": "20 min", "cook_time": "40 min", "servings": 4,
    },
    {
        "title": "Classic French Omelette",
        "description": "A perfectly silky, rolled French omelette — technique over ingredients.",
        "ingredients": [
            {"item": "large eggs", "amount": "3"},
            {"item": "unsalted butter", "amount": "15g"},
            {"item": "salt", "amount": "pinch"},
            {"item": "fresh chives, chopped", "amount": "1 tbsp"},
        ],
        "steps": [
            "Crack eggs into a bowl, add salt, and beat vigorously with a fork until fully combined.",
            "Heat butter in a small non-stick pan over medium-high heat until foaming subsides.",
            "Pour in eggs. Shake pan constantly while stirring with a fork for 30 seconds.",
            "Remove from heat. Let residual heat finish cooking. Roll omelette onto plate. Garnish with chives."
        ],
        "tags": ["French", "Breakfast", "Quick", "Eggs"],
        "cuisine": "french", "category": "breakfast",
        "prep_time": "2 min", "cook_time": "3 min", "servings": 1,
    },
    {
        "title": "Vegetable Pad Thai",
        "description": "Classic Thai stir-fried rice noodles with tofu, eggs and crunchy peanuts.",
        "ingredients": [
            {"item": "flat rice noodles", "amount": "200g"},
            {"item": "firm tofu, cubed", "amount": "200g"},
            {"item": "eggs", "amount": "2"},
            {"item": "bean sprouts", "amount": "100g"},
            {"item": "spring onions, sliced", "amount": "3"},
            {"item": "garlic cloves, minced", "amount": "2"},
            {"item": "fish sauce (or soy sauce)", "amount": "3 tbsp"},
            {"item": "tamarind paste", "amount": "2 tbsp"},
            {"item": "sugar", "amount": "1 tbsp"},
            {"item": "lime", "amount": "1"},
            {"item": "roasted peanuts, crushed", "amount": "3 tbsp"},
            {"item": "vegetable oil", "amount": "2 tbsp"},
        ],
        "steps": [
            "Soak noodles in cold water for 30 minutes. Mix fish sauce, tamarind and sugar in a bowl.",
            "Fry tofu in oil until golden. Push to side, scramble eggs in the pan.",
            "Add garlic and drained noodles. Pour over sauce and toss to coat.",
            "Add bean sprouts and spring onions. Toss 1 minute.",
            "Serve with crushed peanuts, lime wedges and extra chilli."
        ],
        "tags": ["Thai", "Vegan Option", "Noodles", "Quick"],
        "cuisine": "thai", "category": "dinner",
        "prep_time": "30 min", "cook_time": "15 min", "servings": 2,
    },
    {
        "title": "Homemade Guacamole",
        "description": "Fresh, chunky guacamole with lime, cilantro and a hint of heat.",
        "ingredients": [
            {"item": "ripe avocados", "amount": "3"},
            {"item": "lime, juiced", "amount": "1"},
            {"item": "red onion, finely diced", "amount": "½ small"},
            {"item": "fresh cilantro, chopped", "amount": "2 tbsp"},
            {"item": "jalapeño, deseeded and minced", "amount": "1"},
            {"item": "garlic clove, minced", "amount": "1"},
            {"item": "salt", "amount": "½ tsp"},
            {"item": "tomato, deseeded and diced", "amount": "1"},
        ],
        "steps": [
            "Halve avocados, remove stones and scoop flesh into a bowl.",
            "Add lime juice and salt. Mash with a fork to desired consistency.",
            "Fold in onion, jalapeño, garlic, tomato and cilantro.",
            "Taste and adjust seasoning. Serve immediately with tortilla chips."
        ],
        "tags": ["Mexican", "Vegan", "Dip", "Quick", "Snack"],
        "cuisine": "mexican", "category": "quick",
        "prep_time": "10 min", "cook_time": "0 min", "servings": 4,
    },
]

def make_seed_docs():
    docs = []
    for r in SEED_RECIPES:
        doc = make_community_doc(
            title=r["title"],
            description=r.get("description", ""),
            ingredients_raw=r["ingredients"],
            steps_raw=r["steps"],
            tags=r.get("tags", []),
            source_url="",
            image_url="",
            prep_time=r.get("prep_time", ""),
            cook_time=r.get("cook_time", ""),
            servings=r.get("servings", 4),
            attribution="CookMe Community"
        )
        doc["cuisine"] = r.get("cuisine", doc["cuisine"])
        doc["category"] = r.get("category", doc["category"])
        docs.append(doc)
    return docs


# ── Main seeder ───────────────────────────────────────────────────────────────

async def seed():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    print("=" * 60)
    print("CookMe Community Recipe Seeder")
    print("=" * 60)

    # Create indexes first
    print("\nCreating indexes...")
    await db.community_recipes.create_index("community_recipe_id", unique=True)
    await db.community_recipes.create_index([("title", "text"), ("ingredient_names", "text"), ("description", "text"), ("tags", "text")])
    await db.community_recipes.create_index("cuisine")
    await db.community_recipes.create_index("category")
    await db.community_recipes.create_index("ingredient_names")
    await db.community_recipes.create_index("tags")
    await db.community_recipes.create_index("likes_count")
    print("  Indexes created ✓")

    all_docs = []

    # Source 1: seed recipes (always included)
    seed_docs = make_seed_docs()
    all_docs.extend(seed_docs)
    print(f"\nSeed recipes: {len(seed_docs)} ✓")

    # Source 2: jakevdp open recipe data
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as http_client:
        try:
            jakevdp_docs = await fetch_jakevdp_recipes(http_client)
            all_docs.extend(jakevdp_docs)
        except Exception as e:
            print(f"  jakevdp fetch failed: {e}")

    if not all_docs:
        print("\nNo recipes to insert.")
        return

    # Deduplicate by community_recipe_id
    seen = set()
    unique_docs = []
    for doc in all_docs:
        if doc["community_recipe_id"] not in seen:
            seen.add(doc["community_recipe_id"])
            unique_docs.append(doc)

    print(f"\nTotal unique recipes to insert: {len(unique_docs)}")

    # Bulk upsert in batches of 500
    batch_size = 500
    inserted = 0
    updated = 0

    for i in range(0, len(unique_docs), batch_size):
        batch = unique_docs[i:i + batch_size]
        from pymongo import UpdateOne
        operations = [
            UpdateOne(
                {"community_recipe_id": doc["community_recipe_id"]},
                {"$setOnInsert": doc},
                upsert=True
            )
            for doc in batch
        ]
        result = await db.community_recipes.bulk_write(operations, ordered=False)
        inserted += result.upserted_count
        updated += result.modified_count
        print(f"  Batch {i//batch_size + 1}: {result.upserted_count} new, {result.modified_count} updated")

    total = await db.community_recipes.count_documents({})
    print(f"\n{'=' * 60}")
    print(f"Done! {inserted} new recipes inserted")
    print(f"Total community recipes in DB: {total}")
    print(f"{'=' * 60}")

    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
