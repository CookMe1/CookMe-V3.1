"""Automatic, free (no AI) tagging of recipes: cooking type, vegetarian/vegan and cuisine.
Used when a recipe is saved/imported and by scripts/build_master_recipes.py / scripts/retag_recipes.py.
Gluten-free / dairy-free are deliberately NOT tagged: guessing from ingredient lists is unsafe for allergies."""
import re

EXPENSIVE = r"lamb|salmon|prawn|shrimp|lobster|steak|sirloin|fillet|scallop|crab|duck|veal|saffron|truffle|monkfish|venison|brandy|champagne|wine|oyster|mussel|squid|tuna steak"
CHEAP = r"pasta|spaghetti|noodle|rice|egg|potato|bean|lentil|chickpea|bread|oat|tuna|cabbage|carrot|onion|tomato|pea|sausage|mince|chicken thigh|flour|cheese"
SLOW = r"overnight|marinate for (?:at least )?\d+ hours|\b\d+ hours?\b|slow[- ]cook|chill for|refrigerate for"
def text(r): return ((r.get("title") or "")+" "+" ".join(map(str,r.get("steps") or []))).lower()
def ings(r): return " ".join((str(i.get("item", "")) if isinstance(i, dict) else str(i)) for i in r.get("ingredients") or []).lower()
def types(r):
    t, s, ing = (r.get("title") or "").lower(), text(r), ings(r)
    n_ing, n_steps = len(r.get("ingredients") or []), len(r.get("steps") or [])
    tags = set(x.lower() for x in r.get("tags") or [] if isinstance(x,str))
    dessert = (r.get("category")=="dessert") or bool(tags & {"dessert","desert","cake","pudding","pie","baking","sweet"}) or bool(re.search(r"cake|pudding|curd|delight|cookie|brownie|tart\b|pie\b|fudge|ice cream|mousse|cobbler|crumble|biscuit|muffin|candy", t))
    out = []
    if re.search(r"instant pot|instapot|pressure cooker", s): out += ["instant pot","pressure cooker"]
    if re.search(r"slow cooker|crock ?pot", s): out += ["slow cooker","crockpot"]
    if re.search(r"air ?fr(y|i)er", s): out += ["air fryer"]
    if re.search(r"one[- ]pot|one pan|one-pan|sheet pan|traybake|tray bake|\bstew\b|casserole|chilli|chili|risotto|hotpot|\bsoup\b|pilaf|paella", t) or "instant pot" in out or "slow cooker" in out:
        out += ["one pot"]
    quick = (re.search(r"\b(quick|fast|speedy|15[- ]min|20[- ]min|30[- ]min)", t) or
             (n_ing <= 9 and n_steps <= 5 and not dessert and not re.search(r"soup|stew|roast|braise|casserole|bake|pie|hotpot", t))) and not re.search(SLOW, s)
    if quick: out += ["quick","30 min"]
    if (n_ing <= 9 and n_steps <= 7 and not dessert and re.search(CHEAP, ing) and not re.search(EXPENSIVE, ing+" "+t)):
        out += ["student","budget","easy","cheap"]
    return out

MEAT = r"beef|pork|lamb|chicken|turkey|duck|goose|bacon|\bham\b|sausage|chorizo|mince|steak|veal|prosciutto|pancetta|salami|gelatine|gelatin|lard|suet|anchov|fish|salmon|tuna|cod|haddock|prawn|shrimp|crab|lobster|mussel|squid|oyster|sardine|mackerel|trout|bass|venison|rabbit|liver|kidney|oxtail|brisket|ribs?\b|gammon|pilchard|clam|scallop|monkfish"
DAIRY = r"milk|butter|cheese|cream|yogh?urt|ghee|buttermilk|custard|parmesan|feta|mozzarella|halloumi|ricotta|mascarpone|cheddar|paneer|whey|creme fraiche|condensed"
EGGHONEY = r"\begg|mayonnaise|honey|aioli"
GLUTEN = r"flour|bread|pasta|noodle|spaghetti|couscous|barley|bulgur|semolina|breadcrumb|panko|pastry|biscuit|wheat|soy sauce|beer|tortilla|naan|pitta|pita|lasagn|macaroni|orzo|cake|dough|\brye\b|seitan|cracker|bun\b|rolls?\b|pizza|dumpling|wonton"
CUISINES = ["italian","mexican","indian","chinese","thai","japanese","french","spanish","greek","american","british","mediterranean","middle_eastern","korean","vietnamese","turkish","moroccan","german","caribbean","african","irish","polish","portuguese","russian"]
TITLE_CUISINE = {"italian": r"pasta|pizza|risotto|lasagn|carbonara|tiramisu|gnocchi|bruschetta|parmigiana", "mexican": r"taco|burrito|enchilada|quesadilla|guacamole|fajita|nacho|salsa",
  "indian": r"curry|masala|tikka|biryani|dal\b|daal|paneer|korma|naan|samosa|tandoori|bhaji", "chinese": r"stir[- ]fry|chow mein|kung pao|wonton|dumpling|sweet and sour|\bchinese",
  "japanese": r"sushi|ramen|teriyaki|tempura|miso|katsu|udon", "thai": r"\bthai|pad thai|tom yum|satay", "french": r"\bfrench|ratatouille|crepe|croissant|quiche|gratin|confit|cassoulet",
  "greek": r"\bgreek|moussaka|souvlaki|tzatziki|gyro", "spanish": r"paella|tortilla espa|gazpacho|chorizo|tapas|patatas bravas", "middle_eastern": r"hummus|falafel|shawarma|shakshuka|tahini|kebab|baklava|tagine"}


def diet_tags(r):
    text = ((r.get("title") or "") + " " + ings(r)).lower()
    out = []
    veg = not re.search(MEAT, text)
    if veg: out.append("vegetarian")
    plant = re.sub(r"coconut (?:milk|cream|butter)|(?:almond|soy|soya|oat|rice|cashew|hazelnut|plant|nut)[- ](?:milk|butter|cream)|peanut butter|cocoa butter|shea butter|butternut|vegan (?:butter|cheese|cream)|dairy[- ]free (?:milk|butter|cheese|cream)", " ", text)
    dairy = bool(re.search(DAIRY, plant))
    if veg and not dairy and not re.search(EGGHONEY, text): out.append("vegan")
    # gluten-free / dairy-free are NOT tagged: guessing from ingredient lists is unsafe for allergies.
    return out


def infer_cuisine(r):
    c = (r.get("cuisine") or "").strip().lower().replace(" ", "_")
    if c: return c
    tags = {t.lower().replace(" ", "_") for t in r.get("tags") or [] if isinstance(t, str)}
    for k in CUISINES:
        if k in tags: return k
    if "asian" in tags: return "asian"
    for k, pat in TITLE_CUISINE.items():
        if re.search(pat, (r.get("title") or "").lower()): return k
    return ""



def auto_tag(recipe: dict) -> dict:
    """Return {'tags': [...merged...], 'cuisine': '...'} for a recipe dict. Existing tags and cuisine are kept."""
    r = {**recipe, "title": recipe.get("title") or ""}
    existing = [t for t in (recipe.get("tags") or []) if isinstance(t, str)]
    base = {t for t in existing if t.lower() not in ("vegetarian", "vegan")}
    tags = sorted(base | set(types(r)) | set(diet_tags(r)))
    return {"tags": tags, "cuisine": infer_cuisine(r)}
