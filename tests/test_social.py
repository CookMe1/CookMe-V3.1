"""Comments, replies, filter, reporting, account deletion — with two users."""
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
import routes.social_routes as sr
import routes.auth_routes as ar
import public_sharing as ps
from test_public_sharing import good, ME, OTHER

THIRD = {"user_id": "u_3", "email": "3@x.y", "name": "Third Person"}
FOURTH = {"user_id": "u_4", "email": "4@x.y", "name": "Fourth"}
current = {"u": ME}

@pytest.fixture()
def env(monkeypatch):
    async def fake_user(request, db): return current["u"]
    for m in (rr, sr, ar): monkeypatch.setattr(m, "get_current_user", fake_user)
    app = FastAPI()
    for m in (rr, sr, ar): app.include_router(m.router, prefix="/api")
    app.state.db = AsyncMongoMockClient()["t"]; current["u"] = ME
    return TestClient(app)

def publish(c):
    rid = c.post("/api/recipes", json=good()).json()["recipe_id"]
    r = c.post(f"/api/recipes/{rid}/publish", json={"consent": True, "terms_version": ps.TERMS_VERSION, "show_name": True}).json()
    assert r["status"] == "public", r
    return rid

def test_comment_and_reply_thread(env):
    rid = publish(env); current["u"] = OTHER
    c1 = env.post(f"/api/social/recipes/{rid}/comments", json={"text": "Made this last night, lovely!"}).json()
    r1 = env.post(f"/api/social/recipes/{rid}/comments", json={"text": "Glad you liked it", "parent_id": c1["comment_id"]})
    assert r1.status_code == 200
    # reply to a reply stays one level deep
    r2 = env.post(f"/api/social/recipes/{rid}/comments", json={"text": "Agreed!", "parent_id": r1.json()["comment_id"]}).json()
    data = env.get(f"/api/social/recipes/{rid}/comments").json()
    assert data["count"] == 3 and len(data["comments"]) == 1 and len(data["comments"][0]["replies"]) == 2
    assert "user_id" not in data["comments"][0] and data["comments"][0]["author_name"] == "Olly"

def test_filter_blocks_contact_details_and_profanity(env):
    rid = publish(env); current["u"] = OTHER
    for t in ["call me on 07700 900123", "email bob@gmail.com", "this is shit", "see www.mysite.com", "add me on whatsapp"]:
        r = env.post(f"/api/social/recipes/{rid}/comments", json={"text": t})
        assert r.status_code == 400, t
    assert env.get(f"/api/social/recipes/{rid}/comments").json()["count"] == 0

def test_cannot_comment_on_someone_elses_private_recipe(env):
    rid = env.post("/api/recipes", json=good()).json()["recipe_id"]; current["u"] = OTHER
    assert env.post(f"/api/social/recipes/{rid}/comments", json={"text": "hi"}).status_code == 404

def test_delete_rules(env):
    rid = publish(env); current["u"] = OTHER
    cid = env.post(f"/api/social/recipes/{rid}/comments", json={"text": "Nice"}).json()["comment_id"]
    current["u"] = THIRD; assert env.delete(f"/api/social/comments/{cid}").status_code == 403
    current["u"] = ME; assert env.delete(f"/api/social/comments/{cid}").status_code == 200   # recipe owner can remove

def test_reports_hide_comment_and_take_down_recipe(env):
    rid = publish(env); current["u"] = OTHER
    cid = env.post(f"/api/social/recipes/{rid}/comments", json={"text": "Nice"}).json()["comment_id"]
    for u in (ME, THIRD, FOURTH):
        current["u"] = u; assert env.post(f"/api/social/comments/{cid}/report", json={"reason": "spam"}).status_code == 200
    assert env.get(f"/api/social/recipes/{rid}/comments").json()["count"] == 0
    current["u"] = OTHER; env.post(f"/api/social/recipes/{rid}/report", json={"reason": "copied"})   # one report takes it down
    current["u"] = ME
    stored = env.get(f"/api/recipes/{rid}").json()
    assert stored["visibility"] == "private" and stored["publish_status"] == "under_review"
    res = env.post(f"/api/recipes/{rid}/publish", json={"consent": True, "terms_version": ps.TERMS_VERSION})
    assert res.status_code == 403

def test_feed_shows_public_only_and_hides_owner_id(env):
    rid = publish(env); env.post("/api/recipes", json=good(title="Private One"))
    current["u"] = OTHER
    feed = env.get("/api/social/feed").json()["recipes"]
    assert [r["recipe_id"] for r in feed] == [rid] and feed[0]["user_id"] == "shared"

def test_filter_applies_to_recipe_text(env):
    rid = env.post("/api/recipes", json=good(description="Ring me on 07700 900123 for the secret ingredient")).json()["recipe_id"]
    assert not env.get(f"/api/recipes/{rid}/publish-check").json()["ready"]

def test_export_and_delete_account(env):
    rid = publish(env); current["u"] = OTHER
    env.post(f"/api/social/recipes/{rid}/comments", json={"text": "Nice"})
    cid = env.get(f"/api/social/recipes/{rid}/comments").json()["comments"][0]["comment_id"]
    current["u"] = ME
    env.post(f"/api/social/recipes/{rid}/comments", json={"text": "Thanks!", "parent_id": cid})
    assert env.get("/api/auth/me/export").json()["recipes"]
    assert env.request("DELETE", "/api/auth/me", json={}).status_code == 400
    current["u"] = OTHER
    assert env.request("DELETE", "/api/auth/me", json={"confirm": True}).status_code == 200
    current["u"] = ME
    assert env.get(f"/api/social/recipes/{rid}/comments").json()["count"] == 0   # their comment and the replies under it are gone
    assert env.get(f"/api/recipes/{rid}").status_code == 200                     # other people's data untouched

def test_share_to_social_with_note(env):
    rid = env.post("/api/recipes", json=good()).json()["recipe_id"]
    body = {"consent": True, "terms_version": ps.TERMS_VERSION}
    bad = env.post(f"/api/recipes/{rid}/publish", json={**body, "caption": "call me 07700 900123"}).json()
    assert bad["status"] == "needs_changes" and any(i["field"] == "caption" for i in bad["issues"])
    ok = env.post(f"/api/recipes/{rid}/publish", json={**body, "caption": "My nan's Sunday soup"}).json()
    assert ok["status"] == "public"
    current["u"] = OTHER
    feed = env.get("/api/social/feed").json()["recipes"]
    assert feed[0]["share_caption"] == "My nan's Sunday soup"
