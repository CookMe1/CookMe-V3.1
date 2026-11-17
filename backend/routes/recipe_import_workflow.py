"""
Facebook Recipe Import Pipeline
================================
Server-side HTTP ingestion pipeline for Facebook URLs.
Behaves like Stashcook - pure crawler, NO browser behavior.

RULES:
- Server-side HTTP fetching ONLY (httpx)
- Crawler User-Agents (facebookexternalhit, Twitterbot)
- NO cookies, NO auth, NO JavaScript
- Stop on login redirects
- Extract OpenGraph + visible text content
"""

import os
import re
import json
import logging
import uuid
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse
from html import unescape
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

# LLM Integration for recipe parsing
from emergentintegrations.llm.chat import LlmChat, UserMessage

# HTML sanitisation and image optimisation
from html_sanitiser import sanitise_html, sanitise_stats, extract_best_image
from image_optimiser import optimise_image_url

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# MODELS
# ============================================================================

class ImportPayload(BaseModel):
    """Input: URL or pasted text"""
    url: Optional[str] = None
    text: Optional[str] = None


class RecipeOutput(BaseModel):
    """Output: Normalized recipe data"""
    title: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    ingredients: Optional[List[str]] = None
    instructions: Optional[str] = None
    steps: Optional[List[str]] = None
    source: str = "facebook"
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    servings: Optional[int] = None
    nutrition: Optional[dict] = None
    confidence: str = "high"
    confidence_score: float = 1.0
    needs_user_input: bool = False
    user_message: Optional[str] = None
    source_url: Optional[str] = None


class WorkflowResponse(BaseModel):
    """API Response"""
    success: bool
    recipe: Optional[RecipeOutput] = None
    error: Optional[str] = None
    node_reached: str = ""
    needs_confirmation: bool = True


# ============================================================================
# CRAWLER USER-AGENTS (What Facebook expects for link previews)
# ============================================================================

CRAWLER_USER_AGENTS = [
    "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
    "facebookexternalhit/1.1",
    "Twitterbot/1.0",
    "LinkedInBot/1.0",
    "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)",
    "WhatsApp/2.21.12.21",
]


# ============================================================================
# KNOWN RECIPE DOMAINS
# ============================================================================

RECIPE_DOMAINS = [
    'allrecipes.com', 'bbcgoodfood.com', 'food.com', 'foodnetwork.com',
    'epicurious.com', 'bonappetit.com', 'seriouseats.com', 'delish.com',
    'tasty.co', 'simplyrecipes.com', 'cookinglight.com', 'myrecipes.com',
    'budgetbytes.com', 'recipetineats.com', 'halfbakedharvest.com',
    'pinchofyum.com', 'minimalistbaker.com', 'cookieandkate.com',
    'thekitchn.com', 'sallysbakingaddiction.com', 'kingarthurbaking.com',
    'smittenkitchen.com', 'loveandlemons.com', 'damndelicious.net',
    'yummly.com', 'food52.com', 'tasteofhome.com', 'eatingwell.com'
]


# ============================================================================
# OPENGRAPH METADATA EXTRACTOR
# ============================================================================

def extract_opengraph(html: str) -> Dict[str, str]:
    """Extract OpenGraph metadata from HTML"""
    og_data = {
        'title': None,
        'description': None,
        'image': None,
        'url': None,
        'type': None,
        'site_name': None
    }
    
    # OpenGraph patterns
    og_patterns = {
        'title': [
            r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']*)["\']',
            r'<meta[^>]*content=["\']([^"\']*)["\'][^>]*property=["\']og:title["\']',
        ],
        'description': [
            r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']*)["\']',
            r'<meta[^>]*content=["\']([^"\']*)["\'][^>]*property=["\']og:description["\']',
        ],
        'image': [
            r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']*)["\']',
            r'<meta[^>]*content=["\']([^"\']*)["\'][^>]*property=["\']og:image["\']',
        ],
        'url': [
            r'<meta[^>]*property=["\']og:url["\'][^>]*content=["\']([^"\']*)["\']',
        ],
        'type': [
            r'<meta[^>]*property=["\']og:type["\'][^>]*content=["\']([^"\']*)["\']',
        ],
        'site_name': [
            r'<meta[^>]*property=["\']og:site_name["\'][^>]*content=["\']([^"\']*)["\']',
        ]
    }
    
    for key, patterns in og_patterns.items():
        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                og_data[key] = unescape(match.group(1).strip())
                break
    
    # Fallback to standard meta tags
    if not og_data['title']:
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        if title_match:
            og_data['title'] = unescape(title_match.group(1).strip())
    
    if not og_data['description']:
        desc_match = re.search(
            r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']',
            html, re.IGNORECASE
        )
        if desc_match:
            og_data['description'] = unescape(desc_match.group(1).strip())
    
    return og_data


