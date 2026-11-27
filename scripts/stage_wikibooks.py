#!/usr/bin/env python3
"""STAGE recipes from the Wikibooks Cookbook (CC BY-SA 4.0). Nothing here touches the app.
Run on your Mac (needs internet):  pip3 install requests
  python3 scripts/stage_wikibooks.py --limit 60     # small test batch first
  python3 scripts/stage_wikibooks.py                # everything (a few hundred requests, ~10-15 min)
Writes data/staging/wikibooks.json and data/staging/wikibooks_review.csv (open the CSV in Numbers/Excel)."""
import csv, json, re, sys, time
from pathlib import Path
import requests
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"backend"))
from wikibooks_parser import parse_recipe
from recipe_cleaner import clean_recipe, is_cookable
from recipe_tagger import auto_tag, is_dessert

API = "https://en.wikibooks.org/w/api.php"
HEAD = {"User-Agent": "CookMe-staging/1.0 (https://github.com/CookMe1/CookMe-V3.1)"}
OUT = ROOT/"data"/"staging"; CACHE = OUT/"cache"; CACHE.mkdir(parents=True, exist_ok=True)
DRINK = re.compile(r"cocktail|smoothie|\bshake\b|punch|\btea\b|coffee|lemonade|liqueur|\bwine\b|sangria|margarita|martini|\bale\b|\bbeer\b|milkshake|\bsoda\b|syrup|extract", re.I)

def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

def api(params):
    for attempt in range(4):
        r = requests.get(API, params={**params, "format": "json", "formatversion": 2}, headers=HEAD, timeout=60)
        if r.status_code == 200: return r.json()
        time.sleep(3 * (attempt + 1))
    r.raise_for_status()

def list_titles(limit=None):
    titles, cont = [], {}
    while True:
        d = api({"action": "query", "list": "allpages", "apnamespace": 102, "aplimit": 500, "apfilterredir": "nonredirects", **cont})
        titles += [p["title"] for p in d["query"]["allpages"]]
        print(f"  listed {len(titles)} Cookbook pages...", end="\r")
        if limit and len(titles) >= limit * 4: break   # recipes are a fraction of all pages
        if "continue" not in d: break
        cont = d["continue"]; time.sleep(0.5)
    print()
    return titles

def fetch_text(titles):
    out = {}
    for i in range(0, len(titles), 50):
        batch = titles[i:i + 50]; need = [t for t in batch if not (CACHE/(re.sub(r"\\W", "_", t) + ".txt")).exists()]
        if need:
            d = api({"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main", "titles": "|".join(need)})
            for p in d["query"]["pages"]:
                rev = (p.get("revisions") or [{}])[0].get("slots", {}).get("main", {}).get("content", "")
                (CACHE/(re.sub(r"\\W", "_", p["title"]) + ".txt")).write_text(rev, encoding="utf-8")
            time.sleep(1.0)
        for t in batch: out[t] = (CACHE/(re.sub(r"\\W", "_", t) + ".txt")).read_text(encoding="utf-8")
        print(f"  downloaded {min(i + 50, len(titles))}/{len(titles)}", end="\r")
    print()
    return out

def score(r):
    ing = r["ingredients"]; with_amt = sum(1 for i in ing if i["amount"]) / max(len(ing), 1)
    flags = []
    if len(ing) < 5: flags.append("few ingredients")
    if with_amt < 0.7: flags.append("amounts missing")
    if len(r["steps"]) < 3: flags.append("few steps")
    if sum(len(s) for s in r["steps"]) < 200: flags.append("short method")
    if DRINK.search(r["title"]): flags.append("drink")
    return flags, with_amt

def main():
    limit = int(arg("--limit", 0)) or None
    master = {x["title"].strip().lower() for x in json.load(open(ROOT/"data"/"master_recipes.json", encoding="utf-8"))}
    if "--offline" in sys.argv:   # use pages already downloaded into data/staging/cache (no internet needed)
        titles = sorted(f.stem for f in CACHE.glob("*.txt")); print(f"1/3 offline: {len(titles)} cached pages")
    else:
        print("1/3 listing pages"); titles = list_titles(limit)
    print("2/3 downloading"); pages = fetch_text(titles if not limit else titles[: limit * 4])
    print("3/3 parsing"); recipes, seen, skipped = [], set(master), {"not a recipe": 0, "too thin": 0, "duplicate": 0}
    for t, wt in pages.items():
        r = parse_recipe(t, wt)
        if not r: skipped["not a recipe"] += 1; continue
        r = {**clean_recipe(r), **{k: r[k] for k in ("wikibooks_image",)}}
        if not is_cookable(r): skipped["too thin"] += 1; continue
        key = r["title"].lower()
        if key in seen: skipped["duplicate"] += 1; continue
        seen.add(key); tg = auto_tag(r)
        r["tags"] = sorted(set(r.get("tags", [])) | set(tg["tags"])); r["cuisine"] = r.get("cuisine") or tg["cuisine"]
        r["category"] = "dessert" if is_dessert(r) else r.get("category", "")
        recipes.append(r)
        if limit and len(recipes) >= limit: break
    json.dump(recipes, open(OUT/"wikibooks.json", "w", encoding="utf-8"), ensure_ascii=False)
    with open(OUT/"wikibooks_review.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["keep (y/n)", "title", "ingredients", "steps", "% with amounts", "cuisine", "tags", "flags", "link", "recipe_id"])
        for r in sorted(recipes, key=lambda x: (bool(score(x)[0]), x["title"])):
            flags, amt = score(r)
            w.writerow(["n" if flags else "y", r["title"], len(r["ingredients"]), len(r["steps"]), f"{round(amt*100)}%", r["cuisine"], ", ".join(r["tags"][:5]), "; ".join(flags), r["source_url"], r["recipe_id"]])
    clean = sum(1 for r in recipes if not score(r)[0])
    print(f"\nStaged {len(recipes)} recipes ({clean} look clean and are pre-marked 'y'). Skipped: {skipped}")
    print("Next: open data/staging/wikibooks_review.csv, change y/n, save, then run: python3 scripts/approve_staged.py")


if __name__ == "__main__":
    main()
