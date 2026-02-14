"""
Global exception handlers for the application.
Provides consistent error responses across all endpoints.
"""
import logging
import sys
from typing import Union
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.core.exceptions import (
    AppException,
    ErrorCode,
    InternalServerException,
    DatabaseException,
    ValidationException,
    DuplicateEntryException,
)

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI application."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        """Handle all custom application exceptions."""
        logger.warning(
            f"AppException: {exc.error_code} - {exc.message} "
            f"Path: {request.url.path} Method: {request.method}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors."""
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"],
            })

        logger.warning(
            f"Validation error on {request.url.path}: {errors}"
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": ErrorCode.VALIDATION_ERROR,
                    "message": "Request validation failed",
                    "details": {"errors": errors},
                },
            },
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        """Handle database integrity errors (e.g., duplicate entries)."""
        error_msg = str(exc.orig) if exc.orig else str(exc)

        # Check for common integrity errors
        if "Duplicate entry" in error_msg or "unique constraint" in error_msg.lower():
            logger.warning(f"Duplicate entry error on {request.url.path}: {error_msg}")
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "success": False,
                    "error": {
                        "code": ErrorCode.DUPLICATE_ENTRY,
                        "message": "This record already exists",
                    },
                },
            )

        logger.error(f"Database integrity error on {request.url.path}: {error_msg}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": ErrorCode.DATABASE_ERROR,
                    "message": "Database constraint violation",
                },
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        """Handle all SQLAlchemy database errors."""
        error_msg = str(exc)
        logger.error(
            f"Database error on {request.url.path}: {error_msg}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": ErrorCode.DATABASE_ERROR,
                    "message": "A database error occurred",
                },
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle all unhandled exceptions."""
        # Log the full exception with traceback
        logger.error(
            f"Unhandled exception on {request.url.path} {request.method}: {str(exc)}",
            exc_info=True,
        )

        # Remove any debug print statements that might leak info
        # In production, don't expose internal error details
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": ErrorCode.INTERNAL_ERROR,
                    "message": "An unexpected error occurred. Please try again later.",
                },
            },
        )


class ErrorResponse:
    """Helper class for creating standardized error responses."""

    @staticmethod
    def not_found(resource: str, resource_id: Union[str, int, None] = None) -> dict:
        """Create a not found error response."""
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with id '{resource_id}' not found"
        return {
            "success": False,
            "error": {
                "code": ErrorCode.NOT_FOUND,
                "message": message,
            },
        }

    @staticmethod
    def unauthorized(message: str = "Authentication required") -> dict:
        """Create an unauthorized error response."""
        return {
            "success": False,
            "error": {
                "code": ErrorCode.UNAUTHORIZED,
                "message": message,
            },
        }

    @staticmethod
    def forbidden(message: str = "Access denied") -> dict:
        """Create a forbidden error response."""
        return {
            "success": False,
            "error": {
                "code": ErrorCode.FORBIDDEN,
                "message": message,
            },
        }

    @staticmethod
    def validation_error(errors: list) -> dict:
        """Create a validation error response."""
        return {
            "success": False,
            "error": {
                "code": ErrorCode.VALIDATION_ERROR,
                "message": "Validation failed",
                "details": {"errors": errors},
            },
        }

    @staticmethod
    def rate_limited(retry_after: int = 60) -> dict:
        """Create a rate limit exceeded error response."""
        return {
            "success": False,
            "error": {
                "code": ErrorCode.RATE_LIMIT_EXCEEDED,
                "message": "Rate limit exceeded. Please try again later.",
                "details": {"retry_after": retry_after},
            },
        }
