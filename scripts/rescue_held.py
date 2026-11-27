#!/usr/bin/env python3
"""Second look at recipes the earlier checks held back (data/staging/open_new2_held.json).

  python3 scripts/rescue_held.py data/staging/open_new2.json --held data/staging/open_new2_held.json

For old-cookbook recipes whose ingredient list is only written inside the method ("2 cups of flour, 1 egg, a little salt."), the list is
read properly, the list line is removed from the method and the ingredient list is rebuilt from it (the old list was often wrong, e.g.
"1/2 pound" read as "1 lb"). A small table (FIXES) adds the foods that the method itself names for sandwiches, sauces and sweets, using only
what the recipe text says. Recipes that stay held have no method, or a main ingredient the text never gives. Nothing is invented.
Run enrich_staged.py afterwards so nutrition is calculated."""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"backend")); sys.path.insert(0, str(ROOT/"scripts"))
from amount_fixes import repair, coverage
from stage_wikibooks import score
import modernise_old as m

# title (and optional start of first step) -> changes. "ings" replaces the list, "add" appends, "drop" removes steps by position,
# "step" replaces a step, "category", "title".  Entries are "amount|item".
A = "as needed"
FIXES = {
    "Chili and Spice Seasoning": {}, "Hot 'N Spicy Seasoning": {}, "Spinach, Tomatoes, and Corn": {}, "Sunshine Salad": {}, "Anchovy Butter": {},
    "Lemon Butter": {}, "Vinaigrette Sauce": {},
    "Apple Omelet": {"category": "side", "drop": [1], "ings": ["9|large tart apples", "4|eggs", "200 g (1 cup)|sugar", "1 tbsp|butter", "to taste|cinnamon or other spices"]},
    "French Nougat": {"step": {0: "Put the sugar in a saucepan, place on the hob, and stir constantly until melted."}},
    "Orange Fritters": {"ings": ["2|eggs, separated", "2 tbsp|sugar", "1/4|lemon, juiced", f"{A}|flour, enough to make a thick batter", f"{A}|oranges, sliced", f"{A}|oil or butter, for frying", f"{A}|powdered sugar, to sprinkle"]},
    "Caviare Sandwich No. 2": {"ings": ["1 can|caviare", "1/2|lemon, juiced", "1 tsp|olive oil", f"{A}|thin slices white bread, lightly buttered"]},
    "Lobster Sandwich No. 2": {"ings": ["1|cold boiled lobster, meat diced", "1 tbsp|tarragon vinegar", "45 ml (3 tbsp)|melted butter", "to taste|salt", "to taste|red pepper", f"{A}|whole wheat or brown bread, lightly buttered"]},
    "Anchovy Sandwich No. 2": {"ings": ["1 can|boneless anchovies", "3|hard-boiled eggs, chopped fine", "a dash|lemon juice", "5 ml (1 tsp)|melted butter", "a pinch|salt", f"{A}|white bread, lightly buttered", f"{A}|lettuce leaves"]},
    "French Sandwich": {"ings": ["475 ml (1 pint)|cold cooked fish", "2|hard-boiled eggs, chopped fine", "30 ml (2 tbsp)|capers", f"{A}|mayonnaise, to moisten", f"{A}|thin slices white bread, lightly buttered", f"{A}|cress, finely chopped"]},
    "Brown Egg Sandwich": {"ings": ["5|hard-boiled eggs, yolks only", "5 ml (1 tsp)|melted butter", "1 drop|vinegar", "to taste|salt", "to taste|pepper", "a little|French mustard", "1 drop|tabasco sauce", f"{A}|Boston brown bread, sliced wafer thin and lightly buttered", f"{A}|olives, to garnish"]},
    "Chevy Chase Sandwich": {"ings": ["6|hard-boiled eggs", "6|sweet pickles, chopped fine", "a dash|salt", "a dash|white pepper", "10 ml (2 tsp)|melted butter", f"{A}|thin slices white bread, lightly buttered"]},
    "Tartar Sandwich": {"ings": ["30 ml (2 tbsp)|chopped onion", "30 ml (2 tbsp)|chopped parsley", "30 ml (2 tbsp)|capers", "30 ml (2 tbsp)|sour cucumber pickles, chopped", "30 ml (2 tbsp)|mayonnaise dressing", f"{A}|thin slices graham or white bread, lightly buttered"]},
    "Ham Sandwich No. 4": {"add": [f"{A}|mayonnaise dressing", f"{A}|thin slices bread"]},
    "Automobile Sandwich": {"ings": ["900 g (2 lb)|cold boiled ham", "225 g (1/2 lb)|walnut meats", "4|dill pickles", "a little|French mustard", f"{A}|bread, lightly buttered"]},
    "Texas Sandwich": {"ings": ["225 g (1/2 lb)|broiled calf's liver", "to taste|salt", "to taste|cayenne pepper", "5 ml (1 tsp)|melted butter", "a few drops|onion juice", f"{A}|thin slices unbuttered white bread"]},
    "Tongue Sandwich No. 2": {"ings": [f"{A}|boiled tongue, minced", "5 ml (1 tsp)|melted butter", "15 ml (1 tbsp)|tomato ketchup", "a dash|celery salt", f"{A}|thinly buttered bread", f"{A}|sweet pickle, to serve"]},
    "Excursion Sandwich": {"ings": ["240 ml (1 cup)|cold boiled tongue, chopped fine", "30 ml (2 tbsp)|melted butter", "a dash|red pepper", "2 1/2 ml (1/2 tsp)|onion juice", f"{A}|very thin slices white bread", f"{A}|pickle, to serve"]},
    "Mutton And Pea Sandwich": {"ings": [f"{A}|thin slices cold boiled mutton", "240 ml (1/2 pint)|cooked peas", "to taste|salt", "to taste|pepper", "a little|butter", "5 ml (1 tsp)|capers", f"{A}|white bread, lightly buttered", f"{A}|crisp lettuce leaves"]},
    "Chicken And Green Pepper Sandwich": {"ings": ["240 g (2 cups)|cooked chicken", "3|large sweet peppers, stems and seeds removed", "2 1/2 ml (1/2 tsp)|salt", "30 ml (2 tbsp)|sweet cream", f"{A}|thin slices white bread, lightly buttered", f"{A}|lettuce leaves, to serve"]},
    "Parmesan Sandwich": {"ings": [f"{A}|finely grated Parmesan cheese", "a dash|salt", "a dash|pepper", "15 ml (1 tbsp)|tomato ketchup", f"{A}|unsweetened crackers"]},
    "Buffet Sandwich": {"ings": ["150 ml (1 teacup)|grated American or Parmesan cheese", "15 ml (1 tbsp)|melted butter", "5 ml (1 tsp)|made mustard", "a little|salt and pepper", f"{A}|thin slices rye bread, lightly buttered"], "drop": [0]},
    "Pecan And English Walnut Sandwich": {"ings": ["60 g (1/2 cup)|pecan meats", "60 g (1/2 cup)|walnut meats", "120 ml (1/2 cup)|stoned olives, chopped fine", f"{A}|mayonnaise dressing", f"{A}|bread, lightly buttered"]},
    "Peanut Sandwich No. 2": {"ings": ["145 g (1 cup)|freshly roasted shelled peanuts, chopped very fine", "45 ml (3 tbsp)|mayonnaise dressing", "to taste|salt", f"{A}|lightly buttered bread"]},
    "Grape Sandwich": {"ings": ["450 g (1 lb)|white grapes, skinned and seeded", "1|large apple", "2|stalks celery", "a little|French dressing", f"{A}|thin slices white bread, lightly buttered"]},
    "Chocolate Caramels|1/2 pound of chocolate": {"drop": [0], "ings": ["225 g (1/2 lb)|chocolate", "1350 g (3 lb)|dark brown sugar", "56 g (1/8 lb)|butter", "150 ml (1 small teacup)|milk", "to taste|vanilla, or grated lemon or orange peel"]},
    "Spanish Fritters": {"ings": ["480 g (1 quart)|flour", "1|egg, well beaten", "1 large spoonful|yeast", f"{A}|milk", "2 spoonfuls|melted butter", f"{A}|lard, for frying"]},
    "Oxtail Soup": {"add": ["2|large oxtails, cut into pieces", "1|onion, cut fine"]},
    "Salmon Sandwich No. 2": {"drop": [0], "ings": ["1 can|salmon", "2|sticks celery, chopped fine", "1/2|lemon, juiced", "a dash|salt", "5 ml (1 tsp)|melted butter", f"{A}|thin slices white bread, lightly buttered", "1|sprig parsley, to garnish"]},
    "Salmon Sandwich No. 3": {"drop": [0], "ings": ["1 can|salmon", "1|small head lettuce, chopped fine", f"{A}|thin slices white bread, buttered", f"{A}|olives, to garnish"]},
    "Veal Sandwich": {"ings": ["120 g (1 cup)|cooked veal, ground", "15 ml (1 tbsp)|vinegar", "2 1/2 ml (1/2 tsp)|mustard", "1/2|small onion, chopped fine", "to taste|salt and pepper", f"{A}|bread"]},
    "Mutton Sandwich No. 2": {"ings": ["475 ml (1 pint)|cold cooked mutton, chopped very fine", "5 ml (1 tsp)|salt", "15 ml (1 tbsp)|capers", "5 ml (1 tsp)|chopped mint", "a dash|pepper", "15 ml (1 tbsp)|lemon juice", f"{A}|whole wheat bread"]},
    "Chicken And Egg Sandwich": {"ings": ["240 ml (1 cup)|cold chicken, chopped fine", "2|hard-boiled eggs, yolks only, chopped fine", "5 ml (1 tsp)|melted butter", "5 ml (1 tsp)|lemon juice", "5 ml (1 tsp)|rich stock", "to taste|salt and pepper", f"{A}|thin slices white bread, lightly buttered"],
                                 "step": {0: "Chop the cold chicken fine.", 1: "Chop the yolks of the hard-boiled eggs fine."}},
    "Cocoanut Sandwich No. 2": {"ings": ["225 g (1/2 lb)|puff paste", "240 ml (1/2 pint)|cream", "45 ml (3 tbsp)|powdered white sugar", "45 ml (3 tbsp)|desiccated coconut"]},
    "Stuffed Celery Sandwich": {"ings": ["1|cream cheese", "30 ml (2 tbsp)|celery, chopped fine", "15 ml (1 tbsp)|stuffed olives, chopped", "1 1/4 ml (1/4 tsp)|salt", "1/8 tsp|paprika", f"{A}|milk, enough to moisten", f"{A}|bread, cut in circles 1/4 inch thick"]},
    "Caviar Canapés": {"ings": [f"{A}|bread, 1/4 inch thick, cut in 2-inch squares or rounds and toasted", "5 ml (1 tsp) per slice|ice cold caviar", "5 ml (1 tsp)|chopped onion", "5 ml (1 tsp)|chopped parsley", f"{A}|lemon, in quarters, to serve"]},
    "Deviled Tongue Sandwiches": {"category": "snack", "ings": ["240 g (1 cup)|ground cooked tongue", "5 ml (1 tsp)|mustard", "15 ml (1 tbsp)|soup", "5 ml (1 tsp)|mayonnaise", f"{A}|white bread, cut very thin"]},
    "Stewed Beef Tongue": {"category": "main", "add": ["1|fresh beef tongue", "1 or 2 thin slices|ham", "2|medium onions, sliced"]},
    "CELERY SAUCE, for Boiled Turkey, Poultry, &c": {"title": "Celery Sauce for Boiled Turkey or Poultry", "servings": 6, "add": [f"{A}|butter kneaded with flour or arrowroot, to thicken"]},
    "Egg Sauce, or White Sauce": {"title": "Egg Sauce", "servings": 4, "ings": ["2 tbsp|sifted flour", "75 ml (1/2 teacup)|warm butter", "475 ml (1 pint)|sweet milk", "1|saltspoon salt", "a dash|white pepper", "3|hard-boiled eggs, sliced and chopped"]},
    "Lobster Sauce": {"servings": 6, "ings": ["1 tbsp|butter", "1|boiled lobster, coral and spawn only", "112 g (1/4 lb)|sweet butter", "125 ml|water or vinegar", "5 ml (1 tsp)|made mustard"]},
    "Sardine Canapés": {"ings": ["6|sardines, skinned and boned", "30 ml (2 tbsp)|lemon juice", "a few drops|Worcestershire sauce", "a dash|pepper", "10 ml (2 tsp)|chopped parsley", "4 tbsp|creamed butter", f"{A}|stale bread, cut in diamonds and lightly toasted", f"{A}|hard-boiled egg whites, finely chopped", f"{A}|olives, shredded"]},
    "Lobster Sandwich No. 3": {"ings": ["1|medium lobster, meat pounded fine", "15 ml (1 tbsp)|lobster coral, dried and mashed smooth", "1/2|lemon, juiced", "a dash|nutmeg", "28 g (2 tbsp)|soft butter", f"{A}|thin slices white bread, lightly buttered"]},
    "Sardine Sandwich": {"ings": ["2|boxes sardines, skinned and boned", "6|hard-boiled eggs, yolks only", "5 ml (1 tsp)|anchovy paste", "a dash|salt", "a dash|red pepper", "30 ml (2 tbsp)|olive oil", f"{A}|toasted bread"]},
    "Curried Egg And Oyster Sandwiches": {"add": ["4|boiled eggs, chopped very fine", "3|pickled oysters", "to taste|pepper and salt", f"{A}|thin slices white bread, lightly buttered"]},
    "Hot Ham Sandwich No. 2": {"add": [f"{A}|boiled ham, finely minced", f"{A}|thin slices bread, lightly buttered"]},
    "Cheese Rare-Bit Sandwich": {"add": ["112 g (1/4 lb)|American cheese, grated fine", f"{A}|bread"]},
    "Potato And Ham Sandwich": {"ings": ["420 g (1 pint)|well seasoned mashed potatoes", "2|eggs", f"{A}|boiled ham, sliced and neatly trimmed"]},
    "Crab Canapes": {"ings": ["1 can|crab meat", "15 ml (1 tbsp)|sherry", "1|small onion, finely minced", "14 g (1 tbsp)|butter", "240 ml (1 cup)|milk", "7 1/2 g (1 tbsp)|flour", f"{A}|grated Parmesan cheese", f"{A}|rounds of toast"]},
    "Jellied Chicken Sandwich": {"add": [f"{A}|white meat of cold boiled chicken", "1 scant tbsp|gelatine", "120 ml (1/2 cup)|cold water"]},
    "Stuffed Eggs": {"ings": ["6|hard-boiled eggs", "15 ml (1 tbsp)|melted butter", "2 1/2 ml (1/2 tsp)|mustard", "5 ml (1 tsp)|salt", "1 dash|cayenne pepper"]},
    "Cheese Cakes|Place 2 cups of pure milk": {"ings": ["480 ml (2 cups)|pure milk", "1|lemon, juiced", "2|egg yolks", "14 g (1 tbsp)|butter", "150 ml (1 small cup)|sugar", "150 ml (1 small cup)|ground almonds, walnuts or pecans", f"{A}|pastry, to line the patty pans", f"{A}|powdered sugar, to dust"]},
    "Tartare Sauce": {"drop": [0], "ings": ["2|raw egg yolks", "75 ml (1/2 teacup)|pure olive oil", "3 tbsp|vinegar", "1 tbsp|made mustard", "1 tsp|sugar", "1/4 tsp|pepper", "1 tsp|salt", "1 tbsp|onion juice", "1 tbsp|chopped capers", "1 tbsp|chopped cucumber pickle"]},
    "Mixed Summer Salad": {"category": "salad", "drop": [0, 2], "ings": ["3 heads|lettuce", "2 tsp|green mustard leaves", "1 handful|watercress", "5|tender radishes", "1|cucumber", "3|hard-boiled eggs", "2 tsp|white sugar", "1 tsp|salt", "1 tsp|pepper", "1 tsp|made mustard", "150 ml (1 teacup)|vinegar", "75 ml (1/2 teacup)|oil"]},
    "Walnut Ketchup": {"drop": [0], "ings": ["100|green walnuts", "168 g (6 oz)|shallots, cut into pieces", "1|head garlic", "225 g (1/2 lb)|salt", "1.9 l (2 quarts)|vinegar", "56 g (2 oz)|anchovies", "56 g (2 oz)|whole pepper", "7 g (1/4 oz)|mace", "14 g (1/2 oz)|cloves"]},
    "Squash Fritters": {"drop": [0]},
    "Austrian Sandwich": {"drop": [0], "ings": ["2 cans|sardines, boned and skinned, with their oil", "2 balls|cottage cheese", "1|small onion, chopped fine", "30 ml (2 tbsp)|chopped parsley", "30 ml (2 tbsp)|chopped mint", "30 ml (2 tbsp)|vinegar", "to taste|salt", "a dash|red pepper", "2|lemons, grated rind and juice", f"{A}|thin slices rye or brown bread, lightly buttered"]},
    "Dixie Biscuit": {"drop": [0], "ings": ["475 ml (1 pint)|milk", "5 ml (1 tsp)|lard", "10 ml (2 tsp)|butter", "10 ml (2 tsp)|sugar", "1 heaping tsp|salt", "1/2|yeast cake", "720 g (6 cups)|flour", "1|egg, well beaten", f"{A}|melted butter, to brush"]},
    "Mississippi Biscuits": {"drop": [0], "ings": ["240 g (2 cups)|flour", "1/4 tsp|soda", "1 1/2 tsp|baking powder", "5 ml (1 tsp)|salt", "26 g (2 tbsp)|lard", f"{A}|milk, enough to make a soft dough"]},
    "Cotton Blossom Popovers": {"drop": [0]},
    "Flour Muffins": {"drop": [0], "ings": ["2|eggs", "240 ml (1 cup)|milk", "180 g (1 1/2 cups)|flour", "13 g (1 tbsp)|lard", "5 ml (1 tsp)|salt", "10 ml (2 tsp)|baking powder"]},
    "Jeff. Davis Muffins": {"title": "Sour Milk Cornmeal Muffins", "drop": [0, 1], "ings": ["2|eggs", "240 ml (1 cup)|sour milk", "120 g (1 cup)|cornmeal", "60 g (1/2 cup)|flour", "5 ml (1 tsp)|salt", "10 ml (2 tsp)|baking powder", "13 g (1 tbsp)|lard"]},
    "Aunt Sug’s Nut Cookies": {"drop": [0], "ings": ["300 g (1 1/2 cups)|sugar", "225 g (1 cup)|Crisco or butter", "3|eggs", "15 ml (1 tbsp)|cinnamon", "2 1/2 ml (1/2 tsp)|salt", "5 ml (1 tsp)|soda", "60 ml (4 tbsp)|hot water", "360 g (3 cups)|flour", "1 cup each|raisins, currants, and English walnuts or almonds, broken up", "5 ml (1 tsp)|vanilla"]},
    "Mason And Dixon Cookies": {"drop": [0], "ings": ["220 g (1 cup)|brown sugar", "120 ml (1/2 cup)|melted shortening", "1|egg", "120 ml (1/2 cup)|sweet milk", "2 1/2 ml (1/2 tsp)|soda, sifted with the flour", "180 g (1 1/2 cups)|flour", "75 g (1/2 cup)|chopped raisins", "60 g (1/2 cup)|chopped nuts", "2 1/2 ml (1/2 tsp)|salt", "3 squares|melted chocolate"]},
    "Divinity Candy": {"drop": [0], "ings": ["600 g (3 cups)|white sugar", "180 ml (3/4 cup)|white Karo syrup", "2|egg whites", "180 ml (3/4 cup)|water", "5 ml (1 tsp)|vanilla", "120 g (1 cup)|nuts"]},
    "Sea-Foam Candy": {"drop": [0], "ings": ["880 g (4 cups)|brown sugar", "240 ml (1 cup)|water", "2|egg whites", "120 g (1 cup)|nuts", "5 ml (1 tsp)|vanilla"]},
    "Nice And Cheap Jumbles. No Eggs": {"drop": [0], "ings": ["225 g (1 cup)|butter", "400 g (2 cups)|sugar", "240 ml (1 cup)|clabber (soured milk)", "5 ml (1 tsp)|soda, stirred into the clabber", "a little|grated orange or lemon peel", "480 g (1 quart)|sifted flour", f"{A}|citron strips, to decorate (optional)"]},
    "Genoese Cakes": {"drop": [0], "ings": ["225 g (1/2 lb)|butter", "225 g (1/2 lb)|sugar", "4|eggs", "225 g (1/2 lb)|flour", "1 small glass|brandy or wine", f"{A}|bright jelly or preserves, to decorate"]},
    "Nice Drop Cakes": {"drop": [0], "ings": ["225 g (1/2 lb)|sugar", "112 g (1/4 lb)|butter, creamed with the sugar", "4|eggs, well beaten", "225 g (1/2 lb)|currants", "1 spoonful|brandy", "to taste|grated nutmeg or lemon peel", f"{A}|flour, enough for a stiff batter"]},
    "Grilled Chicken Taco Salad Bowls": {}, "Leftover Cranberry Sauce Parfait": {},
}


