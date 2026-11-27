"""
auth_routes.py — Social-only authentication
=============================================
All login/registration is via OAuth providers.
No usernames or passwords are stored.

Supported providers:
  - Google (via Emergent Auth)
  - Facebook
  - Apple
  - Twitter/X
  - Instagram (uses Facebook OAuth)
"""

from fastapi import APIRouter, HTTPException, Request, Response
from datetime import datetime, timedelta, timezone
import httpx
import logging
import os
import jwt
from jwt import PyJWKClient
from starlette.concurrency import run_in_threadpool

import account_ops
from auth import create_access_token, get_current_user, generate_user_id, is_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Helper ────────────────────────────────────────────────────────────────────

async def _upsert_oauth_user(db, email: str, name: str, avatar: str, provider: str) -> dict:
    """Find or create a user from an OAuth provider. Returns the user doc."""
    user_doc = await db.users.find_one({"email": email}, {"_id": 0})
    banned = await db.banned_emails.find_one({"email": (email or "").lower()})
    if banned or (user_doc and user_doc.get("status") == "banned"):
        raise HTTPException(status_code=403, detail="This account has been closed.")

    if user_doc:
        update_fields = {"auth_provider": provider}
        if name:
            update_fields["name"] = name
        if avatar:
            update_fields["avatar"] = avatar
        await db.users.update_one(
            {"user_id": user_doc["user_id"]},
            {"$set": update_fields},
        )
        user_doc.update(update_fields)
        return user_doc

    user_id = generate_user_id()
    user_doc = {
        "user_id": user_id,
        "email": email,
        "name": name or email.split("@")[0],
        "avatar": avatar or f"https://ui-avatars.com/api/?name={name or 'User'}&background=D35400&color=fff",
        "bio": "",
        "auth_provider": provider,
        "is_food_blogger": False,
        "social_enabled": True,
        "followers_count": 0,
        "following_count": 0,
        "recipes_count": 0,
        "created_at": datetime.now(timezone.utc),
    }
    await db.users.insert_one(user_doc)
    return user_doc


async def _create_session(db, user_id: str, session_token: str, response: Response):
    """Store session in MongoDB and set cookie."""
    session_doc = {
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
        "created_at": datetime.now(timezone.utc),
    }
    await db.user_sessions.delete_many({"user_id": user_id})
    await db.user_sessions.insert_one(session_doc)

    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=30 * 24 * 60 * 60,
        path="/",
        httponly=True,
        secure=False,
        samesite="lax",
    )


# ── Google OAuth (via Emergent Auth) ──────────────────────────────────────────

@router.post("/google/callback")
async def google_callback(request: Request, response: Response):
    db = request.app.state.db
    body = await request.json()
    session_id = body.get("session_id")

    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID required")

    async with httpx.AsyncClient() as client:
        try:
            auth_response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id},
                timeout=10.0,
            )
            auth_response.raise_for_status()
            auth_data = auth_response.json()
        except Exception as e:
            logger.error(f"Google OAuth error: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to verify session: {str(e)}")

    email = auth_data.get("email")
    name = auth_data.get("name")
    picture = auth_data.get("picture")
    session_token = auth_data.get("session_token")

    if not email or not session_token:
        raise HTTPException(status_code=400, detail="Invalid session data")

    user_doc = await _upsert_oauth_user(db, email, name, picture, "google")
    await _create_session(db, user_doc["user_id"], session_token, response)

    access_token = create_access_token(data={"sub": user_doc["user_id"]})

    user_response = await db.users.find_one(
        {"user_id": user_doc["user_id"]}, {"_id": 0}
    )
    user_response["access_token"] = access_token
    return user_response


# ── Email / password and more (via Auth0) ─────────────────────────────────────
# Needs two env vars on the server: AUTH0_DOMAIN (e.g. dev-abc123.eu.auth0.com) and AUTH0_CLIENT_ID.
# The browser logs in on Auth0's own page and sends us the signed ID token; we verify it here.
# No passwords ever touch Grubly.

_auth0_jwks = {}


