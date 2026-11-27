#!/usr/bin/env python3
"""Add what Wikibooks recipes lack: prep/cook times (estimated from the method, flagged time_estimated),
a proper description, and nutrition per serving (from the local USDA table). Photos come from fill_images.py.
  python3 scripts/enrich_staged.py data/staging/wikibooks_approved.json
Safe to re-run. Recipes where nutrition can't be worked out reliably (too few ingredients matched) are left without it."""
import asyncio, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
import master_enrich as e
from description_quality import description_is_weak
from nutrition_lookup import calculate_recipe_nutrition_free


async def enrich(rows):
    t = d = n = 0
    for r in rows:
        for i in r.get("ingredients") or []:      # Wikibooks wording: '1 kg of round beef' -> amount '1 kg', item 'round beef'
            i["item"] = re.sub(r"^(?:of|a|an)\s+", "", str(i.get("item") or "").strip(), flags=re.I)
        if not r.get("prep_time") or not r.get("cook_time") or r.get("prep_time") in ("", "15 min"):
            real_cook = r.get("cook_time") if r.get("cook_time") and not r.get("time_estimated") else ""
            prep, cook, est = e.estimate_times(r)
            r["prep_time"] = r.get("prep_time") or prep
            r["cook_time"] = real_cook or cook
            r["time_estimated"] = True
            t += 1
        if description_is_weak(r.get("description"), r.get("title", "")):
            r["description"] = e.make_description(r); r["description_auto"] = True; d += 1
        if not r.get("nutrition"):
            try:
                srv = int(str(r.get("servings") or 4).split()[0])
            except ValueError:
                srv = 4
            nut = await calculate_recipe_nutrition_free(r.get("ingredients") or [], srv)
            if nut and not (30 <= nut.get("calories", 0) <= 1500):
                nut = None            # over 1,500 kcal a serving is almost always a wrong serving count: show nothing rather than a wrong number
            if nut:
                r["nutrition"] = nut; n += 1
    return t, d, n


def main():
    p = ROOT / sys.argv[1]
    rows = json.loads(p.read_text(encoding="utf-8"))
    t, d, n = asyncio.run(enrich(rows))
    p.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    print(f"{len(rows)} recipes: {t} got estimated times, {d} got a description, {n} got nutrition ({sum(1 for r in rows if not r.get("nutrition"))} without).")


if __name__ == "__main__":
    main()
