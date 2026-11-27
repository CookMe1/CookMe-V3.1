#!/usr/bin/env python3
"""Clean up and modernise staged recipes that came from old cookbooks or institutional manuals, without changing the recipe.

  python3 scripts/modernise_old.py data/staging/open_new2.json [--held data/staging/open_new2_held.json]

What it does (wording only; quantities and method stay the same):
  - steps: drops page/index lines, manual codes ("O 002 00", "DO NOT COOK") and "see Recipe Notes" pointers; number words become digits
    ("twenty-four hours" -> "24 hours"); old words become today's ("catsup" -> "ketchup", "teaspoonful" -> "teaspoon", "take from the fire"
    -> "take off the heat", "quick oven" -> "hot oven 200 C"); every step starts with a capital and ends with a full stop.
  - ingredients: fixes lines where the text ran together ("sweet butter and two cups"), and adds ingredients that were only named in the
    method ("1 cup of sugar", "2 tablespoonfuls of brandy") with metric amounts.
  - recipes that still cannot stand alone (they point at another recipe number, or the method names a batch size that doesn't match the
    scaled ingredients) are marked needs_review and kept out.
  - recipes that were held for being too short get a second look with the repaired lists; the ones that pass come back.
Safe to run twice."""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"backend")); sys.path.insert(0, str(ROOT/"scripts"))
from amount_fixes import repair, coverage
from stage_wikibooks import score

NUM = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
       "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60}
UNITS_WORD = r"(?:tea|table|dessert)spoonfuls?|(?:tea|table|dessert)spoons?|cupfuls?|cups?|ounces?|ozs?\.?|pounds?|lbs?\.?|pints?|quarts?|gills?|minutes?|hours?|inch(?:es)?|eggs?|slices?|cloves?|sticks?|days?|seconds?|degrees"
FRAC = {"half": "1/2", "third": "1/3", "thirds": "1/3", "fourth": "1/4", "fourths": "3/4", "quarter": "1/4", "quarters": "3/4"}
CUP_ML = {"cup": 240, "tbsp": 15, "tsp": 5, "pint": 475, "quart": 950, "gill": 150}
UNIT_NORM = [(r"\b(tea)spoonful(s?)\b", r"teaspoon\2"), (r"\bdessert-?spoonful(s?)\b", r"dessertspoon\1"), (r"\b(table)spoonful(s?)\b", r"tablespoon\2"),
             (r"\bcupful(s?)\b", r"cup\1"), (r"\bteacupful(s?)\b", r"teacup\1"), (r"\btea-spoon(s?)\b", r"teaspoon\1"), (r"\btable-spoon(s?)\b", r"tablespoon\1"), (r"\bbaking-powder\b", "baking powder"),
             (r"\bbread-crumbs\b", "breadcrumbs"), (r"\bsauce-pan\b", "saucepan"), (r"\bto-day\b", "today")]
WORDS = [  # (pattern, replacement) in order
    (r"\bcatsup\b", "ketchup"), (r"\bCatsup\b", "Ketchup"),
    (r"\b(?:take|remove|lift|set)(\s+\w+){0,2}\s+(?:from|off)\s+the\s+(?:fire|range)\b", None),   # handled below
    (r"\bgranite(?:ware)? (sauce ?pan|kettle|pan|pot)\b", r"\1"), (r"\bspider\b", "frying pan"), (r"\bchafing dish\b", "pan"),
    (r"\bquick oven\b", "hot oven (200°C / 400°F)"), (r"\bmoderately hot oven\b", "hot oven (200°C / 400°F)"), (r"\bhot oven\b(?! \()", "hot oven (220°C / 425°F)"),
    (r"\bmoderate oven\b", "moderate oven (180°C / 350°F)"), (r"\bslow oven\b", "low oven (150°C / 300°F)"),
    (r"\bon the (?:fire|range)\b", "on the heat"), (r"\bover the fire\b", "over the heat"), (r"\bback on the fire\b", "back on the heat"),
    (r"\bset (?:it )?back on the (?:fire|range)\b", "return to the heat"), (r"\bturn(?:ed)? on the range\b", "put on the hob"),
    (r"\b(\d+) gills?\b", lambda m: f"{int(m.group(1)) * 150} ml"), (r"\bone gill\b", "150 ml"),
    (r"\bwineglass(?:ful)?\b", "125 ml"), (r"\bwine-?glass(?:ful)?\b", "125 ml"),
]
JUNK_STEP = [r"^[A-Z]\s?\d{3}\s?\d{2}\.?$", r"^DO NOT COOK\.?$", r"^DO NOT [A-Z ]+\.?$", r"\bPAGE\b", r"^CCP\b.*", r"^NOTE:?$", r"^See page \d+\.?$",
             r"^Recipe No\.?$", r"^\W*\d+\W*$", r"^Illustration\b.*", r"^FIG\.? ?\d+.*", r"^\(?Continued\)?\.?$"]
