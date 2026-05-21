"""
Tests for the AppException hierarchy.

Confirms each subclass sets the right status code + error code, and that
to_dict() serialises into the JSON envelope the error handler emits.
"""
import pytest
from fastapi import status

from app.core.exceptions import (
    AccountDisabledException,
    AgentNotFoundException,
    AIServiceException,
    AppException,
    ConversationNotFoundException,
    DatabaseException,
    DocumentNotFoundException,
    DuplicateEntryException,
    ErrorCode,
    ExternalServiceException,
    FileTooLargeException,
    ForbiddenException,
    InternalServerException,
    InvalidCredentialsException,
    InvalidFileTypeException,
    InvalidTokenException,
    NotFoundException,
    PDFParseException,
    ProjectNotFoundException,
    RateLimitExceededException,
    TokenExpiredException,
    TokenRevokedException,
    UnauthorizedException,
    UserNotFoundException,
    ValidationException,
)


# ----- AppException base behaviour -----

class TestAppExceptionBase:
    def test_to_dict_contains_envelope(self):
        exc = AppException(status_code=400, error_code="X_1", message="boom")
        d = exc.to_dict()
        assert d["success"] is False
        assert d["error"]["code"] == "X_1"
        assert d["error"]["message"] == "boom"

    def test_to_dict_includes_details_when_present(self):
        exc = AppException(status_code=400, error_code="X_1", message="boom", details={"field": "x"})
        d = exc.to_dict()
        assert d["error"]["details"] == {"field": "x"}

    def test_to_dict_omits_details_when_empty(self):
        exc = AppException(status_code=400, error_code="X_1", message="boom")
        d = exc.to_dict()
        assert "details" not in d["error"]


# ----- Auth family -----

class TestAuthExceptions:
    @pytest.mark.parametrize("cls,code,status_code", [
        (UnauthorizedException,     ErrorCode.UNAUTHORIZED,         status.HTTP_401_UNAUTHORIZED),
        (InvalidTokenException,     ErrorCode.INVALID_TOKEN,        status.HTTP_401_UNAUTHORIZED),
        (TokenExpiredException,     ErrorCode.TOKEN_EXPIRED,        status.HTTP_401_UNAUTHORIZED),
        (TokenRevokedException,     ErrorCode.TOKEN_REVOKED,        status.HTTP_401_UNAUTHORIZED),
        (InvalidCredentialsException, ErrorCode.INVALID_CREDENTIALS, status.HTTP_401_UNAUTHORIZED),
        (AccountDisabledException,  ErrorCode.ACCOUNT_DISABLED,     status.HTTP_403_FORBIDDEN),
    ])
    def test_status_and_code(self, cls, code, status_code):
        exc = cls()
        assert exc.status_code == status_code
        assert exc.error_code == code

    def test_unauthorized_sets_www_authenticate(self):
        exc = UnauthorizedException()
        assert exc.headers["WWW-Authenticate"] == "Bearer"


# ----- Authorization -----

class TestForbidden:
    def test_status_code_and_default_message(self):
        exc = ForbiddenException()
        assert exc.status_code == status.HTTP_403_FORBIDDEN
        assert exc.error_code == ErrorCode.FORBIDDEN


# ----- Resource not-found family -----

class TestResourceNotFound:
    def test_not_found_with_id_in_message(self):
        exc = NotFoundException(resource="Thing", resource_id="42")
        assert exc.status_code == 404
        assert "Thing" in exc.message and "42" in exc.message

    def test_not_found_without_id_default_message(self):
        exc = NotFoundException()
        assert "not found" in exc.message.lower()

    @pytest.mark.parametrize("cls,expected_code,resource_id", [
        (UserNotFoundException,         ErrorCode.USER_NOT_FOUND,         7),
        (DocumentNotFoundException,     ErrorCode.DOCUMENT_NOT_FOUND,     9),
        (AgentNotFoundException,        ErrorCode.AGENT_NOT_FOUND,        3),
        (ProjectNotFoundException,      ErrorCode.PROJECT_NOT_FOUND,      11),
        (ConversationNotFoundException, ErrorCode.CONVERSATION_NOT_FOUND, 17),
    ])
    def test_resource_subclass_overrides_error_code(self, cls, expected_code, resource_id):
        # Each subclass accepts a single positional id arg of differing name
        # so build via keyword to be explicit.
        exc = cls.__new__(cls)
        cls.__init__(exc, resource_id)
        assert exc.error_code == expected_code
        assert exc.status_code == 404


# ----- Validation -----

class TestValidationErrors:
    def test_validation_exception_status_422(self):
        exc = ValidationException("bad")
        assert exc.status_code == 422
        assert exc.error_code == ErrorCode.VALIDATION_ERROR

    def test_duplicate_entry_status_409(self):
        exc = DuplicateEntryException(field="email")
        assert exc.status_code == 409
        assert "email" in exc.message

    def test_invalid_file_type_lists_allowed(self):
        exc = InvalidFileTypeException(allowed_types=["pdf", "md"])
        assert exc.status_code == 415
        assert "pdf" in exc.message

    def test_invalid_file_type_default_message(self):
        exc = InvalidFileTypeException()
        assert "Invalid file type" in exc.message

    def test_file_too_large_with_size(self):
        exc = FileTooLargeException(max_size="10MB")
        assert exc.status_code == 413
        assert "10MB" in exc.message

    def test_file_too_large_default(self):
        exc = FileTooLargeException()
        assert "too large" in exc.message.lower()


# ----- Rate limiting -----

class TestRateLimit:
    def test_rate_limit_retry_after_header(self):
        exc = RateLimitExceededException(retry_after=30)
        assert exc.status_code == 429
        assert exc.headers["Retry-After"] == "30"

    def test_rate_limit_no_retry_after_means_no_header(self):
        exc = RateLimitExceededException()
        assert exc.headers is None


# ----- External services -----

class TestExternalServices:
    def test_external_default_status_503(self):
        exc = ExternalServiceException(service="X")
        assert exc.status_code == 503
        assert "X" in exc.message

    def test_ai_service_overrides_code(self):
        exc = AIServiceException()
        assert exc.error_code == ErrorCode.AI_SERVICE_ERROR
        assert exc.status_code == 503

    def test_pdf_parse_overrides_code(self):
        exc = PDFParseException()
        assert exc.error_code == ErrorCode.PDF_PARSE_ERROR


# ----- Server errors -----

class TestServerErrors:
    def test_internal_server_default(self):
        exc = InternalServerException()
        assert exc.status_code == 500
        assert exc.error_code == ErrorCode.INTERNAL_ERROR

    def test_database_exception(self):
        exc = DatabaseException("oops")
        assert exc.status_code == 500
        assert exc.error_code == ErrorCode.DATABASE_ERROR
