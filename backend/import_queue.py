"""
import_queue.py
==============
Async recipe import job queue using MongoDB + FastAPI BackgroundTasks.

Instead of making the user wait while the server fetches, sanitises and
extracts a recipe, imports run in the background. The user gets a job_id
immediately and can poll for the result.

Flow:
  1. POST /api/recipes/import-async  → returns {job_id, status: "pending"}
  2. BackgroundTask runs the import
  3. GET  /api/recipes/import-status/{job_id} → {status, recipe} when done

MongoDB collection: import_jobs
  Fields: job_id, user_id, url, status, recipe, error, created_at, completed_at
  TTL index: auto-deleted after 24 hours
"""

import uuid
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from auth import get_current_user
from ai_client import model_for

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recipes", tags=["import"])

JOB_TTL_HOURS = 24   # jobs auto-deleted after 24 hours


# ── Models ────────────────────────────────────────────────────────────────────

class AsyncImportRequest(BaseModel):
    url: str
    platform: Optional[str] = "website"   # website, youtube, instagram, tiktok etc.


# ── Background worker ─────────────────────────────────────────────────────────

async def _run_import_job(job_id: str, url: str, platform: str, user_id: str, db):
    """
    Runs in background. Detects platform, calls the right extraction path,
    stores result back into the import_jobs collection.
    """
    from url_registry import get_from_registry, save_to_registry

    # Mark as processing
    await db.import_jobs.update_one(
        {"job_id": job_id},
        {"$set": {"status": "processing"}}
    )

    try:
        recipe = None

        # ── Check URL registry first (free, instant) ──────────────────────────
        registry_hit = await get_from_registry(db, url)
        if registry_hit:
            logger.info(f"Job {job_id}: URL registry hit for {url}")
            recipe = registry_hit
            recipe["_from_registry"] = True
        else:
            # ── Platform-specific extraction ──────────────────────────────────
            url_lower = url.lower()

            if any(x in url_lower for x in ["youtube.com", "youtu.be"]):
                recipe = await _extract_youtube(url, db)

            elif any(x in url_lower for x in ["instagram.com", "instagr.am"]):
                recipe = await _extract_instagram(url, db)

            elif any(x in url_lower for x in
                     ["tiktok.com", "pinterest.com", "pin.it",
                      "twitter.com", "x.com", "reddit.com", "redd.it",
                      "facebook.com", "fb.com", "fb.watch"]):
                recipe = await _extract_social(url, platform, db)

            else:
                recipe = await _extract_website(url, db)

            # Save to registry if extraction succeeded
            if recipe and recipe.get("title") and recipe.get("ingredients"):
                await save_to_registry(db, url, recipe)

        # Mark done
        await db.import_jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "status": "done",
                "recipe": recipe,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }}
        )
        logger.info(f"Job {job_id}: completed — {recipe.get('title', 'unknown') if recipe else 'no recipe'}")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        await db.import_jobs.update_one(
            {"job_id": job_id},
            {"$set": {
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }}
        )


async def _extract_website(url: str, db) -> dict:
    """Extract recipe from a website URL using JSON-LD or sanitiser+AI."""
    import httpx, json, re
    import os
    from html_sanitiser import sanitise_html, extract_best_image
    from image_optimiser import optimise_image_url
    from cache import url_import_key, get_cache, set_cache, TTL_URL_IMPORT

    # Check cache
    cache_key = url_import_key(url)
    cached = await get_cache(db, cache_key)
    if cached:
        return cached

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=headers) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            raise ValueError(f"HTTP {resp.status_code} fetching {url}")
        html = resp.text

    # Try JSON-LD (free)
    from routes.recipe_routes import _extract_json_ld_recipe
    json_ld = _extract_json_ld_recipe(html)
    if json_ld:
        if json_ld.get("image"):
            _, json_ld["image"] = await optimise_image_url(json_ld["image"])
        await set_cache(db, cache_key, json_ld, ttl_days=TTL_URL_IMPORT)
        return json_ld

    # Sanitise + AI
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    import uuid as _uuid
    EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
    from routes.recipe_routes import extract_wprm_recipe

    extracted_image = extract_best_image(html, url)
    sanitised, fallback_image = sanitise_html(html, base_url=url, max_chars=3500)
    extracted_image = extracted_image or fallback_image

    wprm = extract_wprm_recipe(html)
    wprm_hint = ""
    if wprm["ingredients"]:
        wprm_hint = f"\n\nFound structured ingredients:\n{json.dumps(wprm['ingredients'][:10])}"
    if wprm["steps"]:
        wprm_hint += f"\n\nFound structured steps:\n{json.dumps(wprm['steps'][:5])}"

    chat = LlmChat(
        api_key=EMERGENT_KEY,
        session_id=f"async_extract_{_uuid.uuid4().hex[:8]}",
        system_message="Extract recipe information and return ONLY valid JSON."
    ).with_model(*model_for())

    prompt = f"""Extract the recipe from this content:
{{"title":"","description":"","prep_time":"","cook_time":"","servings":4,"difficulty":"Easy","ingredients":[{{"item":"","amount":""}}],"steps":[],"tags":[]}}
{wprm_hint}
Content: {sanitised}"""

    response = await chat.send_message(UserMessage(text=prompt))
    match = re.search(r'\{.*\}', response, re.DOTALL)
    recipe = json.loads(match.group() if match else response)

    if not recipe.get("image"):
        recipe["image"] = extracted_image
    if recipe.get("image"):
        _, recipe["image"] = await optimise_image_url(recipe["image"])

    await set_cache(db, cache_key, recipe, ttl_days=TTL_URL_IMPORT)
    return recipe


