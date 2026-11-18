import asyncio
from datetime import datetime, timedelta
from mongomock_motor import AsyncMongoMockClient
from cache import get_cache


def test_cache_hit_with_naive_datetimes_from_mongo():
    async def run():
        db = AsyncMongoMockClient()["t"]
        await db.ai_cache.insert_one({"key": "k1", "value": {"a": 1}, "expires_at": datetime.utcnow() + timedelta(days=1)})
        await db.ai_cache.insert_one({"key": "k2", "value": {"a": 2}, "expires_at": datetime.utcnow() - timedelta(days=1)})
        assert await get_cache(db, "k1") == {"a": 1}      # used to crash: naive vs aware
        assert await get_cache(db, "k2") is None          # expired entries are dropped
        assert await get_cache(db, "missing") is None
    asyncio.run(run())
