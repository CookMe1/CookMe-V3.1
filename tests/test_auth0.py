"""Auth0 login: token verification and the 'unverified email' guard. No network needed (we sign tokens ourselves)."""
import sys, time, asyncio, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
os.environ.setdefault("JWT_SECRET", "test-secret")
import jwt, pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from routes import auth_routes

DOMAIN, CID = "dev-test.eu.auth0.com", "client123"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)

class FakeJWKS:
    def get_signing_key_from_jwt(self, t):
        class K: key = KEY.public_key()
        return K

@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("AUTH0_DOMAIN", f"https://{DOMAIN}/")
    monkeypatch.setenv("AUTH0_CLIENT_ID", CID)
    auth_routes._auth0_jwks.clear(); auth_routes._auth0_jwks[DOMAIN] = FakeJWKS()

def tok(**over):
    c = {"iss": f"https://{DOMAIN}/", "aud": CID, "exp": int(time.time()) + 300, "email": "a@b.com", "email_verified": True}
    c.update(over); return jwt.encode(c, KEY, algorithm="RS256")

def test_valid_token():
    assert auth_routes.verify_auth0_id_token(tok())["email"] == "a@b.com"

@pytest.mark.parametrize("bad", [dict(aud="other"), dict(iss="https://evil.com/"), dict(exp=int(time.time()) - 10)])
def test_rejects_bad_claims(bad):
    with pytest.raises(HTTPException) as e: auth_routes.verify_auth0_id_token(tok(**bad))
    assert e.value.status_code == 401

def test_rejects_wrong_signature():
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    t = jwt.encode({"iss": f"https://{DOMAIN}/", "aud": CID, "exp": int(time.time()) + 300}, other, algorithm="RS256")
    with pytest.raises(HTTPException): auth_routes.verify_auth0_id_token(t)

def test_not_configured(monkeypatch):
    monkeypatch.delenv("AUTH0_DOMAIN")
    with pytest.raises(HTTPException) as e: auth_routes.verify_auth0_id_token(tok())
    assert e.value.status_code == 503

class Req:
    def __init__(self, db, body): self.app = type("A", (), {"state": type("S", (), {"db": db})()})(); self._b = body
    async def json(self): return self._b

def test_callback_creates_user_and_blocks_unverified():
    from mongomock_motor import AsyncMongoMockClient
    db = AsyncMongoMockClient()["t"]
    async def run():
        r = await auth_routes.auth0_callback(Req(db, {"id_token": tok(name="Ann")}), None)
        assert r["email"] == "a@b.com" and r["access_token"] and r["auth_provider"] == "auth0"
        with pytest.raises(HTTPException) as e:
            await auth_routes.auth0_callback(Req(db, {"id_token": tok(email_verified=False)}), None)
        assert e.value.status_code == 403
        assert await db.users.count_documents({}) == 1
    asyncio.run(run())
