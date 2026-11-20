"""
Instagram Recipe Import
========================
Uses Instagram's oEmbed API (no login required) to fetch:
  - Post caption (contains the recipe text)
  - Thumbnail image
  - Video permalink

Then parses the caption with AI to extract a structured recipe.

Setup:
  - Set FACEBOOK_ACCESS_TOKEN in your .env for better rate limits
    (get one free at developers.facebook.com → add oEmbed product)
  - Without a token it still works but has stricter rate limits
"""

import os
import re
import json
import uuid
import logging
import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from auth import get_current_user
from emergentintegrations.llm.chat import LlmChat, UserMessage
from image_optimiser import optimise_image_url
from ai_client import model_for

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/instagram", tags=["instagram"])

EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
FACEBOOK_ACCESS_TOKEN = os.environ.get("FACEBOOK_ACCESS_TOKEN", "")


# ── Models ────────────────────────────────────────────────────────────────────

class InstagramImportRequest(BaseModel):
    url: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_instagram_url(url: str) -> str:
    """Strip query params and normalise to a clean Instagram URL."""
    match = re.match(r"(https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[^/?#]+)", url)
    return (match.group(1) + "/") if match else url


def extract_video_url_from_html(html: str) -> Optional[str]:
    """Extract the canonical Instagram permalink from oEmbed HTML."""
    match = re.search(r'data-instgrm-permalink="([^"]+)"', html or "")
    return match.group(1) if match else None


async def fetch_oembed(url: str) -> dict:
    """Call Instagram's oEmbed endpoint."""
    clean = clean_instagram_url(url)
    params = {
        "url": clean,
        "fields": "thumbnail_url,author_name,provider_name,title,html",
        "omitscript": "true",
    }
    if FACEBOOK_ACCESS_TOKEN:
        params["access_token"] = FACEBOOK_ACCESS_TOKEN

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://graph.facebook.com/v18.0/instagram_oembed", params=params
        )

    if resp.status_code == 400:
        raise HTTPException(
            status_code=400,
            detail="Instagram post not found or is private. Make sure the post is set to Public.",
        )
    if resp.status_code == 401:
        raise HTTPException(
            status_code=401,
            detail="Facebook access token invalid or missing. Set FACEBOOK_ACCESS_TOKEN in your .env.",
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Instagram oEmbed returned {resp.status_code}. The post may be private or deleted.",
        )

    return resp.json()


async def parse_caption_with_ai(caption: str, author: str) -> dict:
    """Use AI to extract a structured recipe from an Instagram caption."""
    chat = LlmChat(
        api_key=EMERGENT_KEY,
        session_id=f"ig_{uuid.uuid4().hex[:8]}",
        system_message="You extract structured recipes from social media captions. Return ONLY valid JSON, no markdown, no backticks.",
    ).with_model(*model_for())

    prompt = f"""Extract the recipe from this Instagram caption by @{author}.
If the caption doesn't contain a full recipe, infer one from the dish name/description.

Return this exact JSON structure:
{{
  "recipe_in_content": true or false (true only if the caption really lists ingredients or steps; false if you had to infer the recipe),
  "title": "recipe name",
  "description": "brief appetising description",
  "prep_time": "X min",
  "cook_time": "X min",
  "servings": 4,
  "difficulty": "Easy/Medium/Hard",
  "ingredients": [{{"item": "name", "amount": "quantity"}}],
  "steps": ["step 1", "step 2"],
  "tags": ["tag1", "tag2"],
  "nutrition": {{"calories": 0, "protein": 0, "carbs": 0, "fat": 0}}
}}

Caption:
{caption[:3000]}"""

    response = await chat.send_message(UserMessage(text=prompt))
    clean = re.sub(r"```json|```", "", response).strip()
    match = re.search(r"\{.*\}", clean, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(clean)


# ── Main endpoint ─────────────────────────────────────────────────────────────

@router.post("/import")
async def import_instagram_recipe(body: InstagramImportRequest, request: Request):
    """
    Import a recipe from an Instagram post or reel URL.

    Flow:
      1. Fetch oEmbed data (thumbnail, caption/title, author, embed HTML)
      2. Extract video permalink from embed HTML
      3. Parse caption with AI → structured recipe
      4. Return complete recipe ready to save
    """
    db = request.app.state.db
    await get_current_user(request, db)  # auth check

    url = body.url.strip()
    if "instagram.com" not in url:
        raise HTTPException(status_code=400, detail="Only Instagram URLs are supported by this endpoint.")

    # 1. Fetch oEmbed
    try:
        oembed = await fetch_oembed(url)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach Instagram: {str(e)}")

    caption: str = oembed.get("title", "")
    thumbnail_url: str = oembed.get("thumbnail_url", "")
    author: str = oembed.get("author_name", "unknown")
    embed_html: str = oembed.get("html", "")

    # 2. Extract video permalink
    video_url = extract_video_url_from_html(embed_html) or url

    # 3. Require some content to parse
    if not caption:
        raise HTTPException(
            status_code=422,
            detail="No caption found on this Instagram post. The post may be a private account or have no text.",
        )

    # 4a. A link to the recipe website in the caption beats guessing
    from social_enrich import look_in_comments
    found = await look_in_comments("instagram", url, caption)
    if found["recipe"]:
        rec = found["recipe"]
        if not rec.get("image") and thumbnail_url:
            rec["image"] = thumbnail_url
        if rec.get("image"):
            _, rec["image"] = await optimise_image_url(rec["image"])
        rec["found_via"] = found["found_via"]
        rec["recipe_in_content"] = True
        rec["video_url"] = video_url
        return rec

    # 4b. Parse with AI
    try:
        recipe_data = await parse_caption_with_ai(caption, author)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI parsing failed: {str(e)}")

    # 5. Optimise thumbnail image
    optimised_image = thumbnail_url
    if thumbnail_url:
        _, optimised_image = await optimise_image_url(thumbnail_url)

    # 6. Return enriched recipe
    return {
        "title": recipe_data.get("title", "Instagram Recipe"),
        "description": recipe_data.get("description", ""),
        "image": optimised_image,
        "prep_time": recipe_data.get("prep_time", ""),
        "cook_time": recipe_data.get("cook_time", ""),
        "servings": recipe_data.get("servings", 4),
        "difficulty": recipe_data.get("difficulty", "Medium"),
        "ingredients": recipe_data.get("ingredients", []),
        "steps": recipe_data.get("steps", []),
        "tags": recipe_data.get("tags", ["Instagram"]),
        "nutrition": recipe_data.get("nutrition"),
        "source_url": video_url,
        "source": f"instagram.com/@{author}",
        "thumbnail_url": optimised_image,
        "video_url": video_url,
        "author": author,
        "is_video": "reel" in url.lower() or "/tv/" in url.lower(),
        "recipe_in_content": bool(recipe_data.get("recipe_in_content", True)),
        "comments_checked": False,       # Instagram shows comments only to logged-in people
    }
