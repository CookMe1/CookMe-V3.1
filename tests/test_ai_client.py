import asyncio
import pytest
from fastapi import HTTPException
from mongomock_motor import AsyncMongoMockClient

import ai_client


def test_model_defaults_and_env(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    assert ai_client.model_for() == ("openai", "gpt-4o-mini")
    monkeypatch.setenv("AI_PROVIDER", "anthropic")
    monkeypatch.setenv("AI_MODEL", "claude-haiku-5-5")
    assert ai_client.model_for() == ("anthropic", "claude-haiku-5-5")


def test_parse_json_with_fences():
    assert ai_client.parse_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_daily_limit(monkeypatch):
    monkeypatch.setenv("AI_DAILY_LIMIT", "2")
    db = AsyncMongoMockClient()["t"]

    async def go():
        assert await ai_client.uses_left(db, "u1") == 2
        await ai_client.spend_one(db, "u1")
        await ai_client.spend_one(db, "u1")
        assert await ai_client.uses_left(db, "u1") == 0
        with pytest.raises(HTTPException) as e:
            await ai_client.spend_one(db, "u1")
        assert e.value.status_code == 429
        assert await ai_client.uses_left(db, "u2") == 2  # other people unaffected
    asyncio.run(go())


def test_ai_routes_cache_limit_and_convert(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from routes import ai_routes
    monkeypatch.setenv("AI_DAILY_LIMIT", "2")
    db = AsyncMongoMockClient()["t"]
    calls = {"n": 0}

    async def fake_user(request, db_, allow_restricted=False):
        return {"user_id": "u1", "email": "a@b.c"}

    async def fake_ask(system, prompt, prefix="ai"):
        calls["n"] += 1
        if prefix == "sub":
            return {"substitutes": [{"item": "Oat milk", "amount": "1:1", "note": "Slightly sweeter"}]}
        return {"title": "Vegan Pancakes", "ingredients": [{"item": "Oat milk", "amount": "1 cup"}],
                "steps": ["Mix.", "Fry."], "changes": ["Milk -> oat milk"]}
    monkeypatch.setattr(ai_routes, "get_current_user", fake_user)
    monkeypatch.setattr(ai_routes, "ask_json", fake_ask)
    asyncio.run(db.recipes.insert_one({"recipe_id": "r1", "user_id": "system_seeder", "title": "Pancakes", "servings": 4,
                                       "ingredients": [{"item": "Milk", "amount": "1 cup"}], "steps": ["Mix.", "Fry."]}))
    app = FastAPI(); app.state.db = db; app.include_router(ai_routes.router, prefix="/api")
    c = TestClient(app)

    r1 = c.post("/api/ai/substitutes", json={"ingredient": "Milk", "diet": "vegan"}).json()
    r2 = c.post("/api/ai/substitutes", json={"ingredient": "milk", "diet": "vegan"}).json()
    assert r1["cached"] is False and r2["cached"] is True and calls["n"] == 1
    assert r2["left_today"] == 1                      # the cached repeat cost nothing

    conv = c.post("/api/ai/convert-recipe", json={"recipe_id": "r1", "diet": "vegan"}).json()
    assert conv["title"] == "Vegan Pancakes" and conv["changes"] and conv["left_today"] == 0
    # allowance used up: a new question is refused, a cached one still works
    assert c.post("/api/ai/substitutes", json={"ingredient": "Butter"}).status_code == 429
    assert c.post("/api/ai/substitutes", json={"ingredient": "Milk", "diet": "vegan"}).status_code == 200
    assert c.post("/api/ai/convert-recipe", json={"recipe_id": "nope", "diet": "vegan"}).status_code == 404
    assert c.post("/api/ai/convert-recipe", json={"recipe_id": "r1", "diet": "bogus"}).status_code == 400
