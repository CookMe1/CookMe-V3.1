"""Comments, replies, reporting and the community feed for shared recipes."""
import base64
import io
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

import account_ops
import content_filter
import notify
import public_sharing as ps
from auth import get_current_user, is_admin

router = APIRouter(prefix="/social", tags=["social"])

MAX_LEN = 1000
HIDE_AFTER_REPORTS = 3          # distinct reporters before a comment is hidden pending review
MAX_PER_MINUTE = 5


class CommentIn(BaseModel):
    text: str
    parent_id: Optional[str] = None


class ReportIn(BaseModel):
    reason: Optional[str] = "other"
    details: Optional[str] = None


def display_name(user: dict) -> str:
    """First name + last initial, e.g. "Kabir P." Full names are never shown to other users."""
    parts = (user.get("name") or "").split()
    if not parts:
        return "Grubly user"
    return parts[0] if len(parts) == 1 else f"{parts[0]} {parts[-1][0]}."


async def _visible_recipe(db, user, recipe_id):
    recipe = await db.recipes.find_one({"recipe_id": recipe_id, **ps.shared_or_own(user["user_id"])}, {"_id": 0})
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe


def _public(c: dict, viewer: dict, recipe_owner: str) -> dict:
    return {
        "comment_id": c["comment_id"], "parent_id": c.get("parent_id"), "author_name": c.get("author_name"),
        "text": c["text"], "created_at": c["created_at"],
        "mine": c["user_id"] == viewer["user_id"],
        "can_delete": c["user_id"] == viewer["user_id"] or recipe_owner == viewer["user_id"],
    }


