#!/usr/bin/env python3
"""Load data/master_recipes.json into the shared master recipe list (owner system_seeder).
Dry run by default; add --apply to write. Safe to re-run: updates the recipe's content/tags/image, never touches user data.
  python scripts/load_master_recipes.py            # dry run
  python scripts/load_master_recipes.py --apply
Needs MONGO_URL and DB_NAME (or backend/.env)."""
import json, os, sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv; load_dotenv(root/"backend"/".env")
except ImportError: pass
from pymongo import MongoClient
if not os.environ.get("MONGO_URL") or not os.environ.get("DB_NAME"): sys.exit("Set MONGO_URL and DB_NAME.")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
apply = "--apply" in sys.argv
data = json.load(open(root/"data"/"master_recipes.json", encoding="utf-8"))
new = upd = 0
for r in data:
    exists = db.recipes.find_one({"recipe_id": r["recipe_id"]}, {"_id": 1})
    upd += bool(exists); new += not exists
    if apply:
        keep_social = {k: r.pop(k) for k in ("likes_count","saves_count","favorited_by","hidden_by","gallery_images")}
        db.recipes.update_one({"recipe_id": r["recipe_id"]}, {"$set": r, "$setOnInsert": keep_social}, upsert=True)
print(("APPLIED" if apply else "DRY RUN") + f": {new} new, {upd} updated (of {len(data)})")
if not apply: print("Looks right? Run again with --apply.")
