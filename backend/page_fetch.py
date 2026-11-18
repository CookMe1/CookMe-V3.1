"""Get a recipe page's HTML even when the site blocks plain server requests.

Order: direct (normal browser) -> Googlebot identity -> Jina Reader (HTML mode) -> ScrapingBee (only if SCRAPINGBEE_API_KEY is set).
Each step is tried only if the previous one failed or returned a near-empty page.
"""
import logging
import os
import re
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
GOOGLEBOT_UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def looks_usable(html: str) -> bool:
    """A real recipe page is long and either carries structured recipe data or plenty of text."""
    if not html or len(html) < 3000:
        return False
    low = html.lower()
    if "just a moment" in low[:3000] or "access denied" in low[:3000] or "captcha" in low[:3000]:
        return False
    return True


async def fetch_page_html(url: str, prefer_googlebot: bool = False):
    """Returns (html, how). html is "" when every method failed."""
    uas = [GOOGLEBOT_UA, BROWSER_UA] if prefer_googlebot else [BROWSER_UA, GOOGLEBOT_UA]
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for ua in uas:
            headers = {**BASE_HEADERS, "User-Agent": ua, "Referer": "https://www.google.com/"}
            try:
                r = await client.get(url, headers=headers)
                if r.status_code < 400 and looks_usable(r.text):
                    return r.text, "direct"
            except Exception as e:  # network error: try next method
                logger.info(f"direct fetch failed: {e}")

        try:  # Jina Reader in HTML mode renders the page from its own servers
            r = await client.get(
                f"https://r.jina.ai/{url}",
                headers={"X-Return-Format": "html", "Accept": "text/html"},
                timeout=45.0,
            )
            if r.status_code < 400 and looks_usable(r.text):
                return r.text, "reader"
        except Exception as e:
            logger.info(f"reader fetch failed: {e}")

        key = os.environ.get("SCRAPINGBEE_API_KEY")
        if key:
            try:
                r = await client.get(
                    "https://app.scrapingbee.com/api/v1/",
                    params={"api_key": key, "url": url, "render_js": "false"},
                    timeout=60.0,
                )
                if r.status_code < 400 and looks_usable(r.text):
                    return r.text, "scraper"
            except Exception as e:
                logger.info(f"scraper fetch failed: {e}")
    return "", "failed"
