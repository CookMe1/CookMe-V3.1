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
    monkeypatch.setenv("RELEASE_PER_DAY", "10")
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


def test_daily_number_is_10_to_20_and_steady_through_the_day(monkeypatch):
    monkeypatch.delenv("RELEASE_PER_DAY", raising=False)
    days = [f"2026-12-{d:02d}" for d in range(1, 29)]
    nums = [rq.per_day(d) for d in days]
    assert all(10 <= n <= 20 for n in nums) and len(set(nums)) > 3        # varies, never outside 10-20
    assert rq.per_day("2026-12-05") == rq.per_day("2026-12-05")            # same answer all day


def test_new_releases_wait_in_latest_then_graduate(monkeypatch):
    from datetime import datetime, timedelta, timezone
    monkeypatch.setenv("RELEASE_PER_DAY", "10"); monkeypatch.delenv("HOLD_DAYS", raising=False)   # default: 2 days
    db = make_db(12)
    async def run():
        assert await rq.release_due(db, today="2026-11-18") == 10
        r = await db.recipes.find_one({"recipe_id": "r00"})
        assert r["in_latest"] is True and r["released_at"]
        assert await db.recipes.count_documents({"in_latest": True}) == 10
        assert await rq.graduate(db) == 0                                    # too soon
        assert await rq.graduate(db, now=datetime.now(timezone.utc) + timedelta(days=1)) == 0       # still in Latest after a day
        later = datetime.now(timezone.utc) + timedelta(days=3)
        assert await rq.graduate(db, now=later) == 10                         # after two days they join the library
        assert await db.recipes.count_documents({"in_latest": True}) == 0
    asyncio.run(run())
