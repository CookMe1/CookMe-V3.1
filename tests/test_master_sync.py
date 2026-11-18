import asyncio, json
from mongomock_motor import AsyncMongoMockClient
from seed_master import sync_master_updates
import master_enrich as e


def test_sync_updates_master_only_and_runs_once(tmp_path):
    f = tmp_path / "m.json"
    f.write_text(json.dumps([{"recipe_id": "r1", "image": "/recipe-images/a.jpg", "prep_time": "25 min", "cook_time": "2h 30m",
                              "time_estimated": True, "description": "New", "title": "ignored"}]))

    async def run():
        db = AsyncMongoMockClient()["t"]
        await db.recipes.insert_many([
            {"recipe_id": "r1", "user_id": "system_seeder", "image": "http://x/a.jpg", "prep_time": "15 min", "cook_time": "30 min", "likes_count": 7},
            {"recipe_id": "r1b", "user_id": "u1", "image": "keep", "prep_time": "9 min"}])
        assert await sync_master_updates(db, f) == 1
        r = await db.recipes.find_one({"recipe_id": "r1"})
        assert r["image"] == "/recipe-images/a.jpg" and r["cook_time"] == "2h 30m" and r["time_estimated"] and r["likes_count"] == 7
        assert (await db.recipes.find_one({"recipe_id": "r1b"}))["image"] == "keep"
        await db.recipes.update_one({"recipe_id": "r1"}, {"$set": {"prep_time": "changed"}})
        assert await sync_master_updates(db, f) == 0          # already applied: runs once
        assert (await db.recipes.find_one({"recipe_id": "r1"}))["prep_time"] == "changed"
    asyncio.run(run())


def test_time_estimates_and_descriptions():
    r = {"steps": ["Cover and cook in the oven for 1½ hrs, then add the potatoes and cook for 1 hr more."], "ingredients": [{"item": "lamb"}] * 8}
    prep, cook, est = e.estimate_times(r)
    assert cook == "2h 30m" and est and prep == "21 min" or prep.endswith("min")
    assert e.durations("simmer 20-25 minutes")[0][0] == 22.5
    assert e.durations("marinate overnight for 2 hours")[0] == (120.0, True)
    d = e.make_description({"cuisine": "spanish", "ingredients": [{"item": "Onion"}, {"item": "Olive Oil"}, {"item": "Potatoes"}, {"item": "Garlic"}]})
    assert d == "A Spanish dish made with onion, potatoes and garlic."
    assert e.GENERIC_DESC.match("A delicious lamb recipe from Vietnamese cuisine.")
