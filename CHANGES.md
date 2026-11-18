# Changes in this version

Applied on top of CookMe-feature-updates (March 2026 snapshot).

## From the copilot branch
- backend/server.py: fails fast if MONGO_URL/DB_NAME missing; CORS restricted via CORS_ORIGINS (defaults to * if unset).
- backend/routes/community_routes.py: seasonal featured recipes.
- frontend/src/components/ui/sonner.jsx: no longer imports next-themes.

## Bug fixes (backend/routes/recipe_routes.py)
- Added missing `import re` / `import json` / logger. Before this, the free JSON-LD extractor, extract, extract-social,
  extract-youtube, analyze-photo and translate-ingredient raised NameError, and the image validator's fail-open handler crashed.

## Dead code removed
- Backend: unused imports and variables; functions unit_conv_key, parse_wprm_style, parse_bbc_good_food, parse_cookpad,
  get_image_stats, get_synonyms, ingredients_match; class JobStatus; unused models (User, Token, UserSession, Collection,
  MealPlan, ShoppingList, PantryItem). `Recipe.Config` is kept (it is needed).
- Frontend: src/mockData.js, ui/checkbox.jsx, ui/label.jsx; 34 unused npm packages; added ajv ^8 (needed by the build).

## Added
- scripts/smoke_test.py and scripts/make_test_token.py (see the header of each).

## Deliberately NOT changed
- Emergent LLM package and Emergent Google login (still required for AI features and login).
- plugins/visual-edits and plugins/health-check (craco.config.js loads them in dev), legacy /import-facebook-recipe (tests use it),
  /import-async + registry/cache (cost savings, not yet wired to the frontend), .emergent/, memory/PRD.md (contains test credentials).

## Master recipes + cooking types
- `data/master_recipes.json`: 1,184 shared recipes, no user data (no owners, uploaders, favourites, gallery, likes).
- `scripts/load_master_recipes.py`: loads them (dry run, then `--apply`). Re-runnable.
- `scripts/check_images.py [--fix]`: checks every image link is alive (needs internet).
- `scripts/build_master_recipes.py`: how the file was built from the export (not needed to run the app).
- New endpoint `GET /api/recipes/type/{quick|student|budget|instapot|airfryer}`; Quick, Student, Budget and One-pot pages now use it.
- Master file also keeps the user-imported recipes (ownership and all user fields removed); embedded photos are kept.

## Fixes round 2
- Featured Today now uses real master recipes (new `GET /api/recipes/featured`, stable per day) and opens the recipe; removed the made-up sample list.
- Dashboard: removed duplicate logo and "New Recipe" button; category cards link to the real pages (no fake counts); added Air Fryer page.
- Fixed type pages and dashboard reading the wrong shape from `/api/recipes` (it returns a list).
- Pantry: "Scan ingredients" button (same camera flow as the mobile bar).
- Login shows Google only by default; set `REACT_APP_LOGIN_PROVIDERS=google,facebook,apple,twitter,instagram` to bring the others back.
- Removed tests that called login routes that don't exist; added offline `tests/test_master_recipes.py`.
- Clean `.gitignore` (blocks .env and export files).
- Remaining build warnings are harmless "missing dependency" hints in effects.

## Fewer AI calls
- Pantry "suggest a meal" now matches against the shared master recipes first (word-level match, salt/oil/water treated as on hand); AI only runs if fewer than 3 matches in total.
- Aisle lookup table expanded to ~400 names (whole-word matching) - covers ~93% of master-recipe ingredients without AI.
- AI image generation is off unless `ENABLE_AI_IMAGES=1`; scanned recipe cards no longer trigger it.
- Dashboard empty state.

## Search, units, cooking mode
- New Search page (`/search`, "Search" in the top bar): name, ingredients you want (all must match), vegetarian/vegan, cuisine, under 30 min. Backed by `GET /api/recipes/search`.
- Master file now has vegetarian/vegan tags (worked out from ingredients) and cuisine for about half the recipes. Gluten-free and dairy-free are deliberately NOT tagged (unsafe to guess).
- Recipe page: Original / Metric / US unit toggle (local conversion, no AI), remembered per device.
- Recipe page: "Start cooking" opens full-screen cooking mode: big text, step by step, timers detected from the step text, screen kept awake.
- After pulling, re-run `python scripts/load_master_recipes.py --apply` to add the new tags.

