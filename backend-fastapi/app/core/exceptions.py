"""
Custom exceptions for the application.
Provides a unified error handling system with consistent error codes and messages.
"""
from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class ErrorCode:
    """Error codes for consistent error identification across the application."""

    # Authentication errors (1xxx)
    UNAUTHORIZED = "AUTH_001"
    INVALID_TOKEN = "AUTH_002"
    TOKEN_EXPIRED = "AUTH_003"
    TOKEN_REVOKED = "AUTH_004"
    INVALID_CREDENTIALS = "AUTH_005"
    ACCOUNT_DISABLED = "AUTH_006"
    EMAIL_NOT_VERIFIED = "AUTH_007"

    # Authorization errors (2xxx)
    FORBIDDEN = "AUTHZ_001"
    INSUFFICIENT_PERMISSIONS = "AUTHZ_002"
    RESOURCE_ACCESS_DENIED = "AUTHZ_003"

    # Resource errors (3xxx)
    NOT_FOUND = "RES_001"
    USER_NOT_FOUND = "RES_002"
    DOCUMENT_NOT_FOUND = "RES_003"
    AGENT_NOT_FOUND = "RES_004"
    PROJECT_NOT_FOUND = "RES_005"
    CONVERSATION_NOT_FOUND = "RES_006"
    VERSION_NOT_FOUND = "RES_007"

    # Validation errors (4xxx)
    VALIDATION_ERROR = "VAL_001"
    INVALID_INPUT = "VAL_002"
    DUPLICATE_ENTRY = "VAL_003"
    INVALID_FILE_TYPE = "VAL_004"
    FILE_TOO_LARGE = "VAL_005"

    # Rate limiting errors (5xxx)
    RATE_LIMIT_EXCEEDED = "RATE_001"
    TOO_MANY_REQUESTS = "RATE_002"

    # External service errors (6xxx)
    EXTERNAL_SERVICE_ERROR = "EXT_001"
    AI_SERVICE_ERROR = "EXT_002"
    PDF_PARSE_ERROR = "EXT_003"

    # Server errors (9xxx)
    INTERNAL_ERROR = "SRV_001"
    DATABASE_ERROR = "SRV_002"
    CONFIGURATION_ERROR = "SRV_003"


class AppException(HTTPException):
    """
    Base exception class for all application errors.
    Provides a consistent error response format.
    """

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(status_code=status_code, detail=message, headers=headers)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        result = {
            "success": False,
            "error": {
                "code": self.error_code,
                "message": self.message,
            }
        }
        if self.details:
            result["error"]["details"] = self.details
        return result


# ==================== Authentication Exceptions ====================

class UnauthorizedException(AppException):
    """User is not authenticated."""

    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.UNAUTHORIZED,
            message=message,
            details=details,
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidTokenException(AppException):
    """Token is invalid or malformed."""

    def __init__(self, message: str = "Invalid token", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.INVALID_TOKEN,
            message=message,
            details=details,
            headers={"WWW-Authenticate": "Bearer"},
        )


class TokenExpiredException(AppException):
    """Token has expired."""

    def __init__(self, message: str = "Token has expired", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.TOKEN_EXPIRED,
            message=message,
            details=details,
            headers={"WWW-Authenticate": "Bearer"},
        )


