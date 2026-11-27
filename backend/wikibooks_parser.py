"""Turn a Wikibooks Cookbook page (wikitext) into a CookMe recipe dict. Pure functions, no network.
Wikibooks Cookbook text is CC BY-SA 4.0: every recipe keeps its source_url, licence and credit line."""
import hashlib
import re
from wikibooks_categories import from_categories

LICENSE = "CC BY-SA 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
UNITS = (r"cups?|c\.|tbsp\.?|tablespoons?|tbs\.?|tsp\.?|teaspoons?|g|grams?|kg|kilograms?|ml|milliliters?|millilitres?|l|liters?|litres?|oz\.?|ounces?|"
         r"lbs?\.?|pounds?|pinch(?:es)?|dash(?:es)?|cloves?|slices?|cans?|packages?|packets?|sticks?|pieces?|bunch(?:es)?|sprigs?|heads?|stalks?|handfuls?|pints?|quarts?|gallons?|fl\.? oz\.?")
_NUM = r"(?:\d+\s+\d+/\d+|\d+/\d+|\d+(?:[.,]\d+)?|[½¼¾⅓⅔⅛])"
_AMOUNT = re.compile(rf"^\s*(?P<amt>{_NUM}(?:\s*(?:-|–|to)\s*{_NUM})?\s*(?:(?:{UNITS})(?![a-z]))?(?:\s*\([^)]*\))?)\s+(?P<item>.+)$", re.I)


def clean_markup(text: str) -> str:
    t = text or ""
    t = re.sub(r"<ref[^>]*>.*?</ref>", "", t, flags=re.S)
    t = re.sub(r"<ref[^>]*/>", "", t)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    for _ in range(3):                                  # nested templates
        t = re.sub(r"\{\{[^{}]*\}\}", "", t)
    t = re.sub(r"\[\[(?:File|Image|Category):[^\]]*\]\]", "", t, flags=re.I)
    t = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", t)  # [[Cookbook:Flour|flour]] -> flour
    t = re.sub(r"\[\[([^\]]*)\]\]", lambda m: m.group(1).split(":")[-1], t)
    t = re.sub(r"\[https?://\S+\s+([^\]]+)\]", r"\1", t)
    t = re.sub(r"\[https?://\S+\]", "", t)
    t = re.sub(r"'{2,5}", "", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = t.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", t).strip(" *#:;")


def _template_params(wikitext: str, name: str) -> dict:
    m = re.search(r"\{\{\s*" + name + r"\s*\|(.*?)\}\}", wikitext, flags=re.I | re.S)
    out = {}
    if m:
        body = re.sub(r"\[\[[^\]]*\]\]", lambda x: x.group(0).replace("|", "\u0001"), m.group(1))
        for part in body.split("|"):
            if "=" in part:
                k, v = part.split("=", 1)
                out[k.strip().lower()] = v.replace("\u0001", "|").strip()
    return out


def _section(wikitext: str, names) -> str:
    pat = r"^==+\s*(?:" + "|".join(names) + r")\s*==+\s*$(.*?)(?=^==[^=]|\Z)"
    m = re.search(pat, wikitext, flags=re.I | re.M | re.S)
    return m.group(1) if m else ""


def split_ingredient(line: str) -> dict:
    line = clean_markup(line)
    m = _AMOUNT.match(line)
    if m:
        return {"item": m.group("item").strip(" ,"), "amount": re.sub(r"\s+", " ", m.group("amt")).strip()}
    return {"item": line, "amount": ""}


def _minutes(text: str):
    t = (text or "").lower()
    total = 0
    for n, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m)\b", t):
        total += float(n) * (60 if unit.startswith("h") else 1)
    return int(total) or None


def _time_text(text: str) -> str:
    mins = _minutes(text)
    if not mins:
        return clean_markup(text)[:40]
    return f"{mins // 60} hr {mins % 60} min" if mins >= 60 and mins % 60 else (f"{mins // 60} hr" if mins >= 60 else f"{mins} min")


