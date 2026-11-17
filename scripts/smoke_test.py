#!/usr/bin/env python3
"""
CookMe smoke test: checks the main user journeys against a running backend.

Usage:
  export COOKME_API=https://your-backend.example.com      # no trailing slash
  export COOKME_TOKEN=<JWT>     # from scripts/make_test_token.py, or copy it from a real login
  python scripts/smoke_test.py [--import-url URL] [--photo path/to/food.jpg]

Use a TEST account: the test adds and deletes a pantry item and a recipe, and adds a
shopping-list item. AI steps (import fallback, photo, pantry suggestions, meal plan) need a
working LLM key on the backend and will cost a few cents.
"""
import argparse, base64, json, os, sys, time
from datetime import date, timedelta
try:
    import requests
except ImportError:
    sys.exit("pip install requests")

ap = argparse.ArgumentParser()
ap.add_argument("--api", default=os.environ.get("COOKME_API", ""))
ap.add_argument("--token", default=os.environ.get("COOKME_TOKEN", ""))
ap.add_argument("--import-url", default="https://www.inspiredtaste.net/15938/easy-and-perfect-pizza-dough-recipe/",
                help="a recipe page you know has schema.org recipe data")
ap.add_argument("--photo", default="", help="optional image file for the photo-analysis step")
a = ap.parse_args()
if not a.api or not a.token:
    sys.exit("Set COOKME_API and COOKME_TOKEN (or pass --api/--token).")

API = a.api.rstrip("/") + "/api"
H = {"Authorization": f"Bearer {a.token}", "Content-Type": "application/json"}
results = []

def step(name, fn):
    t = time.time()
    try:
        ok, detail = fn()
    except Exception as e:  # network errors, bad JSON, etc.
        ok, detail = False, f"{type(e).__name__}: {e}"
    results.append((name, ok, detail))
    print(f"{'PASS' if ok is True else 'SKIP' if ok is None else 'FAIL'}  {name}  ({time.time()-t:.1f}s)  {detail}")

def call(method, path, **kw):
    return requests.request(method, API + path, headers=H, timeout=kw.pop("timeout", 90), **kw)

state = {}

def health():
    r = requests.get(API + "/", timeout=30)
    return r.status_code == 200, f"HTTP {r.status_code} (a 502/503 on first call can be a sleeping free host: retry)"

def auth():
    r = call("GET", "/auth/me")
    if r.status_code == 200:
        return True, f"logged in as {r.json().get('email')}"
    return False, f"HTTP {r.status_code}: {r.text[:120]} (401 = bad/expired token or different JWT_SECRET; 404 = token is valid but that user is not in this database)"

def import_url():
    r = call("POST", "/recipes/extract", json={"recipe_url": a.import_url}, timeout=120)
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}: {r.text[:160]}"
    d = r.json()
    n_ing, n_steps = len(d.get("ingredients") or []), len(d.get("steps") or []) or (1 if d.get("instructions") else 0)
    return bool(d.get("title") and n_ing and n_steps), f"title={d.get('title')!r} ingredients={n_ing} steps={n_steps}"

def library():
    body = {"title": "Smoke Test Soup", "description": "smoke test", "prep_time": "5 min", "cook_time": "10 min",
            "servings": 2, "difficulty": "Easy", "ingredients": [{"item": "water", "amount": "1 cup"}],
            "steps": ["Boil water."], "tags": ["smoke-test"]}
    r = call("POST", "/recipes", json=body)
    if r.status_code != 200:
        return False, f"create HTTP {r.status_code}: {r.text[:160]}"
    rid = r.json().get("recipe_id") or r.json().get("id")
    state["recipe_id"] = rid
    lst = call("GET", "/recipes")
    found = lst.status_code == 200 and any((x.get("recipe_id") or x.get("id")) == rid for x in lst.json())
    d = call("DELETE", f"/recipes/{rid}")
    return found and d.status_code in (200, 204), f"created={rid} listed={found} delete=HTTP {d.status_code}"

def photo():
    if not a.photo:
        return None, "skipped (pass --photo food.jpg)"
    b64 = base64.b64encode(open(a.photo, "rb").read()).decode()
    data = f"data:image/jpeg;base64,{b64}"
    v = call("POST", "/recipes/validate-image", json={"image_data": data})
    r = call("POST", "/recipes/analyze-photo", json={"image_data": data}, timeout=120)
    return v.status_code == 200 and r.status_code == 200, f"validate=HTTP {v.status_code} {v.text[:60]!r}; analyze=HTTP {r.status_code}"

def pantry():
    r = call("POST", "/pantry", json={"name": "smoke tomato", "category": "Produce"})
    if r.status_code != 200:
        return False, f"add HTTP {r.status_code}: {r.text[:140]}"
    item = r.json(); iid = item.get("item_id") or item.get("id")
    s = call("POST", "/pantry/suggest-meal", json={"match_type": "any", "extra_ingredients": 5}, timeout=120)
    if iid: call("DELETE", f"/pantry/{iid}")
    n_ai = len(s.json().get("ai_suggestions") or []) if s.status_code == 200 else 0
    # The endpoint returns 200 even when the AI call fails, so require actual AI ideas.
    return s.status_code == 200 and n_ai > 0, f"added={iid} suggest-meal=HTTP {s.status_code} ai_suggestions={n_ai} (0 means the LLM key/model is not working)"

def shopping():
    r = call("POST", "/shopping-list/add-items", json={"items": ["smoke milk"]})
    g = call("GET", "/shopping-list")
    return r.status_code == 200 and g.status_code == 200 and "smoke milk" in g.text.lower(), f"add=HTTP {r.status_code} get=HTTP {g.status_code}"

def meal_plan():
    monday = date.today() - timedelta(days=date.today().weekday())
    r = call("POST", "/meal-plans/generate", json={"week_start": monday.isoformat()}, timeout=180)
    return r.status_code == 200, f"HTTP {r.status_code}: {r.text[:120]}"

for name, fn in [("API reachable", health), ("Login token accepted", auth), ("Import recipe from URL", import_url),
                 ("Recipe library (create/list/delete)", library), ("Photo validate + analyze", photo),
                 ("Pantry + AI suggestions", pantry), ("Shopping list", shopping), ("AI meal plan", meal_plan)]:
    step(name, fn)

failed = [r for r in results if r[1] is False]
print(f"\n{len(results)-len(failed)} ok/skipped, {len(failed)} failed")
sys.exit(1 if failed else 0)
