"""Repair ingredient lines whose quantity ended up inside the name, and decide which ingredients really lack an amount."""
import re
from amounts import split_ingredient
from wikibooks_categories import NO_AMOUNT_NEEDED

_QTY_START = re.compile(r"^\s*(?:\d|[¼½¾⅐⅑⅒⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞]|a (?:pinch|dash|handful|splash)|one |two |three |half )", re.I)
_EMPTY_PARENS = re.compile(r"\s*\(\s*\)")


def repair(ing: dict) -> dict:
    """{'amount': '', 'item': '⅜ cup () white wine'} -> {'amount': '⅜ cup', 'item': 'white wine'}; leaves good lines alone."""
    amount, item = str(ing.get("amount") or "").strip(), str(ing.get("item") or "").strip()
    item = _EMPTY_PARENS.sub("", item).strip()
    if not amount and _QTY_START.match(item):
        a, i = split_ingredient(item)
        if a and i:
            amount, item = a, i
    return {**ing, "amount": amount, "item": item}


def lacks_amount(ing: dict) -> bool:
    if str(ing.get("amount") or "").strip():
        return False
    return not NO_AMOUNT_NEEDED.search(str(ing.get("item") or "").strip().lower())


def coverage(ings) -> float:
    """Share of ingredients that have an amount or never need one."""
    ings = list(ings or [])
    return 1.0 if not ings else sum(1 for i in ings if not lacks_amount(i)) / len(ings)