# ============================================================================
# URL NORMALIZATION
# ============================================================================

def normalize_facebook_url(url: str) -> str:
    """Normalize Facebook URL - force HTTPS, standardize format"""
    if not url:
        return url
    
    # Force HTTPS
    url = url.replace('http://', 'https://')
    
    # Ensure https:// prefix
    if not url.startswith('https://'):
        url = 'https://' + url
    
    # Normalize mobile to www for crawler access
    url = url.replace('https://m.facebook.com', 'https://www.facebook.com')
    
    return url


def is_facebook_url(url: str) -> bool:
    """Check if URL is a Facebook URL"""
    if not url:
        return False
    lower = url.lower()
    return any(domain in lower for domain in [
        'facebook.com', 'fb.com', 'fb.watch', 'm.facebook.com'
    ])


def extract_urls_from_text(text: str) -> List[str]:
    """Extract all URLs from text"""
    pattern = r'https?://[^\s<>"\')\]]+(?=["\'\s<>)\]]|$)'
    urls = re.findall(pattern, text)
    return [re.sub(r'[)\]}>.,;!?]+$', '', url) for url in urls]


def find_external_recipe_url(html: str, og_url: str = None) -> Optional[str]:
    """Find external recipe URLs in the HTML content"""
    urls = extract_urls_from_text(html)
    
    # Also check og:url for redirects
    if og_url:
        urls.append(og_url)
    
    # Skip domains
    skip_domains = [
        'facebook.com', 'fb.com', 'fb.watch', 'fbcdn.net',
        'instagram.com', 'twitter.com', 'x.com', 'tiktok.com',
        'w3.org', 'schema.org', 'googleapis.com', 'google.com',
        'cloudflare.com', 'amazonaws.com', 'apple.com'
    ]
    
    external_urls = []
    recipe_urls = []
    
    for url in urls:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace('www.', '')
            
            if any(skip in domain for skip in skip_domains):
                continue
            
            if not domain or '.' not in domain:
                continue
            
            # Prioritize known recipe domains
            if any(recipe_domain in domain for recipe_domain in RECIPE_DOMAINS):
                recipe_urls.append(url)
            else:
                external_urls.append(url)
                
        except Exception:
            continue
    
    # Return recipe URL first, then any external URL
    if recipe_urls:
        return recipe_urls[0]
    if external_urls:
        return external_urls[0]
    
    return None


# ============================================================================
# SERVER-SIDE HTTP FETCHER (Crawler behavior)
# ============================================================================

