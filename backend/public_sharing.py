"""Making a recipe public: the consent wording, the quality/safety checks, and the filters that decide what everyone can see.
Not legal advice: have a lawyer review CONSENT_TEXT and your Terms of Service before launch."""
import hashlib
import re

from recipe_cleaner import clean_steps

TERMS_VERSION = "2026-11-17"
CONSENT_TEXT = (
    "I wrote this recipe myself (or I have the right to share it), and the photo is my own. "
    "I choose to make it public. I give CookMe a free, non-exclusive, worldwide licence to show it to other CookMe users, "
    "to translate, resize and tag it, and to feature it inside the app. Other users may save a copy for their own personal use. "
    "I can make it private again at any time: CookMe will then stop showing it, but copies other people already saved can stay in their own collections. "
    "I understand CookMe can remove recipes that break its rules."
)
CONSENT_HASH = hashlib.sha256((TERMS_VERSION + CONSENT_TEXT).encode()).hexdigest()

# What counts as "shared with everyone": our own collection plus recipes people have made public.
SHARED = {"$or": [{"user_id": "system_seeder"}, {"visibility": "public"}]}


def shared_or_own(user_id: str) -> dict:
    """Shared recipes (minus ones this person hid) plus all of this person's own recipes."""
    return {"$or": [
        {"user_id": "system_seeder", "hidden_by": {"$ne": user_id}},
        {"visibility": "public", "hidden_by": {"$ne": user_id}},
        {"user_id": user_id, "hidden_by": {"$ne": user_id}},
    ]}


_URL = re.compile(r"https?://|www\.|\b[a-z0-9-]+\.(?:com|net|org|io|co\.uk|es)\b", re.I)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?<!\d)(?:\+?\d[\s-]?){9,}(?!\d)")
_BLOCKED = re.compile(r"\b(?:fuck\w*|shit\w*|cunt|nigger|nigga|faggot|retard\w*|whore|slut)\b", re.I)
_STOCK = ("images.unsplash.com", "placeholder", "no-image")


def check_recipe(r: dict) -> list:
    """Quality and safety checks. Returns a list of {"field", "message"}; an empty list means it can go public."""
    issues = []

    def add(field, msg):
        issues.append({"field": field, "message": msg})

    title = (r.get("title") or "").strip()
    desc = (r.get("description") or "").strip()
    ings = [i for i in (r.get("ingredients") or []) if str((i or {}).get("item", "")).strip()]
    steps = [s for s in (r.get("steps") or []) if isinstance(s, str) and s.strip()]
    image = r.get("image") or ""

    if r.get("source_url") or any(str(t).lower() == "imported" for t in (r.get("tags") or [])):
        add("source", "Recipes imported from another website, video or post can't be made public. Only recipes you wrote yourself.")
    if len(title) < 3 or len(title) > 100:
        add("title", "Give the recipe a clear name (3 to 100 characters).")
    if len(desc) < 20:
        add("description", "Add a short description (at least a sentence) saying what the dish is.")
    if len(ings) < 3:
        add("ingredients", "List at least 3 ingredients.")
    else:
        missing = [str(i["item"]).strip() for i in ings if not str(i.get("amount", "")).strip()]
        if len(missing) / len(ings) > 0.3:
            add("ingredients", "Add amounts for most ingredients, for example: " + ", ".join(missing[:4]) + ".")
    if len(steps) < 2 or sum(len(s) for s in steps) < 100:
        add("steps", "Write the method in at least 2 clear steps (a few sentences in total).")
    elif len(clean_steps(steps)) != len(steps):
        add("steps", "Remove steps that are only a label or number, such as \"Step 1\".")
    if not str(r.get("prep_time") or "").strip() and not str(r.get("cook_time") or "").strip():
        add("time", "Add a prep time or cook time.")
    if not image:
        add("image", "Add a photo of the dish. It must be your own photo.")
    elif image.startswith("http") or any(s in image for s in _STOCK):
        add("image", "Upload your own photo of the dish (photos copied from the web or stock photos can't be used).")

    text = " ".join([title, desc] + steps + [str(i.get("item", "")) for i in ings])
    if _URL.search(text):
        add("text", "Remove web links and website names from the recipe text.")
    if _EMAIL.search(text) or _PHONE.search(text):
        add("text", "Remove email addresses and phone numbers from the recipe text.")
    if _BLOCKED.search(text):
        add("text", "The recipe contains language we don't allow. Please reword it.")
    return issues


async def title_is_taken(db, title: str, recipe_id: str) -> bool:
    """True if another shared recipe already has this name."""
    t = re.escape((title or "").strip())
    if not t:
        return False
    q = {"$and": [SHARED, {"recipe_id": {"$ne": recipe_id}}, {"title": {"$regex": f"^{t}$", "$options": "i"}}]}
    return await db.recipes.find_one(q, {"_id": 1}) is not None


async def full_check(db, r: dict) -> list:
    issues = check_recipe(r)
    if not any(i["field"] == "title" for i in issues) and await title_is_taken(db, r.get("title", ""), r.get("recipe_id", "")):
        issues.append({"field": "title", "message": "A shared recipe with this name already exists. Make the name more specific, for example add what makes yours different."})
    return issues


def mask_owner(recipe: dict, viewer_id: str) -> dict:
    """What another person is allowed to see of a recipe: never the owner's internal id, name only if they agreed to show it,
    and never the lists of which other users favourited or hid it."""
    if not recipe:
        return recipe
    r = dict(recipe)
    if r.get("user_id") not in ("system_seeder", viewer_id):
        r["uploader_name"] = r.get("public_author")
        r["uploader_id"] = None
        r["user_id"] = "shared"
    if r.get("user_id") != viewer_id:
        r["favorited_by"] = [viewer_id] if viewer_id in (recipe.get("favorited_by") or []) else []
        r["hidden_by"] = [viewer_id] if viewer_id in (recipe.get("hidden_by") or []) else []
    return r
