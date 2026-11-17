import asyncio, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from mongomock_motor import AsyncMongoMockClient
import release_queue as rq

def make_db(n=25):
    db = AsyncMongoMockClient()["t"]
    asyncio.run(db.recipe_queue.insert_many([{"recipe_id": f"r{i:02d}", "title": f"Recipe {i}", "queue_order": i, "ingredients": [], "steps": []} for i in range(n)]))
    return db

def test_ten_a_day_in_order_once_per_day(monkeypatch):
    monkeypatch.delenv("RELEASE_PER_DAY", raising=False)
    db = make_db()
    async def run():
        assert await rq.release_due(db, today="2026-11-18") == 10
        assert await rq.release_due(db, today="2026-11-18") == 0           # same day: nothing more
        live = sorted([r["recipe_id"] async for r in db.recipes.find({})])
        assert live == [f"r{i:02d}" for i in range(10)]                     # first ten, in order
        r = await db.recipes.find_one({"recipe_id": "r00"})
        assert r["user_id"] == "system_seeder" and r["released_from_queue"] and r["likes_count"] == 0
        assert await rq.release_due(db, today="2026-11-19") == 10
        assert await rq.release_due(db, today="2026-11-25") == 5            # a week later: only what is left, never a flood
        assert await db.recipe_queue.count_documents({}) == 0
        assert await rq.release_due(db, today="2026-11-26") == 0
    asyncio.run(run())

def test_server_off_for_days_still_releases_one_day(monkeypatch):
    monkeypatch.setenv("RELEASE_PER_DAY", "10")
    db = make_db(40)
    async def run():
        await rq.release_due(db, today="2026-11-18")
        assert await rq.release_due(db, today="2026-12-20") == 10
    asyncio.run(run())

def test_setting_changes_pace_and_zero_pauses(monkeypatch):
    db = make_db(12)
    async def run():
        monkeypatch.setenv("RELEASE_PER_DAY", "3"); assert await rq.release_due(db, today="2026-11-18") == 3
        monkeypatch.setenv("RELEASE_PER_DAY", "0"); assert await rq.release_due(db, today="2026-11-19") == 0
    asyncio.run(run())

def test_already_live_recipe_is_not_duplicated(monkeypatch):
    monkeypatch.setenv("RELEASE_PER_DAY", "10")
    db = make_db(3)
    async def run():
        await db.recipes.insert_one({"recipe_id": "r01", "title": "Existing", "user_id": "someone"})
        await rq.release_due(db, today="2026-11-18")
        assert await db.recipes.count_documents({"recipe_id": "r01"}) == 1
        assert (await db.recipes.find_one({"recipe_id": "r01"}))["title"] == "Existing"
    asyncio.run(run())
