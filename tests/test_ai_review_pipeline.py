"""AI recipe -> cooked -> admin review -> photo -> shared library; and library-first pantry paging."""
import asyncio
import os, sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
os.environ.setdefault("JWT_SECRET", "x")
pytest.importorskip("emergentintegrations")
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
import routes.ai_routes as air
import routes.admin_routes as adm


def make(monkeypatch, uid="u1"):
    db = AsyncMongoMockClient()["t"]
    cur = {"u": uid}

    async def fake_user(request, db_, allow_restricted=False):
        return {"user_id": cur["u"], "email": "a@b.c", "name": "A"}

    async def fake_admin(request, db_):
        return {"user_id": "boss", "email": "boss@x.y"}
    monkeypatch.setattr(air, "get_current_user", fake_user)
    monkeypatch.setattr(adm, "require_admin", fake_admin)
    app = FastAPI(); app.state.db = db
    app.include_router(air.router, prefix="/api"); app.include_router(adm.router, prefix="/api")
    return db, cur, TestClient(app)


def test_cooked_ai_recipe_goes_to_review_then_library(monkeypatch):
    db, cur, c = make(monkeypatch)
    asyncio.run(db.recipes.insert_many([
        {"recipe_id": "ai1", "user_id": "u1", "title": "Garlic Chicken Rice", "ai_generated": True, "servings": 4,
         "ingredients": [{"item": "chicken", "amount": "500g"}], "steps": ["Sear 4 min.", "Simmer 20 min."], "tags": ["AI Suggested", "Dinner"]},
        {"recipe_id": "plain", "user_id": "u1", "title": "My own recipe", "ingredients": [], "steps": []}]))
    # cooking an ordinary recipe never queues it; cooking the AI one does
    assert c.post("/api/ai/cooked", json={"recipe_id": "plain"}).json()["sent_for_review"] is False
    assert c.post("/api/ai/cooked", json={"recipe_id": "ai1"}).json()["sent_for_review"] is True
    assert c.post("/api/ai/cooked", json={"recipe_id": "ai1"}).json()["sent_for_review"] is False  # only once
    q = c.get("/api/admin/ai-recipes").json()
    assert [i["recipe_id"] for i in q["items"]] == ["ai1"] and q["items"][0]["cooked_by"] == 1

    # nothing is public until the admin approves
    assert asyncio.run(db.recipes.count_documents({"user_id": "system_seeder"})) == 0

    async def fake_store(db_, url):
        return "/api/ai/image/img_test"
    import image_search
    monkeypatch.setattr(image_search, "store_photo", fake_store)
    r = c.post("/api/admin/ai-recipes/approve", json={"recipe_id": "ai1", "image_url": "https://pixabay.com/x.jpg", "credit": "Photo by Ann on Pixabay"})
    assert r.status_code == 200
    master = asyncio.run(db.recipes.find_one({"recipe_id": r.json()["master_id"]}))
    assert master["user_id"] == "system_seeder" and master["image"] == "/api/ai/image/img_test"
    assert master["image_attribution"] == "Photo by Ann on Pixabay" and "AI-made" in master["tags"] and "AI Suggested" not in master["tags"]
    assert c.get("/api/admin/ai-recipes").json()["items"] == []
    assert c.post("/api/admin/ai-recipes/approve", json={"recipe_id": "ai1"}).status_code == 404  # no double publish


def test_reject_and_photo_hosts(monkeypatch):
    db, cur, c = make(monkeypatch)
    asyncio.run(db.recipes.insert_one({"recipe_id": "ai2", "user_id": "u1", "title": "Odd Stew", "ai_generated": True, "ai_review": "pending", "ingredients": [], "steps": []}))
    assert c.post("/api/admin/ai-recipes/reject", json={"recipe_id": "ai2"}).status_code == 200
    assert c.get("/api/admin/ai-recipes").json()["items"] == []
    import image_search
    assert image_search._allowed("https://images.pexels.com/photos/1.jpg")
    assert image_search._allowed("https://cdn.pixabay.com/photo/1.jpg")
    assert not image_search._allowed("https://evil.example.com/pixabay.com/1.jpg")
    assert not image_search._allowed("http://pixabay.com/1.jpg")


def test_pantry_more_uses_library_only_and_skips_seen(monkeypatch):
    import routes.pantry_routes as pr
    db = AsyncMongoMockClient()["t"]

    async def fake_user(request, db_, allow_restricted=False):
        return {"user_id": "u1", "email": "a@b.c"}
    monkeypatch.setattr(pr, "get_current_user", fake_user)
    monkeypatch.setattr(pr, "get_cache", lambda *a, **k: asyncio.sleep(0, result=None))
    asked = {"ai": 0}

    class Boom:
        def __init__(self, *a, **k): asked["ai"] += 1
    monkeypatch.setattr(pr, "LlmChat", Boom)
    asyncio.run(db.pantry_items.insert_many([
        {"user_id": "u1", "name": "chicken", "in_stock": True}, {"user_id": "u1", "name": "rice", "in_stock": True}]))
    asyncio.run(db.recipes.insert_many([
        {"recipe_id": f"m{i}", "user_id": "system_seeder", "title": f"Chicken rice {i}",
         "ingredients": [{"item": "chicken", "amount": "1"}, {"item": "rice", "amount": "1 cup"}], "steps": ["x"]} for i in range(3)]))
    app = FastAPI(); app.state.db = db; app.include_router(pr.router, prefix="/api")
    c = TestClient(app)
    first = c.post("/api/pantry/suggest-meal", json={"match_type": "all", "more": True}).json()
    ids = [m["recipe_id"] for m in first["saved_recipe_matches"]]
    assert sorted(ids) == ["m0", "m1", "m2"] and asked["ai"] == 0
    again = c.post("/api/pantry/suggest-meal", json={"match_type": "all", "more": True, "exclude_ids": ids}).json()
    assert again["saved_recipe_matches"] == [] and again["library_exhausted"] is True
    assert again["ai_suggestions"] == [] and asked["ai"] == 0     # never the AI on "Show me more"
