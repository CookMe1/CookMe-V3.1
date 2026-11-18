"""First start on an empty database (e.g. the live site): load the master recipes from data/master_recipes.json.
It only runs when there are NO master recipes yet, so it never brings back recipes you removed and never touches user data.
Switch off with AUTO_SEED_MASTER=0. Later updates still go through scripts/load_master_recipes.py."""
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)
DATA = Path(__file__).resolve().parent.parent / "data" / "master_recipes.json"


async def seed_master_recipes(db, path=None) -> int:
    if os.environ.get("AUTO_SEED_MASTER", "1") == "0":
        return 0
    if await db.recipes.count_documents({"user_id": "system_seeder"}, limit=1):
        return 0
    path = Path(path or DATA)
    if not path.exists():
        logger.warning("Master recipe file not found at %s; the recipe library will be empty", path)
        return 0
    recipes = json.loads(path.read_text(encoding="utf-8"))
    for r in recipes:
        r.setdefault("user_id", "system_seeder")
        for k in ("likes_count", "saves_count"):
            r.setdefault(k, 0)
        for k in ("favorited_by", "hidden_by", "gallery_images"):
            r.setdefault(k, [])
        await db.recipes.update_one({"recipe_id": r["recipe_id"]}, {"$setOnInsert": r}, upsert=True)
    logger.info("Loaded %d master recipes into an empty database", len(recipes))
    return len(recipes)


SYNC_FIELDS = ("image", "prep_time", "cook_time", "time_estimated", "description")
SYNC_VERSION = 2   # bump when data/master_recipes.json gets new corrections that existing databases should receive


async def sync_master_updates(db, path=None) -> int:
    """One-time per version: copy corrected image / time / description fields from data/master_recipes.json into the
    master recipes already in the database (e.g. the local image copies and the estimated times).
    Never touches users' own recipes or anything else on a master recipe (likes, comments, hidden_by...)."""
    if os.environ.get("AUTO_SEED_MASTER", "1") == "0":
        return 0
    state = await db.release_state.find_one({"_id": "master_sync"})
    if state and state.get("version", 0) >= SYNC_VERSION:
        return 0
    path = Path(path or DATA)
    if not path.exists():
        return 0
    changed = 0
    for r in json.loads(path.read_text(encoding="utf-8")):
        fields = {k: r[k] for k in SYNC_FIELDS if k in r}
        if fields and r.get("recipe_id"):
            res = await db.recipes.update_one({"recipe_id": r["recipe_id"], "user_id": "system_seeder"}, {"$set": fields})
            changed += res.modified_count
    await db.release_state.update_one({"_id": "master_sync"}, {"$set": {"version": SYNC_VERSION}}, upsert=True)
    logger.info("Master recipe update: %d recipes corrected", changed)
    return changed
