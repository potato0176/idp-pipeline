"""FastAPI application entry point with lifespan management."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.api.routes import router
from app.api.dependencies import init_services, shutdown_services


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle manager."""
    settings = get_settings()
    setup_logging(debug=settings.debug)
    logger.info(f"Starting {settings.app_name} ({settings.app_env})")

    # Initialize all services
    await init_services()
    logger.info("All services initialized ✓")

    yield  # Application is running

    # Cleanup
    await shutdown_services()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=(
            "Intelligent Document Processing Pipeline API — "
            "Docling + EasyOCR + VLM (Gemma 3 27b) → Markdown/JSON → Vector DB"
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    app.include_router(router)

    return app


# The `app` object Uvicorn will import
app = create_app()
