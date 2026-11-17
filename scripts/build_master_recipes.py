#!/usr/bin/env python3
"""Build data/master_recipes.json from a CookMe export: recipes only, no user data, cleaned images, cooking-type tags.
Usage: python scripts/build_master_recipes.py export.json [out.json]"""
import json, re, sys, collections
SEEDED = {"system_seeder", "daily_import"}
KEEP = ["recipe_id","title","description","image","prep_time","cook_time","servings","difficulty","ingredients","steps",
        "tags","category","cuisine","nutrition","source_url","diet_type","created_at","updated_at"]
EXPENSIVE = r"lamb|salmon|prawn|shrimp|lobster|steak|sirloin|fillet|scallop|crab|duck|veal|saffron|truffle|monkfish|venison|brandy|champagne|wine|oyster|mussel|squid|tuna steak"
CHEAP = r"pasta|spaghetti|noodle|rice|egg|potato|bean|lentil|chickpea|bread|oat|tuna|cabbage|carrot|onion|tomato|pea|sausage|mince|chicken thigh|flour|cheese"
SLOW = r"overnight|marinate for (?:at least )?\d+ hours|\b\d+ hours?\b|slow[- ]cook|chill for|refrigerate for"
def text(r): return (r.get("title","")+" "+" ".join(map(str,r.get("steps") or []))).lower()
def ings(r): return " ".join(str(i.get("item","")) for i in r.get("ingredients") or [] if isinstance(i,dict)).lower()
def types(r):
    t, s, ing = r["title"].lower(), text(r), ings(r)
    n_ing, n_steps = len(r.get("ingredients") or []), len(r.get("steps") or [])
    tags = set(x.lower() for x in r.get("tags") or [] if isinstance(x,str))
    dessert = (r.get("category")=="dessert") or bool(tags & {"dessert","desert","cake","pudding","pie","baking","sweet"}) or bool(re.search(r"cake|pudding|curd|delight|cookie|brownie|tart\b|pie\b|fudge|ice cream|mousse|cobbler|crumble|biscuit|muffin|candy", t))
    out = []
    if re.search(r"instant pot|instapot|pressure cooker", s): out += ["instant pot","pressure cooker"]
    if re.search(r"slow cooker|crock ?pot", s): out += ["slow cooker","crockpot"]
    if re.search(r"air ?fr(y|i)er", s): out += ["air fryer"]
    if re.search(r"one[- ]pot|one pan|one-pan|sheet pan|traybake|tray bake|\bstew\b|casserole|chilli|chili|risotto|hotpot|\bsoup\b|pilaf|paella", t) or "instant pot" in out or "slow cooker" in out:
        out += ["one pot"]
    quick = (re.search(r"\b(quick|fast|speedy|15[- ]min|20[- ]min|30[- ]min)", t) or
             (n_ing <= 9 and n_steps <= 5 and not dessert and not re.search(r"soup|stew|roast|braise|casserole|bake|pie|hotpot", t))) and not re.search(SLOW, s)
    if quick: out += ["quick","30 min"]
    if (n_ing <= 9 and n_steps <= 7 and not dessert and re.search(CHEAP, ing) and not re.search(EXPENSIVE, ing+" "+t)):
        out += ["student","budget","easy","cheap"]
    return out
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
        d["tags"] = sorted(set(x for x in (d.get("tags") or []) if isinstance(x,str)) | set(types(r)))
        d["user_id"]="system_seeder"; d["likes_count"]=0; d["saves_count"]=0
        d["favorited_by"]=[]; d["hidden_by"]=[]; d["gallery_images"]=[]
        out.append(d)
    json.dump(out, open(dst,"w",encoding="utf-8"), ensure_ascii=False)
    print(f"kept {len(out)} recipes -> {dst}")
    for k,v in rep.items(): print(f"  {k}: {v}")
    c = collections.Counter(t for d in out for t in d["tags"] if t in ("quick","student","one pot","instant pot","slow cooker","air fryer"))
    print("cooking types:", dict(c))
if __name__=="__main__": main()