class TokenRevokedException(AppException):
    """Token has been revoked (e.g., user logged out)."""

    def __init__(self, message: str = "Token has been revoked", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.TOKEN_REVOKED,
            message=message,
            details=details,
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidCredentialsException(AppException):
    """Invalid username or password."""

    def __init__(self, message: str = "Invalid username or password", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.INVALID_CREDENTIALS,
            message=message,
            details=details,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AccountDisabledException(AppException):
    """User account is disabled."""

    def __init__(self, message: str = "Account is disabled", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.ACCOUNT_DISABLED,
            message=message,
            details=details,
        )


# ==================== Authorization Exceptions ====================

class ForbiddenException(AppException):
    """User does not have permission to access this resource."""

    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=ErrorCode.FORBIDDEN,
            message=message,
            details=details,
        )


# ==================== Resource Exceptions ====================

class NotFoundException(AppException):
    """Resource not found."""

    def __init__(self, resource: str = "Resource", resource_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with id '{resource_id}' not found"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message=message,
            details=details,
        )


class UserNotFoundException(NotFoundException):
    """User not found."""

    def __init__(self, user_id: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            resource="User",
            resource_id=str(user_id) if user_id else None,
            details=details,
        )
        self.error_code = ErrorCode.USER_NOT_FOUND


class DocumentNotFoundException(NotFoundException):
    """Document not found."""

    def __init__(self, document_id: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            resource="Document",
            resource_id=str(document_id) if document_id else None,
            details=details,
        )
        self.error_code = ErrorCode.DOCUMENT_NOT_FOUND


class AgentNotFoundException(NotFoundException):
    """Agent not found."""

    def __init__(self, agent_id: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            resource="Agent",
            resource_id=str(agent_id) if agent_id else None,
            details=details,
        )
        self.error_code = ErrorCode.AGENT_NOT_FOUND


class ProjectNotFoundException(NotFoundException):
    """Project not found."""

    def __init__(self, project_id: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            resource="Project",
            resource_id=str(project_id) if project_id else None,
            details=details,
        )
        self.error_code = ErrorCode.PROJECT_NOT_FOUND


class ConversationNotFoundException(NotFoundException):
    """Conversation not found."""

    def __init__(self, conversation_id: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            resource="Conversation",
            resource_id=str(conversation_id) if conversation_id else None,
            details=details,
        )
        self.error_code = ErrorCode.CONVERSATION_NOT_FOUND


# ==================== Validation Exceptions ====================

class ValidationException(AppException):
    """Validation error."""

    def __init__(self, message: str = "Validation error", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code=ErrorCode.VALIDATION_ERROR,
            message=message,
            details=details,
        )


class DuplicateEntryException(AppException):
    """Duplicate entry (e.g., email already exists)."""

    def __init__(self, field: str = "entry", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code=ErrorCode.DUPLICATE_ENTRY,
            message=f"This {field} is already in use",
            details=details,
        )


class InvalidFileTypeException(AppException):
    """Invalid file type."""

    def __init__(self, allowed_types: Optional[list] = None, details: Optional[Dict[str, Any]] = None):
        message = "Invalid file type"
        if allowed_types:
            message = f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
        super().__init__(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            error_code=ErrorCode.INVALID_FILE_TYPE,
            message=message,
            details=details,
        )


class FileTooLargeException(AppException):
    """File too large."""

    def __init__(self, max_size: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        message = "File too large"
        if max_size:
            message = f"File too large. Maximum size: {max_size}"
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            error_code=ErrorCode.FILE_TOO_LARGE,
            message=message,
            details=details,
        )


# ==================== Rate Limiting Exceptions ====================

class RateLimitExceededException(AppException):
    """Rate limit exceeded."""

    def __init__(self, retry_after: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        message = "Rate limit exceeded. Please try again later."
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message=message,
            details=details,
            headers=headers if headers else None,
        )


# ==================== External Service Exceptions ====================

class ExternalServiceException(AppException):
    """External service error."""

    def __init__(self, service: str = "External service", message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_message = message or f"{service} is temporarily unavailable"
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message=error_message,
            details=details,
        )


class AIServiceException(ExternalServiceException):
    """AI service error."""

    def __init__(self, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            service="AI service",
            message=message,
            details=details,
        )
        self.error_code = ErrorCode.AI_SERVICE_ERROR


class PDFParseException(ExternalServiceException):
    """PDF parsing error."""

    def __init__(self, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            service="PDF parser",
            message=message or "Failed to parse PDF file",
            details=details,
        )
        self.error_code = ErrorCode.PDF_PARSE_ERROR


# ==================== Server Exceptions ====================

class InternalServerException(AppException):
    """Internal server error."""

    def __init__(self, message: str = "An unexpected error occurred", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.INTERNAL_ERROR,
            message=message,
            details=details,
        )


class DatabaseException(AppException):
    """Database error."""

    def __init__(self, message: str = "Database error", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=ErrorCode.DATABASE_ERROR,
            message=message,
            details=details,
        )
