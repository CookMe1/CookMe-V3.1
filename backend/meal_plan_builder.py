"""Builds a 7-day meal plan from tagged recipes - no AI. Pure functions so they can be tested offline."""
import random
import re
from datetime import date, timedelta

from recipe_tagger import is_dessert

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SUPPORTED_DIETS = {"vegetarian", "vegan"}          # the only restrictions we can honour from tags
BREAKFAST_TAGS = {"breakfast", "brunch", "morning meal"}
BREAKFAST_WORDS = r"pancake|omelet|omelette|porridge|granola|oatmeal|waffle|french toast|scrambled|muesli|breakfast|crepe|shakshuka|eggs? benedict"
NOT_MAIN_TAGS = {"side dish", "side", "starter", "appetizer", "antipasti", "antipasto", "condiment", "beverage", "drink", "miscellaneous", "snack"}
LUNCH_WORDS = r"soup|salad|sandwich|wrap|burger|bowl|toastie|panini|frittata|quesadilla"
STOP = {"fresh", "chopped", "large", "small", "ground", "dried", "of", "and", "or", "the", "a", "to", "taste"}


def _tags(r):
    return {t.lower() for t in r.get("tags") or [] if isinstance(t, str)}


def _words(text):
    return {w.rstrip("s") for w in re.findall(r"[a-z]+", (text or "").lower()) if w not in STOP and len(w) > 2}


NOT_A_MEAL = r"\bbuns?\b|sauce\b|dressing|marinade|\bdips?\b|syrup|relish|chutney|\bjam\b|stuffing|side dish|\bglaze\b|\bstock\b|\brub\b|vinaigrette|compote|pickle|parfait|smoothie|ugali|pretzel"
LIGHT = r"salad|soup|sandwich|wrap|toastie|panini|slaw"
MAIN_TAGS = {"dinner", "main course", "main dish"}


def skeleton(title: str) -> str:
    """Spelling-insensitive key so 'Fettucine Alfredo' and 'Fettuccine Alfredo' count as the same dish."""
    return re.sub(r"(.)\1+", r"\1", re.sub(r"[aeiou\W\d_]", "", (title or "").lower()))


def slot_kinds(r) -> set:
    """Which of breakfast/lunch/dinner a recipe suits. Empty set = not a meal (dessert, drink, side, sauce...)."""
    tags, title = _tags(r), (r.get("title") or "").lower()
    if is_dessert(r) or tags & {"beverage", "drink", "condiment"} or re.search(NOT_A_MEAL, title):
        return set()
    if tags & BREAKFAST_TAGS or re.search(BREAKFAST_WORDS, title):
        return {"breakfast"}
    if tags & NOT_MAIN_TAGS and not tags & MAIN_TAGS and not re.search(LUNCH_WORDS, title):
        return set()
    light = bool(re.search(LIGHT, title)) or bool(tags & {"salad", "soup"})
    if tags & MAIN_TAGS and not light:
        return {"dinner"} | ({"lunch"} if "quick" in tags or "lunch" in tags else set())
    if light:
        return {"lunch"}                                  # salads, soups and sandwiches are lunches
    kinds = {"dinner"}
    if "lunch" in tags or "quick" in tags:
        kinds.add("lunch")
    return kinds


def build_plan(week_start, recipes, pantry_names=(), cuisines=(), diets=(), seed="", prefer_quick_weekdays=True):
    """Returns (days, notes) or None when this request can't be served from recipes (caller falls back to AI)."""
    diets = {d.strip().lower() for d in diets or [] if d and d.strip().lower() not in ("none", "")}
    if diets - SUPPORTED_DIETS:
        return None                                   # e.g. gluten-free / nut-free: can't verify from tags
    notes = []
    pool = [r for r in recipes if r.get("recipe_id") and r.get("title")]
    for d in diets:
        pool = [r for r in pool if d in _tags(r)]
    cuisines = {c.strip().lower().replace(" ", "_") for c in cuisines or [] if c and c.strip()}
    rng = random.Random(seed or week_start)
    pantry = set().union(*[_words(p) for p in pantry_names]) if pantry_names else set()

    def pantry_score(r):
        if not pantry:
            return 0
        ings = [(i.get("item") if isinstance(i, dict) else str(i)) for i in r.get("ingredients") or []]
        return sum(1 for i in ings if _words(i) & pantry) / max(len(ings), 1)

    by_slot = {"breakfast": [], "lunch": [], "dinner": []}
    for r in pool:
        for k in slot_kinds(r):
            by_slot[k].append(r)
    if len(by_slot["dinner"]) < 14 or len(by_slot["lunch"]) < 14:
        return None
    if len(by_slot["breakfast"]) < 7:
        notes.append("Few breakfast recipes match, so breakfasts may repeat.")

    used, used_titles, last_cuisine = set(), set(), {}
    start = date.fromisoformat(week_start[:10])
    days = []
    for i in range(7):
        day = {"date": (start + timedelta(days=i)).isoformat(), "day_name": DAYS[i]}
        for slot in ("breakfast", "lunch", "dinner"):
            cands = by_slot[slot]
            fresh = [r for r in cands if r["recipe_id"] not in used and skeleton(r["title"]) not in used_titles] or cands
            if not fresh:
                day[slot] = None
                continue
            def score(r):
                s = pantry_score(r) * 2
                if cuisines and (r.get("cuisine") or "").lower() in cuisines:
                    s += 2
                if prefer_quick_weekdays and i < 5 and slot != "breakfast" and "quick" in _tags(r):
                    s += 1
                if r.get("cuisine") and r.get("cuisine") == last_cuisine.get(slot):
                    s -= 1                             # avoid the same cuisine two days running
                return s + rng.random() * 1.5          # randomness keeps plans varied
            pick = max(fresh, key=score)
            used.add(pick["recipe_id"])
            used_titles.add(skeleton(pick["title"]))
            last_cuisine[slot] = pick.get("cuisine")
            day[slot] = {"recipe_id": pick["recipe_id"], "recipe_title": pick["title"], "recipe_image": pick.get("image") or None}
        days.append(day)
    if cuisines and not any((r.get("cuisine") or "").lower() in cuisines for r in pool):
        notes.append("No recipes found for those cuisines, so you got a mix.")
    return days, notes
