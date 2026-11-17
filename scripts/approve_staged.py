#!/usr/bin/env python3
"""Turn your reviewed CSV into the approved list. Only rows with keep = y are used.
  python3 scripts/approve_staged.py                       # uses data/staging/wikibooks.json + wikibooks_review.csv
  python3 scripts/approve_staged.py --name wikibooks
Writes data/staging/<name>_approved.json. Then add photos:  python3 scripts/fill_images.py --file data/staging/<name>_approved.json"""
import csv, json, sys
from pathlib import Path
S = Path(__file__).resolve().parent.parent/"data"/"staging"
name = sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else "wikibooks"
recipes = {r["recipe_id"]: r for r in json.load(open(S/f"{name}.json", encoding="utf-8"))}
rows = list(csv.DictReader(open(S/f"{name}_review.csv", encoding="utf-8-sig")))
keep_key = next(k for k in rows[0] if k.startswith("keep"))
approved = []
for row in rows:
    if row[keep_key].strip().lower().startswith("y") and row["recipe_id"] in recipes:
        r = dict(recipes[row["recipe_id"]]); r.pop("wikibooks_image", None); approved.append(r)
json.dump(approved, open(S/f"{name}_approved.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"{len(approved)} approved of {len(rows)}. At 10 a day that is about {len(approved)//10} days of new recipes.")
