"""Backup / restore of user data (not the 1,171 master recipes, caches or login sessions).

Admins download the file from the Admin page; scripts/restore_backup.py puts it back.
Format: gzip, one JSON object per line: {"c": "<collection>", "d": <document>} (MongoDB extended JSON).
"""
import gzip
from datetime import datetime, timezone

from bson import json_util

# Collections that hold users' own data. Sessions/caches are left out on purpose.
COLLECTIONS = ["users", "recipes", "comments", "reports", "banned_emails", "recipe_consents",
               "cookbooks", "meal_plans", "pantry_items", "shopping_list"]
FILTERS = {"recipes": {"user_id": {"$ne": "system_seeder"}}}


async def build_backup(db) -> tuple[bytes, dict]:
    lines, counts = [], {}
    for name in COLLECTIONS:
        n = 0
        async for doc in db[name].find(FILTERS.get(name, {})):
            lines.append(json_util.dumps({"c": name, "d": doc}))
            n += 1
        counts[name] = n
    header = json_util.dumps({"c": "_meta", "d": {"created_at": datetime.now(timezone.utc), "counts": counts}})
    return gzip.compress(("\n".join([header] + lines) + "\n").encode("utf-8")), counts


def read_backup(data: bytes):
    """Yield (collection, document) pairs from a backup file's bytes."""
    for line in gzip.decompress(data).decode("utf-8").splitlines():
        if not line.strip():
            continue
        row = json_util.loads(line)
        if row["c"] != "_meta":
            yield row["c"], row["d"]
