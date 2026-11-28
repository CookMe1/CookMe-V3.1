#!/usr/bin/env python3
"""Remove chosen photos:  python3 scripts/remove_photos.py id1,id2,...   (ids from photo_review.html). Those recipes go back to having no photo and
will not be searched again from the same source (they are marked as tried everywhere), so a bad photo never comes back by itself."""
import json, sys
from pathlib import Path
ST = Path(__file__).resolve().parent.parent/"data"/"staging"
ids = {x.strip() for x in sys.argv[1].split(",") if x.strip()}; n = 0
for f in ("open_new", "open_new2", "wikibooks_approved"):
    p = ST/f"{f}.json"; d = json.load(open(p, encoding="utf-8"))
    for r in d:
        if r["recipe_id"] in ids and r.get("image"):
            for k in ("image", "image_attribution", "image_source", "image_source_url"): r.pop(k, None)
            r["tried"] = ["pexels", "pixabay", "commons"]; r["image_no_match"] = True; n += 1
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False)
print(f"removed {n} photos")
