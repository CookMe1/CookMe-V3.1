"""Admin account, report-a-user lock, under-review page data, ban and reinstate."""
import os, sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
os.environ.setdefault("JWT_SECRET", "x")
os.environ["ADMIN_EMAILS"] = "boss@x.y"
pytest.importorskip("emergentintegrations")
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient
import auth
import routes.recipe_routes as rr, routes.social_routes as sr, routes.auth_routes as ar, routes.admin_routes as adm
import public_sharing as ps
from test_public_sharing import good

BOSS = {"user_id": "u_boss", "email": "boss@x.y", "name": "Boss Person", "auth_provider": "auth0"}
ME = {"user_id": "u_me", "email": "me@x.y", "name": "Kabz Pat"}
BAD = {"user_id": "u_bad", "email": "bad@x.y", "name": "Bad Actor"}
cur = {"u": ME}

@pytest.fixture()
def env(monkeypatch):
    app = FastAPI()
    for m in (rr, sr, ar, adm): app.include_router(m.router, prefix="/api")
    db = AsyncMongoMockClient()["t"]; app.state.db = db
    import asyncio
    async def seed():
        for u in (BOSS, ME, BAD): await db.users.insert_one(dict(u))
    asyncio.get_event_loop().run_until_complete(seed()) if False else None
    # real get_current_user against the db, but with the "logged in" user chosen by the test
    async def fake_lookup(request, db_, allow_restricted=False):
        doc = await db_.users.find_one({"user_id": cur["u"]["user_id"]}, {"_id": 0})
        if doc.get("status") in ("under_review", "banned") and not allow_restricted:
            raise HTTPException(status_code=403, detail={"code": "account_" + doc["status"]})
        return doc
    for m in (rr, sr, ar): monkeypatch.setattr(m, "get_current_user", fake_lookup)
    async def fake_admin(request, db_):
        u = await fake_lookup(request, db_)
        if not auth.is_admin(u): raise HTTPException(status_code=403, detail="Admins only")
        return u
    monkeypatch.setattr(adm, "require_admin", fake_admin)
    c = TestClient(app)
    c.post  # noqa
    import anyio
    anyio.run(seed)  # insert users (mongomock is loop-agnostic)
    cur["u"] = ME
    return c

def as_(u): cur["u"] = u

def publish(c):
    rid = c.post("/api/recipes", json=good()).json()["recipe_id"]
    assert c.post(f"/api/recipes/{rid}/publish", json={"consent": True, "terms_version": ps.TERMS_VERSION}).json()["status"] == "public"
    return rid

def test_only_listed_verified_admin(env):
    assert auth.is_admin(BOSS)
    assert not auth.is_admin({**BOSS, "auth_provider": "facebook"})     # provider must verify email
    assert not auth.is_admin(ME)
    as_(ME); assert env.get("/api/admin/reports").status_code == 403
    as_(BOSS); assert env.get("/api/admin/reports").status_code == 200
    assert env.get("/api/auth/me").json()["is_admin"] is True

def test_report_user_locks_account_and_hides_content(env):
    as_(BAD); rid = publish(env)
    as_(ME)
    r = env.post(f"/api/social/recipes/{rid}/report-user", json={"reason": "abuse", "details": "rude"})
    assert r.status_code == 200
    as_(BAD)
    assert env.get("/api/recipes").status_code == 403 and env.get("/api/recipes").json()["detail"]["code"] == "account_under_review"
    assert env.get("/api/auth/me").json()["status"] == "under_review"      # /me still answers so the app can show the page
    as_(ME); assert env.get(f"/api/recipes/{rid}").status_code == 404      # their recipe is hidden meanwhile

def test_admin_sees_report_and_reinstates(env):
    as_(BAD); rid = publish(env)
    as_(ME); env.post(f"/api/social/recipes/{rid}/report-user", json={"reason": "abuse"})
    as_(BOSS)
    q = env.get("/api/admin/reports").json()
    item = q["items"][0]; assert q["count"] == 1 and item["kind"] == "user"
    assert item["target"]["email"] == "bad@x.y" and item["target"]["recipes"][0]["title"] == "Grandma's Lentil Soup"
    assert env.post("/api/admin/resolve", json={"kind": "user", "target_id": "u_bad", "action": "reinstate"}).status_code == 200
    as_(BAD); assert env.get("/api/auth/me").json()["status"] == "active"
    as_(ME); assert env.get(f"/api/recipes/{rid}").status_code == 200       # restored
    as_(BOSS); assert env.get("/api/admin/reports").json()["count"] == 0

def test_ban_deletes_content_and_blocks_email(env):
    as_(BAD); rid = publish(env)
    as_(ME); env.post(f"/api/social/recipes/{rid}/report-user", json={"reason": "abuse"})
    as_(BOSS); env.post("/api/admin/resolve", json={"kind": "user", "target_id": "u_bad", "action": "ban"})
    as_(ME); assert env.get(f"/api/recipes/{rid}").status_code == 404
    as_(BAD); assert env.get("/api/auth/me").json()["status"] == "banned"
    import anyio, routes.auth_routes as arm
    async def login():
        db = env.app.state.db
        try: await arm._upsert_oauth_user(db, "bad@x.y", "x", "", "auth0")
        except HTTPException as e: return e.status_code
    assert anyio.run(login) == 403

def test_report_recipe_takes_it_down_and_admin_can_restore_or_remove(env):
    as_(BAD); rid = publish(env)
    as_(ME); env.post(f"/api/social/recipes/{rid}/report", json={"reason": "copied"})
    as_(BAD); assert env.get("/api/recipes").status_code == 200           # recipe report does not lock the person
    as_(BOSS); item = env.get("/api/admin/reports").json()["items"][0]; assert item["kind"] == "recipe" and item["target"]["steps"]
    env.post("/api/admin/resolve", json={"kind": "recipe", "target_id": rid, "action": "reinstate"})
    as_(ME); assert env.get(f"/api/recipes/{rid}").status_code == 200
    env.post(f"/api/social/recipes/{rid}/report", json={"reason": "copied"})     # report again after it was reinstated
    as_(BOSS); env.post("/api/admin/resolve", json={"kind": "recipe", "target_id": rid, "action": "remove"})
    as_(BAD); assert env.get(f"/api/recipes/{rid}").status_code == 404

def test_abuse_guards(env):
    as_(ME)
    assert env.post("/api/social/users/u_boss/report", json={}).status_code == 400      # admins can't be locked by a report
    for _ in range(3):                                                                  # reports the admin dismisses...
        as_(ME); env.post("/api/social/users/u_bad/report", json={"reason": "x"})
        as_(BOSS); env.post("/api/admin/resolve", json={"kind": "user", "target_id": "u_bad", "action": "reinstate"})
    as_(ME); assert env.post("/api/social/users/u_bad/report", json={}).status_code == 403   # ...switch reporting off

def test_real_auth_check_blocks_locked_accounts():
    import anyio
    from starlette.requests import Request
    db = AsyncMongoMockClient()["t2"]
    tok = auth.create_access_token({"sub": "u_bad"})
    req = Request({"type": "http", "headers": [(b"authorization", f"Bearer {tok}".encode())]})
    async def run():
        await db.users.insert_one({"user_id": "u_bad", "email": "b@x.y", "status": "under_review"})
        out = {}
        try: await auth.get_current_user(req, db)
        except HTTPException as e: out["blocked"] = (e.status_code, e.detail)
        out["me"] = (await auth.get_current_user(req, db, allow_restricted=True))["status"]
        return out
    r = anyio.run(run)
    assert r["blocked"] == (403, {"code": "account_under_review"}) and r["me"] == "under_review"
