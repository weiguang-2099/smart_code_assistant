from fastapi import FastAPI, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.deps import get_current_user
from app.core.security import get_token_payload, decode_access_token
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
from app.models.user import User

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
app.include_router(projects_router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(code_files_router, prefix="/api/v1/code-files", tags=["Code Files"])
app.include_router(code_gen_router, prefix="/api/v1/ai", tags=["AI Code Generation"])
app.include_router(agent_router, prefix="/api/v1/agent", tags=["AI Agent"])
app.include_router(documents_router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(versions_router, prefix="/api/v1", tags=["Versions"])
app.include_router(user_profile_router, prefix="/api/v1/user", tags=["User Profile"])
app.include_router(document_parse_router, prefix="/api/v1/documents/parse", tags=["Document Parse"])


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


@app.get("/api/v1/debug/auth")
async def debug_auth(current_user: User = Depends(get_current_user)):
    """
    Debug endpoint to test authentication.
    Returns current user info if token is valid.
    """
    return {
        "authenticated": True,
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "is_active": current_user.is_active,
        },
        "message": "Authentication successful!"
    }


@app.get("/api/v1/debug/token")
async def debug_token(authorization: str = Header(None)):
    """
    Debug endpoint to test token decoding without authentication.
    Shows the decoded token payload.
    """
    if not authorization:
        return {
            "error": "No authorization header provided",
            "hint": "Add 'Authorization: Bearer <your_token>' header"
        }

    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization

    # Try to decode
    payload = decode_access_token(token)

    if payload is None:
        return {
            "error": "Failed to decode token",
            "token_start": token[:20] + "..." if len(token) > 20 else token,
            "token_length": len(token)
        }

    # Try to get full payload
    full_payload = get_token_payload(token)

    return {
        "success": True,
        "payload": payload,
        "full_payload": full_payload,
        "token_length": len(token)
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
