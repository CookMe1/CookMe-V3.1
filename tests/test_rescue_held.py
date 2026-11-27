import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import rescue_held as rh


def test_fix_replaces_list_and_drops_list_step():
    r = {"title": "Grape Sandwich", "category": "snack", "ingredients": [{"amount": "1 lb", "item": "x"}],
         "steps": ["Skin and seed the grapes, chop with apple and celery, moisten with French dressing, spread on bread."]}
    rh.apply_fix(r, rh.FIXES["Grape Sandwich"])
    assert len(r["ingredients"]) == 5 and r["rescued"] and "held_because" not in r


def test_every_fix_line_has_amount_and_item():
    for fx in rh.FIXES.values():
        for line in fx.get("ings", []) + fx.get("add", []):
            assert "|" in line and line.split("|", 1)[1].strip()