NOTE_PTR = re.compile(r"\s*\((?:see|See) (?:Recipe )?Notes?[^)]*\)|\s*\((?:see|See) [^)]*?(?:Recipe Notes|Notes)[^)]*\)|\s*See Recipe Notes\.?", re.I)
RECIPE_REF = re.compile(r"\brecipe(?:s)? No\b|\bRecipe # ?\w+|\bsee recipe\b|\bprepare \d+ recipes?\b", re.I)
BATCH = re.compile(r"\b(?:each|per|every) (?:ungreased |greased |lightly greased |lightly sprayed |large |medium |small |baking |steam table |bun |sheet |loaf )*(?:pan|portion|tray|sheet)\b[^.]*\d{2,}|\b\d{2,} (?:steaks|portions|pieces|patties|cutlets|servings)\b", re.I)


FOODS = set("""chicken beef veal lamb mutton pork ham bacon sausage turkey duck goose rabbit hare venison liver kidney tongue fish salmon tuna cod haddock herring sardine anchovy oyster oysters clam crab lobster shrimp prawn scallop scallops
egg eggs cheese cream milk butter potato potatoes onion onions tomato tomatoes carrot carrots cabbage celery mushroom mushrooms spinach peas beans lentils rice noodles macaroni spaghetti bread apple apples pear pears peach peaches lemon lemons orange oranges banana bananas
cherries strawberries raspberries cranberries grapes pineapple coconut almonds walnuts peanuts pecans chocolate cocoa honey molasses pumpkin squash corn turnip turnips beets parsnips cauliflower asparagus cucumber cucumbers peppers""".split())


def missing_foods(r):
    have = " ".join(i.get("item", "").lower() for i in r["ingredients"]) + " " + r["title"].lower()
    text = " ".join(r["steps"]).lower()
    out = set()
    for w in FOODS:
        if re.search(r"\b" + w + r"\b", text) and not re.search(r"\b" + w[:-1] if w.endswith("s") else r"\b" + w, have):
            base = w.rstrip("s")
            if base not in have: out.add(w)
    return out


def relaxed_ok(r):
    """Short recipes are real recipes (taffy, sauces, seasonings). They pass when the list covers every food the method mentions."""
    ing = r["ingredients"]
    if len(ing) < 2 or coverage(ing) < 0.7: return False
    steps = r["steps"]
    if not steps or sum(len(x) for x in steps) < 40: return False
    if len(steps) == 1 and not COOK.search(steps[0]): return False           # only a list, no method
    return not missing_foods(r)