def recipe_id(title: str) -> str:
    return "recipe_" + hashlib.sha1(("wikibooks:" + title).encode()).hexdigest()[:12]


def parse_recipe(title: str, wikitext: str):
    """Returns a recipe dict, or None if the page is not a recipe (no ingredients or no method)."""
    if not wikitext or wikitext.lstrip().lower().startswith("#redirect"):
        return None
    name = re.sub(r"^Cookbook:", "", title).strip()
    summary = _template_params(wikitext, "recipesummary") or _template_params(wikitext, "recipe summary")
    ing_lines = [l for l in _section(wikitext, ["Ingredients"]).split("\n") if l.strip().startswith(("*", "#", ":")) or re.match(r"^\s*\d", l)]
    ingredients = [split_ingredient(re.sub(r"^[\s*#:]+", "", l)) for l in ing_lines]
    ingredients = [i for i in ingredients if i["item"] and len(i["item"]) > 1]
    method = _section(wikitext, ["Procedure", "Directions", "Instructions", "Method", "Preparation"])
    steps = [clean_markup(re.sub(r"^[\s*#:]+", "", l)) for l in method.split("\n") if l.strip().startswith(("#", "*", ":")) or re.match(r"^\s*\d+[.)]", l)]
    steps = [re.sub(r"^\d+[.)]\s*", "", s) for s in steps if len(s) > 3]
    if not steps:                                          # method written as plain paragraphs
        steps = [clean_markup(p) for p in re.split(r"\n\s*\n", method) if len(clean_markup(p)) > 20]
    if len(ingredients) < 2 or not steps:
        return None
    category = clean_markup(summary.get("category", ""))
    cuisine = re.sub(r"\s*(cuisine|recipes?)\s*$", "", category, flags=re.I).strip().lower() if re.search(r"cuisine", category, re.I) else ""
    diff = re.search(r"\d", summary.get("difficulty", ""))
    difficulty = {1: "Easy", 2: "Easy", 3: "Medium", 4: "Hard", 5: "Hard"}.get(int(diff.group(0)) if diff else 0, "Medium")
    serv = re.search(r"\d+", summary.get("servings", ""))
    intro = re.split(r"^==", wikitext, maxsplit=1, flags=re.M)[0]
    intro = re.sub(r"\{\{[^{}]*\}\}", "", intro)
    paras = [clean_markup(p) for p in re.split(r"\n\s*\n", intro) if len(clean_markup(p)) > 40]
    desc = (re.split(r"(?<=[.!?])\s", paras[0])[0] if paras else "")[:200]
    url = "https://en.wikibooks.org/wiki/" + title.replace(" ", "_")
    cats = from_categories(re.findall(r"\[\[Category:([^\]|]+)", wikitext))
    if cats["exclude"]:
        return None
    cuisine = cuisine or cats["cuisine"]
    return {
        "recipe_id": recipe_id(title), "title": name, "description": desc, "image": None,
        "prep_time": "", "cook_time": _time_text(summary.get("time", "")), "servings": int(serv.group(0)) if serv else 4, "servings_stated": bool(serv),
        "difficulty": difficulty, "ingredients": ingredients, "steps": steps,
        "tags": sorted(set([t for t in [category.replace(" recipes", "")] if t and len(t) < 30] + cats["tags"])), "category": "dessert" if cats["dessert"] else "", "cuisine": cuisine,
        "source_url": url, "source_license": LICENSE, "source_history_url": url.replace("/wiki/", "/w/index.php?title=") + "&action=history",
        "user_id": "system_seeder", "likes_count": 0, "saves_count": 0, "favorited_by": [], "hidden_by": [], "gallery_images": [],
        "wikibooks_image": (re.search(r"(?:File|Image):([^|\]]+)", summary.get("image", "") or "") or [None, None])[1] if summary.get("image") else None,
    }
