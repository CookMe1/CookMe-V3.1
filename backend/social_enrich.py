"""Look beyond the caption of a shared social post: links in the caption and in the comments, and recipes posted as comments.

Creators often write "recipe in the comments" or pin a comment with the full recipe or a link to their website.
What is possible for free depends on the platform:
  YouTube  - full description + top comments through the YouTube Data API (free key: YOUTUBE_API_KEY, 10,000 units/day)
  Reddit   - the post's public .json (OP's text and comments); Reddit sometimes blocks server IPs, then it is skipped
  Others   - Instagram, TikTok, Facebook and X show comments only to logged-in people, so they cannot be read from a server.
             For those the app asks the person to paste the comment (or share selected comment text to CookMe).
"""
import logging
import os
import re
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# Never treat these as "the recipe website"
SKIP_DOMAINS = (
    "facebook.com", "fb.com", "fb.me", "fb.watch", "fbcdn.net", "instagram.com", "instagr.am", "cdninstagram.com",
    "twitter.com", "x.com", "t.co", "tiktok.com", "youtube.com", "youtu.be", "ytimg.com", "pinterest.com", "pin.it",
    "reddit.com", "redd.it", "redditmedia.com", "redditstatic.com", "google.com", "googleapis.com", "gstatic.com",
    "w3.org", "schema.org", "apple.com", "amazon.com", "amzn.to", "amzn.com", "a.co", "shopee.com", "paypal.com",
    "patreon.com", "ko-fi.com", "buymeacoffee.com", "discord.gg", "whatsapp.com", "wa.me", "t.me", "spotify.com",
    "linktr.ee", "beacons.ai", "snapchat.com", "twitch.tv", "bit.ly", "tinyurl.com", "shop-links.co", "mailchi.mp",
)
SHORTENERS = ("bit.ly", "tinyurl.com", "buff.ly", "ow.ly", "rb.gy", "tiny.cc")   # resolved by following the redirect
URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.I)
BARE_RE = re.compile(r"(?<![@/\w.])((?:[a-z0-9-]+\.)+(?:com|co\.uk|org|net|uk|io|food|kitchen|recipes?|blog|cooking)(?:/[^\s<>\"')\]]*)?)", re.I)
UNIT_RE = re.compile(r"\b(\d+(?:[./]\d+)?\s*(?:g|kg|ml|l|oz|lb|lbs|cups?|tbsp|tsp|tablespoons?|teaspoons?|cloves?|pinch)\b|\d+/\d+)", re.I)
HINT_RE = re.compile(r"\b(ingredients?|method|directions?|instructions?|recipe)\b", re.I)


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def find_links(text: str) -> list[str]:
    """Candidate recipe-website links in some text, best first, no social/shop/link-hub domains."""
    seen, out = set(), []
    urls = [u.rstrip(".,;:!?)]}>") for u in URL_RE.findall(text or "")]
    for m in BARE_RE.findall(text or ""):          # "full recipe at mysite.com/pasta" without https
        if not any(m in u for u in urls):
            urls.append("https://" + m.rstrip(".,;:!?)]}>"))
    for u in urls:
        d = _domain(u)
        if not d or "." not in d or u in seen:
            continue
        if any(d == s or d.endswith("." + s) for s in SKIP_DOMAINS) and not any(d == s for s in SHORTENERS):
            continue
        seen.add(u)
        out.append(u)
    # a link with a real path (a page) beats a bare homepage
    out.sort(key=lambda u: 0 if len(urlparse(u).path.strip("/")) > 3 else 1)
    return out[:5]


def looks_like_recipe_text(text: str) -> bool:
    """A comment that is itself the recipe: several lines with quantities, or 'Ingredients' plus some quantities."""
    if not text or len(text) < 80:
        return False
    quantities = len(UNIT_RE.findall(text))
    return quantities >= 4 or (bool(HINT_RE.search(text)) and quantities >= 2)


def pick_useful_comments(comments: list[dict], limit: int = 3000) -> tuple[list[str], str]:
    """From comments [{text, by_author, likes}] return (links worth following, recipe-like comment text)."""
    links, texts = [], []
    ranked = sorted(comments, key=lambda c: (not c.get("by_author"), -(c.get("likes") or 0)))
    for c in ranked:
        t = c.get("text") or ""
        for u in find_links(t):
            if u not in links:
                links.append(u)
        if looks_like_recipe_text(t) or (c.get("by_author") and HINT_RE.search(t)):
            texts.append(t.strip())
    return links[:5], "\n\n".join(texts)[:limit]


