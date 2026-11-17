#!/usr/bin/env python3
"""Tidy data/master_recipes.json: drop label steps ("step 1", "2", "▢"), strip step numbers, fix ingredient
amounts ("1.0 cup" -> "1 cup", "White"+"Rice" -> "White Rice"), and move recipes that are still too thin to
cook from into data/master_recipes_rejected.json (for review; they leave the app).
  python scripts/clean_recipes.py          # report only
  python scripts/clean_recipes.py --apply  # rewrite the files"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"backend"))
from recipe_cleaner import clean_recipe, is_cookable

F = ROOT/"data"/"master_recipes.json"; REJ = ROOT/"data"/"master_recipes_rejected.json"
data = json.load(open(F, encoding="utf-8"))
kept, rejected, changed = [], [], 0
for r in data:
    c = clean_recipe(r)
    if (c["steps"], c["ingredients"]) != (r["steps"], r["ingredients"]): changed += 1
    (kept if is_cookable(c) else rejected).append(c)
print(f"{len(data)} recipes: {changed} tidied, {len(rejected)} too thin to cook from, {len(kept)} kept")
for r in rejected[:15]: print("  rejected:", r["title"], f"({len(r['ingredients'])} ingredients, {len(r['steps'])} steps)")
if "--apply" in sys.argv:
    json.dump(kept, open(F, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(rejected, open(REJ, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("written. Rejected recipes saved to data/master_recipes_rejected.json")