def apply_fix(r, fx):
    if "ings" in fx:
        r["ingredients"] = []
        for line in fx["ings"]:
            amt, item = line.split("|", 1); r["ingredients"].append({"amount": amt, "item": item})
    for line in fx.get("add", []):
        amt, item = line.split("|", 1); r["ingredients"].append({"amount": amt, "item": item})
    for i, text in (fx.get("step") or {}).items(): r["steps"][i] = text
    if fx.get("drop"): r["steps"] = [s for n, s in enumerate(r["steps"]) if n not in fx["drop"]]
    r["steps"] = [re.sub(r"\s*\(No\. \d+\)", "", s) for s in r["steps"]]
    for k in ("category", "title", "servings"):
        if k in fx: r[k] = fx[k]
    if "servings" in fx: r["servings_stated"] = True
    r["ingredients"] = [repair(i) if re.search(r"\d", i["amount"]) else i for i in r["ingredients"]]
    r["steps"] = [m.tidy_step(s) for s in r["steps"]]
    r.pop("held_because", None); r["rescued"] = True


def main():
    f = Path(sys.argv[1]); held_path = Path(sys.argv[sys.argv.index("--held") + 1])
    data = json.load(open(f, encoding="utf-8")); held = json.load(open(held_path, encoding="utf-8"))
    back, still = [], []
    for r in held:
        fx = FIXES.get(r["title"])
        if fx is None:
            for key, val in FIXES.items():                    # "Title|start of first step" for titles that occur twice
                if "|" in key and key.split("|")[0] == r["title"] and r["steps"] and r["steps"][0].startswith(key.split("|")[1]): fx = val; break
        if fx is None or (r["title"] in ("Chocolate Caramels", "Cheese Cakes") and not any(k.startswith(r["title"] + "|") and r["steps"][0].startswith(k.split("|")[1]) for k in FIXES)):
            still.append(r); continue
        apply_fix(r, fx); r["modernised"] = True
        if len(r["ingredients"]) >= 2 and len(r["steps"]) >= 1 and sum(len(s) for s in r["steps"]) >= 25 and coverage(r["ingredients"]) >= 0.7:
            back.append(r)
        else:
            r["held_because"] = "still too thin after the fix"; still.append(r)
    json.dump(data + back, open(f, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(still, open(held_path, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"brought back {len(back)}; still held {len(still)}; ready file now {len(data) + len(back)}")


if __name__ == "__main__":
    main()
