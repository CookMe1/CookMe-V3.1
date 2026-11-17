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
