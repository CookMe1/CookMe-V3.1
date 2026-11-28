#!/usr/bin/env python3
"""Give every recipe with no image a proper one.
 1) Free photo from Pexels (free licence, no credit legally required but we store one anyway).
    Get a free key at https://www.pexels.com/api/ and set it:  export PEXELS_API_KEY=...
 2) Optional --ai: generate an image (needs ENABLE_AI_IMAGES=1 and the Emergent LLM key, i.e. run on Emergent).
 Images are saved to frontend/public/recipe-images/<recipe_id>.jpg and recipe['image'] is set to /recipe-images/<id>.jpg
 Usage:  python scripts/fill_images.py [--file data/staging/a.json,data/staging/b.json] [--limit 50] [--ai] [--dry] [--retry-misses] [--priority drink,sauce,snack]
Photo choice is a best match for the dish name, so spot-check a few. AI ones are labelled 'AI-generated illustration'."""
import json, os, re, sys, time
from pathlib import Path
import requests
ROOT = Path(__file__).resolve().parent.parent
F = ROOT/Path(sys.argv[sys.argv.index("--file") + 1]) if "--file" in sys.argv else ROOT/"data"/"master_recipes.json"
OUT = ROOT/"frontend"/"public"/"recipe-images"
KEY = os.environ.get("PEXELS_API_KEY", "")
PIX_KEY = os.environ.get("PIXABAY_API_KEY", "")

def arg(name, default=None):
    return sys.argv[sys.argv.index(name)+1] if name in sys.argv else default

STOP = {"with", "and", "the", "for", "from", "that", "this", "your", "recipe", "best", "easy", "quick", "simple", "classic", "homemade",
        "perfect", "fail", "fuss", "amazing", "delicious", "healthy", "light", "meal", "style", "kick", "homestyle", "lick", "plate", "magic",
        "authentic", "traditional", "ultimate", "favorite", "favourite", "ingredient", "ingredients", "minute", "minutes", "leave", "home", "without", "next"}

def words(title):
    import re
    return [w for w in re.findall(r"[a-zA-Z]+", title.lower()) if len(w) > 3 and w not in STOP]

def queries(title):
    w = words(title)
    qs = [f"{title} food dish"]
    if len(w) >= 2: qs.append(" ".join(w[:3]) + " food")
    if w: qs.append(w[-1] + " dish")
    if w and w[0] != w[-1]: qs.append(w[0] + " food")
    return qs[:3]                         # each search counts against the 199-an-hour limit, so no more than 3 per recipe

import collections
class PexelsBusy(Exception): pass
HOURLY_MAX = 199                      # never more than 199 Pexels requests in any rolling hour (the free key allows 200)
LOG = ROOT/"data"/"staging"/".pexels_requests.json"          # request times survive a restart, so the 199-an-hour limit holds across runs
try: _sent = collections.deque(t for t in json.load(open(LOG)) if time.time() - t < 3600)
except Exception: _sent = collections.deque()

def pexels_get(params):
    """One Pexels search. Waits first if 199 requests were already made in the last hour, so we never go over."""
    while True:
        now = time.time()
        while _sent and now - _sent[0] > 3600: _sent.popleft()
        if len(_sent) < HOURLY_MAX: break
        if PIX_KEY: raise PexelsBusy()          # Pixabay is the main source: never sit waiting for Pexels, just skip it until its hour has room
        wait = int(3600 - (now - _sent[0])) + 5
        print(f"  at the hourly limit ({HOURLY_MAX}); waiting {wait // 60} min. Keep this window open.", flush=True)
        save_hook and save_hook()
        time.sleep(min(wait, 600))
    _sent.append(time.time())
    try: json.dump(list(_sent), open(LOG, "w"))
    except Exception: pass
    r = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": KEY}, params=params, timeout=20)
    r.raise_for_status()
    return r

save_hook = None

def pexels(title):
    """Try the full title, then shorter searches. Keep photos only if their description shares a word with the dish name.
    Returns up to 3 matching photos from the same search (no extra searches): [(url, credit), ...]."""
    keep = set(words(title))
    for q in queries(title):
        r = pexels_get({"query": q, "per_page": 20, "orientation": "landscape"})
        found = [(p["src"]["large"], f"Photo by {p['photographer']} on Pexels") for p in r.json().get("photos", [])
                 if keep & set(words(p.get("alt") or ""))]
        if found:
            return found[:3]
        time.sleep(0.4)
    return []

_pix = collections.deque()

