"""Put a backup downloaded from the Admin page back into the database.

    MONGO_URL=... DB_NAME=... python scripts/restore_backup.py cookme-backup-2026-11-18-1200.jsonl.gz
Existing documents with the same id are overwritten; nothing is deleted. Add --dry-run to only count.
"""
import asyncio, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
import backup_ops
from motor.motor_asyncio import AsyncIOMotorClient


async def main(path, dry):
    rows = list(backup_ops.read_backup(Path(path).read_bytes()))
    counts = {}
    for c, _ in rows:
        counts[c] = counts.get(c, 0) + 1
    print("Backup holds:", counts)
    if dry:
        return
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    for c, d in rows:
        await db[c].replace_one({"_id": d["_id"]}, d, upsert=True)
    print("Restored", len(rows), "documents.")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    asyncio.run(main(args[0], "--dry-run" in sys.argv))