async def _extract_youtube(url: str, db) -> dict:
    """Delegate to the existing YouTube extraction logic."""
    import httpx, json, re, os
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    import uuid as _uuid
    from html import unescape
    from cache import youtube_key, get_cache, set_cache, TTL_YOUTUBE
    from image_optimiser import optimise_image_url

    vid_match = re.search(r'(?:v=|youtu\.be/|/shorts/)([a-zA-Z0-9_-]{11})', url)
    if not vid_match:
        raise ValueError("Invalid YouTube URL")
    video_id = vid_match.group(1)

    cached = await get_cache(db, youtube_key(video_id))
    if cached:
        return cached

    title = author = description = ""
    thumbnail = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        try:
            oe = await client.get(f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json")
            if oe.status_code == 200:
                od = oe.json()
                title     = od.get("title", "")
                author    = od.get("author_name", "")
                thumbnail = od.get("thumbnail_url", thumbnail)
        except Exception:
            pass

        try:
            pg = await client.get(f"https://www.youtube.com/watch?v={video_id}",
                                  headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"})
            if pg.status_code == 200:
                if not title:
                    tm = re.search(r'<meta property="og:title" content="([^"]+)"', pg.text)
                    if tm: title = unescape(tm.group(1))
                dm = re.search(r'<meta name="description" content="([^"]+)"', pg.text)
                if dm: description = unescape(dm.group(1))
                im = re.search(r'<meta property="og:image" content="([^"]+)"', pg.text)
                if im: thumbnail = im.group(1)
        except Exception:
            pass

    EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
    chat = LlmChat(api_key=EMERGENT_KEY, session_id=f"yt_{_uuid.uuid4().hex[:8]}",
                   system_message="Extract recipe details from cooking video info. Return ONLY valid JSON."
                   ).with_model(*model_for())

    prompt = f"""Extract recipe from YouTube video:
Title: {title}  Author: {author}
Description: {description[:800]}
Return JSON: {{"title":"","description":"","prep_time":"","cook_time":"","servings":4,"difficulty":"Easy","ingredients":[],"steps":[],"tags":["YouTube"],"source":"YouTube","video_url":"{url}"}}"""

    response = await chat.send_message(UserMessage(text=prompt))
    match = re.search(r'\{.*\}', response, re.DOTALL)
    recipe = json.loads(match.group() if match else response)

    if not recipe.get("image"):
        recipe["image"] = thumbnail
    if recipe.get("image"):
        _, recipe["image"] = await optimise_image_url(recipe["image"])

    await set_cache(db, youtube_key(video_id), recipe, ttl_days=TTL_YOUTUBE)
    return recipe


async def _extract_instagram(url: str, db) -> dict:
    """Delegate to Instagram oEmbed route."""
    from routes.instagram_routes import fetch_oembed, parse_caption_with_ai
    from image_optimiser import optimise_image_url

    oembed = await fetch_oembed(url)
    caption    = oembed.get("title", "")
    thumbnail  = oembed.get("thumbnail_url", "")
    author     = oembed.get("author_name", "unknown")

    if not caption:
        raise ValueError("No caption found on Instagram post")

    recipe_data = await parse_caption_with_ai(caption, author)
    if thumbnail:
        _, thumbnail = await optimise_image_url(thumbnail)

    return {
        **recipe_data,
        "image": thumbnail,
        "source": f"instagram.com/@{author}",
        "source_url": url,
        "tags": recipe_data.get("tags", ["Instagram"]),
    }


async def _extract_social(url: str, platform: str, db) -> dict:
    """Generic social extraction via extract-social logic."""
    import httpx, json, re, os
    from html_sanitiser import sanitise_html
    from image_optimiser import optimise_image_url
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    import uuid as _uuid

    PLATFORM_UA = {
        "facebook":  "facebookexternalhit/1.1",
        "tiktok":    "Twitterbot/1.0",
        "pinterest": "Mozilla/5.0 (compatible; Pinterestbot/1.0)",
        "twitter":   "Twitterbot/1.0",
        "reddit":    "Mozilla/5.0",
    }
    ua = PLATFORM_UA.get(platform.lower(), "Mozilla/5.0")

    async with httpx.AsyncClient(timeout=20, follow_redirects=True,
                                  headers={"User-Agent": ua, "Accept-Language": "en-US,en;q=0.5"}) as client:
        resp = await client.get(url)
        if resp.status_code >= 400:
            raise ValueError(f"HTTP {resp.status_code} from {platform}")
        html = resp.text

    sanitised, extracted_image = sanitise_html(html, base_url=url, max_chars=3000)
    og_img_m = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html, re.I)
    image_url = (og_img_m.group(1) if og_img_m else None) or extracted_image

    EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
    chat = LlmChat(api_key=EMERGENT_KEY, session_id=f"social_{_uuid.uuid4().hex[:8]}",
                   system_message="Extract recipe from social media. Return ONLY valid JSON."
                   ).with_model(*model_for())

    prompt = f"""Extract recipe from {platform} post:
{{"title":"","description":"","prep_time":"","cook_time":"","servings":4,"difficulty":"Easy","ingredients":[],"steps":[],"tags":["{platform}"]}}
Content: {sanitised[:2500]}"""

    response = await chat.send_message(UserMessage(text=prompt))
    match = re.search(r'\{.*\}', response, re.DOTALL)
    recipe = json.loads(match.group() if match else response)

    if not recipe.get("image"):
        recipe["image"] = image_url
    if recipe.get("image"):
        _, recipe["image"] = await optimise_image_url(recipe["image"])

    return recipe


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/import-async")
async def import_recipe_async(
    body: AsyncImportRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Start an async recipe import. Returns immediately with a job_id.
    Frontend polls /import-status/{job_id} for the result.
    """
    db = request.app.state.db
    user = await get_current_user(request, db)

    job_id = f"job_{uuid.uuid4().hex[:16]}"
    now    = datetime.now(timezone.utc)

    await db.import_jobs.insert_one({
        "job_id":     job_id,
        "user_id":    user["user_id"],
        "url":        body.url,
        "platform":   body.platform,
        "status":     "pending",
        "recipe":     None,
        "error":      None,
        "created_at": now,
        "expires_at": now + timedelta(hours=JOB_TTL_HOURS),
    })

    # Run import in background — user doesn't wait
    background_tasks.add_task(
        _run_import_job, job_id, body.url, body.platform, user["user_id"], db
    )

    return {
        "job_id":     job_id,
        "status":     "pending",
        "created_at": now.isoformat(),
        "poll_url":   f"/api/recipes/import-status/{job_id}",
    }


@router.get("/import-status/{job_id}")
async def get_import_status(job_id: str, request: Request):
    """
    Poll for the status of an async import job.
    Returns {status: 'pending'|'processing'|'done'|'failed', recipe?, error?}
    """
    db = request.app.state.db
    user = await get_current_user(request, db)

    job = await db.import_jobs.find_one(
        {"job_id": job_id, "user_id": user["user_id"]},
        {"_id": 0}
    )

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id":       job["job_id"],
        "status":       job["status"],
        "recipe":       job.get("recipe"),
        "error":        job.get("error"),
        "created_at":   job["created_at"].isoformat() if hasattr(job.get("created_at"), "isoformat") else str(job.get("created_at", "")),
        "completed_at": job.get("completed_at"),
    }
