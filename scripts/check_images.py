#!/usr/bin/env python3
"""Check every image link in data/master_recipes.json is alive and a real picture; blank out dead ones.
Run on your own computer/Emergent shell (needs internet):  python scripts/check_images.py [--fix]
pip install requests"""
import json, sys, concurrent.futures as cf
from pathlib import Path
import requests
f = Path(__file__).resolve().parent.parent/"data"/"master_recipes.json"
data = json.load(open(f, encoding="utf-8"))
def ok(r):
    u = r.get("image")
    if not u: return r, None
    try:
        x = requests.get(u, timeout=15, stream=True)
        good = x.status_code == 200 and x.headers.get("content-type","").startswith("image/") and int(x.headers.get("content-length", 10000)) > 3000
        x.close(); return r, good
    except Exception: return r, False
with cf.ThreadPoolExecutor(16) as ex: res = list(ex.map(ok, data))
bad = [r for r, g in res if g is False]
print(f"{len(bad)} dead/placeholder images out of {sum(1 for r,g in res if g is not None)}")
for r in bad[:30]: print(" ", r["title"], r["image"])
if "--fix" in sys.argv:
    for r in bad: r["image"] = None
    json.dump(data, open(f, "w", encoding="utf-8"), ensure_ascii=False); print("fixed: dead images blanked")