async def fetch_url_as_crawler(url: str) -> Dict[str, Any]:
    """
    Fetch URL using crawler User-Agent.
    NO cookies, NO auth, NO JavaScript.
    Stop on login redirects.
    """
    result = {
        'success': False,
        'html': '',
        'final_url': url,
        'status_code': None,
        'error': None,
        'redirected_to_login': False
    }
    
    # Try each crawler User-Agent
    for ua in CRAWLER_USER_AGENTS:
        try:
            async with httpx.AsyncClient(
                timeout=20.0,
                follow_redirects=False,  # Handle redirects manually
                verify=True
            ) as client:
                headers = {
                    'User-Agent': ua,
                    'Accept': 'text/html,application/xhtml+xml',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Cache-Control': 'no-cache',
                    # NO cookies
                }
                
                current_url = url
                redirect_count = 0
                max_redirects = 5
                
                while redirect_count < max_redirects:
                    response = await client.get(current_url, headers=headers)
                    result['status_code'] = response.status_code
                    
                    # Check for redirects
                    if response.status_code in [301, 302, 303, 307, 308]:
                        location = response.headers.get('location', '')
                        
                        # STOP if redirected to login
                        if '/login' in location.lower() or 'login.php' in location.lower():
                            logger.info(f"Crawler: Login redirect detected, stopping")
                            result['redirected_to_login'] = True
                            result['error'] = 'login_redirect'
                            break
                        
                        # Follow redirect
                        if location.startswith('/'):
                            parsed = urlparse(current_url)
                            location = f"{parsed.scheme}://{parsed.netloc}{location}"
                        
                        current_url = location
                        redirect_count += 1
                        continue
                    
                    # Got response
                    if response.status_code == 200:
                        html = response.text
                        
                        # Check if content has login form (blocked)
                        if is_login_page(html):
                            logger.info(f"Crawler: Page contains login form")
                            result['redirected_to_login'] = True
                            result['error'] = 'login_required'
                            result['html'] = html  # Still return HTML for OG extraction
                            break
                        
                        result['success'] = True
                        result['html'] = html
                        result['final_url'] = current_url
                        logger.info(f"Crawler: Successfully fetched {len(html)} bytes with {ua}")
                        return result
                    
                    # Non-success status
                    break
                
                # If we got HTML (even from login page), try to extract OG data
                if result.get('html'):
                    return result
                    
        except httpx.TimeoutException:
            logger.warning(f"Crawler: Timeout with {ua}")
            result['error'] = 'timeout'
        except httpx.HTTPError as e:
            logger.warning(f"Crawler: HTTP error with {ua}: {e}")
            result['error'] = str(e)
        except Exception as e:
            logger.warning(f"Crawler: Error with {ua}: {e}")
            result['error'] = str(e)
    
    return result


def is_login_page(html: str) -> bool:
    """Check if HTML is a login/blocked page"""
    lower_html = html.lower()
    
    # Check for login indicators
    login_indicators = [
        '<form' in lower_html and 'password' in lower_html,
        'id="loginform"' in lower_html,
        'name="login"' in lower_html,
        'log in to facebook' in lower_html,
        'log into facebook' in lower_html,
        'you must log in' in lower_html,
    ]
    
    # Check for minimal content (just a shell page)
    if len(html) < 5000 and 'password' in lower_html:
        return True
    
    return any(login_indicators)


# ============================================================================
# EXTERNAL RECIPE FETCHER
# ============================================================================

