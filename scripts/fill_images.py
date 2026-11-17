#!/usr/bin/env python3
"""Give every recipe with no image a proper one.
 1) Free photo from Pexels (free licence, no credit legally required but we store one anyway).
    Get a free key at https://www.pexels.com/api/ and set it:  export PEXELS_API_KEY=...
 2) Optional --ai: generate an image (needs ENABLE_AI_IMAGES=1 and the Emergent LLM key, i.e. run on Emergent).
 Images are saved to frontend/public/recipe-images/<recipe_id>.jpg and recipe['image'] is set to /recipe-images/<id>.jpg
 Usage:  python scripts/fill_images.py [--file data/staging/wikibooks_approved.json] [--limit 50] [--ai] [--dry]
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

def pexels(title):
    """Try the full title, then shorter searches. Keep a photo only if its description shares a word with the dish name."""
    keep = set(words(title))
    for q in queries(title):
        r = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": KEY},
                         params={"query": q, "per_page": 5, "orientation": "landscape"}, timeout=20)
        r.raise_for_status()
        for p in r.json().get("photos", []):
            if keep & set(words(p.get("alt") or "")):
                return p["src"]["large"], f"Photo by {p['photographer']} on Pexels"
        time.sleep(0.4)
    return None, None

def ai_image(title):
    import asyncio, base64
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id="img", system_message="You create realistic overhead food photos.")
    chat.with_model("gemini", "gemini-2.5-flash-image-preview").with_params(modalities=["image", "text"])
    _, imgs = asyncio.run(chat.send_message_multimodal_response(UserMessage(text=f"Realistic overhead photo of {title}, plated on a ceramic plate, natural light, no text, no people.")))
    return base64.b64decode(imgs[0]["data"]) if imgs else None

if __name__ == "__main__":
    data = json.load(open(F, encoding="utf-8")); OUT.mkdir(parents=True, exist_ok=True)
    todo = [r for r in data if not r.get("image")]; lim = int(arg("--limit", len(todo)))
    done = 0; searches = 0; MAX = 190   # Pexels free key allows ~200 searches/hour
    def save():
        if "--dry" not in sys.argv: json.dump(data, open(F, "w", encoding="utf-8"), ensure_ascii=False)
    for r in todo[:lim]:
        if KEY and searches >= MAX and "--ai" not in sys.argv:
            print(f"Reached the hourly Pexels limit. Progress saved. Run the same command again in 1 hour."); break
        dest = OUT/f"{r['recipe_id']}.jpg"; img = None; credit = None
        if dest.exists():   # already downloaded earlier: just link it, no search needed
            r["image"] = f"/recipe-images/{r['recipe_id']}.jpg"; r.setdefault("image_attribution", "Photo from Pexels"); done += 1; continue
        try:
            if KEY:
                searches += 1
                url, credit = pexels(r["title"])
                if url: img = requests.get(url, timeout=30).content
            if img is None and "--ai" in sys.argv and os.environ.get("ENABLE_AI_IMAGES") == "1":
                img = ai_image(r["title"]); credit = "AI-generated illustration"
                r["image_source"] = "ai-generated"
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                print("Pexels says too many requests. Progress saved. Run the same command again in 1 hour."); break
            print("  skip", r["title"], e); continue
        except Exception as e:
            print("  skip", r["title"], e); continue
        if not img: print("  no match:", r["title"]); continue
        print("  ok:", r["title"], "-", credit)
        if "--dry" not in sys.argv:
            dest.write_bytes(img); r["image"] = f"/recipe-images/{r['recipe_id']}.jpg"; r["image_attribution"] = credit
        done += 1; time.sleep(0.4)
        if done % 10 == 0: save()
    save()
    left = sum(1 for r in data if not r.get("image"))
    print(f"filled {done} this run; {left} recipes still have no image")
