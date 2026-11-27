from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME")
if not MONGO_URL:
    raise RuntimeError("MONGO_URL is required. Set it in the environment or backend/.env.")
if not DB_NAME:
    raise RuntimeError("DB_NAME is required. Set it in the environment or backend/.env.")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = db
    logger.info("Connected to MongoDB")
    try:
        await db.recipes.create_index([("user_id", 1), ("created_at", -1)])
        await db.recipes.create_index([("created_at", -1)])
        await db.recipes.create_index([("favorited_by", 1)])
        await db.recipes.create_index([("recipe_id", 1)], unique=True)
        await db.recipes.create_index([("category", 1)])
        await db.recipes.create_index([("cuisine", 1)])
        await db.recipes.create_index([("title", "text"), ("description", "text"), ("tags", "text")])
        await db.users.create_index([("user_id", 1)], unique=True)
        await db.users.create_index([("email", 1)], unique=True)
        await db.pantry_items.create_index([("user_id", 1), ("in_stock", 1)])
        await db.pantry_items.create_index([("user_id", 1), ("category", 1)])
        await db.shopping_list.create_index([("user_id", 1)])
        await db.user_sessions.create_index([("session_token", 1)])
        await db.user_sessions.create_index([("expires_at", 1)], expireAfterSeconds=0)
        await db.cookbooks.create_index([("user_id", 1), ("created_at", -1)])
        # social / sharing / admin
        await db.comments.create_index([("recipe_id", 1), ("status", 1), ("created_at", 1)])
        await db.comments.create_index([("user_id", 1), ("created_at", -1)])
        await db.comments.create_index([("comment_id", 1)])
        await db.comments.create_index([("parent_id", 1)], sparse=True)
        await db.reports.create_index([("status", 1), ("created_at", 1)])
        await db.reports.create_index([("kind", 1), ("target_id", 1), ("status", 1)])
        await db.reports.create_index([("reporter_id", 1), ("created_at", -1)])
        await db.recipe_consents.create_index([("user_id", 1)])
        await db.recipes.create_index([("visibility", 1), ("public_since", -1)])
        await db.recipes.create_index([("user_id", 1), ("visibility", 1)])
        await db.recipes.create_index([("hidden_by", 1)])
        await db.client_errors.create_index([("created_at", 1)], expireAfterSeconds=60 * 60 * 24 * 30)
        await db.cookbooks.create_index([("cookbook_id", 1)], unique=True)
        await db.meal_plans.create_index([("user_id", 1), ("week_start", -1)])
        await db.meal_plans.create_index([("meal_plan_id", 1)], unique=True)

        from cache import create_cache_indexes
        from url_registry import create_registry_indexes
        await create_cache_indexes(db)
        await create_registry_indexes(db)
        await db.import_jobs.create_index("job_id", unique=True)
        await db.import_jobs.create_index("user_id")
        await db.import_jobs.create_index("expires_at", expireAfterSeconds=0)
        await db.community_recipes.create_index("community_recipe_id", unique=True, sparse=True)
        await db.community_recipes.create_index([
            ("title", "text"), ("ingredient_names", "text"),
            ("description", "text"), ("tags", "text")
        ])
        await db.community_recipes.create_index("cuisine")
        await db.community_recipes.create_index("category")
        await db.community_recipes.create_index("ingredient_names")
        await db.community_recipes.create_index("likes_count")
        await db.community_likes.create_index(
            [("user_id", 1), ("community_recipe_id", 1)], unique=True, sparse=True
        )
        logger.info("Database indexes created/verified successfully")
    except Exception:
        logger.exception("Index creation failed; continuing startup")

    seed_task = None
    try:
        import asyncio
        from seed_master import seed_master_recipes, sync_master_updates

        async def _seed_then_sync():
            await seed_master_recipes(db)      # first start on an empty database only
            await sync_master_updates(db)      # one-time corrections (local images, times, descriptions)
        seed_task = asyncio.create_task(_seed_then_sync())
    except Exception:
        logger.exception("Could not start the master recipe seeding")

    try:
        import asyncio
        from ai_client import verify_model
        asyncio.create_task(verify_model())   # tests the AI model once; falls back to GPT-4o mini if it fails
    except Exception:
        logger.exception("Could not start the AI model check")

    release_task = None
    try:
        import asyncio
        from release_queue import release_loop
        release_task = asyncio.create_task(release_loop(db))
    except Exception:
        logger.exception("Could not start the daily recipe release")

    yield

    if release_task:
        release_task.cancel()
    client.close()
    logger.info("Closed MongoDB connection")


# Optional crash reporting: set SENTRY_DSN (free plan at sentry.io) and `pip install sentry-sdk`. Does nothing otherwise.
if os.getenv("SENTRY_DSN"):
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=os.environ["SENTRY_DSN"], traces_sample_rate=0.0, send_default_pii=False)
    except Exception:
        logging.getLogger(__name__).warning("SENTRY_DSN is set but sentry-sdk is not installed")

app = FastAPI(lifespan=lifespan)

# Compress API responses (recipe lists shrink 3-5x)
from starlette.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Credentials with wildcard origins are rejected by browsers. This app uses bearer
# tokens, so credentials are disabled until explicit origins are configured.
allowed_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins or ["*"],
    allow_credentials=bool(allowed_origins),
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

api_router = APIRouter(prefix="/api")
from routes.auth_routes import router as auth_router
from routes.recipe_routes import router as recipe_router
from routes.pantry_routes import router as pantry_router
from routes.shopping_routes import router as shopping_router
from routes.recipe_import_workflow import router as import_workflow_router
from routes.cookbook_routes import router as cookbook_router
from routes.meal_plan_routes import router as meal_plan_router
from routes.instagram_routes import router as instagram_router
from routes.translation_routes import router as translation_router
from routes.community_routes import router as community_router
from routes.social_routes import router as social_router
from routes.admin_routes import router as admin_router
from routes.ai_routes import router as ai_router
from routes.monitoring_routes import router as monitoring_router
from routes.localisation_routes import router as localisation_router
from import_queue import router as import_queue_router

for router in (
    auth_router, recipe_router, pantry_router, shopping_router,
    import_workflow_router, cookbook_router, meal_plan_router,
    instagram_router, translation_router, community_router,
    localisation_router, import_queue_router, social_router, admin_router, monitoring_router, ai_router,
):
    api_router.include_router(router)


@api_router.get("/")
async def root():
    return {"message": "Grubly API is running"}


app.include_router(api_router)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