def _auth0_settings():
    domain = (os.environ.get("AUTH0_DOMAIN") or "").strip().replace("https://", "").strip("/")
    client_id = (os.environ.get("AUTH0_CLIENT_ID") or "").strip()
    return domain, client_id


def verify_auth0_id_token(token: str) -> dict:
    """Check the signature, issuer, audience and expiry of an Auth0 ID token. Returns its claims."""
    domain, client_id = _auth0_settings()
    if not domain or not client_id:
        raise HTTPException(status_code=503, detail="Email login is not set up yet")
    jwks = _auth0_jwks.setdefault(domain, PyJWKClient(f"https://{domain}/.well-known/jwks.json"))
    try:
        key = jwks.get_signing_key_from_jwt(token).key
        return jwt.decode(token, key, algorithms=["RS256"], audience=client_id, issuer=f"https://{domain}/")
    except Exception as e:
        logger.warning(f"Auth0 token rejected: {e}")
        raise HTTPException(status_code=401, detail="Invalid login token")


@router.post("/auth0/callback")
async def auth0_callback(request: Request, response: Response):
    db = request.app.state.db
    body = await request.json()
    id_token = body.get("id_token")
    if not id_token:
        raise HTTPException(status_code=400, detail="ID token required")

    claims = await run_in_threadpool(verify_auth0_id_token, id_token)
    email = (claims.get("email") or "").lower()
    if not email:
        raise HTTPException(status_code=400, detail="No email on this account")
    # Never link an unverified email to an existing Grubly account (stops account takeover).
    if not claims.get("email_verified"):
        raise HTTPException(status_code=403, detail="Please verify your email first (check your inbox), then log in again")

    user_doc = await _upsert_oauth_user(db, email, claims.get("name"), claims.get("picture"), "auth0")
    access_token = create_access_token(data={"sub": user_doc["user_id"]})
    user_response = await db.users.find_one({"user_id": user_doc["user_id"]}, {"_id": 0})
    user_response["access_token"] = access_token
    return user_response



# ── Facebook / Instagram OAuth ────────────────────────────────────────────────

@router.post("/facebook/callback")
async def facebook_callback(request: Request, response: Response):
    """Exchange a Facebook access token for a Grubly session.
    Instagram login also routes here since it uses Facebook's OAuth."""
    db = request.app.state.db
    body = await request.json()
    fb_access_token = body.get("access_token")
    provider = body.get("provider", "facebook")

    if not fb_access_token:
        raise HTTPException(status_code=400, detail="Facebook access token required")

    async with httpx.AsyncClient() as client:
        try:
            fb_response = await client.get(
                "https://graph.facebook.com/me",
                params={
                    "fields": "id,name,email,picture.type(large)",
                    "access_token": fb_access_token,
                },
                timeout=10.0,
            )
            fb_response.raise_for_status()
            fb_data = fb_response.json()
        except Exception as e:
            logger.error(f"Facebook OAuth error: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to verify Facebook token: {str(e)}")

    email = fb_data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by Facebook. Please grant email permission.")

    name = fb_data.get("name")
    picture = fb_data.get("picture", {}).get("data", {}).get("url")

    user_doc = await _upsert_oauth_user(db, email, name, picture, provider)
    access_token = create_access_token(data={"sub": user_doc["user_id"]})
    await _create_session(db, user_doc["user_id"], access_token, response)

    user_response = await db.users.find_one(
        {"user_id": user_doc["user_id"]}, {"_id": 0}
    )
    user_response["access_token"] = access_token
    return user_response


# ── Twitter/X OAuth 2.0 ──────────────────────────────────────────────────────