## Nutrition (USDA), dictionary, automatic tagging, photo language
- **USDA nutrition (free, offline):** run `python scripts/build_usda_table.py` ONCE (needs internet) to create `data/nutrition_usda.json`. Nutrition then uses it first, then Open Food Facts/Edamam, then AI. Until the file exists the app behaves as before. Also fixed OFF sodium (grams -> mg).
- **Our own ingredient dictionary** (161 ingredients x English/Spanish/French/German/Italian/Portuguese) - `data/ingredient_dictionary.json`, edit and regenerate with `scripts/build_ingredient_dictionary.py`. `translate-ingredient`, nutrition and pantry matching use it before AI. Please have a native speaker check the entries.
- **Automatic tagging** (`backend/recipe_tagger.py`): every saved recipe gets cooking-type, vegetarian/vegan tags and a cuisine, free. Backfill existing recipes with `python scripts/retag_recipes.py --apply`.
- **Photo scan language:** the app language is sent with the photo so a recipe card in another language comes back translated into the user's language.

## Meal plans from recipes
- "Generate" in the Meal Planner now builds the week from tagged recipes (master list + the user's own): breakfast / lunch / dinner picked by tags and title, no repeats, vegetarian/vegan honoured, cuisine and pantry preferred, quick meals on weekdays. Free, instant.
- Only requests we can't honour from tags (e.g. gluten-free, nut-free) or too few recipes still use AI.

## Images, credits and meal-plan quality
- Fallback: recipes with no/broken image now show a neutral "Photo coming soon" tile instead of one repeated stock photo (the stock photo is no longer saved into recipes).
- Every recipe page has a Source block ("Recipe from X" + link, CC BY 3.0 note for Foodista, photo credit). Profile > Settings has a Credits card (TheMealDB, Foodista, spoonacular, USDA, Open Food Facts).
- `scripts/check_images.py` now flags missing, dead, tiny, stock and repeated images (`--fix` blanks them).
- `scripts/fill_images.py` fills blanks from Pexels (free key) and optionally AI (`--ai`, on Emergent). Run both on a machine with internet, then commit `frontend/public/recipe-images/` + the JSON.
- Meal plans: dinners need 6+ ingredients (or a main-course tag); sides, dips and snacks (e.g. Padron peppers) are excluded.

## Email login (Auth0)
- Login page gets a "Continue with email" button when these are set (otherwise it stays hidden and nothing changes):
  - Frontend env: `REACT_APP_AUTH0_DOMAIN`, `REACT_APP_AUTH0_CLIENT_ID`
  - Backend env: `AUTH0_DOMAIN`, `AUTH0_CLIENT_ID`
- Flow: Auth0's own page handles sign-up/password/reset. CookMe receives a signed ID token, `POST /api/auth/auth0/callback` checks signature, issuer, audience and expiry, then logs the person in like Google does. No passwords stored by CookMe.
- Unverified emails are refused, so nobody can take over an existing account by signing up with someone else's address.
- New dependency: `@auth0/auth0-react` (run `yarn install` after pulling). Tests: `tests/test_auth0.py`.

## Recipe data cleanup
- `backend/recipe_cleaner.py` + `scripts/clean_recipes.py`: drops label steps ("step 1", "2", "▢"), strips step numbers, splits one-paragraph methods into readable steps, fixes amounts ("1.0 cup" -> "1 cup", "White"+"Rice" -> "White Rice").
- Applied to `data/master_recipes.json`: 990 recipes tidied, 23 too thin to cook from moved to `data/master_recipes_rejected.json` (1,180 kept).
- `scripts/load_master_recipes.py --apply --prune` also removes master recipes that are no longer in the file (never touches user recipes).

## Checkup fixes
- Pantry suggestions now rank by how many of your pantry items a recipe uses (and need 2+ when you have 2+), with synonyms ("pasta" covers spaghetti/penne, "cheese" covers cheddar/feta, etc.). Before, a 1-item omelette could outrank chicken-and-rice dishes.
- Meal plans: fixed doubled-backslash typos that stopped the "not a meal" filter matching chips/nuts/ideas; desserts such as "Rocky Road Dessert Bars" and caramels no longer count as dinner.
- Recipe photos: removed 6 unused files, recompressed the largest (max 182 KB).
- New tests: `tests/test_regressions.py`.

## Recipe counter
- `GET /api/recipes/stats` returns `{total, mine}`. The dashboard shows "1,171 recipes to explore · N of your own" under the welcome line; the search page shows the number of matches.
- Featured recipes can now pick recipes with the new local photos (before, only `http` image links were eligible).

## Featured once a day + slow, steady recipe growth
- Featured recipes: random but fixed for the whole day (changes at midnight UTC). Picks from the shared recipes plus your own; never other people's private recipes.
- **Bug fixed:** the recipe model dropped `image_attribution`, so photographer credits never reached the recipe page. Added `image_attribution`, `image_source`, `source_license`, `source_history_url`.
- **Staging pipeline** (nothing reaches the app until approved):
  1. `python3 scripts/stage_wikibooks.py --limit 60` (test), then without `--limit` for everything. Writes `data/staging/wikibooks.json` + `wikibooks_review.csv`.
  2. Open the CSV, set keep to y/n, save.
  3. `python3 scripts/approve_staged.py` -> `wikibooks_approved.json`
  4. `python3 scripts/fill_images.py --file data/staging/wikibooks_approved.json` (Pexels, ~190 per hour)
  5. Commit + push; in Emergent pull, then `python scripts/queue_recipes.py data/staging/wikibooks_approved.json --apply`
- **Daily release:** `backend/release_queue.py` runs inside the backend; the first check each day moves the next `RELEASE_PER_DAY` (default 10) recipes from the `recipe_queue` collection into the app. A server outage never causes a flood. `RELEASE_PER_DAY=0` pauses it.
- `load_master_recipes.py --prune` never removes recipes released from the queue.
- Wikibooks recipes show "Recipe from Wikibooks Cookbook · licensed CC BY-SA 4.0 · Authors"; credits card updated.

## Public recipe sharing + privacy fixes
- Owners can "Share publicly" from their recipe page. They must tick a consent box (free, non-exclusive licence to show it in CookMe); consent is stored in `recipe_consents` with a hash of the exact wording.
- Recipes go through automated checks (title, description, 3+ ingredients, 2+ steps, time, own photo, no links/contact details, no blocked words, no duplicate titles). Failures return to the owner as "needs changes" with a list; they fix it in the new Edit page (`/recipe/:id/edit`) and resubmit.
- Imported-from-web recipes cannot be made public. Editing a public recipe re-runs the checks; failing ones go back to private.
- Owners can make a recipe private again at any time. Public recipes show "shared by" (or "CookMe community").
- Privacy fixes: `GET /recipes/{id}`, `/category/{category}` and `/master/all` used to expose other users' private recipes; now only owner / master / public. Owner ids and favourites are masked on others' recipes.
- Pantry search, meal planner, featured and counters include public recipes.
- NOT legal advice: have a lawyer review the consent text, and add Terms/Privacy pages and a report/takedown button.

## Legal pages, community comments and safety
- New `/terms` and `/privacy` pages (public, linked from the login screen and Profile → Settings). Set `REACT_APP_OPERATOR_NAME`, `REACT_APP_CONTACT_EMAIL` and optionally `REACT_APP_GOVERNING_LAW` in the frontend env to fill in who runs CookMe and how to reach them.
- `backend/content_filter.py`: blocks phone numbers (incl. spaced / spelled-out), email addresses (incl. "name at gmail dot com"), web links, social handles ("@name", WhatsApp, "DM me") and profanity (English, Spanish, Hindi/Urdu; catches f.u.c.k, sh1t, f*ck). Used for comments, replies and public recipe checks.
- Comments + replies (one level) on public and master recipes (`/api/social/...`); posting rate-limited, duplicates blocked, authors shown as "First L.". Recipe owner or comment author can delete.
- Report buttons: 3 distinct reports hide a comment; 3 reports on a public recipe make it private ("under_review", can't be re-published until reviewed).
- "Shared by members" strip on the Social page (`/api/social/feed`).
- Account: `GET /api/auth/me/export` (download my data) and `DELETE /api/auth/me` (erase account + content), buttons in Profile → Settings.
- NOT legal advice: have a lawyer review both pages before launch.

## Admin account, reporting and account review
- **Admin**: set `ADMIN_EMAILS` (comma list) in the backend env. Those emails (signed in via Google or Auth0, which verify email) get an "Admin: review reported content" link in Profile → Settings and the `/admin` page. Nobody else can open it.
- **Report buttons** on every public/master recipe and comment: report the item, or report the person who wrote/shared it.
  - Report a *user* → their account is locked at once. They see "Your profile is under review" instead of the app; their public recipes and comments are hidden meanwhile.
  - Report a *recipe* → it is taken down (private, "under review") at once.
  - Report a *comment* → hidden after 3 reports; always shows in the admin queue.
- **Admin queue** (`/admin`): the reported profile (name, email, recipes, recent comments), the full recipe (photo, ingredients, method) or the comment, every reporter's reason/details. Buttons: Reinstate/Keep it (restores everything), Delete (recipe/comment), Delete & block account (erases the person's content and blocks that email from logging in again).
- **Email alert**: optional. Set `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` (+ `SMTP_FROM`, `SMTP_PORT`, `APP_URL`) and each report is emailed to `ADMIN_EMAILS`. Without SMTP the alert is only in the queue and the server log.
- **Abuse guards**: max 5 reports per user per day, one open report per target, admins can't be reported/locked, and a reporter whose reports are dismissed 3 times can no longer report.

## Share to Social
- The owner button on a recipe is now **Share to Social** (was "Share publicly"): optional note (max 200 chars, run through the contact-info/profanity filter), consent, our checks, then the recipe appears in **Shared by members** on the Social page with the note. **Remove from Social** takes it back down.

## First start on an empty database
- `backend/seed_master.py`: when the backend starts and there are **no** master recipes, it loads `data/master_recipes.json` in the background (so the live site's empty database gets the library automatically). Never re-adds recipes you deleted, never touches user data. `AUTO_SEED_MASTER=0` switches it off. Updates later still go through `scripts/load_master_recipes.py`.

## Removed the unit converter
- Removed the "Unit Converter" box (and its voice button) from the bottom of the recipe page: ingredient amounts already scale and convert with the servings and unit settings. (It also called an AI service directly from the browser with no key, so it never worked.)

## Bottom navigation always at the bottom
- The phone bottom bar is now pinned to the very bottom edge (it used to float 68px up, left over from the ad banner), full width, with room for the iPhone home bar / notch (`viewport-fit=cover` + safe-area inset). Buttons share the width evenly, so it fits from 320px phones up; it hides while you type so the keyboard never covers it. Tablets and laptops (768px+) use the top menu as before.
- Shopping "All done" banner sits above the bar (`--bottom-nav-h` CSS variable).

## Cooking mode: timers, protein plans, air fryer
- **Timers**: any number of timers run at once (they keep running as you move between steps, use real time so they stay right if the phone sleeps, beep + vibrate, +1 min, pause). Times found in a step ("10–12 minutes", "five minutes", "4 minutes per side") become one-tap buttons; "per side" asks you to flip and starts side 2. There is also always a "your own timer" row (1/5/10/15 min), so there is a timer even when a step has no time written in it.
- **Cooking setup** (on the Instructions tab, and as the "Before you start" screen when you tap Start cooking): *What are you cooking?* (beef steak, lamb, pork chops, chicken breast/thighs/whole, salmon, white fish, burgers, sausages, roast joints; pre-selected from the recipe) → *How big?* (thickness or weight) → *How do you like it?* (rare to well done, with core temperatures) → *How are you cooking it?* (pan, oven, grill/BBQ, air fryer). It works out the heat, timings (per side / total / halfway turn), rest time and target core temperature, shows a safety note for rarer-than-guidance choices, and the plan's timers replace the recipe's times on the steps that cook the protein. Choices are remembered.
- **Air fryer method**: pick Air fryer for any suitable recipe (oven/frying steps; not soups, stews, pasta...). Oven steps become air-fryer temperature and time (about −20°C, ×0.75), frying becomes 190°C with a little oil, preheat step becomes "preheat the air fryer 3 min", shake/turn-halfway reminders. Adjust for air fryer size (small / basket / large or oven-style), crispness (softer / standard / extra crispy) and fine-tune ±5°C and ±10% time. Boiling, simmering and sauce steps stay as written.
- All times are rules of thumb; the app says to use a meat thermometer. Logic lives in `utils/cookingTools.js` (11 unit tests).

## Phone menu: three-line dropdown with the same options as the website
- The top bar now shows on phones and tablets, with a three-line button on the top right.
- It opens a full-height menu with the same links as the website: Home, Recipes, Search, Planner, Shopping, Pantry, Social, Categories, Add Recipe, Profile, Admin (admins only), Terms, Privacy, Logout.
- Closes on navigation, Escape or the X button. The bottom bar stays on phones.

## Speed pass
- Database indexes for comments, reports, consents and the public-recipe feed (created automatically at startup).
- API responses are gzip-compressed.
- Pages load on demand (main JavaScript 916 KB -> 521 KB; about 157 KB over the wire).
- `/api/recipes/featured` no longer loads every recipe id; the database picks and the pick is remembered for the day.
- Social feed comment counts use one query instead of one per recipe.
- Recipe photos lazy-load (hero images still load immediately).
- Comments and admin report lists are capped at 300 per request.
- New `scripts/mirror_images.py` downloads hotlinked master-recipe images, shrinks them and rewrites `data/master_recipes.json` (run on your own computer).

## Safety net: backups and error reports
- Admin page: **Download backup** (one file with all user data; master recipes, caches and login sessions are left out) and **Show recent app errors**.
- `scripts/restore_backup.py` puts a backup file back (`--dry-run` only counts).
- Browser crashes are reported to `/api/monitoring/client-error` (rate-limited, kept 30 days).
- Optional backend crash alerts: set `SENTRY_DSN` and install `sentry-sdk`.
- `docs/legal-review-brief.md`: what to give a lawyer for the Terms/Privacy review.