async def fetch_external_recipe(url: str) -> RecipeOutput:
    """Fetch and parse recipe from external URL using HTML sanitiser + JSON-LD."""
    logger.info(f"Fetching external recipe: {url}")

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }

            # ── Soft-paywall sites: add Googlebot UA + Google referer ─────────
            # These sites publish full JSON-LD in HTML for Google indexing.
            # Adding a Google referer triggers "first click free" behaviour,
            # which gives access to the full recipe content without login.
            SOFT_PAYWALL_DOMAINS = {
                'cooking.nytimes.com', 'nytimes.com',
                'washingtonpost.com',
                'theguardian.com', 'guardian.com',
                'bonappetit.com',
                'epicurious.com',
                'telegraph.co.uk',
                'ottolenghi.co.uk',
                'latimes.com',
                'seriouseats.com',
                'food52.com',
                'delish.com',
                'esquire.com',
                'menshealth.com',
                'womenshealthmag.com',
                'prevention.com',
                'countryliving.com',
                'goodhousekeeping.com',
                'homecookingshow.in',
            }
            domain_check = urlparse(url).netloc.lower().replace('www.', '')
            if any(d in domain_check for d in SOFT_PAYWALL_DOMAINS):
                headers['User-Agent'] = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
                headers['Referer'] = 'https://www.google.com/'
                logger.info(f"Using Googlebot headers for soft-paywall domain: {domain_check}")

            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {response.status_code}")
            html = response.text
    except Exception as e:
        logger.error(f"Failed to fetch external URL: {e}")
        raise HTTPException(status_code=502, detail=str(e))

    domain = urlparse(url).netloc.replace('www.', '')
    recipe = RecipeOutput(source="external", source_url=url)

    # ── Step 1: JSON-LD schema.org (zero AI cost) ─────────────────────────────
    json_ld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
    json_ld_matches = re.findall(json_ld_pattern, html, re.DOTALL | re.IGNORECASE)

    for match in json_ld_matches:
        try:
            cleaned = re.sub(r'(?<!\\)\n', ' ', match.strip())
            cleaned = re.sub(r'(?<!\\)\r', ' ', cleaned)
            cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', cleaned)
            data = json.loads(cleaned)

            if isinstance(data, dict) and '@graph' in data:
                data = data['@graph']

            def is_recipe_type(item):
                if not isinstance(item, dict):
                    return False
                t = item.get('@type', '')
                if isinstance(t, str):
                    return t.lower() == 'recipe'
                elif isinstance(t, list):
                    return any(x.lower() == 'recipe' for x in t if isinstance(x, str))
                return False

            recipes = [item for item in data if is_recipe_type(item)] if isinstance(data, list) else ([data] if is_recipe_type(data) else [])

            for r in recipes:
                recipe.title = r.get('name', recipe.title)
                recipe.description = r.get('description', '')

                ingredients = r.get('recipeIngredient', [])
                recipe.ingredients = [str(i).strip() for i in ingredients if i]

                instructions = r.get('recipeInstructions', [])
                if isinstance(instructions, str):
                    recipe.instructions = instructions
                    recipe.steps = [s.strip() for s in instructions.split('\n') if s.strip()]
                elif isinstance(instructions, list):
                    steps = []
                    for inst in instructions:
                        if isinstance(inst, str):
                            steps.append(inst.strip())
                        elif isinstance(inst, dict):
                            text = inst.get('text', '') or inst.get('name', '')
                            if text:
                                steps.append(text.strip())
                    recipe.steps = [s for s in steps if s]
                    recipe.instructions = '\n'.join(recipe.steps)

                images = r.get('image', [])
                if isinstance(images, str):
                    recipe.image = images
                elif isinstance(images, list) and images:
                    recipe.image = images[0] if isinstance(images[0], str) else images[0].get('url', '')
                elif isinstance(images, dict):
                    recipe.image = images.get('url', '')

                recipe_yield = r.get('recipeYield', 4)
                if isinstance(recipe_yield, str):
                    m = re.search(r'\d+', recipe_yield)
                    recipe.servings = int(m.group()) if m else 4
                elif isinstance(recipe_yield, (int, float)):
                    recipe.servings = int(recipe_yield)

                recipe.prep_time = parse_duration(r.get('prepTime', ''))
                recipe.cook_time = parse_duration(r.get('cookTime', ''))

                # ── Nutrition (free if site publishes schema.org NutritionInformation) ──
                n = r.get('nutrition', {})
                if isinstance(n, dict):
                    def _num(val):
                        if val is None: return None
                        try:
                            import re as _re
                            return round(float(_re.search(r'[\d.]+', str(val)).group()))
                        except Exception: return None
                    cal = _num(n.get('calories'))
                    if cal:
                        recipe.nutrition = {
                            'calories': cal,
                            'protein':  _num(n.get('proteinContent')),
                            'carbs':    _num(n.get('carbohydrateContent')),
                            'fat':      _num(n.get('fatContent')),
                            'fiber':    _num(n.get('fiberContent')),
                            'sugar':    _num(n.get('sugarContent')),
                            'sodium':   _num(n.get('sodiumContent')),
                        }

                if recipe.title and recipe.ingredients:
                    recipe.confidence = "high"
                    recipe.confidence_score = 1.0
                    logger.info(f"JSON-LD extraction: {recipe.title} ({len(recipe.ingredients)} ingredients)")
                    # Optimise image asynchronously
                    if recipe.image:
                        _, recipe.image = await optimise_image_url(recipe.image)
                    return recipe

        except json.JSONDecodeError:
            continue
        except Exception as e:
            logger.warning(f"JSON-LD parse error: {e}")
            continue

    # ── Step 2: HTML sanitisation + AI fallback ───────────────────────────────
    # Extract image BEFORE sanitising (sanitiser also does this but we want it early)
    image_url = extract_best_image(html, url)

    sanitised_text, extracted_image = sanitise_html(html, base_url=url, max_chars=3500)
    image_url = image_url or extracted_image

    stats = sanitise_stats(html, sanitised_text)
    logger.info(
        f"HTML sanitised: {stats['original_chars']:,} → {stats['sanitised_chars']:,} chars "
        f"({stats['reduction_pct']}% reduction, ~{stats['sanitised_tokens_approx']} tokens)"
    )

    # OpenGraph fallback for title/description
    og = extract_opengraph(html)
    recipe.title = og.get('title') or recipe.title
    recipe.description = og.get('description') or recipe.description
    recipe.image = image_url or og.get('image') or ''

    if recipe.title and sanitised_text:
        recipe.confidence = "medium"
        recipe.confidence_score = 0.5
        recipe.needs_user_input = True
        recipe.user_message = f"Found recipe from {domain} — please verify details."

    # Optimise image
    if recipe.image:
        _, recipe.image = await optimise_image_url(recipe.image)

    return recipe


