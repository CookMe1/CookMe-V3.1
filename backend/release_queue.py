"""Slow, steady growth: approved recipes wait in the `recipe_queue` collection and are released a few per day.
The backend checks once an hour; the first check of a new day releases the next RELEASE_PER_DAY (default 10).
If the server was off for days it still releases only one day's worth (no sudden flood)."""
import asyncio
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def per_day() -> int:
    try:
        return max(0, int(os.environ.get("RELEASE_PER_DAY", "10")))
    except ValueError:
        return 10


async def release_due(db, today=None, limit=None) -> int:
    """Move the next recipes from the queue into the shared recipe list. Returns how many were released."""
    today = today or datetime.now(timezone.utc).date().isoformat()
    n = per_day() if limit is None else limit
    state = await db.release_state.find_one({"_id": "recipes"}) or {}
    if n <= 0 or state.get("last_release_date") == today:
        return 0
    batch = await db.recipe_queue.find({}, {"_id": 0}).sort("queue_order", 1).limit(n).to_list(n)
    now = datetime.now(timezone.utc).isoformat()
    released = 0
    for r in batch:
        r.pop("queue_order", None)
        r.update({"user_id": "system_seeder", "released_from_queue": True, "created_at": now, "updated_at": now})
        for k in ("likes_count", "saves_count"):
            r.setdefault(k, 0)
        for k in ("favorited_by", "hidden_by", "gallery_images"):
            r.setdefault(k, [])
        await db.recipes.update_one({"recipe_id": r["recipe_id"]}, {"$setOnInsert": r}, upsert=True)
        await db.recipe_queue.delete_one({"recipe_id": r["recipe_id"]})
        released += 1
    await db.release_state.update_one({"_id": "recipes"}, {"$set": {"last_release_date": today, "released_today": released}}, upsert=True)
    if released:
        logger.info("Released %d recipes from the queue", released)
    return released


async def release_loop(db, every_seconds: int = 3600):
    while True:
        try:
            await release_due(db)
        except Exception:
            logger.exception("Recipe release failed; will retry")
        await asyncio.sleep(every_seconds)
