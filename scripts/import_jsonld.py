#!/usr/bin/env python3
"""Turn schema.org-style recipe JSON (the CookMe zip, or batches brought back by Grok) into the staging format.
Nothing here touches the app or the database.

  python3 scripts/import_jsonld.py PATH [PATH...] --name open_new
      PATH = a .json file, a folder of them, or a .zip. Writes data/staging/<name>.json (good ones) and
      data/staging/<name>_held.json (kept aside, with the reason). Then:  python3 scripts/enrich_staged.py data/staging/<name>.json

What it does: only open licences (CC0, public domain, CC BY, CC BY-SA, MIT, Unlicense, Apache, BSD, US federal works);
drops anything already in the library (Wikibooks approved list, master list, earlier staged files); repairs amounts;
keeps author, source link and licence on every recipe so a credit line can be shown."""
import hashlib, json, re, sys, zipfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"backend")); sys.path.insert(0, str(ROOT/"scripts"))
from amounts import split_ingredient
from amount_fixes import repair, coverage
from wikibooks_categories import kind_tags, is_special_kind, from_categories
from stage_wikibooks import score

S = ROOT/"data"/"staging"
OK_LICENSES = {  # SPDX / words -> label shown to people
    "cc0-1.0": "CC0", "cc0": "CC0", "public domain": "Public Domain", "pdm": "Public Domain", "unlicense": "Unlicense",
    "mit": "MIT", "apache-2.0": "Apache-2.0", "bsd-2-clause": "BSD", "bsd-3-clause": "BSD", "cc-by-4.0": "CC BY 4.0",
    "cc-by-3.0": "CC BY 3.0", "cc-by-sa-4.0": "CC BY-SA 4.0", "cc-by-sa-3.0": "CC BY-SA 3.0",
    "us federal government work": "US Federal Government work"}
CUISINES = {"indian", "pakistani", "bangladeshi", "sri_lankan", "middle_eastern", "turkish", "moroccan", "north_african", "west_african",
            "east_african", "african", "chinese", "japanese", "korean", "thai", "vietnamese", "filipino", "indonesian", "malaysian", "caribbean",
            "latin_american", "mexican", "french", "italian", "spanish", "greek", "german", "polish", "russian", "british", "irish", "american",
            "mediterranean", "asian", "european", "southeast_asian", "south_asian"}
CUISINE_FIX = {"north_african": "african", "west_african": "african", "east_african": "african", "pakistani": "south_asian",
               "bangladeshi": "south_asian", "sri_lankan": "south_asian", "filipino": "southeast_asian", "indonesian": "southeast_asian",
               "malaysian": "southeast_asian"}


def norm(t):
    return re.sub(r"[^a-z0-9]", "", re.sub(r"\(.*?\)", "", str(t).lower()))


def licence_of(r):
    meta = r.get("cookmeMeta") or {}
    raw = str(meta.get("licenseSpdx") or r.get("license") or r.get("license_url") or "").strip().lower()
    for key in sorted(OK_LICENSES, key=len, reverse=True):
        if raw == key or raw.rstrip("/").endswith("/" + key):
            return OK_LICENSES[key]
    for pat, label in ((r"creativecommons\.org/licenses/by-sa/4", "CC BY-SA 4.0"), (r"creativecommons\.org/licenses/by-sa/3", "CC BY-SA 3.0"),
                       (r"creativecommons\.org/licenses/by/4", "CC BY 4.0"), (r"creativecommons\.org/licenses/by/3", "CC BY 3.0"),
                       (r"creativecommons\.org/publicdomain/zero", "CC0"), (r"opensource\.org/licenses/mit", "MIT"),
                       (r"unlicense\.org", "Unlicense"), (r"apache\.org/licenses", "Apache-2.0")):
        if re.search(pat, raw):
            return label
    return ""


def minutes(iso):
    m = re.match(r"^PT(?:(\d+)H)?(?:(\d+)M)?$", str(iso or ""))
    if not m or not (m.group(1) or m.group(2)):
        return ""
    mins = int(m.group(1) or 0) * 60 + int(m.group(2) or 0)
    return f"{mins // 60}h {mins % 60}m" if mins >= 60 and mins % 60 else (f"{mins // 60}h" if mins >= 60 else f"{mins} min")


def to_steps(x):
    out = []
    for s in x or []:
        t = s.get("text") if isinstance(s, dict) else s
        if isinstance(t, str) and t.strip():
            out.append(re.sub(r"\s+", " ", t).strip())
    return out


def load(paths):
    files = []
    for p in map(Path, paths):
        if p.suffix == ".zip":
            with zipfile.ZipFile(p) as z:
                files += [json.loads(z.read(n)) for n in z.namelist() if n.endswith(".json")]
        elif p.is_dir():
            files += [json.load(open(f, encoding="utf-8")) for f in sorted(p.rglob("*.json"))]
        else:
            files.append(json.load(open(p, encoding="utf-8")))
    for d in files:
        yield from (d.get("recipes", []) if isinstance(d, dict) else d)


