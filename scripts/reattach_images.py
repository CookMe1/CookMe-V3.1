#!/usr/bin/env python3
"""Copy photo links (and photographer credits) from a backup of master_recipes.json into the current one,
for recipes that have no image yet. Used after a merge conflict so no downloaded photo is lost.
  python3 scripts/reattach_images.py ~/Desktop/my_recipes_backup.json"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
F = ROOT/"data"/"master_recipes.json"
backup = {r["recipe_id"]: r for r in json.load(open(Path(sys.argv[1]).expanduser(), encoding="utf-8"))}
data = json.load(open(F, encoding="utf-8")); n = 0
for r in data:
    b = backup.get(r["recipe_id"])
    if r.get("image") or not b: continue
    img = b.get("image") or ""
    if img.startswith("/recipe-images/") and (ROOT/"frontend"/"public"/img.lstrip("/")).exists():
        r["image"] = img
        for k in ("image_attribution", "image_source"):
            if b.get(k): r[k] = b[k]
        n += 1
json.dump(data, open(F, "w", encoding="utf-8"), ensure_ascii=False)
print(f"re-attached {n} photos; {sum(1 for r in data if not r.get('image'))} recipes still have no image")
