"""Find a free photo for a recipe on Pixabay or Pexels, and keep our own copy.

Needs at least one key in the backend environment: PIXABAY_API_KEY (free at pixabay.com/api/docs)
and/or PEXELS_API_KEY (free at pexels.com/api). Photos are downloaded, resized and stored in our own
database, never hotlinked (Pixabay requires that).
"""
import io
import os
import uuid
import logging
from datetime import datetime, timezone

import httpx
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)
ALLOWED_HOSTS = ("pixabay.com", "pexels.com")


def configured() -> bool:
    return bool(os.environ.get("PIXABAY_API_KEY") or os.environ.get("PEXELS_API_KEY"))


async def search_photos(query: str, limit: int = 6) -> list:
    """Candidates: [{url, thumb, credit, page, site}]. Empty list when no key is set or nothing is found."""
    out = []
    q = (query or "").strip()[:100]
    if not q:
        return out
    async with httpx.AsyncClient(timeout=15.0) as client:
        key = os.environ.get("PIXABAY_API_KEY")
        if key:
            try:
                r = await client.get("https://pixabay.com/api/", params={
                    "key": key, "q": q + " food", "image_type": "photo", "safesearch": "true",
                    "per_page": limit, "orientation": "horizontal"})
                for h in (r.json().get("hits") or []):
                    out.append({"url": h.get("largeImageURL") or h.get("webformatURL"), "thumb": h.get("previewURL") or h.get("webformatURL"),
                                "credit": f"Photo by {h.get('user', 'a photographer')} on Pixabay", "page": h.get("pageURL"), "site": "pixabay"})
            except Exception as e:
                logger.info(f"pixabay search failed: {e}")
        key = os.environ.get("PEXELS_API_KEY")
        if key:
            try:
                r = await client.get("https://api.pexels.com/v1/search", params={"query": q + " food", "per_page": limit, "orientation": "landscape"},
                                     headers={"Authorization": key})
                for p in (r.json().get("photos") or []):
                    src = p.get("src") or {}
                    out.append({"url": src.get("large") or src.get("medium"), "thumb": src.get("small") or src.get("tiny"),
                                "credit": f"Photo by {p.get('photographer', 'a photographer')} on Pexels", "page": p.get("url"), "site": "pexels"})
            except Exception as e:
                logger.info(f"pexels search failed: {e}")
    return [c for c in out if c.get("url")][: limit * 2]


def _allowed(url: str) -> bool:
    try:
        host = url.split("/")[2].lower()
    except Exception:
        return False
    return url.startswith("https://") and any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS)


async def store_photo(db, url: str) -> str:
    """Download, shrink (max 900px, JPEG) and save in our database. Returns the path the app serves it from."""
    if not _allowed(url):
        raise ValueError("Photo must come from Pixabay or Pexels")
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(r.content))).convert("RGB")
    img.thumbnail((900, 900))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=78, optimize=True)
    image_id = f"img_{uuid.uuid4().hex[:12]}"
    await db.images.insert_one({"image_id": image_id, "data": buf.getvalue(), "content_type": "image/jpeg",
                                "source_url": url, "created_at": datetime.now(timezone.utc)})
    return f"/api/ai/image/{image_id}"
