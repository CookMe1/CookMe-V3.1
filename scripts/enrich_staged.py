#!/usr/bin/env python3
"""Finish Wikibooks recipes: servings, times, description and nutrition. Photos come from fill_images.py.
  python3 scripts/enrich_staged.py data/staging/wikibooks_approved.json
Servings: used as written when the Wikibooks page states them; otherwise worked out from the recipe's total calories
(about 550 kcal a serving for a main, 300 for a dessert or bake, 80 for a sauce or dip) and flagged servings_estimated.
Nutrition is per serving from the local USDA table. Anything that comes out implausible (under 30 kcal for a dish, or over 1,400 kcal a
serving, or too few ingredients matched) gets NO nutrition and needs_review = true, so nothing wrong reaches the app.
Times are estimated from the method unless the page gives them (flagged time_estimated). Safe to re-run."""
import asyncio, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
import master_enrich as e
from description_quality import description_is_weak
from nutrition_lookup import calculate_recipe_nutrition_free

SAUCE = re.compile(r"sauce|dressing|\bdip\b|marinade|\brub\b|spice|seasoning|syrup|stock|broth|spread|jam\b|jelly|relish|chutney|paste|mayonnaise|aioli|pickle|vinaigrette|gravy|salsa|glaze|butter\b|powder|mix\b", re.I)
SWEET = re.compile(r"cake|cookie|biscuit|brownie|pie\b|tart|pudding|muffin|bread|scone|pastry|cobbler|crumble|crisp|fudge|candy|ice cream|mousse|cheesecake|dessert|bar\b|bars\b|flapjack|macaron|doughnut|donut", re.I)
CUISINE_FIX = {"tanzanian": "african"}


SPECIAL_SAUCE = {"sauce", "dressing", "dip", "marinade", "spread", "syrup"}


def target_kcal(r):
    t = r.get("title", "")
    tags = {str(x).lower() for x in r.get("tags") or []}
    if "drink" in tags:
        return 150, 1, 12
    if tags & SPECIAL_SAUCE:
        return 80, 4, 24
    if "snack" in tags:
        return 200, 2, 16
    if r.get("category") == "dessert" or SWEET.search(t):
        return 300, 2, 16
    if SAUCE.search(t):
        return 80, 4, 16
    return 550, 2, 12


async def enrich(rows):
    st = {"times": 0, "desc": 0, "nutr": 0, "srv_est": 0, "review": 0}
    for r in rows:
        r["cuisine"] = CUISINE_FIX.get(r.get("cuisine"), r.get("cuisine"))
        for i in r.get("ingredients") or []:      # Wikibooks wording: '1 kg of round beef' -> amount '1 kg', item 'round beef'
            i["item"] = re.sub(r"^(?:of|a|an)\s+", "", str(i.get("item") or "").strip(), flags=re.I)
        # times
        real_cook = r.get("cook_time") if r.get("cook_time") and not r.get("time_estimated") else ""
        prep, cook, _ = e.estimate_times(r)
        r["prep_time"] = prep if not r.get("prep_time") or r.get("time_estimated") else r["prep_time"]
        r["cook_time"] = real_cook or cook
        r["time_estimated"] = True
        st["times"] += 1
        if description_is_weak(r.get("description"), r.get("title", "")):
            r["description"] = e.make_description(r); r["description_auto"] = True; st["desc"] += 1
        # servings + nutrition
        r.pop("nutrition", None); r.pop("needs_review", None)
        total = await calculate_recipe_nutrition_free(r.get("ingredients") or [], 1)
        if not total:
            if not r.get("servings_stated"): r["servings_estimated"] = True
            r["needs_review"] = True; st["review"] += 1
            continue
        if not r.get("servings_stated"):
            tgt, lo, hi = target_kcal(r)
            r["servings"] = max(lo, min(hi, round(total["calories"] / tgt)))
            r["servings_estimated"] = True; st["srv_est"] += 1
        n = max(1, int(r["servings"]))
        per = {k: (round(v / n) if k in ("calories", "sodium") else round(v / n, 1)) for k, v in total.items() if isinstance(v, (int, float)) and k != "calc_v"}
        per.update({"source": total.get("source", "usda"), "calc_v": total.get("calc_v", 3)})
        special = bool({str(x).lower() for x in r.get("tags") or []} & (SPECIAL_SAUCE | {"drink"}))
        if (0 if special else 30) <= per["calories"] <= 1400:
            r["nutrition"] = per; st["nutr"] += 1
        else:
            r["needs_review"] = True; st["review"] += 1
    return st


def main():
    p = ROOT / sys.argv[1]
    rows = json.loads(p.read_text(encoding="utf-8"))
    st = asyncio.run(enrich(rows))
    p.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    print(f"{len(rows)} recipes: times {st['times']}, descriptions {st['desc']}, servings worked out for {st['srv_est']}, "
          f"nutrition for {st['nutr']}, {st['review']} flagged needs_review (no nutrition shown).")


if __name__ == "__main__":
    main()
