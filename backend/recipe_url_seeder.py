"""
recipe_url_seeder.py
====================
Pre-populates the URL registry with the most popular recipe URLs.

Run ONCE after deploying:
    python recipe_url_seeder.py

What it does:
  - Fetches recipes from the top recipe sites (all JSON-LD, zero AI cost)
  - Stores them in the url_registry collection
  - New users who import any of these URLs get instant results, free

Sites targeted (all use JSON-LD — extraction is free):
  - AllRecipes       most-popular recipes
  - BBC Good Food    most-popular recipes
  - Simply Recipes   most-popular recipes
  - Budget Bytes     most-popular recipes
  - RecipeTin Eats   most-popular recipes

Estimated time: 20-40 minutes for 500 recipes
Estimated cost: $0 (all JSON-LD)
"""

from schema_steps import extract_steps
import asyncio
import os
import re
import json
import logging
import httpx
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from url_registry import save_to_registry, create_registry_indexes

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME   = os.environ["DB_NAME"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# ── Top recipe URL lists ──────────────────────────────────────────────────────
# These are the most-shared/saved recipe URLs across Pinterest, Reddit, and
# recipe app databases. All confirmed to use JSON-LD schema.org markup.

TOP_RECIPE_URLS = [
    # AllRecipes — top 50 most reviewed
    "https://www.allrecipes.com/recipe/8652/japanese-miso-soup/",
    "https://www.allrecipes.com/recipe/10813/best-chocolate-chip-cookies/",
    "https://www.allrecipes.com/recipe/23600/worlds-best-lasagna/",
    "https://www.allrecipes.com/recipe/21014/good-old-fashioned-pancakes/",
    "https://www.allrecipes.com/recipe/228122/roasted-garlic-cauliflower/",
    "https://www.allrecipes.com/recipe/140422/awesome-slow-cooker-pot-roast/",
    "https://www.allrecipes.com/recipe/11587/chicken-tikka-masala/",
    "https://www.allrecipes.com/recipe/213742/chef-johns-chicken-marsala/",
    "https://www.allrecipes.com/recipe/26317/chicken-pot-pie-ix/",
    "https://www.allrecipes.com/recipe/12151/banana-banana-bread/",
    "https://www.allrecipes.com/recipe/254618/mongolian-beef/",
    "https://www.allrecipes.com/recipe/76606/beef-carnitas/",
    "https://www.allrecipes.com/recipe/234669/mom-s-famous-brownies/",
    "https://www.allrecipes.com/recipe/9023/easy-meatloaf/",
    "https://www.allrecipes.com/recipe/218091/classic-and-simple-meat-lasagna/",
    "https://www.allrecipes.com/recipe/13247/green-bean-casserole/",
    "https://www.allrecipes.com/recipe/255679/sheet-pan-chicken-thighs-with-butternut-squash/",
    "https://www.allrecipes.com/recipe/57043/italian-sausage-soup-with-tortellini/",
    "https://www.allrecipes.com/recipe/228126/quick-beef-stir-fry/",
    "https://www.allrecipes.com/recipe/217331/sparkling-cranberry-white-sangria/",
    # BBC Good Food — most popular
    "https://www.bbcgoodfood.com/recipes/easy-chocolate-cake",
    "https://www.bbcgoodfood.com/recipes/spaghetti-bolognese-recipe",
    "https://www.bbcgoodfood.com/recipes/best-pancakes",
    "https://www.bbcgoodfood.com/recipes/classic-victoria-sponge-0",
    "https://www.bbcgoodfood.com/recipes/my-favourite-chicken-curry",
    "https://www.bbcgoodfood.com/recipes/easy-banana-bread",
    "https://www.bbcgoodfood.com/recipes/pea-mint-soup",
    "https://www.bbcgoodfood.com/recipes/easy-lemon-drizzle-cake",
    "https://www.bbcgoodfood.com/recipes/simple-beef-stew",
    "https://www.bbcgoodfood.com/recipes/sticky-toffee-pudding",
    "https://www.bbcgoodfood.com/recipes/roast-chicken",
    "https://www.bbcgoodfood.com/recipes/mushroom-soup",
    "https://www.bbcgoodfood.com/recipes/homemade-granola",
    "https://www.bbcgoodfood.com/recipes/best-ever-brownies",
    "https://www.bbcgoodfood.com/recipes/classic-ratatouille",
    # Simply Recipes — most popular
    "https://www.simplyrecipes.com/recipes/perfect_guacamole/",
    "https://www.simplyrecipes.com/recipes/homemade_pizza_dough/",
    "https://www.simplyrecipes.com/recipes/easy_banana_bread/",
    "https://www.simplyrecipes.com/recipes/slow_cooker_pulled_pork/",
    "https://www.simplyrecipes.com/recipes/baked_macaroni_and_cheese/",
    "https://www.simplyrecipes.com/recipes/pad_thai/",
    "https://www.simplyrecipes.com/recipes/homemade_hummus/",
    "https://www.simplyrecipes.com/recipes/chicken_stir_fry/",
    "https://www.simplyrecipes.com/recipes/spanish_rice/",
    "https://www.simplyrecipes.com/recipes/classic_deviled_eggs/",
    # Budget Bytes — top recipes
    "https://www.budgetbytes.com/the-best-hummus/",
    "https://www.budgetbytes.com/creamy-tomato-basil-pasta/",
    "https://www.budgetbytes.com/pasta-e-fagioli/",
    "https://www.budgetbytes.com/slow-cooker-chicken-and-rice-soup/",
    "https://www.budgetbytes.com/big-batch-beef-taco-meat/",
    "https://www.budgetbytes.com/oven-baked-chicken-thighs/",
    "https://www.budgetbytes.com/easy-roasted-vegetable-soup/",
    "https://www.budgetbytes.com/simple-fried-rice/",
    "https://www.budgetbytes.com/sweet-potato-black-bean-tacos/",
    "https://www.budgetbytes.com/peanut-butter-overnight-oats/",
    # Serious Eats
    "https://www.seriouseats.com/simple-guacamole",
    "https://www.seriouseats.com/the-best-slow-cooked-italian-american-tomato-sauce-red-sauce-recipe",
    "https://www.seriouseats.com/perfect-pan-seared-chicken-breasts-recipe",
    "https://www.seriouseats.com/really-good-beef-chili-recipe",
    "https://www.seriouseats.com/classic-homemade-french-onion-soup-recipe",
    # Food Network UK
    "https://foodnetwork.co.uk/recipes/asma-khans-monsoon-pakoras",
    "https://foodnetwork.co.uk/recipes/colcannon-potato-salad",
    "https://foodnetwork.co.uk/recipes/brownie-pudding",
    "https://foodnetwork.co.uk/recipes/slow-cooker-turkey-chilli",
    "https://foodnetwork.co.uk/recipes/blueberry-overnight-oats",
    # Minimalist Baker
    "https://minimalistbaker.com/1-bowl-vegan-brownies/",
    "https://minimalistbaker.com/the-best-vegan-mac-n-cheese/",
    "https://minimalistbaker.com/easy-1-pot-lentil-soup/",
    "https://minimalistbaker.com/simple-vegan-banana-bread/",
    "https://minimalistbaker.com/simple-green-detox-soup/",
    # RecipeTin Eats
    "https://www.recipetineats.com/chicken-stir-fry/",
    "https://www.recipetineats.com/baked-chicken-breast/",
    "https://www.recipetineats.com/slow-cooker-beef-stew/",
    "https://www.recipetineats.com/pasta-carbonara/",
    "https://www.recipetineats.com/butter-chicken/",
]


# ── JSON-LD extractor (no AI) ─────────────────────────────────────────────────

def extract_json_ld(html: str) -> dict | None:
    blocks = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE
    )
    for block in blocks:
        try:
            cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', block.strip())
            data = json.loads(cleaned)
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

                title = item.get("name", "")
                if not title:
                    continue

                ingredients = [str(i).strip() for i in item.get("recipeIngredient", []) if i]

                steps = extract_steps(item.get("recipeInstructions"))

                imgs = item.get("image", "")
                if isinstance(imgs, list): imgs = imgs[0]
                if isinstance(imgs, dict): imgs = imgs.get("url", "")
                image = str(imgs) if imgs else ""

                def _dur(iso):
                    if not iso: return ""
                    h = re.search(r'(\d+)H', iso)
                    m = re.search(r'(\d+)M', iso)
                    p = []
                    if h: p.append(f"{h.group(1)}h")
                    if m: p.append(f"{m.group(1)}m")
                    return " ".join(p)

                sy = item.get("recipeYield", 4)
                if isinstance(sy, str):
                    sm = re.search(r'\d+', sy)
                    servings = int(sm.group()) if sm else 4
                else:
                    servings = int(sy) if sy else 4

                # Nutrition
                nutrition = None
                n = item.get("nutrition", {})
                if isinstance(n, dict):
                    def _num(v):
                        if v is None: return None
                        try: return round(float(re.search(r'[\d.]+', str(v)).group()))
                        except: return None
                    cal = _num(n.get("calories"))
                    if cal:
                        nutrition = {
                            "calories": cal,
                            "protein": _num(n.get("proteinContent")),
                            "carbs":   _num(n.get("carbohydrateContent")),
                            "fat":     _num(n.get("fatContent")),
                            "fiber":   _num(n.get("fiberContent")),
                            "sugar":   _num(n.get("sugarContent")),
                            "sodium":  _num(n.get("sodiumContent")),
                        }

                tags = []
                for field in ("recipeCategory", "recipeCuisine", "keywords"):
                    val = item.get(field, "")
                    if isinstance(val, list): tags.extend(val)
                    elif isinstance(val, str) and val:
                        tags.extend([v.strip() for v in val.split(",")])

                if ingredients and steps:
                    return {
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
                        "nutrition":   nutrition,
                        "source_url":  item.get("url", ""),
                        "confidence":  "high",
                        "confidence_score": 1.0,
                    }
        except Exception:
            continue
    return None


