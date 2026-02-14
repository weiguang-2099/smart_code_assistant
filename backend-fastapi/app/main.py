from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.error_handlers import register_exception_handlers
from app.core.rate_limiter import setup_rate_limiting
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.projects import router as projects_router
from app.api.code_files import router as code_files_router
from app.api.code_gen import router as code_gen_router
from app.api.agent import router as agent_router
from app.api.documents import router as documents_router
from app.api.versions import router as versions_router
from app.api.user_profile import router as user_profile_router
from app.api.document_parse import router as document_parse_router
from app.api.agents import router as agents_router, conversations_router, training_router

# Create FastAPI application
app = FastAPI(
    title="Smart Code Assistant API",
    description="AI-powered code generation and review platform",
    version="1.0.0",
    docs_url="/docs" if settings.FASTAPI_ENV == "development" else None,
    redoc_url="/redoc" if settings.FASTAPI_ENV == "development" else None,
)

# Register global exception handlers
register_exception_handlers(app)

# Setup rate limiting
setup_rate_limiting(app)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# Include routers
app.include_router(health_router, prefix="", tags=["Health"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(projects_router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(code_files_router, prefix="/api/v1/code-files", tags=["Code Files"])
app.include_router(code_gen_router, prefix="/api/v1/ai", tags=["AI Code Generation"])
app.include_router(agent_router, prefix="/api/v1/agent", tags=["AI Agent"])
app.include_router(documents_router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(versions_router, prefix="/api/v1", tags=["Versions"])
app.include_router(user_profile_router, prefix="/api/v1/user", tags=["User Profile"])
app.include_router(document_parse_router, prefix="/api/v1/documents/parse", tags=["Document Parse"])
# Agent system routes
app.include_router(agents_router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(conversations_router, prefix="/api/v1/conversations", tags=["Conversations"])
app.include_router(training_router, prefix="/api/v1/training-tasks", tags=["Training Tasks"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Smart Code Assistant API",
        "version": "1.0.0",
        "docs": "/docs" if settings.FASTAPI_ENV == "development" else None
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
