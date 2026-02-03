from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str
    version: str
    database: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "database": "connected"
            }
        }