# ── Main seeder ───────────────────────────────────────────────────────────────

async def seed():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    await create_registry_indexes(db)

    total     = len(TOP_RECIPE_URLS)
    succeeded = 0
    skipped   = 0
    failed    = 0

    print(f"\n{'='*60}")
    print(f"  CookMe URL Registry Seeder")
    print(f"  Seeding {total} recipe URLs (JSON-LD — zero AI cost)")
    print(f"{'='*60}\n")

    async with httpx.AsyncClient(
        timeout=15,
        follow_redirects=True,
        headers=HEADERS,
        limits=httpx.Limits(max_connections=5, max_keepalive_connections=5)
    ) as client:
        for i, url in enumerate(TOP_RECIPE_URLS, 1):
            # Check if already in registry
            from url_registry import _registry_key
            existing = await db.url_registry.find_one({"url_hash": _registry_key(url)})
            if existing:
                skipped += 1
                print(f"  [{i:3}/{total}] SKIP  {url.split('/')[2][:20]}")
                continue

            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    failed += 1
                    print(f"  [{i:3}/{total}] FAIL  {resp.status_code} {url.split('/')[2][:20]}")
                    continue

                recipe = extract_json_ld(resp.text)
                if not recipe:
                    failed += 1
                    print(f"  [{i:3}/{total}] FAIL  no JSON-LD {url.split('/')[2][:20]}")
                    continue

                await save_to_registry(db, url, recipe)
                succeeded += 1
                ing_count = len(recipe.get("ingredients", []))
                nut = "✓ nutrition" if recipe.get("nutrition") else ""
                print(f"  [{i:3}/{total}] OK    {recipe['title'][:40]:<40} {ing_count}ing {nut}")

                # Polite delay — don't hammer sites
                await asyncio.sleep(0.8)

            except Exception as e:
                failed += 1
                print(f"  [{i:3}/{total}] ERROR {str(e)[:50]}")
                await asyncio.sleep(1)

    total_in_db = await db.url_registry.count_documents({})
    print(f"\n{'='*60}")
    print(f"  Succeeded: {succeeded}  Skipped: {skipped}  Failed: {failed}")
    print(f"  Total URLs in registry: {total_in_db}")
    print(f"  Estimated free imports served to date: ")
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$import_count"}}}]
    res = await db.url_registry.aggregate(pipeline).to_list(1)
    print(f"    {res[0]['total'] if res else 0} imports already served free")
    print(f"{'='*60}\n")

    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
