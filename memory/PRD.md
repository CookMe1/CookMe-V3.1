# CookMe - Recipe Management App

## Original Problem Statement
Build a "Stashcook" clone named "CookMe" - an application for recipe management with features like AI-powered suggestions, importing recipes from URLs/YouTube/photos, and social sharing.

## Core Requirements
- Recipe management with AI-powered suggestions
- Import recipes from URLs, YouTube videos, and photos
- 1-Click Share: Share recipes from other apps directly into CookMe using native share functionality
- Saved recipes stored permanently in database
- Photo Cropping, New Photo Upload Sequence, Image Gallery
- Categories ("Airfryer", "International") and Uploader Tagging
- Social page for sharing recipes and favoriting
- Professional dark theme with bottom navigation bar
- Robust login system with email verification

## Tech Stack
- **Frontend**: React, TailwindCSS, Shadcn UI
- **Backend**: FastAPI (Python)
- **Database**: MongoDB (cookme_db)
- **Authentication**: JWT with email verification
- **PWA**: Installable Progressive Web App

## What's Been Implemented

### Authentication
- ✅ JWT-based authentication
- ✅ Google OAuth integration (Emergent-managed)
- ✅ **Simplified Registration** (Jan 2025) - No email verification required, users auto-verified on signup
- ✅ **CORS Fix for Apple Devices** (Jan 2025) - Fixed preflight request handling by moving CORS middleware before routes

### Recipe Management
- ✅ Create, Read, Update, Delete recipes
- ✅ Recipe categories and cuisines filtering
- ✅ Recipe gallery with multiple images
- ✅ Favorites/Likes system
- ✅ Recipe saving/bookmarking
- ✅ **"My Recipes" user isolation** (Jan 2025) - Users only see their own recipes, Master List shows all
- ✅ **Ultra-fast database loading** - MongoDB indexes on user_id, created_at, favorited_by, recipe_id

### Import Features
- ✅ URL extraction (websites, blogs)
- ✅ YouTube video extraction
- ✅ Photo analysis with AI (recipes & ingredients)
- ✅ Text paste parsing
- ✅ PWA Share Target API

### Node-based Recipe Import Pipeline (Jan 2025 - COMPLETE)
**Server-side HTTP crawler pipeline - behaves exactly like Stashcook.**

**Architecture (NON-BROWSER):**
- Pure server-side HTTP fetching via httpx
- Crawler User-Agents: `facebookexternalhit/1.1`, `Twitterbot/1.0`
- NO cookies, NO auth, NO JavaScript execution
- Stop immediately on `/login` redirects
- Extract OpenGraph metadata + visible text content

**Supported Input:**
- `https://www.facebook.com/share/p/...` (posts)
- `https://www.facebook.com/share/r/...` (reels/videos)
- `https://www.facebook.com/groups/.../posts/...`
- `https://fb.watch/...`
- Any Facebook URL variant
- External recipe URLs (50+ recipe domains)
- Direct text paste

**Pipeline Flow:**
1. **Normalize URL** - Force HTTPS, standardize format
2. **Fetch as Crawler** - HTTP GET with crawler UA, no cookies
3. **Check for Login Block** - Stop on `/login` redirects
4. **Extract OpenGraph** - og:title, og:description, og:image
5. **Find External URLs** - Detect recipe links in content
6. **Parse Content** - JSON-LD schema.org or AI extraction
7. **Return Structured Data** - title, ingredients, steps, image

**Output Format:**
```json
{
  "title": "Recipe Name",
  "description": "Brief description",
  "image": "URL",
  "ingredients": ["ingredient 1", "ingredient 2"],
  "instructions": "Step-by-step text",
  "source": "facebook"
}
```

**Features:**
- Extracts OG metadata even from blocked pages
- "Paste Recipe Text" fallback for login-blocked content
- AI parsing with GPT-4o-mini for text content
- Schema.org JSON-LD extraction for recipe sites
- Confidence scoring (high/medium/user-assisted)
- Graceful failure with helpful messages

**Test Results (Jan 17, 2025):**
| URL Type | Result |
|----------|--------|
| Public video `/share/r/` | ✅ 17 ingredients, 8 steps, 90% confidence |
| Group post `/share/p/` | ✅ OG metadata + paste option |
| Direct text paste | ✅ 7 ingredients, 7 steps |
| External recipe URL | ✅ 15 ingredients via JSON-LD |

### Camera/Photo Features (Jan 2025)
- ✅ Camera/Gallery selection modal
- ✅ "Take Photo with Camera" or "Upload from Gallery" options
- ✅ Photo cropping workflow
- ✅ AI image generation for recipes without photos
- ✅ Ingredient detection → Pantry prompt (3+ ingredients)
- ✅ **Image Quality Validation** (Jan 2025) - All image uploads validated before AI analysis
  - Conservative rejection: Blurry, dark, unreadable images rejected
  - AI-powered assessment using GPT-5.2 vision model
  - User-friendly error messages: "Image is too blurry", "Lighting is too dark", etc.
  - Automatic compression to under 1MB
  - Applied to: Photo tab, Camera button, ShareHandler, Gallery uploads

### Pantry & Shopping
- ✅ Pantry management
- ✅ Shopping list functionality
- ✅ Add detected ingredients to pantry from photos
- ✅ "Suggest a Meal" feature - AI-powered recipe suggestions based on pantry items
  - Match type options: All ingredients, Most ingredients (70%+), Any match
  - Extra ingredients slider (0-10 additional items willing to buy)
  - Shows saved recipe matches + AI-generated recipe ideas
  - Displays matched ingredients (✓ You have) and missing ingredients (+ Need to buy)
  - Save AI suggestions directly to recipe collection
  - "Add all" to Shopping List - One-click add missing ingredients
