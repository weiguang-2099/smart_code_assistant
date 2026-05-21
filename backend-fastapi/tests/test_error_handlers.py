"""
Tests for the global exception handlers + ErrorResponse helpers.

End-to-end through a minimal FastAPI app so each branch of the handler is
actually exercised in the request pipeline.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.error_handlers import ErrorResponse, register_exception_handlers
from app.core.exceptions import (
    ErrorCode,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)


@pytest.fixture
def app():
    """A tiny app whose routes deliberately raise each kind of exception."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/app-exc")
    async def raises_app_exc():
        raise NotFoundException(resource="Item", resource_id="42")

    @app.get("/unauth")
    async def raises_unauth():
        raise UnauthorizedException()

    @app.get("/validation")
    async def raises_validation():
        raise ValidationException("bad input")

    @app.get("/duplicate")
    async def raises_duplicate():
        raise IntegrityError(
            statement="INSERT ...",
            params={},
            orig=Exception("Duplicate entry 'x' for key 'users.email'"),
        )

    @app.get("/integrity-other")
    async def raises_integrity_other():
        raise IntegrityError(
            statement="UPDATE ...",
            params={},
            orig=Exception("FOREIGN KEY constraint failed"),
        )

    @app.get("/sqlalchemy")
    async def raises_sqla():
        raise SQLAlchemyError("connection lost")

    @app.get("/unhandled")
    async def raises_random():
        raise RuntimeError("boom")

    @app.post("/echo")
    async def echo(payload: dict):
        return payload

    return app


@pytest.fixture
def client(app):
    # raise_server_exceptions=False lets the global 500 handler convert RuntimeError
    # into a JSONResponse rather than re-raising into the test runner.
    return TestClient(app, raise_server_exceptions=False)


class TestAppExceptionHandler:
    def test_app_exception_serialised_with_envelope(self, client):
        r = client.get("/app-exc")
        assert r.status_code == 404
        body = r.json()
        assert body["success"] is False
        assert body["error"]["code"] == ErrorCode.NOT_FOUND
        assert "Item" in body["error"]["message"]
        assert "42" in body["error"]["message"]

    def test_unauthorized_emits_www_authenticate_header(self, client):
        r = client.get("/unauth")
        assert r.status_code == 401
        assert r.headers.get("WWW-Authenticate") == "Bearer"

    def test_validation_exception(self, client):
        r = client.get("/validation")
        assert r.status_code == 422
        assert r.json()["error"]["code"] == ErrorCode.VALIDATION_ERROR


class TestSQLAlchemyHandlers:
    def test_duplicate_entry_mapped_to_409(self, client):
        r = client.get("/duplicate")
        assert r.status_code == 409
        assert r.json()["error"]["code"] == ErrorCode.DUPLICATE_ENTRY

    def test_other_integrity_error_returns_500(self, client):
        r = client.get("/integrity-other")
        assert r.status_code == 500
        assert r.json()["error"]["code"] == ErrorCode.DATABASE_ERROR

    def test_general_sqlalchemy_error_returns_500(self, client):
        r = client.get("/sqlalchemy")
        assert r.status_code == 500
        assert r.json()["error"]["code"] == ErrorCode.DATABASE_ERROR


class TestGenericExceptionHandler:
    def test_unhandled_exception_mapped_to_500_no_leak(self, client):
        r = client.get("/unhandled")
        assert r.status_code == 500
        body = r.json()
        assert body["error"]["code"] == ErrorCode.INTERNAL_ERROR
        # Must not leak the raw exception message
        assert "boom" not in body["error"]["message"]


class TestRequestValidationHandler:
    def test_pydantic_validation_returns_envelope(self, client):
        # FastAPI raises RequestValidationError when payload is malformed.
        # Sending non-dict to /echo (which declares dict) triggers it.
        r = client.post("/echo", content="not-json", headers={"Content-Type": "application/json"})
        assert r.status_code == 422
        body = r.json()
        assert body["error"]["code"] == ErrorCode.VALIDATION_ERROR
        assert "errors" in body["error"]["details"]


# ----- ErrorResponse helpers (pure dict builders) -----

class TestErrorResponseHelpers:
    def test_not_found_includes_id(self):
        d = ErrorResponse.not_found("User", 7)
        assert d["error"]["code"] == ErrorCode.NOT_FOUND
        assert "7" in d["error"]["message"]

    def test_not_found_without_id(self):
        d = ErrorResponse.not_found("Item")
        assert "Item not found" == d["error"]["message"]

    def test_unauthorized_default(self):
        d = ErrorResponse.unauthorized()
        assert d["error"]["code"] == ErrorCode.UNAUTHORIZED

    def test_unauthorized_custom_message(self):
        d = ErrorResponse.unauthorized("custom msg")
        assert d["error"]["message"] == "custom msg"

    def test_forbidden(self):
        d = ErrorResponse.forbidden()
        assert d["error"]["code"] == ErrorCode.FORBIDDEN

    def test_validation_error(self):
        d = ErrorResponse.validation_error([{"field": "x", "message": "required"}])
        assert d["error"]["code"] == ErrorCode.VALIDATION_ERROR
        assert d["error"]["details"]["errors"][0]["field"] == "x"

    def test_rate_limited(self):
        d = ErrorResponse.rate_limited(retry_after=30)
        assert d["error"]["details"]["retry_after"] == 30
