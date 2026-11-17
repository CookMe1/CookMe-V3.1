"""Tidy up recipe steps and ingredient amounts that came out of scraped/imported sources messy.
Pure functions, no database, no AI. Used by scripts/clean_recipes.py."""
import re

_LABEL = re.compile(r"^\s*(step\s*\d+|\d+[.)]?|▢|pro\s*tips?:?|tips?:?|notes?:?|instructions?:?|directions?:?|method:?|preparation:?)\s*$", re.I)
_PREFIX = re.compile(r"^\s*(step\s*\d+\s*[:.\-–)]?\s*|\d+\s*[.)]\s+)", re.I)

_FRACTIONS = {0.25: "1/4", 0.5: "1/2", 0.75: "3/4", 0.33: "1/3", 0.67: "2/3", 0.125: "1/8", 0.2: "1/5"}
_QUANTITY_WORDS = {"pinch", "handful", "to taste", "dash", "splash", "some", "few", "as needed", "a little", "bunch",
                   "sprig", "sprigs", "drizzle", "knob", "sprinkle", "large", "small", "medium", "a few", "a handful",
                   "for serving", "to serve", "for frying", "for garnish", "optional", "plenty", "lots"}
_PREP_WORDS = {"chopped", "sliced", "diced", "minced", "grated", "crushed", "melted", "softened", "beaten", "ground",
               "peeled", "shredded", "cubed", "halved", "mashed", "toasted", "cooked", "drained", "rinsed"}


def split_long_step(text, target=220):
    """One big paragraph -> several steps, grouping whole sentences up to ~target characters."""
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text)
    out, cur = [], ""
    for sent in sentences:
        if cur and len(cur) + len(sent) + 1 > target:
            out.append(cur); cur = sent
        else:
            cur = f"{cur} {sent}".strip()
    if cur: out.append(cur)
    return out


def clean_steps(steps):
    out = []
    for s in steps or []:
        if not isinstance(s, str): continue
        s = re.sub(r"<[^>]+>", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        if not s or _LABEL.match(s) or not re.search(r"[A-Za-z]", s):
            continue
        s = _PREFIX.sub("", s).strip()
        if not s or not re.search(r"[A-Za-z]", s):
            continue
        if out and out[-1].lower() == s.lower():
            continue
        out.append(s)
    # a whole method written as one or two huge blocks: break it into readable steps
    limit = 180 if len(out) < 3 else 400
    if len(out) < 4 and any(len(x) > limit for x in out):
        out = [piece for x in out for piece in (split_long_step(x, 160) if len(x) > limit else [x])]
    return out


def _tidy_number(m):
    v = float(m.group(0))
    if v == int(v): return str(int(v))
    frac = _FRACTIONS.get(round(v, 2))
    if frac: return frac
    whole = int(v); rest = round(v - whole, 2)
    if whole and rest in _FRACTIONS: return f"{whole} {_FRACTIONS[rest]}"
    return f"{v:g}"


def clean_amount(amount):
    a = re.sub(r"\s+", " ", str(amount or "")).strip()
    return re.sub(r"(?<![\d/.])\d+\.\d+(?=\s|$)", _tidy_number, a) if a else ""


def clean_ingredient(ing):
    item = re.sub(r"\s+", " ", str(ing.get("item") or "")).strip()
    amount = clean_amount(ing.get("amount"))
    low = amount.lower()
    # an "amount" with no number that is really a description ("White" + "Rice", "Chopped" + "Onion")
    if amount and not re.search(r"\d", amount) and low not in _QUANTITY_WORDS and re.fullmatch(r"[A-Za-z\-]+( [A-Za-z\-]+)?", amount):
        if low in _PREP_WORDS: item, amount = f"{item}, {low}", ""
        else: item, amount = f"{amount} {item}", ""
    out = dict(ing); out["item"] = item; out["amount"] = amount
    return out


def clean_recipe(r):
    """Returns a cleaned copy of the recipe dict."""
    r = dict(r)
    r["steps"] = clean_steps(r.get("steps"))
    r["ingredients"] = [clean_ingredient(i) for i in (r.get("ingredients") or []) if str(i.get("item") or "").strip()]
    return r


def is_cookable(r):
    """A recipe is worth showing if there are enough ingredients and a real method."""
    steps = r.get("steps") or []
    return len(r.get("ingredients") or []) >= 3 and len(steps) >= 2 and sum(len(s) for s in steps) >= 80
