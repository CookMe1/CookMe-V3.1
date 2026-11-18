import asyncio
from mongomock_motor import AsyncMongoMockClient
from fastapi import FastAPI
from fastapi.testclient import TestClient
from shopping_merge import merge_ingredients


def test_merge_adds_same_unit_and_joins_different():
    out = {m["name"].lower(): m["amount"] for m in merge_ingredients([
        [{"item": "Onion", "amount": "1"}, {"item": "Olive Oil", "amount": "2 tbsp"}, {"item": "Salt", "amount": "1 tsp"}],
        [{"item": "onions", "amount": "2"}, {"item": "olive oil", "amount": "1 tbsp"}, {"item": "Flour", "amount": "200g"}],
        [{"item": "Flour", "amount": "1 cup"}, {"item": "Parsley", "amount": "handful"}]])}
    assert out["onion"] == "3" and out["olive oil"] == "3 tbsp"
    assert out["flour"] == "200g + 1 cup" and out["parsley"] == "handful"
    assert "salt" not in out


def test_endpoint_skips_pantry_and_combines(monkeypatch):
    import auth
    from routes import shopping_routes
    db = AsyncMongoMockClient()["t"]

    async def fake_user(request, db_, allow_restricted=False):
        return {"user_id": "u1", "email": "a@b.c"}
    monkeypatch.setattr(shopping_routes, "get_current_user", fake_user)
    asyncio.run(db.recipes.insert_many([
        {"recipe_id": "r1", "user_id": "system_seeder", "ingredients": [{"item": "Chicken breast", "amount": "2"}, {"item": "Rice", "amount": "200g"}, {"item": "Onion", "amount": "1"}]},
        {"recipe_id": "r2", "user_id": "system_seeder", "ingredients": [{"item": "Rice", "amount": "100g"}, {"item": "Lemon", "amount": "1"}]}]))
    asyncio.run(db.pantry_items.insert_one({"user_id": "u1", "name": "Rice", "in_stock": True}))
    app = FastAPI(); app.state.db = db; app.include_router(shopping_routes.router, prefix="/api")
    r = TestClient(app).post("/api/shopping-list/from-recipes", json={"recipe_ids": ["r1", "r2"]}).json()
    assert r["in_pantry"] == ["Rice"] and r["added_count"] == 3 and r["recipes_used"] == 2
    items = asyncio.run(db.shopping_lists.find_one({"user_id": "u1"}))["items"]
    assert sorted(i["name"] for i in items) == ["Chicken breast", "Lemon", "Onion"]
    # asking again does not duplicate
    r2 = TestClient(app).post("/api/shopping-list/from-recipes", json={"recipe_ids": ["r1", "r2"]}).json()
    assert r2["added_count"] == 0 and r2["already_on_list"] == 3
