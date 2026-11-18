"""Download hotlinked recipe images into frontend/public/recipe-images (resized, compressed)
and point data/master_recipes.json at the local copies.

Run on your own computer (needs internet and Pillow):
    pip install pillow requests
    python scripts/mirror_images.py            # all
    python scripts/mirror_images.py --limit 50 # try a few first
Safe to re-run: files already downloaded are skipped. Failed images keep their original link.
"""
import argparse, hashlib, io, json, sys
from pathlib import Path
import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "master_recipes.json"
OUT = ROOT / "frontend" / "public" / "recipe-images"
MAX_W = 800


def mirror(url: str):
    name = "recipe_" + hashlib.md5(url.encode()).hexdigest()[:12] + ".jpg"
    path = OUT / name
    if not path.exists():
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 CookMe image mirror"})
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
        if im.width > MAX_W:
            im = im.resize((MAX_W, round(im.height * MAX_W / im.width)))
        im.save(path, "JPEG", quality=78, optimize=True, progressive=True)
    return "/recipe-images/" + name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    data = json.loads(DATA.read_text())
    recipes = data if isinstance(data, list) else data["recipes"]
    done = failed = 0
    for r in recipes:
        img = str(r.get("image") or "")
        if not img.startswith("http"):
            continue
        if a.limit and done >= a.limit:
            break
        try:
            r["image"] = mirror(img)
            done += 1
        except Exception as e:
            failed += 1
            print("skip", img[:80], "-", type(e).__name__, file=sys.stderr)
        if (done + failed) % 50 == 0:
            print(f"{done} saved, {failed} failed")
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(f"Done: {done} saved locally, {failed} kept their original link.")


if __name__ == "__main__":
    main()