def convert(r):
    meta = r.get("cookmeMeta") or {}
    title = re.sub(r"\s+", " ", str(r.get("name") or "")).strip()
    url = r.get("url") or meta.get("sourceUrl") or ""
    ings = []
    for line in r.get("recipeIngredient") or []:
        a, i = split_ingredient(str(line))
        ings.append(repair({"amount": a, "item": i}))
    kw = r.get("keywords") or []
    kw = [k.strip() for k in (kw.split(",") if isinstance(kw, str) else kw) if k and k.strip()]
    cats = [str(r.get("recipeCategory") or "")] + kw
    info = from_categories([c for c in cats if c])
    tags = sorted({k.lower() for k in kw if len(k) < 24} | set(info["tags"]) | set(kind_tags(title, kw)))
    cat = str(r.get("recipeCategory") or "").lower()
    if "drink" in cat and "drink" not in tags: tags.append("drink")
    category = "dessert" if (info["dessert"] or "dessert" in cat) else ("" if not cat or "meal" in cat or "friendly" in cat or "international" in cat else cat)
    cuisine = str(r.get("recipeCuisine") or "").lower().replace(" ", "_")
    cuisine = cuisine if cuisine in CUISINES else (info["cuisine"] or "")
    cuisine = CUISINE_FIX.get(cuisine, cuisine)
    y = re.search(r"\d+", str(r.get("recipeYield") or ""))
    desc = str(r.get("description") or "")
    if re.search(r"a quick recipe from the|from the Wikibooks Cookbook \(", desc) or len(desc) < 25:
        desc = ""
    author = meta.get("originalAuthor")
    author = author.get("name") if isinstance(author, dict) else (author or (r.get("author") or {}).get("name") if isinstance(r.get("author"), dict) else r.get("author"))
    rid = "recipe_" + hashlib.sha1(((url or "") + "|" + title).encode()).hexdigest()[:12]   # url alone is shared by every recipe of one book
    out = {"recipe_id": rid, "title": title, "description": desc, "image": None, "prep_time": minutes(r.get("prepTime")),
           "cook_time": minutes(r.get("cookTime")), "servings": int(y.group()) if y and int(y.group()) > 0 else 4,
           "servings_stated": bool(y and int(y.group()) > 0 and not r.get("servings_estimated")), "difficulty": "Medium",
           "ingredients": ings, "steps": to_steps(r.get("recipeInstructions")), "tags": tags, "category": category, "cuisine": cuisine,
           "source_url": url, "source_license": licence_of(r), "source_author": author or "",
           "source_license_url": meta.get("licenseUrl") or r.get("license_url") or r.get("license") or "",
           "source_attribution": meta.get("attributionText") or "", "source_share_alike": bool(meta.get("shareAlike") or "SA" in licence_of(r)),
           "user_id": "system_seeder", "likes_count": 0, "saves_count": 0, "favorited_by": [], "hidden_by": [], "gallery_images": []}
    if not out["prep_time"] and not out["cook_time"]:
        out["time_estimated"] = True
    img = r.get("image")
    if img and meta.get("imageLicense"):
        out["source_image"] = {"url": img if isinstance(img, str) else (img[0] if isinstance(img, list) else img.get("url")),
                               "license": meta.get("imageLicense"), "author": meta.get("imageAuthor"), "page": meta.get("imageSourcePage")}
    return out


def main():
    paths = [a for a in sys.argv[1:] if not a.startswith("--") and a != (sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else "")]
    name = sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else "open_new"
    have = set()
    for f in [ROOT/"data"/"master_recipes.json", *S.glob("*_approved.json")]:
        if f.exists() and f.stem != name:
            d = json.load(open(f, encoding="utf-8")); have |= {norm(x.get("title", "")) for x in (d if isinstance(d, list) else d.get("recipes", []))}
    good, held, stats = {}, [], {"read": 0, "licence": 0, "already have": 0, "duplicate in batch": 0}
    for raw in load(paths):
        stats["read"] += 1
        r = convert(raw)
        if not r["source_license"] or not r["source_url"] or not r["title"]:
            stats["licence"] += 1; held.append({**r, "held_because": "no open licence or no source link"}); continue
        k = norm(r["title"])
        if k in have:
            stats["already have"] += 1; continue
        flags, amt = score(r)
        if flags:
            held.append({**r, "held_because": "; ".join(flags), "needs_amounts": "amounts missing" in flags}); continue
        if k in good:
            stats["duplicate in batch"] += 1
            if coverage(r["ingredients"]) <= coverage(good[k]["ingredients"]): continue
        good[k] = r
    json.dump(list(good.values()), open(S/f"{name}.json", "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(held, open(S/f"{name}_held.json", "w", encoding="utf-8"), ensure_ascii=False)
    print(stats, f"\n{len(good)} good -> data/staging/{name}.json; {len(held)} held -> {name}_held.json")
    import collections
    print("held reasons:", collections.Counter(h["held_because"] for h in held).most_common(6))


if __name__ == "__main__":
    main()
