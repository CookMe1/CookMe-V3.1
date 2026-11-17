"""
image_optimiser.py
==================
Fetches recipe images from external URLs and optimises them:
  - Resizes to max 800×600 (sufficient for recipe cards)
  - Converts to JPEG at quality 75 (visually lossless for food photos)
  - Returns as a base64 data URL OR saves to a CDN-ready bytes object

Typical reduction: 2–5MB original → 80–200KB optimised (90%+ smaller)

Usage:
    from image_optimiser import optimise_image_url, optimise_image_bytes

Requirements:
    pip install Pillow httpx   (both already in requirements.txt)
"""

import io
import base64
import logging
from typing import Optional, Tuple

import httpx
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

MAX_WIDTH  = 800
MAX_HEIGHT = 600
JPEG_QUALITY = 75          # 75 is visually lossless for photos, great compression
MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024   # 10MB download limit
TIMEOUT = 10               # seconds


# ── Core functions ─────────────────────────────────────────────────────────────

def optimise_image_bytes(data: bytes, fmt: str = 'JPEG') -> bytes:
    """
    Takes raw image bytes, returns optimised JPEG bytes.
    Handles WEBP, PNG, GIF, AVIF → JPEG conversion automatically.
    """
    try:
        img = Image.open(io.BytesIO(data))

        # Convert palette/RGBA to RGB for JPEG compatibility
        if img.mode in ('P', 'RGBA', 'LA', 'L'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode in ('RGBA', 'LA'):
                background.paste(img, mask=img.split()[-1])
            elif img.mode == 'P':
                img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1])
            else:
                background.paste(img)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Auto-rotate based on EXIF orientation
        img = ImageOps.exif_transpose(img)

        # Resize — maintain aspect ratio, never upscale
        if img.width > MAX_WIDTH or img.height > MAX_HEIGHT:
            img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.LANCZOS)

        # Encode to JPEG
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=JPEG_QUALITY, optimize=True, progressive=True)
        return buffer.getvalue()

    except Exception as e:
        logger.warning(f"Image optimisation failed: {e}")
        return data   # return original on failure


def bytes_to_base64_data_url(data: bytes, mime: str = 'image/jpeg') -> str:
    """Convert bytes to a base64 data URL."""
    encoded = base64.b64encode(data).decode('utf-8')
    return f"data:{mime};base64,{encoded}"


async def optimise_image_url(
    url: str,
    return_base64: bool = False,
) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Download and optimise an image from a URL.

    Returns:
        (optimised_bytes, optimised_url_or_base64)

        If return_base64=True, the second value is a data URL.
        If return_base64=False, the second value is the original URL
        (caller should store the bytes to their own storage).

    On any failure returns (None, original_url) so the caller can
    gracefully fall back to the unoptimised original URL.
    """
    if not url or not url.startswith('http'):
        return None, url

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; CookMeBot/1.0)',
            'Accept': 'image/webp,image/avif,image/jpeg,image/png,*/*',
        }

        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)

            if response.status_code != 200:
                logger.warning(f"Image fetch failed: {response.status_code} for {url}")
                return None, url

            content_length = int(response.headers.get('content-length', 0))
            if content_length > MAX_DOWNLOAD_BYTES:
                logger.warning(f"Image too large ({content_length} bytes), skipping optimisation")
                return None, url

            raw_bytes = response.content
            if len(raw_bytes) > MAX_DOWNLOAD_BYTES:
                return None, url

        # Optimise
        optimised = optimise_image_bytes(raw_bytes)
        original_kb = len(raw_bytes) / 1024
        optimised_kb = len(optimised) / 1024
        reduction = round((1 - optimised_kb / original_kb) * 100) if original_kb > 0 else 0
        logger.info(f"Image optimised: {original_kb:.0f}KB → {optimised_kb:.0f}KB ({reduction}% reduction)")

        if return_base64:
            return optimised, bytes_to_base64_data_url(optimised)
        else:
            return optimised, url   # caller stores bytes

    except httpx.TimeoutException:
        logger.warning(f"Image download timeout: {url}")
        return None, url
    except Exception as e:
        logger.warning(f"Image optimisation error for {url}: {e}")
        return None, url


