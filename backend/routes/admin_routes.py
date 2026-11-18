"""Admin review queue: reported users, recipes and comments. Admins are set with the ADMIN_EMAILS env var."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

import account_ops
import notify
from auth import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


class Resolve(BaseModel):
    kind: str          # user | recipe | comment
    target_id: str
    action: str        # reinstate | remove | ban


def _user_card(u: dict) -> dict:
    return {"user_id": u.get("user_id"), "name": u.get("name"), "email": u.get("email"),
            "joined": u.get("created_at"), "status": u.get("status") or "active", "provider": u.get("auth_provider")}


async def _owner(db, uid):
    return _user_card(await db.users.find_one({"user_id": uid}, {"_id": 0}) or {"user_id": uid, "name": "(deleted)"})


async def _target(db, kind, tid):
    if kind == "user":
        u = await db.users.find_one({"user_id": tid}, {"_id": 0})
        if not u:
            return None
        recipes = await db.recipes.find({"user_id": tid}, {"_id": 0, "recipe_id": 1, "title": 1, "visibility": 1, "publish_status": 1}).to_list(20)
        comments = await db.comments.find({"user_id": tid}, {"_id": 0, "text": 1, "status": 1}).sort("created_at", -1).to_list(10)
        return {**_user_card(u), "bio": u.get("bio"), "recipe_count": await db.recipes.count_documents({"user_id": tid}),
                "recipes": recipes, "recent_comments": comments}
    if kind == "recipe":
        r = await db.recipes.find_one({"recipe_id": tid}, {"_id": 0})
        if not r:
            return None
        r = {k: r.get(k) for k in ("recipe_id", "title", "description", "image", "ingredients", "steps", "visibility", "publish_status", "public_author", "source_url")}
        r["owner"] = await _owner(db, (await db.recipes.find_one({"recipe_id": tid}, {"user_id": 1}))["user_id"])
        return r
    if kind == "comment":
        c = await db.comments.find_one({"comment_id": tid}, {"_id": 0})
        if not c:
            return None
        rec = await db.recipes.find_one({"recipe_id": c["recipe_id"]}, {"_id": 0, "title": 1, "recipe_id": 1}) or {}
        return {"text": c["text"], "status": c["status"], "created_at": c["created_at"], "recipe_title": rec.get("title"),
                "recipe_id": c["recipe_id"], "author": await _owner(db, c["user_id"])}
    return None


@router.get("/reports")
async def open_reports(request: Request):
    db = request.app.state.db
    await require_admin(request, db)
    rows = await db.reports.find({"status": "open"}, {"_id": 0}).sort("created_at", 1).to_list(300)
    groups = {}
    for r in rows:
        g = groups.setdefault((r["kind"], r["target_id"]), {"kind": r["kind"], "target_id": r["target_id"], "reports": [], "first_reported": r["created_at"]})
        reporter = await db.users.find_one({"user_id": r["reporter_id"]}, {"_id": 0, "name": 1, "email": 1}) or {}
        g["reports"].append({"reason": r["reason"], "details": r.get("details"), "created_at": r["created_at"],
                             "reporter": f"{reporter.get('name', '?')} ({reporter.get('email', '?')})"})
    out = []
    for g in groups.values():
        g["target"] = await _target(db, g["kind"], g["target_id"])
        if g["target"] is None:      # already deleted (e.g. the account was banned) so nothing left to review
            await _close_reports(db, g["kind"], g["target_id"], "upheld")
            continue
        out.append(g)
    out.sort(key=lambda g: g["first_reported"])
    return {"count": len(out), "items": out}


async def _close_reports(db, kind, tid, status):
    rows = await db.reports.find({"kind": kind, "target_id": tid, "status": "open"}, {"_id": 0}).to_list(1000)
    await db.reports.update_many({"kind": kind, "target_id": tid, "status": "open"},
                                 {"$set": {"status": status, "resolved_at": datetime.now(timezone.utc)}})
    if status == "dismissed":      # reporters whose reports keep getting dismissed lose the ability to report
        for r in rows:
            await db.users.update_one({"user_id": r["reporter_id"]}, {"$inc": {"reports_dismissed": 1}})


@router.post("/resolve")
async def resolve(data: Resolve, request: Request):
    db = request.app.state.db
    await require_admin(request, db)
    kind, tid, action = data.kind, data.target_id, data.action
    if kind not in ("user", "recipe", "comment") or action not in ("reinstate", "remove", "ban"):
        raise HTTPException(status_code=400, detail="Unknown action")

    if kind == "user":
        if action == "remove":
            raise HTTPException(status_code=400, detail="Use ban for users")
        if action == "ban":
            await account_ops.ban_user(db, tid)
        else:
            await account_ops.unlock_user(db, tid)
        # anything else reported about this person's content is settled with the same decision
        await _close_reports(db, "user", tid, "upheld" if action == "ban" else "dismissed")

    elif kind == "recipe":
        r = await db.recipes.find_one({"recipe_id": tid}, {"_id": 0})
        if not r:
            raise HTTPException(status_code=404, detail="Recipe not found")
        if action == "reinstate":
            if r.get("held_by_review"):
                await db.recipes.update_one({"recipe_id": tid}, {"$set": {"visibility": "public", "publish_status": "public"}, "$unset": {"held_by_review": ""}})
            await _close_reports(db, "recipe", tid, "dismissed")
        else:
            await db.recipes.delete_one({"recipe_id": tid})
            await db.comments.delete_many({"recipe_id": tid})
            await _close_reports(db, "recipe", tid, "upheld")
            if action == "ban" and r.get("user_id") not in (None, "system_seeder"):
                await account_ops.ban_user(db, r["user_id"])
                await _close_reports(db, "user", r["user_id"], "upheld")

    else:
        c = await db.comments.find_one({"comment_id": tid}, {"_id": 0})
        if not c:
            raise HTTPException(status_code=404, detail="Comment not found")
        if action == "reinstate":
            await db.comments.update_one({"comment_id": tid}, {"$set": {"status": "visible"}, "$unset": {"held_by_review": ""}})
            await _close_reports(db, "comment", tid, "dismissed")
        else:
            await db.comments.delete_many({"$or": [{"comment_id": tid}, {"parent_id": tid}]})
            await _close_reports(db, "comment", tid, "upheld")
            if action == "ban":
                await account_ops.ban_user(db, c["user_id"])
                await _close_reports(db, "user", c["user_id"], "upheld")
    return {"message": "Done"}


@router.post("/test-email")
async def test_email(request: Request):
    db = request.app.state.db
    await require_admin(request, db)
    try:
        await notify.send_test()
    except Exception as e:
        return {"sent": False, "error": str(e)[:300]}
    return {"sent": True}


@router.get("/backup")
async def download_backup(request: Request):
    """One-click backup of all user data (admins only). Keep the file somewhere private: it holds personal data."""
    import backup_ops
    db = request.app.state.db
    await require_admin(request, db)
    blob, counts = await backup_ops.build_backup(db)
    name = "cookme-backup-" + datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M") + ".jsonl.gz"
    return Response(blob, media_type="application/gzip", headers={
        "Content-Disposition": f'attachment; filename="{name}"', "X-Backup-Counts": ",".join(f"{k}={v}" for k, v in counts.items())})


@router.get("/errors")
async def recent_errors(request: Request):
    db = request.app.state.db
    await require_admin(request, db)
    rows = await db.client_errors.find({}, {"_id": 0}).sort("created_at", -1).to_list(30)
    return {"errors": rows}


class ImproveBody(BaseModel):
    limit: int = 25


@router.post("/improve-descriptions")
async def improve_descriptions(body: ImproveBody, request: Request):
    """Upgrade the plain auto-written descriptions of the library recipes with short AI-written ones, a batch at a time."""
    import asyncio
    from description_quality import improved_description
    db = request.app.state.db
    await require_admin(request, db)
    q = {"user_id": "system_seeder", "description_auto": True}
    rows = await db.recipes.find(q, {"_id": 0, "recipe_id": 1, "title": 1, "cuisine": 1, "ingredients": 1, "steps": 1}).limit(max(1, min(body.limit, 50))).to_list(50)
    sem = asyncio.Semaphore(5)

    async def one(r):
        async with sem:
            text, src = await improved_description(r, use_ai=True)
        if src != "ai":
            return False
        await db.recipes.update_one({"recipe_id": r["recipe_id"]}, {"$set": {"description": text, "description_auto": False, "description_source": "ai"}})
        return True

    results = await asyncio.gather(*(one(r) for r in rows))
    return {"updated": sum(results), "failed": len(results) - sum(results), "remaining": await db.recipes.count_documents(q)}


@router.get("/description-status")
async def description_status(request: Request):
    db = request.app.state.db
    await require_admin(request, db)
    return {"plain_descriptions": await db.recipes.count_documents({"user_id": "system_seeder", "description_auto": True})}


@router.post("/ai-test")
async def ai_test(request: Request):
    """One tiny AI call with the configured model, so a model change can be checked before relying on it."""
    import time
    from ai_client import model_for, ask_json
    db = request.app.state.db
    await require_admin(request, db)
    provider, model = model_for()
    started = time.time()
    try:
        data = await ask_json("Return only valid JSON.", 'Reply with exactly {"ok": true, "word": "ready"}', "test")
        return {"ok": bool(data.get("ok")), "provider": provider, "model": model,
                "seconds": round(time.time() - started, 2), "reply": data}
    except Exception as e:
        return {"ok": False, "provider": provider, "model": model,
                "seconds": round(time.time() - started, 2), "error": str(e)[:300]}


@router.post("/fetch-test")
async def fetch_test(request: Request):
    """Shows what each way of fetching a page did (status, size, usable) so blocked sites can be diagnosed."""
    from page_fetch import fetch_page_html
    db = request.app.state.db
    await require_admin(request, db)
    body = await request.json()
    url = str(body.get("url", "")).strip()
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="url required")
    diag: list = []
    html, how = await fetch_page_html(url, diag=diag)
    return {"how": how, "chars": len(html), "has_recipe_data": '"Recipe"' in html, "steps": diag}


# ── AI recipes that people cooked: review, add a free photo, publish to the shared library ────────────

class AiRecipeAction(BaseModel):
    recipe_id: str
    image_url: Optional[str] = None      # chosen Pixabay/Pexels photo
    credit: Optional[str] = None


@router.get("/ai-recipes")
async def ai_recipes_pending(request: Request):
    db = request.app.state.db
    await require_admin(request, db)
    from image_search import configured
    items = []
    async for r in db.recipes.find({"ai_review": "pending"}, {"_id": 0}).sort("ai_review_at", 1).limit(50):
        cooks = await db.recipe_cooks.count_documents({"recipe_id": r["recipe_id"]})
        items.append({
            "recipe_id": r["recipe_id"], "title": r.get("title"), "description": r.get("description"),
            "servings": r.get("servings"), "prep_time": r.get("prep_time"), "cook_time": r.get("cook_time"),
            "ingredients": r.get("ingredients", []), "steps": r.get("steps", []), "tags": r.get("tags", []),
            "cooked_by": cooks, "image": r.get("image") or "",
        })
    return {"items": items, "photos_configured": configured()}


@router.post("/ai-recipes/photos")
async def ai_recipe_photos(body: AiRecipeAction, request: Request):
    db = request.app.state.db
    await require_admin(request, db)
    from image_search import search_photos, configured
    if not configured():
        raise HTTPException(status_code=400, detail="Add PIXABAY_API_KEY or PEXELS_API_KEY to the backend settings first.")
    r = await db.recipes.find_one({"recipe_id": body.recipe_id}, {"_id": 0, "title": 1})
    if not r:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return {"photos": await search_photos(r.get("title", ""))}


@router.post("/ai-recipes/approve")
async def ai_recipe_approve(body: AiRecipeAction, request: Request):
    """Publish a copy of the recipe to the shared library (with a free photo if one was chosen)."""
    import uuid
    db = request.app.state.db
    await require_admin(request, db)
    src = await db.recipes.find_one({"recipe_id": body.recipe_id, "ai_review": "pending"}, {"_id": 0})
    if not src:
        raise HTTPException(status_code=404, detail="Recipe not waiting for review")
    image, credit = src.get("image") or "", None
    if body.image_url:
        from image_search import store_photo
        try:
            image = await store_photo(db, body.image_url)
            credit = body.credit
        except Exception:
            raise HTTPException(status_code=400, detail="Could not download that photo. Pick another one.")
    now = datetime.now(timezone.utc)
    tags = [t for t in (src.get("tags") or []) if t not in ("AI Suggested", "AI Converted", "Pantry Recipe")]
    master = {
        "recipe_id": f"recipe_{uuid.uuid4().hex[:12]}", "user_id": "system_seeder",
        "title": src.get("title"), "description": src.get("description", ""), "image": image,
        "image_attribution": credit, "prep_time": src.get("prep_time", ""), "cook_time": src.get("cook_time", ""),
        "servings": src.get("servings", 4), "difficulty": src.get("difficulty", "Medium"),
        "ingredients": src.get("ingredients", []), "steps": src.get("steps", []),
        "tags": tags + ["AI-made"], "category": src.get("category"), "cuisine": src.get("cuisine"),
        "source": "CookMe community (AI-made, reviewed by CookMe)", "ai_generated": True,
        "uploader_id": "system_seeder", "uploader_name": "CookMe", "likes_count": 0, "saves_count": 0,
        "hidden_by": [], "favorited_by": [], "gallery_images": [], "created_at": now, "updated_at": now,
    }
    await db.recipes.insert_one(master)
    await db.recipes.update_one({"recipe_id": body.recipe_id}, {"$set": {"ai_review": "approved", "ai_master_id": master["recipe_id"]}})
    return {"ok": True, "master_id": master["recipe_id"]}


@router.post("/ai-recipes/reject")
async def ai_recipe_reject(body: AiRecipeAction, request: Request):
    db = request.app.state.db
    await require_admin(request, db)
    res = await db.recipes.update_one({"recipe_id": body.recipe_id, "ai_review": "pending"}, {"$set": {"ai_review": "rejected"}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Recipe not waiting for review")
    return {"ok": True}
