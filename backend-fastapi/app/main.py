from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.health import router as health_router
from app.api.auth import router as auth_router

# Create FastAPI application
app = FastAPI(
    title="Smart Code Assistant API",
    description="AI-powered code generation and review platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="", tags=["Health"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Smart Code Assistant API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/api/v1")
async def api_v1():
    """API v1 endpoint."""
    return {
        "message": "Smart Code Assistant API v1",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.FASTAPI_HOST,
        port=settings.FASTAPI_PORT,
        reload=settings.FASTAPI_ENV == "development",
        log_level="info"
    )
