#!/usr/bin/env python3
"""Add automatic tags (cooking type, vegetarian/vegan) and cuisine to recipes already in the database.
Only ADDS tags and fills a blank cuisine; never removes your tags. Dry run by default.
  python scripts/retag_recipes.py            # shows what would change
  python scripts/retag_recipes.py --apply
Needs MONGO_URL and DB_NAME (or backend/.env)."""
import os, sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / "backend"))
try:
    from dotenv import load_dotenv; load_dotenv(root / "backend" / ".env")
except ImportError:
    pass
from pymongo import MongoClient
from recipe_tagger import auto_tag
if not os.environ.get("MONGO_URL") or not os.environ.get("DB_NAME"):
    sys.exit("Set MONGO_URL and DB_NAME.")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
apply = "--apply" in sys.argv
changed = cuisines = 0
for r in db.recipes.find({}, {"recipe_id": 1, "title": 1, "ingredients": 1, "steps": 1, "tags": 1, "cuisine": 1, "category": 1}):
    auto = auto_tag(r)
    old = set(r.get("tags") or [])
    new_tags = sorted(old | set(auto["tags"]))
    upd = {}
    if set(new_tags) != old:
        upd["tags"] = new_tags
    if not r.get("cuisine") and auto["cuisine"]:
        upd["cuisine"] = auto["cuisine"]; cuisines += 1
    if upd:
        changed += 1
        if apply:
            db.recipes.update_one({"_id": r["_id"]}, {"$set": upd})
print(("APPLIED" if apply else "DRY RUN") + f": {changed} recipes updated ({cuisines} got a cuisine)")
if not apply: print("Looks right? Run again with --apply.")