def words_to_digits(s):
    def tok(w):
        w = w.lower()
        return NUM.get(w)
    def compound(m):                                    # twenty-four, thirty five
        a, b = TENS[m.group(1).lower()], NUM[m.group(2).lower()]
        return str(a + b)
    s = re.sub(r"\b(twenty|thirty|forty|fifty|sixty)[- ](one|two|three|four|five|six|seven|eight|nine)\b(?=\s+(?:" + UNITS_WORD + r"))", compound, s, flags=re.I)
    # fractions with a unit after: "one-fourth teaspoon", "one half cup", "two-thirds cup", "a quarter pound"
    def frac(m):
        n = tok(m.group(1)); f = FRAC[m.group(2).lower()]
        if n is None: return m.group(0)
        if f == "1/2" and n == 1: return "1/2"
        if f in ("1/3", "1/4") and n > 1: top = n; return f"{top}/{f.split('/')[1]}"
        if f == "3/4" and n == 3: return "3/4"
        return f if n == 1 else m.group(0)
    s = re.sub(r"\b(a|an|one|two|three)[- ](half|thirds?|fourths?|quarters?)\b(?=\s+(?:of\s+)?(?:an?\s+)?(?:" + UNITS_WORD + r"|[a-z]))", frac, s, flags=re.I)
    s = re.sub(r"\bhalf an? (hour|pound|cup|teaspoon|tablespoon|pint|inch)\b", lambda m: "1/2 " + m.group(1) if m.group(1) != "hour" else "30 minutes", s, flags=re.I)
    s = re.sub(r"\ba half hour\b", "30 minutes", s, flags=re.I)
    # plain number words before a unit/time word: "three eggs", "ten minutes", "one cup"
    def plain(m):
        n = tok(m.group(1))
        if m.group(1).lower() in ("a", "an"): return m.group(0)       # keep "a cup" natural
        return f"{n} {m.group(2)}"
    s = re.sub(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|sixty)\s+(" + UNITS_WORD + r")\b", plain, s, flags=re.I)
    return s