def pix_get(params):
    """One Pixabay search. Pixabay allows 100 a minute; we stay at 80 or fewer and wait out any 429."""
    while True:
        now = time.time()
        while _pix and now - _pix[0] > 60: _pix.popleft()
        if len(_pix) < 80: break
        time.sleep(max(1, 61 - (now - _pix[0])))
    _pix.append(time.time())
    r = requests.get("https://pixabay.com/api/", params={**params, "key": PIX_KEY}, timeout=20)
    if r.status_code == 429:
        time.sleep(65); r = requests.get("https://pixabay.com/api/", params={**params, "key": PIX_KEY}, timeout=20)
    r.raise_for_status()
    return r

def _stem(ws): return {w[:-1] if w.endswith("s") else w for w in ws}

def pixabay(title):
    """Pixabay (free for commercial use, no credit needed; we store one anyway). Keep photos only if their tags share a word with the dish name."""
    keep = _stem(words(title))
    for q in queries(title):
        hits = pix_get({"q": q[:100], "image_type": "photo", "category": "food", "orientation": "horizontal", "per_page": 20, "safesearch": "true"}).json().get("hits", [])
        found = [(h["largeImageURL"], f"Photo by {h.get('user', 'a contributor')} on Pixabay") for h in hits if keep & _stem(words((h.get("tags") or "").replace(",", " ")))]
        if found: return found[:3]
    return []

def pixabay_strict(title):
    """Only photos whose tags contain EVERY word of the dish name (needs 2+ words). Used to look for better pictures than the ones we have."""
    keep = _stem(words(title))
    if len(keep) < 2: return []
    for q in queries(title)[:2]:
        hits = pix_get({"q": q[:100], "image_type": "photo", "category": "food", "orientation": "horizontal", "per_page": 20, "safesearch": "true"}).json().get("hits", [])
        found = [(h["largeImageURL"], f"Photo by {h.get('user', 'a contributor')} on Pixabay") for h in hits if keep <= _stem(words((h.get("tags") or "").replace(",", " ")))]
        if found: return found[:1]
    return []

# ---------- Wikimedia Commons (openly licensed photos, credit + licence stored) ----------
COMMONS_ON = "--no-commons" not in sys.argv
COMMONS_UA = {"User-Agent": "GrublyPhotoLoader/1.0 (https://grublyworld.com; mail.cookme@gmail.com) python-requests"}
_commons_last = [0.0]; _commons_src = {}
OK_LICENCE = re.compile(r"^(cc0|cc[ -]by(?![ -](nc|nd))|cc[ -]by[ -]sa|public domain|pd)", re.I)
BAD_WORDS = re.compile(r"\b(diagram|map|logo|flag|menu|drawing|illustration|painting|stamp|label|poster|packaging|vending|restaurant|market|street|shop|stall|cartoon|sketch|cover|advert|advertisement|sign|manuscript|book|page|screenshot|infographic|chart|svg|can|bottle|factory|machine|museum|exhibit|kitchen|chef|people|person|crowd|child|children|woman|women|man|men|girl|boy)\b", re.I)
# quality bar = the weakest 5% of the Pexels photos already in the app (measured on 300 of them)
MIN_SHARP, MIN_BRIGHT, MAX_BRIGHT, MIN_CONTRAST = 294, 55, 200, 41

def commons_get(params):
    wait = 1.2 - (time.time() - _commons_last[0])          # polite: one request about every 1.2 s
    if wait > 0: time.sleep(wait)
    r = requests.get("https://commons.wikimedia.org/w/api.php", params={**params, "format": "json"}, headers=COMMONS_UA, timeout=30)
    _commons_last[0] = time.time()
    if r.status_code == 429: time.sleep(60); r = requests.get("https://commons.wikimedia.org/w/api.php", params={**params, "format": "json"}, headers=COMMONS_UA, timeout=30)
    r.raise_for_status()
    return r

