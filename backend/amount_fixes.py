"""Repair ingredient lines whose quantity ended up inside the name, and decide which ingredients really lack an amount."""
import re
from amounts import split_ingredient
from wikibooks_categories import NO_AMOUNT_NEEDED

_QTY_START = re.compile(r"^\s*(?:\d|[¼½¾⅐⅑⅒⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞]|a (?:pinch|dash|handful|splash)|one |two |three |half )", re.I)
_EMPTY_PARENS = re.compile(r"\s*\(\s*\)")


_FRAC = {"¼": .25, "½": .5, "¾": .75, "⅛": .125, "⅜": .375, "⅝": .625, "⅞": .875, "⅓": 1 / 3, "⅔": 2 / 3}
_SUM = re.compile(r"^\s*([\d¼½¾⅛⅜⅝⅞⅓⅔]+)\s*\+\s*([\d¼½¾⅛⅜⅝⅞⅓⅔]+)\s*(.*)$")
_ITEM_UNIT = re.compile(r"^(?:(?:heaping|heaped|level|rounded|scant)\s+)?(tsp|teaspoons?|tbsp|tablespoons?|cups?|cloves?|pinch(?:es)?|handfuls?|slices?|sprigs?|parts?|shots?|jiggers?|dashes|drops|measures?|scoops?|glass(?:es)?|mililiters?|bottles?)\b\s*(?:\([^)]*\))?\s*(?:of\s+)?(.*)$", re.I)
_SIZE = re.compile(r"^(?:small|medium|large|big)\b", re.I)


def _val(tok: str) -> float:
    total = 0.0
    for ch in tok:
        total += _FRAC[ch] if ch in _FRAC else 0
    digits = re.sub(r"[^\d]", "", tok)
    return total + (float(digits) if digits else 0)


def repair(ing: dict) -> dict:
    """{'amount': '', 'item': '⅜ cup () white wine'} -> {'amount': '⅜ cup', 'item': 'white wine'}; leaves good lines alone."""
    amount, item = str(ing.get("amount") or "").strip(), str(ing.get("item") or "").strip()
    item = _EMPTY_PARENS.sub("", item).strip()
    m = _SUM.match(amount)                                  # "5½+⅛ tsp" -> "5.625 tsp"
    if m:
        amount = f"{_val(m.group(1)) + _val(m.group(2)):g} {m.group(3)}".strip()
    item = re.sub(r"^(?:ea\.?|each)\s+", "", item, flags=re.I)         # "ea. (300 g) eggs"
    lead = re.match(r"^\(\s*(\d+(?:\.\d+)?\s*(?:g|kg|ml|l|oz))\s*\)\s*(.+)$", item, re.I)   # "(300 g) white sugar"
    if lead:
        amount = f"{lead.group(1)}" if not amount or re.fullmatch(r"[\d.\s½¼¾]+(?:cups?|tbsp|tsp)?", amount, re.I) else amount
        item = lead.group(2)
    lp = re.match(r"^\(([^)]*\d[^)]*)\)\s*(.+)$", item)          # "500 g" + "(1.1 lb) beef" -> "500 g (1.1 lb)" + "beef"
    if lp and amount:
        amount, item = f"{amount} ({lp.group(1).strip()})", lp.group(2).strip()
    mu = _ITEM_UNIT.match(item)                              # amount '1', item 'heaping tsp of ground coffee' -> '1 tsp', 'ground coffee'
    if not amount and re.match(r"^(?:parts?|shots?|jiggers?|dashes|drops|measures?|scoops?)\b", item, re.I):   # bar measures with no number: one
        amount = "1"
    if mu and amount and re.fullmatch(r"[\d.\s½¼¾⅓⅔]+", amount):
        amount, item = f"{amount} {mu.group(1)}".strip(), mu.group(2) or item
    if not amount and _SIZE.match(item):                    # "medium onion" with no number: one
        amount = "1"
    if not amount and re.match(r"^[\d¼½¾⅛⅜⅝⅞⅓⅔]", item):
        mq = re.match(r"^([\d.\s/¼½¾⅛⅜⅝⅞⅓⅔]+?)\s*((?:cups?|tbsp|tsp|tablespoons?|teaspoons?|kg|g|ml|l|oz|lbs?)\b)?\s+(.+)$", item, re.I)
        if mq and mq.group(3):
            amount, item = f"{mq.group(1).strip()} {mq.group(2) or ''}".strip(), mq.group(3).strip()
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
