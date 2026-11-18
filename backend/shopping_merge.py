"""Combine the ingredients of several recipes into one shopping list: same item -> one line, amounts added up."""
import re

from amounts import _number

_UNIT_WORDS = {"g", "kg", "ml", "l", "tsp", "tbsp", "cup", "cups", "oz", "lb", "clove", "cloves", "tin", "can", "bunch", "pinch", "slice", "slices"}
_STAPLES_SKIP = {"water", "ice", "salt", "pepper", "black pepper", "salt and pepper", "salt & pepper"}


def _name_key(name: str) -> str:
    n = re.sub(r"\(.*?\)", " ", name.lower())
    n = re.sub(r"[^a-z ]", " ", n)
    n = re.sub(r"\b(fresh|chopped|sliced|diced|finely|large|small|medium|to taste|optional)\b", " ", n)
    words = [w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in n.split()]
    return " ".join(words)


def _split_amount(amount: str):
    """('2 cups') -> (2.0, 'cup'); ('drizzle') -> (None, 'drizzle')."""
    text = (amount or "").strip().lower()
    if not text:
        return None, ""
    qty, text, end = _number(text)
    rest = text[end:] if qty is not None else text
    word = re.sub(r"[^a-z]", "", (rest.strip().split(" ") or [""])[0])
    word = {"cups": "cup", "cloves": "clove", "slices": "slice", "tablespoons": "tbsp", "tablespoon": "tbsp",
            "teaspoons": "tsp", "teaspoon": "tsp", "grams": "g", "gram": "g", "kilos": "kg", "tins": "tin", "cans": "can"}.get(word, word)
    return qty, (word if word in _UNIT_WORDS or qty is None else "")


def _fmt(q: float) -> str:
    return str(int(q)) if abs(q - round(q)) < 0.05 else f"{q:.1f}".rstrip("0").rstrip(".")


def merge_ingredients(ingredient_lists) -> list:
    """ingredient_lists: one list per recipe of {"item","amount"} dicts or strings. Returns [{"name","amount"}]."""
    merged = {}
    for ings in ingredient_lists:
        for ing in ings or []:
            name = (ing.get("item") or ing.get("name") or "") if isinstance(ing, dict) else str(ing)
            amount = (ing.get("amount") or "") if isinstance(ing, dict) else ""
            name = name.strip()
            key = _name_key(name)
            if not key or key in _STAPLES_SKIP:
                continue
            entry = merged.setdefault(key, {"name": name[:1].upper() + name[1:], "parts": []})
            entry["parts"].append(_split_amount(amount) + (amount.strip(),))
    out = []
    for entry in merged.values():
        by_unit, extras = {}, []
        for qty, unit, raw in entry["parts"]:
            if qty is None:
                if raw and raw.lower() not in extras:
                    extras.append(raw.lower())
            else:
                by_unit[unit] = by_unit.get(unit, 0) + qty
        pieces = [f"{_fmt(q)}{(' ' + u) if u and u not in ('g', 'kg', 'ml', 'l') else u}".strip() for u, q in by_unit.items()]
        out.append({"name": entry["name"], "amount": " + ".join(pieces + extras) or "1"})
    return out