def parse_duration(duration: str) -> str:
    """Parse ISO 8601 duration to human readable"""
    if not duration:
        return ""
    
    hours = re.search(r'(\d+)H', duration)
    minutes = re.search(r'(\d+)M', duration)
    
    parts = []
    if hours:
        parts.append(f"{hours.group(1)}h")
    if minutes:
        parts.append(f"{minutes.group(1)}m")
    
    return ' '.join(parts) if parts else ""


# ============================================================================
# AI RECIPE PARSER
# ============================================================================

async def parse_text_with_ai(text: str, og_data: Dict = None) -> RecipeOutput:
    """Use AI to extract recipe from text content"""
    logger.info("Parsing text with AI")
    
    recipe = RecipeOutput(source="facebook")
    
    # Use OG data as fallback
    if og_data:
        recipe.title = og_data.get('title', '')
        recipe.description = og_data.get('description', '')
        recipe.image = og_data.get('image', '')
    
    if not text or len(text.strip()) < 30:
        recipe.confidence = "user-assisted"
        recipe.confidence_score = 0.1
        recipe.needs_user_input = True
        recipe.user_message = "Not enough content to extract recipe. Please paste the recipe text."
        return recipe
    
    try:
        emergent_key = os.environ.get('EMERGENT_LLM_KEY', '')
        
        if not emergent_key:
            raise ValueError("No LLM key")
        
        prompt = f"""Analyze this text and extract recipe information. Return JSON only:

{{
  "is_recipe": boolean,
  "title": "recipe name",
  "description": "brief description",
  "ingredients": ["ingredient 1", "ingredient 2"],
  "steps": ["step 1", "step 2"],
  "servings": number or null,
  "prep_time": "time string" or null,
  "cook_time": "time string" or null,
  "confidence": 0.0 to 1.0
}}

Text:
{text[:3500]}

Return valid JSON only, no markdown."""

        session_id = str(uuid.uuid4())
        llm = LlmChat(
            api_key=emergent_key,
            session_id=session_id,
            system_message="Extract recipe data from text. Return valid JSON only."
        ).with_model("openai", "gpt-4o-mini")
        
        response_text = await llm.send_message(UserMessage(text=prompt))
        
        # Parse JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            parsed = json.loads(json_match.group())
            
            if not parsed.get('is_recipe', True):
                recipe.confidence = "user-assisted"
                recipe.confidence_score = 0.1
                recipe.needs_user_input = True
                recipe.user_message = "This doesn't appear to be a recipe."
                return recipe
            
            recipe.title = parsed.get('title') or recipe.title or "Recipe"
            recipe.description = parsed.get('description') or recipe.description
            recipe.ingredients = parsed.get('ingredients', [])
            recipe.steps = parsed.get('steps', [])
            recipe.instructions = '\n'.join(recipe.steps) if recipe.steps else ''
            recipe.servings = parsed.get('servings')
            recipe.prep_time = parsed.get('prep_time')
            recipe.cook_time = parsed.get('cook_time')
            
            ai_confidence = float(parsed.get('confidence', 0.7))
            recipe.confidence_score = ai_confidence
            recipe.confidence = "high" if ai_confidence >= 0.8 else "medium" if ai_confidence >= 0.5 else "user-assisted"
            recipe.needs_user_input = ai_confidence < 0.5
            
            if recipe.needs_user_input:
                recipe.user_message = "Low confidence extraction. Please review and edit."
            
            logger.info(f"AI extracted: {recipe.title}, {len(recipe.ingredients)} ingredients, confidence {ai_confidence}")
            return recipe
            
    except json.JSONDecodeError as e:
        logger.error(f"AI JSON decode error: {e}")
    except Exception as e:
        logger.error(f"AI parsing failed: {e}")
    
    # Fallback
    recipe.confidence = "user-assisted"
    recipe.confidence_score = 0.2
    recipe.needs_user_input = True
    recipe.user_message = "Could not parse recipe automatically. Please paste the recipe text."
    
    return recipe


