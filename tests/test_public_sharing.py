"""Privacy + 'make my recipe public' flow, with two different users. Needs the routes importable (emergentintegrations)."""
import os, sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
os.environ.setdefault("JWT_SECRET", "x")
pytest.importorskip("emergentintegrations")
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
import routes.recipe_routes as rr
import public_sharing as ps

ME, OTHER = {"user_id": "u_me", "email": "me@x.y", "name": "Kabz"}, {"user_id": "u_other", "email": "o@x.y", "name": "Olly"}
current = {"u": ME}

def good(**over):
    r = {"title": "Grandma's Lentil Soup", "description": "A thick, cosy lentil soup that my family makes every winter.",
         "image": "data:image/jpeg;base64,AAAA", "prep_time": "10 min", "cook_time": "40 min", "servings": 4, "difficulty": "Easy",
         "ingredients": [{"item": "red lentils", "amount": "250 g"}, {"item": "onion", "amount": "1"}, {"item": "carrots", "amount": "2"}, {"item": "stock", "amount": "1 litre"}],
         "steps": ["Soften the chopped onion and carrots in oil for five minutes.", "Add the lentils and stock, then simmer for thirty minutes until soft.", "Blend half the soup and season well."],
         "tags": [], "category": None, "cuisine": None}
    r.update(over); return r

@pytest.fixture()
def env(monkeypatch):
    async def fake_user(request, db): return current["u"]
    monkeypatch.setattr(rr, "get_current_user", fake_user)
    app = FastAPI(); app.include_router(rr.router, prefix="/api"); app.state.db = AsyncMongoMockClient()["t"]
    current["u"] = ME
    return TestClient(app)

def create(c, **over):
    r = c.post("/api/recipes", json=good(**over)); assert r.status_code == 200, r.text; return r.json()["recipe_id"]

def as_user(u): current["u"] = u

def test_private_recipe_is_invisible_to_others(env):
    rid = create(env, category="healthy"); as_user(OTHER)
    assert env.get(f"/api/recipes/{rid}").status_code == 404
    assert rid not in [r["recipe_id"] for r in env.get("/api/recipes/master/all").json()]
    assert rid not in [r["recipe_id"] for r in env.get("/api/recipes/category/healthy").json()]
    assert rid not in [r["recipe_id"] for r in env.get("/api/recipes/search?q=lentil").json()["recipes"]]
    as_user(ME); assert env.get(f"/api/recipes/{rid}").status_code == 200   # the owner still can

def test_imported_recipe_cannot_go_public(env):
    rid = create(env, source_url="https://someblog.com/soup", tags=["Imported"])
    r = env.get(f"/api/recipes/{rid}/publish-check").json()
    assert not r["ready"] and any(i["field"] == "source" for i in r["issues"])

def test_incomplete_recipe_goes_back_with_a_list(env):
    rid = create(env, description="", image=None, steps=["Step 1"], ingredients=[{"item": "egg", "amount": ""}])
    res = env.post(f"/api/recipes/{rid}/publish", json={"consent": True, "terms_version": ps.TERMS_VERSION}).json()
    assert res["status"] == "needs_changes"
    fields = {i["field"] for i in res["issues"]}
    assert {"image", "steps", "ingredients"} <= fields        # a blank description is now filled in when the recipe is saved
    stored = env.get(f"/api/recipes/{rid}").json()
    assert stored["visibility"] != "public" and stored["publish_status"] == "needs_changes" and stored["publish_issues"]

def test_consent_is_required_and_recorded(env):
    rid = create(env)
    assert env.post(f"/api/recipes/{rid}/publish", json={}).status_code == 400
    assert env.post(f"/api/recipes/{rid}/publish", json={"consent": True, "terms_version": "old"}).status_code == 400
    assert env.get(f"/api/recipes/{rid}").json().get("visibility") != "public"
    ok = env.post(f"/api/recipes/{rid}/publish", json={"consent": True, "terms_version": ps.TERMS_VERSION, "show_name": True})
    assert ok.json()["status"] == "public"
    doc = env.app.state.db.recipe_consents
    import asyncio
    rec = asyncio.run(doc.find_one({"recipe_id": rid}))
    assert rec["user_id"] == "u_me" and rec["terms_version"] == ps.TERMS_VERSION and rec["consent_text_sha256"] == ps.CONSENT_HASH

