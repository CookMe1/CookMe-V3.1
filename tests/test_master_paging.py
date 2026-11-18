import asyncio, sys
from mongomock_motor import AsyncMongoMockClient


def test_master_all_pages_and_filters():
    sys.path.insert(0, "backend")
    from fastapi import Response
    from types import SimpleNamespace
    import routes.recipe_routes as rr

    async def run():
        db = AsyncMongoMockClient()["t"]
        docs = [{"recipe_id": f"r{i}", "user_id": "system_seeder", "title": f"Dish {i}", "description": "d", "category": "dinner" if i % 2 else "dessert",
                 "ingredients": [{"item": "x"}], "steps": ["s"], "created_at": i, "favorited_by": ["u1"] if i == 3 else [], "hidden_by": []} for i in range(50)]
        await db.recipes.insert_many(docs)
        rr.get_current_user = lambda request, db: asyncio.sleep(0, {"user_id": "u1"})
        req = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=db)))
        res = Response()
        page = await rr.get_master_recipes(req, res, limit=10, skip=0)
        assert len(page) == 10 and res.headers["X-Total-Count"] == "50"
        assert "ingredients" not in page[0] and "steps" not in page[0]
        res2 = Response()
        d = await rr.get_master_recipes(req, res2, category="dessert", limit=60)
        assert len(d) == 25 and res2.headers["X-Total-Count"] == "25"
        res3 = Response()
        s = await rr.get_master_recipes(req, res3, search="dish 3.", limit=60)   # regex characters are escaped
        assert s == [] and res3.headers["X-Total-Count"] == "0"
        res4 = Response()
        fav = [r for r in await rr.get_master_recipes(req, res4, limit=60) if r["is_favorited"]]
        assert [r["recipe_id"] for r in fav] == ["r3"]

    asyncio.run(run())