async def recipe_from_links(links: list[str], limit: int = 3):
    """First link whose page carries a real recipe (structured data). Returns (recipe_dict, url) or (None, None)."""
    from page_fetch import fetch_page_html
    from routes.recipe_routes import _extract_json_ld_recipe
    for url in links[:limit]:
        try:
            html, _how = await fetch_page_html(url)
            data = _extract_json_ld_recipe(html) if html else None
        except Exception as e:                       # one bad link must not stop the import
            logger.info("link %s failed: %s", url, e)
            continue
        if data and data.get("ingredients") and data.get("steps"):
            if not str(data.get("source_url") or "").startswith("http"):
                data["source_url"] = url
            return data, url
    return None, None


# ── comment fetchers ──────────────────────────────────────────────────────────

async def youtube_details(video_id: str) -> dict:
    """Full description and top comments via the YouTube Data API. {} without a key or on any failure."""
    key = os.environ.get("YOUTUBE_API_KEY", "")
    if not key:
        return {}
    out = {"description": "", "comments": [], "channel_id": ""}
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            v = await c.get("https://www.googleapis.com/youtube/v3/videos",
                            params={"part": "snippet", "id": video_id, "key": key})
            if v.status_code == 200 and v.json().get("items"):
                sn = v.json()["items"][0]["snippet"]
                out["description"] = sn.get("description", "")
                out["channel_id"] = sn.get("channelId", "")
            t = await c.get("https://www.googleapis.com/youtube/v3/commentThreads",
                            params={"part": "snippet", "videoId": video_id, "maxResults": 60, "order": "relevance",
                                    "textFormat": "plainText", "key": key})
            if t.status_code == 200:
                for it in t.json().get("items", []):
                    s = it["snippet"]["topLevelComment"]["snippet"]
                    out["comments"].append({
                        "text": s.get("textDisplay", ""), "likes": s.get("likeCount", 0),
                        "by_author": (s.get("authorChannelId") or {}).get("value") == out["channel_id"] and bool(out["channel_id"]),
                    })
            elif t.status_code == 403:
                logger.info("YouTube comments are off for this video or the quota is used up")
    except Exception as e:
        logger.info("YouTube API failed: %s", e)
    return out


async def reddit_details(url: str) -> dict:
    """The post text and top comments from Reddit's public JSON. {} if Reddit refuses."""
    try:
        api = url.split("?")[0].rstrip("/") + ".json?limit=40&raw_json=1"
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
            r = await c.get(api, headers={"User-Agent": "CookMe/1.0 (recipe importer)"})
        if r.status_code != 200:
            return {}
        post_l, com_l = r.json()
        post = post_l["data"]["children"][0]["data"]
        op = post.get("author")
        comments = [{"text": ch["data"].get("body", ""), "likes": ch["data"].get("score", 0),
                     "by_author": ch["data"].get("author") == op}
                    for ch in com_l["data"]["children"] if ch.get("kind") == "t1"]
        return {"description": post.get("selftext", ""), "comments": comments, "title": post.get("title", "")}
    except Exception as e:
        logger.info("Reddit JSON failed: %s", e)
        return {}


async def look_in_comments(platform: str, url: str, caption: str, video_id: str = "") -> dict:
    """Everything useful from comments + caption.
    Returns {recipe, recipe_url, found_via, comment_text, comments_checked, description}."""
    res = {"recipe": None, "recipe_url": None, "found_via": None, "comment_text": "", "comments_checked": False, "description": ""}
    comments, description = [], ""
    p = (platform or "").lower()
    if p == "youtube" and video_id:
        d = await youtube_details(video_id)
    elif p == "reddit":
        d = await reddit_details(url)
    else:
        d = {}
    if d:
        comments = d.get("comments", [])
        description = d.get("description", "")
        res["comments_checked"] = bool(comments)
    res["description"] = description

    caption_links = find_links(f"{caption}\n{description}")
    comment_links, comment_text = pick_useful_comments(comments)
    res["comment_text"] = comment_text
    for links, via in ((caption_links, "link in the post"), (comment_links, "link in the comments")):
        recipe, link = await recipe_from_links(links)
        if recipe:
            res.update({"recipe": recipe, "recipe_url": link, "found_via": via})
            break
    return res
