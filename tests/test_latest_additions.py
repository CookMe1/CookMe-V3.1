import asyncio, sys
from types import SimpleNamespace
from mongomock_motor import AsyncMongoMockClient


def test_latest_endpoints_and_main_lists_exclude_new_releases():
    sys.path.insert(0, "backend")
    from fastapi import Response
    import routes.recipe_routes as rr

    async def run():
        db = AsyncMongoMockClient()["t"]
        base = dict(user_id="system_seeder", ingredients=[{"item": "x"}], steps=["s"], hidden_by=[], favorited_by=[], description="d", category="")
        await db.recipes.insert_many([
            {**base, "recipe_id": "old", "title": "Old Soup", "created_at": 1},
            {**base, "recipe_id": "new1", "title": "New Drink", "tags": ["drink"], "in_latest": True, "released_at": "2026-11-27T10:00:00+00:00"},
            {**base, "recipe_id": "new2", "title": "New Sauce", "tags": ["sauce"], "in_latest": True, "released_at": "2026-11-27T11:00:00+00:00"},
            {**base, "recipe_id": "drk", "title": "Tea", "tags": ["drink"]},
        ])
        rr.get_current_user = lambda request, db: asyncio.sleep(0, {"user_id": "u1"})
        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=db)))
        main = await rr.get_master_recipes(req, Response(), limit=60)
        assert sorted(r["recipe_id"] for r in main) == ["drk", "old"]           # new ones are held back from the library
        late = await rr.latest_additions(req)
        assert [r["recipe_id"] for r in late["recipes"]] == ["new2", "new1"] and late["total"] == 2   # newest first
        s = await rr.latest_summary(req, since=None)
        assert s["new_since"] == 2 and s["total_in_latest"] == 2
        s = await rr.latest_summary(req, since="2026-11-27T10:30:00+00:00")
        assert s["new_since"] == 1                                               # only what arrived after their last visit
        drinks = await rr.get_recipes_by_cooking_type("drinks", req)
        assert [r["recipe_id"] for r in drinks["recipes"]] == ["drk"]            # held-back drink not listed yet
        for t in ("sauces", "snacks"):
            await rr.get_recipes_by_cooking_type(t, req)
    asyncio.run(run())
