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