def test_public_recipe_is_visible_everywhere_and_unpublish_hides_it(env):
    rid = create(env)
    env.post(f"/api/recipes/{rid}/publish", json={"consent": True, "terms_version": ps.TERMS_VERSION, "show_name": False})
    as_user(OTHER)
    got = env.get(f"/api/recipes/{rid}"); assert got.status_code == 200 and got.json()["public_author"] == "CookMe community"
    assert rid in [r["recipe_id"] for r in env.get("/api/recipes/search?q=lentil").json()["recipes"]]
    assert env.get("/api/recipes/stats").json()["total"] == 1
    as_user(ME); assert env.post(f"/api/recipes/{rid}/unpublish").json()["status"] == "private"
    as_user(OTHER); assert env.get(f"/api/recipes/{rid}").status_code == 404
    assert env.get("/api/recipes/stats").json()["total"] == 0

def test_editing_a_public_recipe_rechecks_it(env):
    rid = create(env); env.post(f"/api/recipes/{rid}/publish", json={"consent": True, "terms_version": ps.TERMS_VERSION})
    r = env.put(f"/api/recipes/{rid}", json={"description": ""}).json()
    assert r["visibility"] == "private" and r["publish_status"] == "needs_changes"
    as_user(OTHER); assert env.get(f"/api/recipes/{rid}").status_code == 404
    as_user(ME); env.put(f"/api/recipes/{rid}", json={"description": "A thick, cosy lentil soup that my family makes every winter."})
    assert env.post(f"/api/recipes/{rid}/publish", json={"consent": True, "terms_version": ps.TERMS_VERSION}).json()["status"] == "public"

def test_only_owner_can_edit_or_publish(env):
    rid = create(env); as_user(OTHER)
    assert env.put(f"/api/recipes/{rid}", json={"title": "Hijacked"}).status_code == 404
    assert env.post(f"/api/recipes/{rid}/publish", json={"consent": True, "terms_version": ps.TERMS_VERSION}).status_code == 404

def test_duplicate_public_title_is_refused(env):
    a = create(env); env.post(f"/api/recipes/{a}/publish", json={"consent": True, "terms_version": ps.TERMS_VERSION})
    as_user(OTHER); b = create(env)
    res = env.post(f"/api/recipes/{b}/publish", json={"consent": True, "terms_version": ps.TERMS_VERSION}).json()
    assert res["status"] == "needs_changes" and any("already exists" in i["message"] for i in res["issues"])

def test_links_contact_details_and_stock_photos_are_refused():
    assert any(i["field"] == "text" for i in ps.check_recipe(good(description="Best soup ever, see www.myblog.com for more")))
    assert any(i["field"] == "text" for i in ps.check_recipe(good(description="A lovely soup. Email me at a.b@mail.com for tips and tricks.")))
    assert any(i["field"] == "image" for i in ps.check_recipe(good(image="https://images.unsplash.com/photo-1546069901-ba9599a7e63c")))
    assert ps.check_recipe(good()) == []

def test_other_users_ids_and_hidden_names_are_masked(env):
    rid = create(env); env.post(f"/api/recipes/{rid}/publish", json={"consent": True, "terms_version": ps.TERMS_VERSION, "show_name": False})
    env.post(f"/api/recipes/{rid}/save")                     # I favourite it (my id lands in favorited_by)
    as_user(OTHER)
    d = env.get(f"/api/recipes/{rid}").json()
    assert d["user_id"] == "shared" and d["uploader_id"] is None and d["uploader_name"] == "CookMe community"
    assert "u_me" not in str(d["favorited_by"]) and "u_me" not in str(d["hidden_by"])
    s = env.get("/api/recipes/search?q=lentil").json()["recipes"][0]
    assert s["user_id"] == "shared"
    as_user(ME)
    assert env.get(f"/api/recipes/{rid}").json()["user_id"] == "u_me"      # owner sees their own id
