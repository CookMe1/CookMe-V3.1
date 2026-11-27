#!/usr/bin/env python3
"""Give every recipe with no image a proper one.
 1) Free photo from Pexels (free licence, no credit legally required but we store one anyway).
    Get a free key at https://www.pexels.com/api/ and set it:  export PEXELS_API_KEY=...
 2) Optional --ai: generate an image (needs ENABLE_AI_IMAGES=1 and the Emergent LLM key, i.e. run on Emergent).
 Images are saved to frontend/public/recipe-images/<recipe_id>.jpg and recipe['image'] is set to /recipe-images/<id>.jpg
 Usage:  python scripts/fill_images.py [--file data/staging/a.json,data/staging/b.json] [--limit 50] [--ai] [--dry] [--retry-misses] [--priority drink,sauce,snack]
Photo choice is a best match for the dish name, so spot-check a few. AI ones are labelled 'AI-generated illustration'."""
import json, os, sys, time
from pathlib import Path
import requests
ROOT = Path(__file__).resolve().parent.parent
F = ROOT/Path(sys.argv[sys.argv.index("--file") + 1]) if "--file" in sys.argv else ROOT/"data"/"master_recipes.json"
OUT = ROOT/"frontend"/"public"/"recipe-images"
KEY = os.environ.get("PEXELS_API_KEY", "")

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
    return qs

import collections
HOURLY_MAX = 199                      # never more than 199 Pexels requests in any rolling hour (the free key allows 200)
_sent = collections.deque()

def pexels_get(params):
    """One Pexels search. Waits first if 199 requests were already made in the last hour, so we never go over."""
    while True:
        now = time.time()
        while _sent and now - _sent[0] > 3600: _sent.popleft()
        if len(_sent) < HOURLY_MAX: break
        wait = int(3600 - (now - _sent[0])) + 5
        print(f"  at the hourly limit ({HOURLY_MAX}); waiting {wait // 60} min. Keep this window open.", flush=True)
        save_hook and save_hook()
        time.sleep(min(wait, 600))
    _sent.append(time.time())
    r = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": KEY}, params=params, timeout=20)
    r.raise_for_status()
    return r

save_hook = None

def pexels(title):
    """Try the full title, then shorter searches. Keep photos only if their description shares a word with the dish name.
    Returns up to 3 matching photos from the same search (no extra searches): [(url, credit), ...]."""
    keep = set(words(title))
    for q in queries(title):
        r = pexels_get({"query": q, "per_page": 8, "orientation": "landscape"})
        found = [(p["src"]["large"], f"Photo by {p['photographer']} on Pexels") for p in r.json().get("photos", [])
                 if keep & set(words(p.get("alt") or ""))]
        if found:
            return found[:3]
        time.sleep(0.4)
    return []

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
    todo = [r for _, data in sets for r in data if not r.get("image") and not r.get("needs_review") and (not r.get("image_no_match") or "--retry-misses" in sys.argv)]
    lim = int(arg("--limit", len(todo)))
    if arg("--priority"):                                   # e.g. --priority drink,sauce,snack : those sections get their photos first
        order = {c: n for n, c in enumerate(arg("--priority").split(","))}
        todo.sort(key=lambda r: order.get(r.get("category"), len(order)))
    done = 0; extra = []
    def save():
        if "--dry" not in sys.argv:
            for f, data in sets: json.dump(data, open(f, "w", encoding="utf-8"), ensure_ascii=False)
    save_hook = save
    for r in todo[:lim]:
        dest = OUT/f"{r['recipe_id']}.jpg"; img = None; credit = None; extra = []
        if dest.exists():   # already downloaded earlier: just link it, no search needed
            r["image"] = f"/recipe-images/{r['recipe_id']}.jpg"; r.setdefault("image_attribution", "Photo from Pexels"); done += 1; continue
        try:
            if KEY:
                found = pexels(r["title"])
                if found:
                    url, credit = found[0]
                    img = requests.get(url, timeout=30).content
                    extra = found[1:]
            if img is None and "--ai" in sys.argv and os.environ.get("ENABLE_AI_IMAGES") == "1":
                img = ai_image(r["title"]); credit = "AI-generated illustration"
                r["image_source"] = "ai-generated"
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                print("Pexels says too many requests. Progress saved. Run the same command again in 1 hour."); break
            print("  skip", r["title"], e); continue
        except Exception as e:
            print("  skip", r["title"], e); continue
        if not img:
            print("  no match:", r["title"])
            if KEY and "--dry" not in sys.argv: r["image_no_match"] = True     # remembered, so the next run skips it (use --retry-misses to try again)
            continue
        print("  ok:", r["title"], "-", credit)
        if "--dry" not in sys.argv:
            dest.write_bytes(img); r["image"] = f"/recipe-images/{r['recipe_id']}.jpg"; r["image_attribution"] = credit
            for n, (u2, c2) in enumerate(extra, start=2):      # more matching photos become the recipe's extra pictures
                try:
                    d2 = OUT/f"{r['recipe_id']}_{n}.jpg"; d2.write_bytes(requests.get(u2, timeout=30).content)
                    r.setdefault("gallery_images", []).append({"user_id": "system_seeder", "image_url": f"/recipe-images/{r['recipe_id']}_{n}.jpg",
                                                              "attribution": c2, "uploaded_at": "2026-11-27T00:00:00+00:00"})
                except Exception as e: print("  extra photo skipped:", e)
        done += 1; time.sleep(0.4)
        if done % 10 == 0: save()
    save()
    left = sum(1 for _, data in sets for r in data if not r.get("image") and not r.get("needs_review") and not r.get("image_no_match"))
    print(f"filled {done} this run; {left} recipes still have no image")