def tidy_step(s):
    s = NOTE_PTR.sub("", s)
    for pat, rep in UNIT_NORM: s = re.sub(pat, rep, s, flags=re.I)
    for pat, rep in WORDS:
        if rep is None:
            s = re.sub(pat, lambda m: re.sub(r"\s+(?:from|off) the (?:fire|range)", " off the heat", m.group(0)), s, flags=re.I); continue
        s = re.sub(pat, rep, s)
    s = words_to_digits(s)
    s = re.sub(r"\b(a scant|a half-?|half a|scant|1/\d|1|a|an)[ -](teaspoon|tablespoon|cup|pint|quart|pound|ounce|dessertspoon)s\b", r"\1 \2", s, flags=re.I)
    s = re.sub(r"\b(\d/\d|\d) (a )?(teaspoon|tablespoon|cup|pint|quart|pound|ounce)s\b(?=[^.]*$)", lambda m: m.group(0) if m.group(1) in ("2","3","4","5","6","7","8","9") else m.group(0)[:-1], s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\s+([,.;:])", r"\1", s)
    if s and s[0].islower(): s = s[0].upper() + s[1:]
    if s and s[-1] not in ".!?": s += "."
    return s


def tidy_item(it):
    it = re.sub(r"\bcatsup\b", "ketchup", it, flags=re.I)
    for pat, rep in UNIT_NORM: it = re.sub(pat, rep, it, flags=re.I)
    return it


def is_junk(s):
    t = s.strip()
    if not t: return True
    if any(re.search(p, t) for p in JUNK_STEP): return True
    if len(re.findall(r"\b\d{2,3}\b", t)) >= 4 and len(t) < 160 and not re.search(r"\b(minutes?|hours?|°|degrees|ml|g)\b", t): return True   # index lines
    return False


QTY = r"(?P<q>\d+(?:\s?\d/\d)?|\d/\d|an?|one|two|three|four|five|six|seven|eight|nine|ten|twelve)(?:[- ](?P<f>half|third|fourth|quarter)s?)?"
UNIT = r"(?P<u>cups?|cupfuls?|(?:tea|table|dessert)spoon(?:ful)?s?|tsp\.?|tbsp\.?|ounces?|oz\.?|pounds?|lbs?\.?|pints?|quarts?|gills?)"
EXTRA = re.compile(QTY + r"\s+" + UNIT + r"\s+(?:of\s+)?(?P<item>[a-z][a-z\-]*(?:\s[a-z][a-z\-]*){0,2}?)(?=\s*(?:[,.;:]|\band\b|\bwith\b|\bto\b|\bin\b|\bat\b|\buntil\b|\btill\b|\bor\b|\bfor\b|\bthen\b|\bmixed\b|\bchopped\b|\bgrated\b|\bsifted\b|\bwell\b|\bfine\b|$))", re.I)
STOPITEMS = {"measure", "the", "a", "an", "it", "them", "each", "and", "water", "boiling", "hot", "cold", "more", "this", "that", "these", "those", "same", "pan", "dish", "bowl", "oven", "heat", "fire", "time"}
HEAD_SKIP = {"fresh", "ground", "large", "small", "fine", "finely", "chopped", "grated", "granulated", "sifted", "powdered", "boiling", "good", "sweet", "dry", "light", "dark", "brown", "white"}


def num_val(q, f):
    q = q.strip().lower()
    if re.fullmatch(r"\d+ \d/\d", q): a, b = q.split(); n, d = b.split("/"); v = int(a) + int(n) / int(d)
    elif re.fullmatch(r"\d/\d", q): n, d = q.split("/"); v = int(n) / int(d)
    elif q.isdigit(): v = int(q)
    else: v = NUM.get(q, 1)
    if f:
        d = {"half": 2, "third": 3, "fourth": 4, "quarter": 4}[f.lower()]
        v = (v / d) if q in NUM or q.isdigit() else v
    return v


def frac_str(v):
    whole = int(v); rest = v - whole
    for n, d in ((1, 4), (1, 3), (1, 2), (2, 3), (3, 4)):
        if abs(rest - n / d) < 0.04: return (f"{whole} " if whole else "") + f"{n}/{d}"
    return str(round(v, 1)).rstrip("0").rstrip(".") if rest else str(whole)


def metric(v, unit):
    u = unit.lower().rstrip(".")
    if u.startswith("cup"): return f"{round(v * 240 / 5) * 5:g} ml ({frac_str(v)} cup{'s' if v > 1 else ''})"
    if u.startswith(("tea", "tsp")): return f"{frac_str(v)} tsp"
    if u.startswith(("table", "tbsp")): return f"{frac_str(v)} tbsp"
    if u.startswith("dessert"): return f"{frac_str(v * 2)} tsp"
    if u.startswith(("ounce", "oz")): return f"{round(v * 28)} g ({frac_str(v)} oz)"
    if u.startswith(("pound", "lb")): return f"{round(v * 450 / 5) * 5} g ({frac_str(v)} lb)"
    if u.startswith("pint"): return f"{round(v * 475 / 5) * 5} ml ({frac_str(v)} pint)"
    if u.startswith("quart"): return f"{round(v * 950 / 10) * 10} ml ({frac_str(v)} quart)"
    if u.startswith("gill"): return f"{round(v * 150)} ml"
    return f"{frac_str(v)} {unit}"


def head(item):
    w = [x for x in re.findall(r"[a-z]+", item.lower()) if x not in HEAD_SKIP]
    return w[-1].rstrip("s") if w else item.lower()


def garbled(item):
    return bool(re.search(r"\b(and|with|in|a|the|of|to)$", item.strip(), re.I) or re.search(r"\b(and|with) (an?|\w+) (cups?|teaspoons?|tablespoons?|ounces?|pounds?)\b", item, re.I)
                or re.search(r"\b(in a|in the|into a)\b", item, re.I))


def fix_items(r):
    """Cut ingredient names that ran on into the next one ('sweet butter and two cups' -> 'sweet butter')."""
    changed = False
    for ing in r["ingredients"]:
        it = ing.get("item", "")
        new = re.split(r"\s+(?:and|with)\s+(?:an?|\d+|one|two|three|four|five|six|a half)\b|\s+(?:in|into) (?:a|the)\b", it, maxsplit=1, flags=re.I)[0]
        new = re.sub(r"\s+(?:and|with|in|a|the|of|to)$", "", new, flags=re.I).strip(" ,")
        if new and new != it: ing["item"] = new; changed = True
    return changed


def add_from_steps(r):
    """Add ingredients that are only named in the method."""
    have = {head(i.get("item", "")) for i in r["ingredients"]}
    added = []
    for s in r["steps"]:
        for m in EXTRA.finditer(s):
            item = m.group("item").strip().lower()
            first = item.split()[0]
            if first in STOPITEMS or item in STOPITEMS: continue
            h = head(item)
            if h in have or len(h) < 3: continue
            v = num_val(m.group("q"), m.group("f"))
            if v <= 0 or v > 40: continue
            have.add(h); added.append({"amount": metric(v, m.group("u")), "item": item})
    if added: r["ingredients"].extend(added)
    return len(added)


COOK = re.compile(r"\b(mix|add|stir|cook|boil|put|melt|bake|beat|simmer|pour|place|take|wash|cut|chop|fry|heat|serve|let|make|rub|roll|sift|dissolve|drain|season|bring)\b", re.I)
PART = re.compile(r"^(?:" + QTY + r"\s+" + UNIT + r"\s+(?:of\s+)?)?(?P<item>[A-Za-z][A-Za-z\- ]{2,40}?)(?:\s+to taste)?$", re.I)


def ingredient_list_step(r):
    """A step that is only a list of quantities ('1 cup of sugar, 2 tablespoons of brandy, a pinch of salt.') becomes ingredients."""
    have = {head(i.get("item", "")) for i in r["ingredients"]}
    keep, added = [], 0
    for s in r["steps"]:
        body = s.rstrip(".")
        if len(EXTRA.findall(body)) + len(re.findall(QTY + r"\s+" + UNIT, body, re.I)) >= 2 and body.count(",") >= 2 and not COOK.search(body) and len(body) < 400:
            parts = [x.strip() for x in re.split(r",\s*(?:and\s+)?|\s+and\s+(?=(?:\d|an?\s|one|two|three|four|five|six|a pinch|the same))", body) if x.strip()]
            new = []; ok = True
            for x in parts:
                x = re.sub(r"^(?:and|also)\s+", "", x, flags=re.I)
                m = PART.match(x)
                if not m: ok = False; break
                item = re.sub(r"^(?:the same of|a pinch of|a dash of)\s+", "", m.group("item").strip().lower())
                if not item or item.split()[0] in {"the", "a", "an", "it", "them", "each", "and", "this", "that"}: ok = False; break
                size = re.match(r"^(.*?)\s+the size of (an? \w+|\w+)$", item)
                if size: item = size.group(1)
                amt = metric(num_val(m.group("q"), m.group("f")), m.group("u")) if m.group("q") else (f"size of {size.group(2)}" if size else "to taste" if re.search(r"to taste$", x, re.I) else "")
                new.append((head(item), {"amount": amt, "item": item}))
            if ok and new:
                for h, ing in new:
                    if h not in have: have.add(h); r["ingredients"].append(ing); added += 1
                continue                                   # the step is dropped: its content is now in the ingredient list
        keep.append(s)
    r["steps"] = keep
    return added


def modern_title(t):
    t = re.sub(r"\bCatsup\b", "Ketchup", t); t = re.sub(r"’S\b", "’s", t); t = re.sub(r"'S\b", "'s", t)
    return t


def strip_suffix_title(r, taken):
    t = r["title"]
    m = re.match(r"^(.*\S) (sauce|snack|drink|dessert|side|main|soup|salad|bread|breakfast)$", t)
    if m and m.group(1)[:1].isupper() and m.group(1).lower() not in taken:
        r["title"] = m.group(1); taken.add(m.group(1).lower())


def process(r, taken):
    notes = []
    if fix_items(r): notes.append("ingredients")
    old_steps = list(r["steps"])
    steps = []
    for s in old_steps:
        if is_junk(s): continue
        t = tidy_step(s)
        if t and not is_junk(t): steps.append(t)
    if steps != old_steps: notes.append("steps")
    r["steps"] = steps
    for ing in r["ingredients"]:
        mj = re.match(r"^(?:the )?juice of (\d+(?:/\d+)?|an?|one|half an?) ?(\w+)$", str(ing.get("item", "")), re.I)
        if mj and not str(ing.get("amount", "")).strip():
            q = mj.group(1).lower(); ing["amount"] = {"a": "1", "an": "1", "one": "1", "half a": "1/2", "half an": "1/2"}.get(q, q); ing["item"] = mj.group(2) + ", juiced"
        ing["item"] = tidy_item(ing.get("item", "")); ing["amount"] = re.sub(r"\bteacupful\b", "teacup", str(ing.get("amount", "")))
    if ingredient_list_step(r): notes.append("ingredient list step")
    if len(r["ingredients"]) < 4 or any(garbled(i.get("item", "")) for i in r["ingredients"]):
        if add_from_steps(r): notes.append("ingredients from method")
    r["ingredients"] = [repair(i) for i in r["ingredients"]]
    r["title"] = modern_title(r["title"]); strip_suffix_title(r, taken)
    # drop exact duplicate ingredients that wording fixes can create (tomato catsup + tomato ketchup)
    seen = set(); uniq = []
    for i in r["ingredients"]:
        k = i.get("item", "").lower()
        if k in seen: continue
        seen.add(k); uniq.append(i)
    r["ingredients"] = uniq
    text = " ".join(r["steps"])
    reason = None
    if RECIPE_REF.search(text) or any(RECIPE_REF.search(i.get("item", "") + " " + i.get("amount", "")) for i in r["ingredients"]):
        reason = "points at another recipe"
    elif BATCH.search(text):
        reason = "method names a large-batch size"
    return notes, reason


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    f = Path(args[0]); data = json.load(open(f, encoding="utf-8"))
    held_path = Path(sys.argv[sys.argv.index("--held") + 1]) if "--held" in sys.argv else None
    held = json.load(open(held_path, encoding="utf-8")) if held_path and held_path.exists() else []
    # NHS recipes were ruled out: remove wherever they are
    drop = lambda r: "nhs.uk" in str(r.get("source_url", "")) or "Open Government" in str(r.get("source_license", ""))
    n_nhs = sum(drop(r) for r in data + held); data = [r for r in data if not drop(r)]; held = [r for r in held if not drop(r)]
    taken = {r["title"].lower() for r in data}
    stats = {"fixed": 0, "back": 0, "still_held": 0, "to_review": 0}
    old_src = lambda r: any(k in str(r.get("source_url", "")) for k in ("gutenberg", "archive.org", "fadedpage"))
    out = []
    for r in data:
        if old_src(r) or "TM 10-412" in str(r.get("source_attribution", "")):
            notes, reason = process(r, taken)
            if notes: stats["fixed"] += 1
            if reason: r["needs_review"] = True; r["review_reason"] = reason; stats["to_review"] += 1
            r["modernised"] = True
        else:                                               # modern sources: only tidy the "see Recipe Notes" pointers
            r["steps"] = [NOTE_PTR.sub("", s).strip() for s in r["steps"]]
        out.append(r)
    still = []
    for r in held:
        if old_src(r): notes, reason = process(r, taken)
        else: reason = None
        flags, _ = score(r)
        r["modernised"] = True
        if flags and not reason and old_src(r) and relaxed_ok(r) and not any(f == "amounts missing" for f in flags): flags = []
        if flags or reason:
            r["held_because"] = "; ".join(flags + ([reason] if reason else [])); still.append(r); stats["still_held"] += 1
        else:
            r.pop("held_because", None); out.append(r); stats["back"] += 1
    json.dump(out, open(f, "w", encoding="utf-8"), ensure_ascii=False)
    if held_path: json.dump(still, open(held_path, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"NHS removed {n_nhs}; tidied {stats['fixed']}; marked needs_review {stats['to_review']}; "
          f"brought back from held {stats['back']}; still held {stats['still_held']}; total now {len(out)}")


if __name__ == "__main__":
    main()
