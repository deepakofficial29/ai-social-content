"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import health, jobs, media
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, get_logger
from app.database.connection import create_tables

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    create_tables()
    logger.info("Application startup complete.")
    yield
    logger.info("Application shutdown.")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler for typed AppErrors
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.message,
                "error": {"code": exc.error_code, "details": exc.details},
            },
        )

    # Catch-all for unexpected errors
    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception: %s", exc)
        message = str(exc) if settings.DEBUG else "An internal error occurred."
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": message,
                "error": {"code": "INTERNAL_ERROR", "details": {}},
            },
        )

    # Routes
    prefix = settings.API_V1_PREFIX
    app.include_router(health.router, prefix=prefix)
    app.include_router(media.router, prefix=prefix)
    app.include_router(jobs.router, prefix=prefix)

    return app


app = create_app()