# ============================================================================
# MAIN WORKFLOW ENDPOINT
# ============================================================================

@router.post("/import-recipe-workflow", response_model=WorkflowResponse)
async def import_recipe_workflow(payload: ImportPayload):
    """
    Main recipe import endpoint.
    
    Server-side HTTP pipeline - NO browser behavior.
    Uses crawler User-Agents for Facebook URLs.
    """
    
    if not payload.url and not payload.text:
        raise HTTPException(status_code=400, detail="Please provide a URL or text")
    
    logger.info("=== Recipe Import Pipeline Started ===")
    
    # =========================================================================
    # CASE 1: Direct text input - parse with AI
    # =========================================================================
    if payload.text and not payload.url:
        logger.info("Processing direct text input")
        
        # Check if text contains URLs
        urls = extract_urls_from_text(payload.text)
        
        if urls:
            # Extract URL and process it
            payload.url = urls[0]
            logger.info(f"Found URL in text: {payload.url}")
        else:
            # Pure text - parse with AI
            recipe = await parse_text_with_ai(payload.text)
            return WorkflowResponse(
                success=True,
                recipe=recipe,
                node_reached="text_ai_parse",
                needs_confirmation=True
            )
    
    # =========================================================================
    # CASE 2: URL input
    # =========================================================================
    url = normalize_facebook_url(payload.url)
    logger.info(f"Processing URL: {url}")
    
    # Check if Facebook URL
    is_fb = is_facebook_url(url)
    
    if is_fb:
        # -----------------------------------------------------------------
        # FACEBOOK URL - Use crawler fetch
        # -----------------------------------------------------------------
        logger.info("Detected Facebook URL - using crawler fetch")
        
        fetch_result = await fetch_url_as_crawler(url)
        
        # Extract OpenGraph from whatever HTML we got
        og_data = {}
        if fetch_result.get('html'):
            og_data = extract_opengraph(fetch_result['html'])
            logger.info(f"OG data: title={og_data.get('title')}, has_image={bool(og_data.get('image'))}")
        
        # Check for external recipe URL in content
        external_url = None
        if fetch_result.get('html'):
            external_url = find_external_recipe_url(fetch_result['html'], og_data.get('url'))
        
        if external_url:
            logger.info(f"Found external recipe URL: {external_url}")
            try:
                recipe = await fetch_external_recipe(external_url)
                recipe.source_url = external_url
                
                # Use OG image if recipe has none
                if not recipe.image and og_data.get('image'):
                    recipe.image = og_data.get('image')
                
                return WorkflowResponse(
                    success=True,
                    recipe=recipe,
                    node_reached="external_recipe",
                    needs_confirmation=True
                )
            except Exception as e:
                logger.warning(f"External recipe fetch failed: {e}")
        
        # Check if we got blocked (login redirect)
        if fetch_result.get('redirected_to_login'):
            logger.info("Facebook requires login - returning with OG data")
            
            recipe = RecipeOutput(
                title=og_data.get('title') or "Recipe from Facebook",
                description=og_data.get('description') or "",
                image=og_data.get('image'),
                source="facebook",
                source_url=url,
                confidence="user-assisted",
                confidence_score=0.0,
                needs_user_input=True,
                user_message="This Facebook post requires login to view. Please copy the recipe text from Facebook and paste it here."
            )
            
            return WorkflowResponse(
                success=True,
                recipe=recipe,
                node_reached="login_blocked",
                needs_confirmation=True
            )
        
        # Got content - try to extract recipe
        if fetch_result.get('success') and fetch_result.get('html'):
            # Sanitise the HTML — extract only recipe-relevant text, discard nav/ads/footer
            sanitised_text, extracted_image = sanitise_html(
                fetch_result['html'], base_url=url, max_chars=3500
            )

            # Combine OG description with sanitised content
            full_text = f"{og_data.get('title', '')}\n{og_data.get('description', '')}\n{sanitised_text}"

            recipe = await parse_text_with_ai(full_text, og_data)
            recipe.source_url = url

            if not recipe.image:
                recipe.image = og_data.get('image') or extracted_image

            # Optimise the image
            if recipe.image:
                _, recipe.image = await optimise_image_url(recipe.image)
            
            return WorkflowResponse(
                success=True,
                recipe=recipe,
                node_reached="facebook_content",
                needs_confirmation=True
            )
        
        # Failed to get content - return with OG data only
        recipe = RecipeOutput(
            title=og_data.get('title') or "Recipe from Facebook",
            description=og_data.get('description') or "",
            image=og_data.get('image'),
            source="facebook",
            source_url=url,
            confidence="user-assisted",
            confidence_score=0.1,
            needs_user_input=True,
            user_message="Could not access Facebook content. Please paste the recipe text."
        )
        
        return WorkflowResponse(
            success=True,
            recipe=recipe,
            node_reached="facebook_limited",
            needs_confirmation=True
        )
    
    else:
        # -----------------------------------------------------------------
        # NON-FACEBOOK URL - Standard recipe fetch
        # -----------------------------------------------------------------
        logger.info("Processing non-Facebook URL")
        
        try:
            recipe = await fetch_external_recipe(url)
            recipe.source_url = url
            
            return WorkflowResponse(
                success=True,
                recipe=recipe,
                node_reached="direct_url",
                needs_confirmation=True
            )
        except Exception as e:
            logger.error(f"URL fetch failed: {e}")
            
            return WorkflowResponse(
                success=False,
                recipe=RecipeOutput(
                    source="external",
                    source_url=url,
                    confidence="user-assisted",
                    confidence_score=0.0,
                    needs_user_input=True,
                    user_message=f"Could not fetch URL. Please paste the recipe text."
                ),
                error=str(e),
                node_reached="url_failed",
                needs_confirmation=True
            )


