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
