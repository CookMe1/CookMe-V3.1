#!/usr/bin/env python3
"""After modernise_old.py: sort what is left.
  python3 scripts/triage_staged.py data/staging/open_new2.json --held data/staging/open_new2_held.json
  - recipes that point at another recipe or name a large-batch size  -> <name>_needs_attention.json (kept out)
  - institutional mixes, washes, frostings, fountain syrups, fondant  -> <name>_dropped.json
  - flagged recipes whose method names foods missing from the list    -> back into the held file
Run enrich_staged.py again afterwards so nutrition is recalculated."""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"scripts")); sys.path.insert(0, str(ROOT/"backend"))
import modernise_old as m

DROP = re.compile(r"\bSyrup\b|\bWash\b|\bFrost(?:ing)?\b|\(Dehydrated|\bMix\)|\bMix$|Fondant|Icing Mix|Cookie Mix", re.I)


def main():
    f = Path(sys.argv[1]); held_path = Path(sys.argv[sys.argv.index("--held") + 1])
    d = json.load(open(f, encoding="utf-8")); h = json.load(open(held_path, encoding="utf-8"))
    stem = f.with_suffix("")
    attention = [r for r in d if r.get("review_reason")]; d = [r for r in d if not r.get("review_reason")]
    dropped = [r for r in d if r.get("needs_review") and DROP.search(r["title"])]; d = [r for r in d if r not in dropped]
    moved = []
    for r in list(d):
        if r.get("needs_review") and r.get("modernised") and m.missing_foods(r):
            r["held_because"] = "main ingredient missing from the list"; r.pop("needs_review", None); r.pop("nutrition", None); moved.append(r); d.remove(r)
    json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(h + moved, open(held_path, "w", encoding="utf-8"), ensure_ascii=False)
    for name, rows in (("needs_attention", attention), ("dropped", dropped)):      # add to what earlier runs put aside, never overwrite it
        p = Path(f"{stem}_{name}.json"); old = json.load(open(p, encoding="utf-8")) if p.exists() else []
        have = {r["recipe_id"] for r in old}
        json.dump(old + [r for r in rows if r["recipe_id"] not in have], open(p, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"kept {len(d)}; needs attention +{len(attention)}; dropped +{len(dropped)}; moved to held {len(moved)}; held now {len(h) + len(moved)}")


if __name__ == "__main__":
    main()