# ============================================================================
# LEGACY ENDPOINTS (Backwards compatibility)
# ============================================================================

@router.post("/import-facebook-recipe")
async def import_facebook_recipe_legacy(request_body: dict):
    """Legacy endpoint - redirects to new workflow"""
    url = request_body.get('url', '')
    text = request_body.get('text', '')
    
    payload = ImportPayload(url=url, text=text)
    result = await import_recipe_workflow(payload)
    
    if not result.success and result.error:
        raise HTTPException(status_code=400, detail=result.error)
    
    r = result.recipe
    
    return {
        "title": r.title,
        "description": r.description,
        "instructions": r.instructions,
        "ingredients": [{"item": ing, "amount": "", "category": "Other"} for ing in (r.ingredients or [])],
        "imageUrl": r.image,
        "sourceUrl": r.source_url,
        "platform": "Facebook",
        "prep_time": r.prep_time or "30 min",
        "cook_time": r.cook_time or "30 min",
        "servings": r.servings or 4,
        "steps": r.steps or [],
        "confidence": r.confidence,
        "confidence_score": r.confidence_score,
        "needs_user_input": r.needs_user_input,
        "user_message": r.user_message
    }


@router.get("/import-facebook-recipe")
async def import_facebook_recipe_get(url: str):
    """GET endpoint for backwards compatibility"""
    return await import_facebook_recipe_legacy({"url": url})
