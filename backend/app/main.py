from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.db.session import init_db, close_db
from app.api.routes import api_router

# ── Boot ───────────────────────────────────────────────────────────────────

settings = get_settings()
setup_logging("DEBUG" if settings.app_env == "development" else "INFO")
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting CodeMentor AI backend (env=%s)", settings.app_env)
    try:
        await init_db()
    except Exception as e:
        logger.warning("DB init skipped: %s", e)
    yield
    await close_db()
    logger.info("Backend shutdown complete")


# ── App ────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="CodeMentor AI",
    description="Autonomous AI mentor for competitive programming and DSA",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", include_in_schema=False)
async def root():
    return JSONResponse({"message": "CodeMentor AI API", "docs": "/docs"})
