from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from core.config import get_settings
from core.redis_client import redis_client, test_redis_connection
from app.v1 import users, teams, projects, tasks, revenues, meetings, dashboards, auth,notifications
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("🚀 Starting FastAPI application...")
    logger.info(f"📦 Project: {settings.PROJECT_NAME}")
    logger.info(f"🌍 Environment: {settings.ENVIRONMENT}")
    
    # Test Redis connection
    try:
        redis_connected = await test_redis_connection()
        if redis_connected:
            logger.info("✅ Redis connection successful")
        else:
            logger.warning("⚠️  Redis connection failed - caching will be disabled")
    except Exception as e:
        logger.error(f"❌ Redis connection error: {e}")
        logger.warning("⚠️  Continuing without Redis - caching will be disabled")
    
    logger.info("✅ Application startup complete")
    
    yield  # Application is running
    
    # Shutdown
    logger.info("🛑 Shutting down FastAPI application...")
    
    try:
        await redis_client.close()
        logger.info("✅ Redis connection closed")
    except Exception as e:
        logger.error(f"❌ Error closing Redis: {e}")
    
    logger.info("✅ Application shutdown complete")


def get_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        lifespan=lifespan  # Add lifespan handler
    )
    
    app.add_middleware(
        CORSMiddleware,
        # allow_origins=settings.origins_list,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(users.router, prefix=settings.API_V1_STR)
    app.include_router(teams.router, prefix=settings.API_V1_STR)
    app.include_router(projects.router, prefix=settings.API_V1_STR)
    app.include_router(tasks.router, prefix=settings.API_V1_STR)
    app.include_router(revenues.router, prefix=settings.API_V1_STR)
    app.include_router(meetings.router, prefix=settings.API_V1_STR)
    app.include_router(dashboards.router, prefix=settings.API_V1_STR)
    app.include_router(auth.router, prefix=settings.API_V1_STR)
    app.include_router(notifications.router, prefix=settings.API_V1_STR)
    
    return app


app = get_app()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    redis_status = "disconnected"
    
    try:
        await redis_client.execute_command('PING')
        redis_status = "connected"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "redis": redis_status,
        "environment": settings.ENVIRONMENT
    }
