#!/usr/bin/env python3
"""Build data/nutrition_usda.json (per-100g nutrition for ~7,800 generic foods) from USDA FoodData Central.
USDA data is public domain.

  python scripts/build_usda_table.py                 # downloads the SR Legacy CSV zip (needs internet)
  python scripts/build_usda_table.py --zip file.zip  # or use a zip you downloaded yourself

Download page: https://fdc.nal.usda.gov/download-datasets (choose "SR Legacy", CSV).
Output units per 100 g: calories (kcal), protein/carbs/fat/fiber/sugar (g), sodium (mg).
"""
import argparse, csv, io, json, sys, urllib.request, zipfile
from pathlib import Path

URL = "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip"
NUTRIENTS = {"1008": "calories", "1003": "protein", "1005": "carbs", "1004": "fat", "1079": "fiber", "2000": "sugar", "1093": "sodium"}
OUT = Path(__file__).resolve().parent.parent / "data" / "nutrition_usda.json"


def read_csv(z, name):
    member = next(n for n in z.namelist() if n.endswith("/" + name) or n == name)
    with z.open(member) as f:
        yield from csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    if a.zip:
        data = open(a.zip, "rb").read()
    else:
        print("Downloading", URL)
        data = urllib.request.urlopen(URL, timeout=120).read()
    z = zipfile.ZipFile(io.BytesIO(data))
    foods = {r["fdc_id"]: r["description"] for r in read_csv(z, "food.csv")
             if r.get("data_type", "sr_legacy_food") in ("sr_legacy_food", "foundation_food")}
    vals = {}
    for r in read_csv(z, "food_nutrient.csv"):
        key = NUTRIENTS.get(r["nutrient_id"])
        if key and r["fdc_id"] in foods and r.get("amount") not in (None, ""):
            vals.setdefault(r["fdc_id"], {})[key] = round(float(r["amount"]), 2)
    out = []
    for fid, name in foods.items():
        v = vals.get(fid)
        if v and "calories" in v:
            out.append({"n": name, **{k: v.get(k, 0) for k in NUTRIENTS.values()}})
    out.sort(key=lambda x: x["n"])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"Wrote {len(out)} foods -> {a.out}")


if __name__ == "__main__":
    main()
