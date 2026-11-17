"""Runs the staging script against a fake Wikibooks (no internet)."""
import csv, importlib.util, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from test_wikibooks_parser import SAMPLE

def good(i):
    ings = "\n".join(f"* {n} cups [[Cookbook:Thing{j}|thing{j}]]" for j, n in enumerate(range(1, 7)))
    steps = "\n".join(f"# Do step {k} carefully, stirring so that nothing sticks to the bottom of the pan." for k in range(1, 5))
    return f"{{{{recipesummary|Category=Italian cuisine|Servings=4|Time=30 minutes}}}}\n\n== Ingredients ==\n{ings}\n\n== Procedure ==\n{steps}\n"

PAGES = {"Cookbook:Irish Soda Bread": SAMPLE, "Cookbook:Flour": "Flour is a powder.", "Cookbook:Pasta Dish One": good(1),
         "Cookbook:Mint Cocktail": good(2), "Cookbook:Thin": "== Ingredients ==\n* 1 egg\n* 1 cup milk\n== Procedure ==\n# Mix."}

def test_staging_end_to_end(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("stage", ROOT / "scripts" / "stage_wikibooks.py")
    st = importlib.util.module_from_spec(spec); spec.loader.exec_module(st)
    monkeypatch.setattr(st, "OUT", tmp_path); monkeypatch.setattr(st, "CACHE", tmp_path / "c"); (tmp_path / "c").mkdir()
    def fake_api(params):
        if params.get("list") == "allpages":
            return {"query": {"allpages": [{"title": t} for t in PAGES]}}
        titles = params["titles"].split("|")
        return {"query": {"pages": [{"title": t, "revisions": [{"slots": {"main": {"content": PAGES[t]}}}]} for t in titles]}}
    monkeypatch.setattr(st, "api", fake_api); monkeypatch.setattr(st.time, "sleep", lambda s: None)
    monkeypatch.setattr(sys, "argv", ["stage"])
    st.main()
    data = json.load(open(tmp_path / "wikibooks.json", encoding="utf-8"))
    titles = {r["title"] for r in data}
    assert "Irish Soda Bread" in titles and "Pasta Dish One" in titles and "Flour" not in titles and "Thin" not in titles
    rows = list(csv.reader(open(tmp_path / "wikibooks_review.csv", encoding="utf-8-sig")))
    keep = {r[1]: r[0] for r in rows[1:]}
    assert keep["Pasta Dish One"] == "y" and keep["Mint Cocktail"] == "n"
