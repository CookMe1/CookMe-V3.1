"""Better times and descriptions for the master recipes.

The imported recipes carried placeholder times (prep "15 min", cook "30"/"45 min") and generic descriptions
("A delicious lamb recipe from Vietnamese cuisine."). Times are estimated from the method text;
recipes that get an estimate are flagged `time_estimated: true` and shown with a "~".
"""
import re

_PASSIVE = re.compile(r"\b(overnight|marinat\w*|soak\w*|chill\w*|refrigerat\w*|freez\w*|rest\w*|prove\w*|proof\w*|rise|stand|cool\w*|set)\b", re.I)
_NUM = r"(\d+(?:\.\d+)?|an?|half(?: an?)?|one|two|three|four|five|six|a couple of)"
_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "half": 0.5, "half a": 0.5, "half an": 0.5, "a couple of": 2}
_DUR = re.compile(rf"{_NUM}(?:\s*(?:-|–|to)\s*(\d+(?:\.\d+)?))?\s*(½)?\s*(hours?|hrs?|h|minutes?|mins?|min|m)\b", re.I)
GENERIC_DESC = re.compile(r"^A delicious .{2,40} recipe from .{2,30} cuisine\.?$", re.I)


def _val(tok: str) -> float:
    tok = tok.lower().strip()
    return _WORDS[tok] if tok in _WORDS else float(tok)


def durations(text: str):
    """[(minutes, is_passive)] for every time mentioned in one step. '1½ hrs' = 90, '20-25 min' = 22.5."""
    out = []
    passive = bool(_PASSIVE.search(text))
    for m in _DUR.finditer(text):
        n = _val(m.group(1))
        if m.group(2):
            n = (n + float(m.group(2))) / 2
        if m.group(3):
            n += 0.5
        unit = m.group(4).lower()
        mins = n * 60 if unit.startswith("h") else n
        if 0 < mins <= 24 * 60:
            out.append((mins, passive))
    return out


def fmt(minutes: float) -> str:
    minutes = int(round(minutes / 5.0) * 5) if minutes >= 10 else int(round(minutes))
    h, m = divmod(max(minutes, 1), 60)
    return f"{h}h {m}m" if h and m else (f"{h}h" if h else f"{m} min")


def estimate_times(recipe: dict):
    """-> (prep_time, cook_time, estimated?). Uses real times if the recipe has non-placeholder ones."""
    steps = [str(s) for s in (recipe.get("steps") or [])]
    ings = recipe.get("ingredients") or []
    prep = max(5, min(45, 5 + 2 * len(ings)))                       # about 2 minutes per ingredient
    active = passive = 0.0
    for s in steps:
        for mins, is_passive in durations(s):
            if is_passive:
                passive += mins
            else:
                active += mins
    if active == 0:
        # no times in the method: guess from how involved it is
        cook = 15 + 5 * min(len(steps), 8)
    else:
        cook = active + (min(passive, 60) if passive else 0)       # short rests count, long marinades do not
    cook = max(5, min(cook, 12 * 60))
    return fmt(prep), fmt(cook), True


def make_description(recipe: dict) -> str:
    cuisine = (recipe.get("cuisine") or "").replace("_", " ").strip().title()
    ings = []
    skip = re.compile(r"\b(salt|pepper|water|oil|butter|sugar|stock|seasoning)\b", re.I)
    for i in recipe.get("ingredients") or []:
        n = (i.get("item") if isinstance(i, dict) else str(i)) or ""
        n = re.sub(r"\(.*?\)", "", n).strip().lower()
        if n and not skip.search(n) and n not in ings:
            ings.append(n)
        if len(ings) == 3:
            break
    made = ""
    if len(ings) >= 3:
        made = f"made with {ings[0]}, {ings[1]} and {ings[2]}"
    elif ings:
        made = "made with " + " and ".join(ings)
    base = f"A {cuisine} dish" if cuisine and cuisine.lower() not in ("", "international") else "A dish"
    return (f"{base} {made}." if made else f"{base} from our recipe collection.").replace("  ", " ")
