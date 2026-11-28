#!/usr/bin/env python3
"""Make a contact sheet to eyeball photos before they go live.

  python3 scripts/photo_review.py                # newest sources only: Wikimedia Commons + Pixabay photos
  python3 scripts/photo_review.py --all          # every photo
  python3 scripts/photo_review.py --sample 300   # random 300 of the chosen set

Opens as data/staging/photo_review.html (double-click it). Every photo starts ticked = keep. Untick the bad ones, press "Copy the ones to remove",
and paste the list to Claude (or run  python3 scripts/remove_photos.py id1,id2,...). Removed recipes simply go back to having no photo."""
import json, random, sys, html
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; ST = ROOT/"data"/"staging"
FILES = ["open_new", "open_new2", "wikibooks_approved"]
allp = "--all" in sys.argv; sample = int(sys.argv[sys.argv.index("--sample") + 1]) if "--sample" in sys.argv else 0
rows = []
for f in FILES:
    for r in json.load(open(ST/f"{f}.json", encoding="utf-8")):
        a = r.get("image_attribution") or ""
        if r.get("image") and not r.get("needs_review") and (allp or r.get("image_source") == "wikimedia-commons" or "Pixabay" in a):
            rows.append(r)
if sample and len(rows) > sample: random.seed(1); rows = random.sample(rows, sample)
cards = "".join(
    f'<label class="c"><input type="checkbox" checked data-id="{r["recipe_id"]}"><img loading="lazy" src="../../frontend/public{html.escape(r["image"])}">'
    f'<b>{html.escape(r["title"])}</b><small>{html.escape(r.get("image_attribution") or "")}</small></label>' for r in rows)
page = f"""<!doctype html><meta charset=utf-8><title>Grubly photo review</title>
<style>body{{font:14px system-ui;margin:16px;background:#f6f4ef}}.g{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}}
.c{{background:#fff;border-radius:10px;padding:8px;display:block;position:relative}}.c img{{width:100%;aspect-ratio:3/2;object-fit:cover;border-radius:6px}}
.c input{{position:absolute;top:14px;left:14px;width:22px;height:22px}}.c small{{display:block;color:#666}}.c:has(input:not(:checked)){{outline:3px solid #d33;opacity:.55}}
button{{position:sticky;top:8px;padding:10px 16px;font-size:15px;border-radius:8px;border:0;background:#2b6;color:#fff;z-index:3}}</style>
<button onclick="let l=[...document.querySelectorAll('input:not(:checked)')].map(i=>i.dataset.id).join(',');navigator.clipboard.writeText(l);this.textContent='Copied '+(l?l.split(',').length:0)+' to remove'">Copy the ones to remove</button>
<p>{len(rows)} photos. Untick any that look cheap, blurry, dark, off-topic or show the wrong dish.</p><div class="g">{cards}</div>"""
out = ST/"photo_review.html"; out.write_text(page, encoding="utf-8"); print(f"{len(rows)} photos -> {out}")
