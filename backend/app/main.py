import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import Settings, get_settings
from app.db import DatabaseError, SupabaseAuth, SupabaseRepository
from app.ml.model import RulModel
from app.routes import limiter, router

logger = logging.getLogger("avisense")


def create_app(settings: Settings | None = None, *, repo=None, auth=None, model: RulModel | None = None) -> FastAPI:
    """Build the API. Run with `uvicorn app.main:create_app --factory`.

    Tests pass their own repository, auth and model.
    """
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        client = httpx.AsyncClient(timeout=15.0)
        app.state.model = model or RulModel(settings.model_dir)
        app.state.repo = repo or SupabaseRepository(client, settings.supabase_url, settings.supabase_anon_key)
        app.state.auth = auth or SupabaseAuth(client, settings.supabase_url, settings.supabase_anon_key)
        logger.info("Model %s loaded from %s", app.state.model.version, settings.model_dir)
        yield
        await client.aclose()

    app = FastAPI(
        title="Avisense API",
        version="3.0.0",
        description="Remaining-useful-life estimates and explanations for turbofan engines.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.exception_handler(DatabaseError)
    async def database_error(request: Request, exc: DatabaseError):
        logger.error("Database error on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(status_code=502, content={"detail": "The database request failed. Try again shortly."})

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Something went wrong on the server."})

    app.include_router(router)
    return app

