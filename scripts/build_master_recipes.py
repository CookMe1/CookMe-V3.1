#!/usr/bin/env python3
"""Build data/master_recipes.json from a CookMe export: recipes only, no user data, cleaned images, cooking-type tags.
Usage: python scripts/build_master_recipes.py export.json [out.json]"""
import json, re, sys, collections
SEEDED = {"system_seeder", "daily_import"}
KEEP = ["recipe_id","title","description","image","prep_time","cook_time","servings","difficulty","ingredients","steps",
        "tags","category","cuisine","nutrition","source_url","diet_type","created_at","updated_at"]
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from recipe_tagger import types, diet_tags, infer_cuisine, ings  # noqa: E402

def clean_image(u):
    if isinstance(u,str) and u.startswith("data:image/") and len(u) < 1_500_000: return u  # user-uploaded photo, kept
    if not u or not isinstance(u,str) or not u.startswith("http"): return None
    return u.replace("-312x231.", "-636x393.")
def main():
    src = sys.argv[1]; dst = sys.argv[2] if len(sys.argv)>2 else "data/master_recipes.json"
    R = json.load(open(src,encoding="utf-8"))["collections"]["recipes"]["documents"]
    rep = collections.Counter(); out=[]; seen=set(); img_seen=set()
    for r in R:
        k = re.sub(r"\W+"," ",(r.get("title") or "").lower()).strip()
        if not k or not r.get("ingredients") or not r.get("steps"): rep["dropped: empty/incomplete"]+=1; continue
        if k in seen: rep["dropped: duplicate title"]+=1; continue
        seen.add(k)
        d = {f:r[f] for f in KEEP if f in r}
        d["image"] = clean_image(d.get("image"))
        if d["image"] and d["image"] in img_seen: d["image"]=None; rep["image removed: repeated"]+=1
        elif d["image"]: img_seen.add(d["image"])
        if not d["image"]: rep["no image (will show app placeholder)"]+=1
        for f in ("created_at","updated_at"):
            v=d.get(f); d[f]=v["$date"] if isinstance(v,dict) else v
        base = set(x for x in (d.get("tags") or []) if isinstance(x,str)) - {"vegetarian", "Vegetarian", "vegan", "Vegan"}
        d["tags"] = sorted(base | set(types(r)) | set(diet_tags(r)))
        d["cuisine"] = infer_cuisine(r)
        d["user_id"]="system_seeder"; d["likes_count"]=0; d["saves_count"]=0
        d["favorited_by"]=[]; d["hidden_by"]=[]; d["gallery_images"]=[]
        out.append(d)
    json.dump(out, open(dst,"w",encoding="utf-8"), ensure_ascii=False)
    print(f"kept {len(out)} recipes -> {dst}")
    for k,v in rep.items(): print(f"  {k}: {v}")
    c = collections.Counter(t for d in out for t in d["tags"] if t in ("quick","student","one pot","instant pot","slow cooker","air fryer","vegetarian","vegan"))
    print("cooking types and diets:", dict(c))
    print("with cuisine:", sum(1 for d in out if d["cuisine"]), "of", len(out))
if __name__=="__main__": main()
