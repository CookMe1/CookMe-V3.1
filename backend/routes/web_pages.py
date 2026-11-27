"""Public web pages for recipes, so Google and link previews (WhatsApp, Instagram, X) can see them.
Only recipes that are safe to show on the open web: ones a person chose to make public, ones with an open licence
(Wikibooks, CC BY-SA), and reviewed AI-written ones. The older library recipes copied from other websites are NOT included."""
import html
import json
import os
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

router = APIRouter(prefix="/web")

OPEN_WEB = {"$or": [
    {"visibility": "public"},
    {"source_license": {"$exists": True, "$nin": [None, ""]}},
    {"user_id": "system_seeder", "ai_generated": True},
]}
QUERY = {"$and": [OPEN_WEB, {"title": {"$nin": [None, ""]}}]}


def site_url(request: Request) -> str:
    return (os.getenv("APP_URL") or f"{request.url.scheme}://{request.url.netloc}").rstrip("/")


def _abs(url, base):
    if not url:
        return ""
    return url if str(url).startswith("http") else base + (url if str(url).startswith("/") else "/" + str(url))


def _iso(t):
    """'15 min' / '1 hr 30 min' -> ISO 8601 duration for Google; '' if it cannot be read."""
    import re
    s = str(t or "").lower()
    h = re.search(r"(\d+)\s*(?:h|hr|hour)", s)
    m = re.search(r"(\d+)\s*(?:m|min)", s)
    if not (h or m):
        return ""
    return "PT" + (f"{int(h.group(1))}H" if h else "") + (f"{int(m.group(1))}M" if m else "")


def _steps(r):
    out = []
    for s in r.get("steps") or []:
        out.append(str(s.get("text") or s.get("instruction") or "") if isinstance(s, dict) else str(s))
    return [s for s in out if s.strip()]


def _ings(r):
    out = []
    for i in r.get("ingredients") or []:
        if isinstance(i, dict):
            out.append(" ".join(x for x in (str(i.get("amount") or "").strip(), str(i.get("item") or "").strip()) if x))
        else:
            out.append(str(i))
    return [i for i in out if i.strip()]


def render_recipe(r: dict, base: str) -> str:
    e = html.escape
    title = r.get("title", "Recipe")
    desc = (r.get("description") or f"{title} on Grubly.")[:300]
    img = _abs(r.get("image"), base)
    ings, steps = _ings(r), _steps(r)
    url = f"{base}/api/web/recipe/{r['recipe_id']}"
    n = r.get("nutrition") or {}
    ld = {"@context": "https://schema.org", "@type": "Recipe", "name": title, "description": desc,
          "recipeIngredient": ings, "url": url,
          "recipeInstructions": [{"@type": "HowToStep", "text": s} for s in steps]}
    if img:
        ld["image"] = [img]
    if _iso(r.get("prep_time")):
        ld["prepTime"] = _iso(r.get("prep_time"))
    if _iso(r.get("cook_time")):
        ld["cookTime"] = _iso(r.get("cook_time"))
    if r.get("servings"):
        ld["recipeYield"] = str(r["servings"])
    if n.get("calories"):
        ld["nutrition"] = {"@type": "NutritionInformation", "calories": f"{n['calories']} calories"}
    if r.get("public_author") or r.get("uploader_name"):
        ld["author"] = {"@type": "Person", "name": r.get("public_author") or r.get("uploader_name")}
    ld_json = json.dumps(ld).replace("</", "<\\/")

    credit = ""
    if r.get("source_license"):
        src = r.get("source_url") or ""
        by = f' by {e(r["source_author"])}' if r.get("source_author") else ""
        credit = (f'<p class="credit">Recipe{by} from <a href="{e(src)}" rel="nofollow noopener">{e(src)}</a>, '
                  f'licensed {e(str(r["source_license"]))}. Changes may have been made.</p>')
    elif r.get("public_author"):
        credit = f'<p class="credit">Shared by {e(r["public_author"])} on Grubly.</p>'
    if img and r.get("image_attribution"):
        credit += f'<p class="credit">{e(r["image_attribution"])}</p>'

    facts = " · ".join(x for x in (
        f"Prep {e(str(r['prep_time']))}" if r.get("prep_time") else "",
        f"Cook {e(str(r['cook_time']))}" if r.get("cook_time") else "",
        f"Serves {e(str(r['servings']))}" if r.get("servings") else "",
        f"{e(str(n['calories']))} kcal per serving" if n.get("calories") else "") if x)

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} | Grubly</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(url)}">
<meta property="og:type" content="article"><meta property="og:site_name" content="Grubly">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url)}">{f'<meta property="og:image" content="{e(img)}">' if img else ''}
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{ld_json}</script>
<style>body{{font-family:system-ui,sans-serif;background:#18181b;color:#e4e4e7;margin:0;line-height:1.55}}
main{{max-width:720px;margin:0 auto;padding:20px}}img{{max-width:100%;border-radius:12px}}h1{{margin:.4em 0 .2em}}
.facts{{color:#a1a1aa}}.cta{{display:inline-block;background:#f97316;color:#fff;padding:12px 20px;border-radius:10px;text-decoration:none;font-weight:600;margin:16px 0}}
a{{color:#fb923c}}.credit{{font-size:.8rem;color:#a1a1aa}}li{{margin:.35em 0}}</style></head><body><main>
<p><a href="{e(base)}/">Grubly</a></p><h1>{e(title)}</h1>{f'<img src="{e(img)}" alt="{e(title)}">' if img else ''}
<p class="facts">{facts}</p><p>{e(desc)}</p>
<a class="cta" href="{e(base)}/">Save to Grubly</a>
<h2>Ingredients</h2><ul>{''.join(f'<li>{e(i)}</li>' for i in ings)}</ul>
<h2>Method</h2><ol>{''.join(f'<li>{e(s)}</li>' for s in steps)}</ol>{credit}
<p class="credit">Grubly: import recipes from any link, see the nutrition, cook from your pantry.</p></main></body></html>"""


@router.get("/recipe/{recipe_id}", response_class=HTMLResponse)
async def public_recipe(recipe_id: str, request: Request):
    db = request.app.state.db
    r = await db.recipes.find_one({"$and": [QUERY, {"recipe_id": recipe_id}]}, {"_id": 0})
    if not r or not _ings(r) or not _steps(r):
        raise HTTPException(status_code=404, detail="Recipe not found")
    return HTMLResponse(render_recipe(r, site_url(request)), headers={"Cache-Control": "public, max-age=3600"})


@router.get("/sitemap.xml")
async def sitemap(request: Request):
    db = request.app.state.db
    base = site_url(request)
    rows = await db.recipes.find(QUERY, {"_id": 0, "recipe_id": 1, "updated_at": 1}).limit(5000).to_list(5000)
    urls = [f"<url><loc>{html.escape(base)}/</loc></url>"]
    for r in rows:
        lm = str(r.get("updated_at") or "")[:10]
        urls.append(f"<url><loc>{html.escape(base)}/api/web/recipe/{html.escape(r['recipe_id'])}</loc>"
                    + (f"<lastmod>{html.escape(lm)}</lastmod>" if len(lm) == 10 else "") + "</url>")
    xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(urls) + "</urlset>"
    return Response(xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=3600"})
