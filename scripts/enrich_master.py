"""Rewrite data/master_recipes.json with estimated times and better descriptions (see backend/master_enrich.py).
Safe to re-run. Usage: python scripts/enrich_master.py"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
import master_enrich as e  # noqa: E402

PATH = ROOT / "data" / "master_recipes.json"
PLACEHOLDER_PREP = {"15 min"}
PLACEHOLDER_COOK = {"30 min", "45 min"}


def main():
    data = json.loads(PATH.read_text())
    rows = data if isinstance(data, list) else data["recipes"]
    t = d = 0
    for r in rows:
        if r.get("prep_time") in PLACEHOLDER_PREP and r.get("cook_time") in PLACEHOLDER_COOK and not r.get("time_estimated"):
            r["prep_time"], r["cook_time"], r["time_estimated"] = e.estimate_times(r)
            t += 1
        if e.GENERIC_DESC.match(r.get("description") or ""):
            r["description"] = e.make_description(r)
            d += 1
    PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(f"{t} recipes got estimated times, {d} got a better description (of {len(rows)}).")


if __name__ == "__main__":
    main()
