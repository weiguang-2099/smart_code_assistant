from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.deps import get_db
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint to verify service status.
    
    Args:
        db: Database session
        
    Returns:
        HealthResponse: Health status including database connectivity
    """
    try:
        # Test database connection
        result = await db.execute(text("SELECT 1"))
        await result.fetchone()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        database=db_status
    )