@router.get("/recipes/{recipe_id}/comments")
async def list_comments(recipe_id: str, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    recipe = await _visible_recipe(db, user, recipe_id)
    rows = await db.comments.find({"recipe_id": recipe_id, "status": "visible"}, {"_id": 0}).sort("created_at", 1).to_list(300)
    owner = recipe.get("user_id")
    tops = [_public(c, user, owner) for c in rows if not c.get("parent_id")]
    by_id = {t["comment_id"]: t for t in tops}
    for t in tops:
        t["replies"] = []
    for c in rows:
        if c.get("parent_id") in by_id:
            by_id[c["parent_id"]]["replies"].append(_public(c, user, owner))
    tops.reverse()  # newest conversations first; replies stay oldest-first
    return {"comments": tops, "count": len(rows)}


@router.post("/recipes/{recipe_id}/comments")
async def add_comment(recipe_id: str, data: CommentIn, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    recipe = await _visible_recipe(db, user, recipe_id)
    text = re.sub(r"[ \t]+", " ", (data.text or "")).strip()
    if not text:
        raise HTTPException(status_code=400, detail="Write something first.")
    if len(text) > MAX_LEN:
        raise HTTPException(status_code=400, detail=f"Please keep comments under {MAX_LEN} characters.")

    issues = content_filter.problems(text)
    if issues:
        raise HTTPException(status_code=400, detail=issues[0]["message"] + " Your comment was not posted.")

    parent_id = data.parent_id
    if parent_id:
        parent = await db.comments.find_one({"comment_id": parent_id, "recipe_id": recipe_id, "status": "visible"}, {"_id": 0})
        if not parent:
            raise HTTPException(status_code=404, detail="The comment you're replying to is gone.")
        parent_id = parent.get("parent_id") or parent["comment_id"]   # replies stay one level deep

    now = datetime.now(timezone.utc)
    recent = await db.comments.count_documents({"user_id": user["user_id"], "created_at": {"$gte": now - timedelta(minutes=1)}})
    if recent >= MAX_PER_MINUTE:
        raise HTTPException(status_code=429, detail="You're posting very quickly. Please wait a minute.")
    dup = await db.comments.find_one({"user_id": user["user_id"], "text": text, "created_at": {"$gte": now - timedelta(minutes=10)}})
    if dup:
        raise HTTPException(status_code=400, detail="You already posted that.")

    doc = {"comment_id": f"cm_{uuid.uuid4().hex[:12]}", "recipe_id": recipe_id, "parent_id": parent_id,
           "user_id": user["user_id"], "author_name": display_name(user), "text": text,
           "status": "visible", "reporters": [], "created_at": now}
    await db.comments.insert_one(dict(doc))
    return _public(doc, user, recipe.get("user_id"))


@router.delete("/comments/{comment_id}")
async def delete_comment(comment_id: str, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    c = await db.comments.find_one({"comment_id": comment_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Comment not found")
    recipe = await db.recipes.find_one({"recipe_id": c["recipe_id"]}, {"_id": 0, "user_id": 1}) or {}
    if user["user_id"] not in (c["user_id"], recipe.get("user_id")):
        raise HTTPException(status_code=403, detail="You can only delete your own comments")
    await db.comments.delete_many({"$or": [{"comment_id": comment_id}, {"parent_id": comment_id}]})
    return {"message": "Deleted"}


MAX_REPORTS_PER_DAY = 5
MAX_DISMISSED = 3     # after this many reports the admin dismissed, a user can no longer report


async def _guard_reporter(db, user):
    if (user.get("reports_dismissed") or 0) >= MAX_DISMISSED:
        raise HTTPException(status_code=403, detail="Reporting is switched off for your account.")
    since = datetime.now(timezone.utc) - timedelta(days=1)
    if await db.reports.count_documents({"reporter_id": user["user_id"], "created_at": {"$gte": since}}) >= MAX_REPORTS_PER_DAY:
        raise HTTPException(status_code=429, detail="You've sent a lot of reports today. Please try again tomorrow.")


async def _record_report(db, user, kind, target_id, data: ReportIn, target_user_id=None) -> bool:
    await _guard_reporter(db, user)
    if await db.reports.find_one({"kind": kind, "target_id": target_id, "reporter_id": user["user_id"], "status": "open"}):
        return False
    details = "" if content_filter.problems(data.details or "") else (data.details or "")[:500]
    await db.reports.insert_one({
        "report_id": f"rp_{uuid.uuid4().hex[:12]}", "kind": kind, "target_id": target_id, "target_user_id": target_user_id,
        "reporter_id": user["user_id"], "reason": (data.reason or "other")[:30], "details": details,
        "status": "open", "created_at": datetime.now(timezone.utc)})
    return True


async def _alert(what: str, reporter: dict, data: ReportIn, extra: str):
    await notify.alert_admin(
        f"Grubly report: {what}",
        f"{what}\nReason: {data.reason or 'other'}\nDetails: {(data.details or '')[:300]}\n"
        f"Reported by: {reporter.get('name')} ({reporter.get('email')})\n\n{extra}")


async def _report_user(db, reporter, target_uid, data: ReportIn, context: str):
    target = await db.users.find_one({"user_id": target_uid}, {"_id": 0})
    if not target or target_uid in ("system_seeder", reporter["user_id"]):
        raise HTTPException(status_code=400, detail="That user can't be reported.")
    if is_admin(target):
        raise HTTPException(status_code=400, detail="That user can't be reported.")
    await _record_report(db, reporter, "user", target_uid, data, target_uid)
    if target.get("status") not in ("banned",):
        await account_ops.lock_user(db, target_uid)
    await _alert("a user was reported and their account is under review", reporter, data,
                 f"User: {target.get('name')} ({target.get('email')})\nFrom: {context}")
    return {"message": "Thank you. The account has been put under review while we check it."}


@router.post("/comments/{comment_id}/report")
async def report_comment(comment_id: str, data: ReportIn, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    c = await db.comments.find_one({"comment_id": comment_id, "status": "visible"}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Comment not found")
    if c["user_id"] == user["user_id"]:
        raise HTTPException(status_code=400, detail="You can't report your own comment")
    if await _record_report(db, user, "comment", comment_id, data, c["user_id"]):
        await _alert("a comment was reported", user, data, f"Comment: {c['text']}")
    if await db.reports.count_documents({"kind": "comment", "target_id": comment_id}) >= HIDE_AFTER_REPORTS:
        await db.comments.update_one({"comment_id": comment_id}, {"$set": {"status": "hidden"}})
    return {"message": "Thank you. We'll review it."}


@router.post("/comments/{comment_id}/report-user")
async def report_comment_author(comment_id: str, data: ReportIn, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    c = await db.comments.find_one({"comment_id": comment_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Comment not found")
    return await _report_user(db, user, c["user_id"], data, f"Comment: {c['text']}")


@router.post("/recipes/{recipe_id}/report")
async def report_recipe(recipe_id: str, data: ReportIn, request: Request):
    """Reporting a public recipe takes it down straight away (back to private, 'under review') until the admin decides."""
    db = request.app.state.db
    user = await get_current_user(request, db)
    recipe = await _visible_recipe(db, user, recipe_id)
    if recipe.get("user_id") == user["user_id"]:
        raise HTTPException(status_code=400, detail="You can't report your own recipe")
    owner = recipe.get("user_id") if recipe.get("user_id") != "system_seeder" else None
    if await _record_report(db, user, "recipe", recipe_id, data, owner):
        if recipe.get("visibility") == "public":
            await db.recipes.update_one({"recipe_id": recipe_id}, {"$set": {
                "visibility": "private", "publish_status": "under_review", "held_by_review": True}})
        await _alert("a recipe was reported", user, data, f"Recipe: {recipe.get('title')}\n{(recipe.get('description') or '')[:300]}")
    return {"message": "Thank you. The recipe has been taken down while we review it."}


@router.post("/recipes/{recipe_id}/report-user")
async def report_recipe_author(recipe_id: str, data: ReportIn, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    recipe = await _visible_recipe(db, user, recipe_id)
    return await _report_user(db, user, recipe.get("user_id"), data, f"Recipe: {recipe.get('title')}")


@router.post("/users/{user_id}/report")
async def report_user(user_id: str, data: ReportIn, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    return await _report_user(db, user, user_id, data, "Profile")


@router.get("/feed")
async def community_feed(request: Request, limit: int = 20, skip: int = 0):
    """Recipes members chose to share, newest first."""
    db = request.app.state.db
    user = await get_current_user(request, db)
    limit = max(1, min(limit, 50))
    rows = await db.recipes.find({"visibility": "public"}, {"_id": 0}).sort("public_since", -1).skip(max(skip, 0)).to_list(limit)
    ids = [r["recipe_id"] for r in rows]
    counts = {}
    if ids:
        agg = await db.comments.aggregate([
            {"$match": {"recipe_id": {"$in": ids}, "status": "visible"}},
            {"$group": {"_id": "$recipe_id", "n": {"$sum": 1}}},
        ]).to_list(len(ids))
        counts = {a["_id"]: a["n"] for a in agg}
    out = []
    for r in rows:
        r = ps.mask_owner(r, user["user_id"])
        r["comment_count"] = counts.get(r["recipe_id"], 0)
        out.append(r)
    return {"recipes": out}


# ── "I made this": a photo and a few words about a recipe you cooked ──────────────────────────────────────────────
# Works for any recipe the person can see (master library, shared, or their own). It shares only the photo and note,
# never the recipe text, so recipes from open-licence sources can be talked about freely.
MAX_NOTE = 300
MAX_MADE_PER_DAY = 5
MAX_PHOTO_BYTES = 8_000_000
HIDE_MADE_AFTER_REPORTS = 3


class MadeIn(BaseModel):
    recipe_id: str
    note: Optional[str] = ""
    image_data: str          # data URL of the person's own photo


def _shrink_photo(data_url: str) -> bytes:
    m = re.match(r"^data:image/(?:jpeg|jpg|png|webp);base64,(.+)$", data_url or "", re.S)
    if not m:
        raise HTTPException(status_code=400, detail="Please add a photo of what you made (JPG, PNG or WebP).")
    try:
        raw = base64.b64decode(m.group(1))
        if len(raw) > MAX_PHOTO_BYTES:
            raise HTTPException(status_code=400, detail="That photo is too large. Please choose one under 8 MB.")
        from PIL import Image, ImageOps
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
        im.thumbnail((900, 900))
        out = io.BytesIO()
        im.save(out, "JPEG", quality=78, optimize=True)
        return out.getvalue()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="We couldn't read that photo. Please try another one.")


def _made_public(p: dict, viewer: dict) -> dict:
    return {"post_id": p["post_id"], "recipe_id": p["recipe_id"], "recipe_title": p.get("recipe_title"),
            "author_name": p.get("author_name"), "note": p.get("note") or "", "photo_url": f"/api/social/made/{p['post_id']}/photo",
            "created_at": p["created_at"], "mine": p["user_id"] == viewer["user_id"]}


@router.post("/made")
async def post_made_it(data: MadeIn, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    recipe = await _visible_recipe(db, user, data.recipe_id)
    note = re.sub(r"[ \t]+", " ", (data.note or "")).strip()
    if len(note) > MAX_NOTE:
        raise HTTPException(status_code=400, detail=f"Please keep your note under {MAX_NOTE} characters.")
    for p in content_filter.problems(note)[:1]:
        raise HTTPException(status_code=400, detail=p["message"] + " Your post was not shared.")
    now = datetime.now(timezone.utc)
    if await db.made_posts.count_documents({"user_id": user["user_id"], "created_at": {"$gte": now - timedelta(days=1)}}) >= MAX_MADE_PER_DAY:
        raise HTTPException(status_code=429, detail="You've shared a lot today. Please try again tomorrow.")
    photo = _shrink_photo(data.image_data)
    doc = {"post_id": f"mp_{uuid.uuid4().hex[:12]}", "recipe_id": recipe["recipe_id"], "recipe_title": recipe.get("title"),
           "user_id": user["user_id"], "author_name": display_name(user), "note": note, "photo": photo,
           "status": "visible", "created_at": now}
    await db.made_posts.insert_one(dict(doc))
    return _made_public(doc, user)


@router.get("/made")
async def list_made(request: Request, limit: int = 20, skip: int = 0, recipe_id: Optional[str] = None):
    db = request.app.state.db
    user = await get_current_user(request, db)
    q = {"status": "visible"}
    if recipe_id:
        q["recipe_id"] = recipe_id
    rows = await db.made_posts.find(q, {"_id": 0, "photo": 0}).sort("created_at", -1).skip(max(skip, 0)).to_list(max(1, min(limit, 50)))
    return {"posts": [_made_public(r, user) for r in rows]}


@router.get("/made/{post_id}/photo")
async def made_photo(post_id: str, request: Request):
    """The photo itself. No sign-in needed so it can be used in an <img> tag; hidden posts are not served."""
    row = await request.app.state.db.made_posts.find_one({"post_id": post_id, "status": "visible"}, {"_id": 0, "photo": 1})
    if not row or not row.get("photo"):
        raise HTTPException(status_code=404, detail="Photo not found")
    return Response(content=bytes(row["photo"]), media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})


@router.delete("/made/{post_id}")
async def delete_made(post_id: str, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    p = await db.made_posts.find_one({"post_id": post_id}, {"_id": 0, "user_id": 1})
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    if p["user_id"] != user["user_id"] and not is_admin(user):
        raise HTTPException(status_code=403, detail="You can only delete your own posts")
    await db.made_posts.delete_one({"post_id": post_id})
    return {"message": "Deleted"}


@router.post("/made/{post_id}/report")
async def report_made(post_id: str, data: ReportIn, request: Request):
    db = request.app.state.db
    user = await get_current_user(request, db)
    p = await db.made_posts.find_one({"post_id": post_id, "status": "visible"}, {"_id": 0, "photo": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    if p["user_id"] == user["user_id"]:
        raise HTTPException(status_code=400, detail="You can't report your own post")
    if await _record_report(db, user, "made_post", post_id, data, p["user_id"]):
        await _alert("a photo post was reported", user, data, f"Post: {p.get('note')}\nRecipe: {p.get('recipe_title')}")
    if await db.reports.count_documents({"kind": "made_post", "target_id": post_id}) >= HIDE_MADE_AFTER_REPORTS:
        await db.made_posts.update_one({"post_id": post_id}, {"$set": {"status": "hidden"}})
    return {"message": "Thank you. We'll review it."}
