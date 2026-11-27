#!/usr/bin/env python3
"""Use a schema.org recipe zip/JSON to improve recipes we already have (fills gaps only, never overwrites good data).
  python3 scripts/merge_zip_into_staged.py PATH --file data/staging/wikibooks_approved.json
Adds: full author list + licence link + attribution text (needed for CC BY-SA credit), Commons photo details (source_image),
useful tags (halal, vegan, spicy, air fryer when the method really uses one ...), dessert category, cuisine, stated servings."""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"backend")); sys.path.insert(0, str(ROOT/"scripts"))
import import_jsonld as I

KEEP_TAGS = {"halal", "kosher", "vegetarian", "vegan", "gluten-free", "gluten free", "dairy-free", "spicy", "one pot", "slow cooker", "crockpot",
             "microwave", "bbq", "kid friendly", "drink", "alcoholic", "cocktail", "smoothie", "sauce", "dressing", "dip", "marinade", "snack", "easy"}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    f = Path(sys.argv[sys.argv.index("--file") + 1]) if "--file" in sys.argv else ROOT/"data"/"staging"/"wikibooks_approved.json"
    f = f if f.is_absolute() else ROOT/f
    path = [a for a in args if a != str(f) and a != sys.argv[sys.argv.index("--file") + 1]] if "--file" in sys.argv else args
    ours = json.load(open(f, encoding="utf-8"))
    byurl = {r.get("source_url"): r for r in ours}; bynorm = {I.norm(r["title"]): r for r in ours}
    n = {"matched": 0, "tags": 0, "author": 0, "image": 0, "servings": 0, "cuisine": 0, "dessert": 0}
    for raw in I.load(path):
        z = I.convert(raw)
        o = byurl.get(z["source_url"]) or bynorm.get(I.norm(z["title"]))
        if not o: continue
        n["matched"] += 1
        text = " ".join(o["steps"] + [i["item"] for i in o["ingredients"]]).lower()
        have = {t.lower() for t in o.get("tags") or []}
        add = {t for t in z["tags"] if t in KEEP_TAGS and t not in have}
        if "air fryer" in {t.lower() for t in z["tags"]} and re.search(r"air[- ]?fr", text): add.add("air fryer")
        if add: o["tags"] = sorted(set(o.get("tags") or []) | add); n["tags"] += 1
        for k in ("source_author", "source_license_url", "source_attribution"):
            if z.get(k) and not o.get(k):
                o[k] = z[k]; n["author"] += k == "source_author"
        if "source_share_alike" in z: o["source_share_alike"] = z["source_share_alike"]
        if z.get("source_image") and not o.get("source_image"): o["source_image"] = z["source_image"]; n["image"] += 1
        if z["servings_stated"] and not o.get("servings_stated"):
            o["servings"] = z["servings"]; o["servings_stated"] = True; o.pop("servings_estimated", None); n["servings"] += 1
        if z["cuisine"] and not o.get("cuisine"): o["cuisine"] = z["cuisine"]; n["cuisine"] += 1
        if z["category"] == "dessert" and o.get("category") != "dessert": o["category"] = "dessert"; n["dessert"] += 1
    json.dump(ours, open(f, "w", encoding="utf-8"), ensure_ascii=False)
    print(n)


if __name__ == "__main__":
    main()