@router.post("/twitter/callback")
async def twitter_callback(request: Request, response: Response):
    """Exchange a Twitter/X OAuth 2.0 access token for a Grubly session."""
    db = request.app.state.db
    body = await request.json()
    twitter_access_token = body.get("access_token")

    if not twitter_access_token:
        raise HTTPException(status_code=400, detail="Twitter access token required")

    async with httpx.AsyncClient() as client:
        try:
            tw_response = await client.get(
                "https://api.x.com/2/users/me",
                params={"user.fields": "name,profile_image_url,description"},
                headers={"Authorization": f"Bearer {twitter_access_token}"},
                timeout=10.0,
            )
            tw_response.raise_for_status()
            tw_data = tw_response.json().get("data", {})
        except Exception as e:
            logger.error(f"Twitter OAuth error: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to verify Twitter token: {str(e)}")

    name = tw_data.get("name", "")
    username = tw_data.get("username", "")
    picture = tw_data.get("profile_image_url", "").replace("_normal", "_400x400")

    email = body.get("email")
    if not email:
        email = f"{username}@twitter.cookme.app"

    user_doc = await _upsert_oauth_user(db, email, name, picture, "twitter")
    access_token = create_access_token(data={"sub": user_doc["user_id"]})
    await _create_session(db, user_doc["user_id"], access_token, response)

    user_response = await db.users.find_one(
        {"user_id": user_doc["user_id"]}, {"_id": 0}
    )
    user_response["access_token"] = access_token
    return user_response


# ── Apple Sign In ─────────────────────────────────────────────────────────────

@router.post("/apple/callback")
async def apple_callback(request: Request, response: Response):
    """Exchange an Apple identity token for a Grubly session."""
    db = request.app.state.db
    body = await request.json()
    id_token = body.get("id_token")
    apple_user = body.get("user", {})

    if not id_token:
        raise HTTPException(status_code=400, detail="Apple ID token required")

    from jose import jwt as jose_jwt, JWTError
    try:
        claims = jose_jwt.get_unverified_claims(id_token)
    except JWTError as e:
        logger.error(f"Apple JWT decode error: {e}")
        raise HTTPException(status_code=400, detail="Invalid Apple ID token")

    email = claims.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by Apple")

    name = ""
    if apple_user:
        first = apple_user.get("name", {}).get("firstName", "")
        last = apple_user.get("name", {}).get("lastName", "")
        name = f"{first} {last}".strip()

    existing = await db.users.find_one({"email": email})
    if existing and not name:
        name = existing.get("name", "")

    user_doc = await _upsert_oauth_user(db, email, name, None, "apple")
    access_token = create_access_token(data={"sub": user_doc["user_id"]})
    await _create_session(db, user_doc["user_id"], access_token, response)

    user_response = await db.users.find_one(
        {"user_id": user_doc["user_id"]}, {"_id": 0}
    )
    user_response["access_token"] = access_token
    return user_response


# ── Get Current User ──────────────────────────────────────────────────────────

@router.get("/me")
async def get_me(request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db, allow_restricted=True)
    user = dict(user)
    user["is_admin"] = is_admin(user)
    return user


# ── Download / delete my data (GDPR) ──────────────────────────────────────────

_USER_DATA = account_ops.USER_DATA


@router.get("/me/export")
async def export_my_data(request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    out = {"account": user, "exported_at": datetime.now(timezone.utc).isoformat()}
    for name in _USER_DATA:
        out[name] = await db[name].find({"user_id": user["user_id"]}, {"_id": 0}).to_list(10000)
    out["sharing_consents"] = await db.recipe_consents.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(10000)
    return out


@router.delete("/me")
async def delete_my_account(request: Request, response: Response):
    """Erase the account and everything the user created. Replies under their comments go too.
    Public-sharing consent records are kept (without the account) as proof of the licence given."""
    db = request.app.state.db
    user = await get_current_user(request, db)
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    if body.get("confirm") is not True:
        raise HTTPException(status_code=400, detail="Confirmation required")
    uid = user["user_id"]
    await account_ops.erase_user_content(db, uid)
    await db.users.delete_one({"user_id": uid})
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Your account and data have been deleted"}


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(request: Request, response: Response):
    db = request.app.state.db

    session_token = request.cookies.get("session_token")
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]

    if session_token and session_token.count(".") != 2:
        await db.user_sessions.delete_one({"session_token": session_token})

    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out successfully"}