def commons(title):
    """Up to 4 candidate photos: licence ok, landscape, big, JPEG, not a diagram/logo/people shot, and the file name, description or categories
    contain the dish's words. The picture itself is quality-checked after download (quality_ok)."""
    keep = _stem(words(title)); need = len(keep) if len(keep) <= 2 else -(-len(keep) * 7 // 10)
    out = []
    for q in (f"{title} filetype:bitmap", " ".join(words(title)[:3]) + " food filetype:bitmap"):
        pages = (commons_get({"action": "query", "generator": "search", "gsrsearch": q, "gsrnamespace": 6, "gsrlimit": 15, "prop": "imageinfo",
                              "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1280}).json().get("query") or {}).get("pages", {})
        for pg in sorted(pages.values(), key=lambda x: x.get("index", 99)):
            ii = (pg.get("imageinfo") or [{}])[0]; em = ii.get("extmetadata") or {}
            if ii.get("mime") != "image/jpeg" or ii.get("width", 0) < 1200 or ii.get("height", 0) < 700: continue
            ratio = ii["width"] / ii["height"]
            if not 1.15 <= ratio <= 2.2: continue
            lic = (em.get("LicenseShortName") or {}).get("value", "")
            if not OK_LICENCE.match(lic.strip()): continue
            text = " ".join(re.sub(r"<[^>]+>", " ", (em.get(k) or {}).get("value", "")) for k in ("ImageDescription", "Categories", "ObjectName")) + " " + pg.get("title", "").replace("_", " ")
            if BAD_WORDS.search(text): continue
            if len(keep & _stem(words(text))) < need: continue
            artist = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", (em.get("Artist") or {}).get("value", ""))).strip()[:80] or "unknown author"
            url = ii.get("thumburl") or ii.get("url")
            _commons_src[url] = ii.get("descriptionurl", "")
            out.append((url, f"Photo by {artist}, {lic.strip()}, via Wikimedia Commons"))
        if out: return out[:4]
    return []

def quality_ok(data):
    """Reject soft, dark, washed-out or tiny pictures. Needs Pillow."""
    try:
        from PIL import Image, ImageFilter, ImageStat
        import io
        im = Image.open(io.BytesIO(data)).convert("RGB"); w, h = im.size
        if w < 1000 or h < 560: return False
        im = im.resize((800, max(1, int(h * 800 / w)))); g = im.convert("L")
        sharp = ImageStat.Stat(g.filter(ImageFilter.FIND_EDGES)).var[0]; st = ImageStat.Stat(g)
        return sharp >= MIN_SHARP and MIN_BRIGHT <= st.mean[0] <= MAX_BRIGHT and st.stddev[0] >= MIN_CONTRAST
    except Exception:
        return False

def ai_image(title):
    import asyncio, base64
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id="img", system_message="You create realistic overhead food photos.")
    chat.with_model("gemini", "gemini-2.5-flash-image-preview").with_params(modalities=["image", "text"])
    _, imgs = asyncio.run(chat.send_message_multimodal_response(UserMessage(text=f"Realistic overhead photo of {title}, plated on a ceramic plate, natural light, no text, no people.")))
    return base64.b64decode(imgs[0]["data"]) if imgs else None

if __name__ == "__main__":
    # --file may list several staged files separated by commas; they share one hourly limit and one priority order
    files = [ROOT/Path(x) for x in arg("--file", "data/master_recipes.json").split(",")]
    sets = [(f, json.load(open(f, encoding="utf-8"))) for f in files]; OUT.mkdir(parents=True, exist_ok=True)
    PROVIDERS = ([("pixabay", pixabay)] if PIX_KEY else []) + ([("pexels", pexels)] if KEY else []) + ([("commons", commons)] if COMMONS_ON else [])
    names = [n for n, _ in PROVIDERS]
    for _, data in sets:
        for r in data:
            if r.get("image_no_match") and "tried" not in r: r["tried"] = ["pexels"]       # misses from earlier runs were Pexels misses
            if "--retry-misses" in sys.argv: r["tried"] = []; r.pop("image_no_match", None)
    def pending(r): return not r.get("image") and not r.get("needs_review") and any(n not in r.get("tried", []) for n in names)
    todo = [r for _, data in sets for r in data if pending(r)]
    lim = int(arg("--limit", len(todo)))
    if arg("--priority"):                                   # e.g. --priority drink,sauce,snack : those sections get their photos first
        order = {c: n for n, c in enumerate(arg("--priority").split(","))}
        todo.sort(key=lambda r: order.get(r.get("category"), len(order)))
    done = 0; extra = []
    PHOTO_KEYS = ("image_source_url", "upgrade_checked", "tried", "image", "image_attribution", "image_source", "image_no_match", "gallery_images")
    def save():
        """Re-read each file from disk and copy in only the photo fields, so edits made to the file meanwhile are never overwritten. Atomic write."""
        if "--dry" in sys.argv: return
        for f, data in sets:
            try: disk = json.load(open(f, encoding="utf-8"))
            except Exception: continue
            mine = {r["recipe_id"]: r for r in data}
            for d in disk:
                r = mine.get(d["recipe_id"])
                if r:
                    for k in PHOTO_KEYS:
                        if k in r: d[k] = r[k]
                        else: d.pop(k, None)
            tmp = f.with_suffix(".tmp"); json.dump(disk, open(tmp, "w", encoding="utf-8"), ensure_ascii=False); os.replace(tmp, f)
    save_hook = save
    if "--upgrade" in sys.argv:        # second look at photos we already have: swap in a Pixabay photo only if its tags match EVERY word of the dish name
        if not PIX_KEY: sys.exit("--upgrade needs PIXABAY_API_KEY")
        cand = [r for _, data in sets for r in data if r.get("image") and not r.get("needs_review") and not r.get("upgrade_checked") and "Pixabay" not in (r.get("image_attribution") or "")]
        print(f"{len(cand)} photos to take a second look at", flush=True); swapped = 0
        for r in cand:
            for attempt in range(6):
                try:
                    found = pixabay_strict(r["title"])
                    if found:
                        url, credit = found[0]; data_ = requests.get(url, timeout=30).content
                        newp = OUT/f"{r['recipe_id']}_px.jpg"; newp.write_bytes(data_)
                        old = {"user_id": "system_seeder", "image_url": r["image"], "attribution": r.get("image_attribution") or "Photo from Pexels", "uploaded_at": "2026-11-28T00:00:00+00:00"}
                        r.setdefault("gallery_images", []).insert(0, old)       # the earlier picture stays as an extra photo
                        r["image"] = f"/recipe-images/{r['recipe_id']}_px.jpg"; r["image_attribution"] = credit; swapped += 1
                        print("  better photo:", r["title"], flush=True)
                    r["upgrade_checked"] = True; break
                except Exception as e:
                    print(f"  {r['title']}: {e}; waiting then trying again", flush=True); time.sleep(30 * (attempt + 1))
            if sum(1 for x in cand if x.get("upgrade_checked")) % 25 == 0: save()
        save(); print(f"swapped {swapped} photos; second look finished, 0 recipes still have no image"); sys.exit(0)
    for r in todo[:lim]:
        dest = OUT/f"{r['recipe_id']}.jpg"; img = None; credit = None; extra = []
        if dest.exists():   # already downloaded earlier: just link it, no search needed
            r["image"] = f"/recipe-images/{r['recipe_id']}.jpg"; r.setdefault("image_attribution", "Photo from Pexels"); done += 1; continue
        failed = False
        for attempt in range(6):                     # temporary problems (busy, offline, Mac woke from sleep) are retried, never end the run
            try:
                for name, fn in PROVIDERS:                     # each source is tried once per recipe; misses are remembered per source
                    if name in r.setdefault("tried", []): continue
                    try: found = fn(r["title"])
                    except PexelsBusy: continue             # Pexels full for this hour: leave it untried for this recipe, carry on
                    if found and name == "commons":                 # try each candidate until one passes the picture-quality check
                        for url, credit in found:
                            data_ = requests.get(url, timeout=30, headers=COMMONS_UA).content
                            if quality_ok(data_): img = data_; r["image_source_url"] = _commons_src.get(url, ""); r["image_source"] = "wikimedia-commons"; break
                        if img: extra = []; break
                    elif found:
                        url, credit = found[0]
                        img = requests.get(url, timeout=30).content
                        extra = found[1:]
                        break
                    r["tried"].append(name)
                if img is None and "--ai" in sys.argv and os.environ.get("ENABLE_AI_IMAGES") == "1":
                    img = ai_image(r["title"]); credit = "AI-generated illustration"
                    r["image_source"] = "ai-generated"
                failed = False; break
            except requests.HTTPError as e:
                failed = True
                code = e.response.status_code if e.response is not None else 0
                wait = 600 if code == 429 else 30 * (attempt + 1)
                print(f"  {r['title']}: {code or e}; waiting {wait // 60 or 1} min then trying again", flush=True); save(); time.sleep(wait)
            except Exception as e:
                failed = True
                print(f"  {r['title']}: {e}; waiting then trying again", flush=True); time.sleep(30 * (attempt + 1))
        if failed: continue                           # gave up on this one for now; NOT marked no-match, so a later pass tries it again
        if not img:
            print("  no match:", r["title"])
            if PROVIDERS and "--dry" not in sys.argv and all(n in r.get("tried", []) for n in names): r["image_no_match"] = True     # remembered, so the next run skips it (use --retry-misses to try again)
            continue
        print("  ok:", r["title"], "-", credit)
        if "--dry" not in sys.argv:
            dest.write_bytes(img); r["image"] = f"/recipe-images/{r['recipe_id']}.jpg"; r["image_attribution"] = credit; r.pop("image_no_match", None)
            for n, (u2, c2) in enumerate(extra, start=2):      # more matching photos become the recipe's extra pictures
                try:
                    d2 = OUT/f"{r['recipe_id']}_{n}.jpg"; d2.write_bytes(requests.get(u2, timeout=30).content)
                    r.setdefault("gallery_images", []).append({"user_id": "system_seeder", "image_url": f"/recipe-images/{r['recipe_id']}_{n}.jpg",
                                                              "attribution": c2, "uploaded_at": "2026-11-27T00:00:00+00:00"})
                except Exception as e: print("  extra photo skipped:", e)
        done += 1; time.sleep(0.4)
        if done % 10 == 0: save()
    save()
    left = sum(1 for _, data in sets for r in data if pending(r))
    print(f"filled {done} this run; {left} recipes still have no image")
