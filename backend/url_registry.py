"""
url_registry.py
===============
Shared recipe registry — the first user to import a URL pays the extraction
cost. Every subsequent user who imports the same URL gets it instantly, free.

MongoDB collection: url_registry
  Fields: url_hash, url, recipe, domain, imported_by, import_count,
          created_at, updated_at

This is separate from the per-user AI cache — it's a global shared store.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from cache import normalise_url, _hash as cache_hash

logger = logging.getLogger(__name__)


def _registry_key(url: str) -> str:
    """Stable key for a URL — normalised to maximise hit rate."""
    return cache_hash(normalise_url(url))


async def get_from_registry(db, url: str) -> Optional[dict]:
    """
    Look up a URL in the shared registry.
    Returns the stored recipe dict if found, None otherwise.
    Also increments the import_count for analytics.
    """
    key = _registry_key(url)
    doc = await db.url_registry.find_one({"url_hash": key}, {"_id": 0})
    if not doc:
        return None

    recipe = doc.get("recipe")
    if not recipe:
        return None

    # Track how many times this registry entry has been served
    await db.url_registry.update_one(
        {"url_hash": key},
        {"$inc": {"import_count": 1}, "$set": {"last_served_at": datetime.now(timezone.utc)}}
    )

    logger.info(f"Registry hit: {doc.get('url', url)!r} (served {doc.get('import_count', 0)+1} times)")
    return recipe


async def save_to_registry(db, url: str, recipe: dict, user_id: str = None) -> None:
    """
    Save a successfully extracted recipe to the shared registry.
    Skips saving if the recipe has low confidence or missing key fields.
    """
    # Only save high-quality extractions
    if not recipe.get("title"):
        return
    if not recipe.get("ingredients") or len(recipe.get("ingredients", [])) < 2:
        return
    if not recipe.get("steps") or len(recipe.get("steps", [])) < 1:
        return
    # Don't cache low-confidence results
    if recipe.get("confidence") in ("user-assisted",) or recipe.get("confidence_score", 1.0) < 0.5:
        return

    key = _registry_key(url)
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.replace("www.", "").lower()

    # Strip internal fields before storing
    clean_recipe = {k: v for k, v in recipe.items()
                    if not k.startswith("_") and k not in ("from_cache", "import_fingerprint")}

    now = datetime.now(timezone.utc)
    await db.url_registry.update_one(
        {"url_hash": key},
        {"$setOnInsert": {
            "url_hash":    key,
            "url":         url,
            "domain":      domain,
            "recipe":      clean_recipe,
            "imported_by": user_id,
            "import_count": 0,
            "created_at":  now,
        }, "$set": {
            "updated_at": now,
        }},
        upsert=True,
    )
    logger.info(f"Registry saved: {url!r} — {clean_recipe.get('title', '?')}")


async def get_registry_stats(db) -> dict:
    """Return stats about the URL registry for admin/dashboard."""
    total    = await db.url_registry.count_documents({})
    top_domains_cursor = db.url_registry.aggregate([
        {"$group": {"_id": "$domain", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ])
    top_domains = [doc async for doc in top_domains_cursor]
    total_served = await db.url_registry.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$import_count"}}}
    ]).to_list(1)

    return {
        "total_urls": total,
        "total_imports_served_free": total_served[0]["total"] if total_served else 0,
        "top_domains": top_domains,
    }


async def create_registry_indexes(db) -> None:
    """Create indexes for the registry collection."""
    await db.url_registry.create_index("url_hash", unique=True)
    await db.url_registry.create_index("domain")
    await db.url_registry.create_index("import_count")
    await db.url_registry.create_index("created_at")