- ✅ **User-Specific Data Isolation** (Jan 2025) - Each user has their own pantry and shopping list
  - Backend filters by user_id from JWT token
  - Shopping list: GET/PUT/DELETE `/api/shopping-list`, POST `/api/shopping-list/add-items`
  - Pantry: GET/POST/PUT/DELETE `/api/pantry`
  - Cross-user access returns 404 (items not found)
- ✅ **Batch Processing for Cost Savings** (Jan 2025) - Shopping list uses 1.5s debounce
  - Multiple rapid changes batched into single API call
  - Reduces API costs and server load
  - Visual "saving..." indicator during batch save

### UI/UX
- ✅ Dark cinematic theme
- ✅ Bottom navigation (mobile)
- ✅ Responsive design
- ✅ PWA with offline support
- ✅ **Google AdMob Banner** (Jan 2025) - Adaptive ad banner at bottom of ALL pages
  - Placeholder mode when not configured (shows "AD SPACE" message)
  - Configure via REACT_APP_ADMOB_PUBLISHER_ID and REACT_APP_ADMOB_AD_UNIT_ID
  - Fixed position at bottom, z-index 9999 ensures visibility over all content
  - Bottom navigation repositioned above ad banner on mobile
  - Works on: Login, Dashboard, Recipes, Pantry, Shopping List, Profile, all pages

## Pending Issues

### P0 - Resolved (Jan 2025)
- ✅ **CORS Error on Apple Devices** - Fixed by moving CORSMiddleware before routes, setting allow_origins=["*"]
- ✅ **Body Stream Already Read Error** - Fixed in AuthContext.js by cloning response before reading in error handling
- ✅ **Email Verification Removed** - Users can now sign up immediately without email verification

### P1 - Medium Priority
- **AI-Generated Image Fallback**: Auto-generate images when URL/YouTube imports have no image
- **Verify UI Bug Fixes**: Shopping list navigation, recipe detail back button (from previous sessions)

### P2 - Lower Priority
- **Recipe Comments**: Allow users to add/view comments on recipes

## Future/Backlog
- Social media feed integration (Facebook, Twitter, Instagram)
- Serving size adjustments with nutrition recalculation
- Web-based alternatives for "prevent sleep mode" and "biometric login"
- Refactor large components (Pantry.js, AddRecipe.js - both >1000 lines)

## Key Files
- `/app/backend/routes/recipe_import_workflow.py` - Complete node-based import workflow
- `/app/frontend/src/pages/ShareHandler.js` - Unified import workflow frontend
- `/app/frontend/src/components/BottomNavigation.js` - Orange camera button with modal
- `/app/frontend/src/components/AdBanner.js` - Global Google AdMob banner component (Jan 2025)
- `/app/frontend/src/pages/AddRecipe.js` - Recipe creation with photo workflow
- `/app/frontend/src/pages/Pantry.js` - Pantry management with "Suggest a Meal" feature
- `/app/frontend/src/pages/ShoppingList.js` - User-specific shopping list with batch processing (Jan 2025)
- `/app/backend/routes/recipe_routes.py` - Recipe API endpoints including image validation
- `/app/backend/routes/pantry_routes.py` - Pantry API endpoints including /suggest-meal
- `/app/backend/routes/shopping_routes.py` - Shopping list API endpoints with user isolation
- `/app/frontend/src/utils/imageValidator.js` - Image quality validation utility (Jan 2025)

## Key API Endpoints
- `POST /api/import-recipe-workflow` - Node-based privacy-respecting import (primary)
- `POST /api/import-facebook-recipe` - Legacy endpoint (redirects to new workflow)
- `POST /api/recipes/extract` - Website URL extraction
- `POST /api/recipes/extract-youtube` - YouTube video extraction
- `POST /api/recipes/validate-image` - Image quality validation before AI analysis (Jan 2025)
- `POST /api/pantry/suggest-meal` - AI meal suggestions
- `POST /api/shopping-list/add-multiple` - Batch add to shopping list

## Test Credentials
- Test user: `test2@cookme.com` / `Test123!` (email verified)
- Shopping/Pantry test user 1: `shoptest@cookme.com` / `Test123!` (user_id: user_e4d8741d487e)
- Shopping/Pantry test user 2: `shoptest2@cookme.com` / `Test123!` (user_id: user_5216e4bf7942)
- Or create new user via UI (no email verification needed)
- Test users created during testing: `test_apple_user_[timestamp]@cookme.com` / `TestPassword123!`

## Recipe Import Compatibility
Successfully imports from major recipe sites:
- ✅ InspiredTaste, AllRecipes, Bon Appetit, Serious Eats, Simply Recipes
- ✅ Most WordPress Recipe plugins (WPRM, etc.)
- ✅ Sites using schema.org JSON-LD Recipe markup
- ⚠️ Food Network (blocked by Cloudflare - 403)

**Recent Fixes (Feb 2025):**
- Fixed JSON-LD parsing for malformed JSON with newlines in string values
- Added support for array @type (e.g., `['Recipe', 'NewsArticle']`)
- Improved User-Agent to avoid bot detection on major sites

## Deleted Files
- `/app/backend/routes/facebook_import.py` - Obsolete cookie-based scraper (deleted Jan 17, 2025)
