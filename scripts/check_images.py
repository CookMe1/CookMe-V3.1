#!/usr/bin/env python3
"""Find dead, tiny, stock/placeholder and repeated images in data/master_recipes.json.
Needs internet (run on your computer or the Emergent shell):  pip install requests
  python scripts/check_images.py          # report only
  python scripts/check_images.py --fix    # blank the bad ones (so fill_images.py can replace them)
A 'holding' image = the same picture file used by 2+ recipes, or a known stock fallback URL."""
import json, sys, hashlib, collections, concurrent.futures as cf
from pathlib import Path
import requests
f = Path(__file__).resolve().parent.parent/"data"/"master_recipes.json"
data = json.load(open(f, encoding="utf-8"))
STOCK = ("images.unsplash.com/photo-1546069901", "placeholder", "no-image", "noimage", "default.jpg")

def check(r):
    u = r.get("image")
    if not u: return r, "missing", None
    if u.startswith("data:"): return r, "data-url", None
    if any(s in u for s in STOCK): return r, "stock", None
    try:
        x = requests.get(u, timeout=20)
        if x.status_code != 200: return r, f"http-{x.status_code}", None
        if not x.headers.get("content-type", "").startswith("image/"): return r, "not-image", None
        if len(x.content) < 5000: return r, "tiny", None
        return r, "ok", hashlib.sha1(x.content).hexdigest()
    except Exception: return r, "error", None

if __name__ == "__main__":
    with cf.ThreadPoolExecutor(16) as ex: res = list(ex.map(check, data))
    hashes = collections.Counter(h for _, s, h in res if h)
    problems = []
    for r, s, h in res:
        if s == "ok" and hashes[h] > 1: s = "repeated"
        if s != "ok": problems.append((r, s))
    summary = collections.Counter(s for _, s in problems)
    print(f"{len(problems)} of {len(data)} recipes need a new image:", dict(summary))
    for r, s in problems[:40]: print(f"  [{s}] {r['title']}")
    if "--fix" in sys.argv:
        for r, s in problems: r["image"] = None; r.pop("image_attribution", None)
        json.dump(data, open(f, "w", encoding="utf-8"), ensure_ascii=False)
        print("bad images blanked; now run scripts/fill_images.py")
