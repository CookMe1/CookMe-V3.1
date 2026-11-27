#!/usr/bin/env python3
"""Put approved recipes into the release queue (they appear in the app ~10 per day, in this order).
Dry run by default.  python scripts/queue_recipes.py data/staging/wikibooks_approved.json [--apply]
Safe to re-run: recipes already live or already queued are skipped. Needs MONGO_URL and DB_NAME (or backend/.env)."""
import json, os, sys
from pathlib import Path
root = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv; load_dotenv(root/"backend"/".env")
except ImportError: pass
from pymongo import MongoClient
if not os.environ.get("MONGO_URL") or not os.environ.get("DB_NAME"): sys.exit("Set MONGO_URL and DB_NAME.")
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
data = json.load(open(root/sys.argv[1], encoding="utf-8"))
apply = "--apply" in sys.argv
start = (db.recipe_queue.find_one(sort=[("queue_order", -1)]) or {}).get("queue_order", 0)
added = skipped = 0
for r in data:
    if r.get("needs_review") or not r.get("image"):      # only finished recipes (nutrition checked, photo added) join the queue
        skipped += 1; continue
    if db.recipes.find_one({"recipe_id": r["recipe_id"]}, {"_id": 1}) or db.recipe_queue.find_one({"recipe_id": r["recipe_id"]}, {"_id": 1}):
        skipped += 1; continue
    added += 1
    if apply: db.recipe_queue.insert_one({**r, "queue_order": start + added})
print(("APPLIED" if apply else "DRY RUN") + f": {added} queued, {skipped} skipped (already live or queued). Waiting in queue now: {db.recipe_queue.count_documents({})}")
if not apply: print("Looks right? Run again with --apply.")
