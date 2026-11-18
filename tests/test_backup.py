import asyncio, gzip
from mongomock_motor import AsyncMongoMockClient
import backup_ops


def test_backup_roundtrip_skips_master_recipes_and_sessions():
    async def run():
        db = AsyncMongoMockClient()["t"]
        await db.users.insert_one({"user_id": "u1", "email": "a@b.c"})
        await db.recipes.insert_many([{"recipe_id": "r1", "user_id": "u1"}, {"recipe_id": "r2", "user_id": "system_seeder"}])
        await db.user_sessions.insert_one({"session_token": "secret"})
        blob, counts = await backup_ops.build_backup(db)
        assert counts["users"] == 1 and counts["recipes"] == 1
        text = gzip.decompress(blob).decode()
        assert "secret" not in text and "r2" not in text
        rows = list(backup_ops.read_backup(blob))
        assert ("recipes", ) [0] in [c for c, _ in rows] and len(rows) == 2
        db2 = AsyncMongoMockClient()["t2"]
        for c, d in rows:
            await db2[c].replace_one({"_id": d["_id"]}, d, upsert=True)
        assert (await db2.recipes.find_one({"recipe_id": "r1"}))["user_id"] == "u1"
    asyncio.run(run())
