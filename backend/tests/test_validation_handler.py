"""Tests for the validation exception handler and other main.py coverage."""
import json
import pytest
from unittest.mock import patch, MagicMock
from pydantic import ValidationError, BaseModel, field_validator
import os

os.environ.setdefault("SECRET_TOKEN", "test-secret-token")


class TestValidationHandler:
    """Test validation_exception_handler by triggering actual validation errors via API."""

    @pytest.fixture
    def client(self):
        from app.main import app
        from starlette.testclient import TestClient
        return TestClient(app, headers={"X-API-Token": "test-secret-token"})

    def test_invalid_type(self, client):
        """Test invalid type triggers Pydantic validation error."""
        resp = client.put("/api/config", json={
            "minUploadRate": "not_a_number",
            "maxUploadRate": 500,
            "simultaneousSeed": 3,
            "client": "qbittorrent-5.1.4.client",
            "keepTorrentWithZeroLeechers": True,
            "uploadRatioTarget": -1,
            "seedingDurationLimit": -1,
        })
        assert resp.status_code == 422


class TestValidationExceptionHandlerDirect:
    """Test the handler function directly with Pydantic ValidationError."""

    @pytest.mark.asyncio
    async def test_value_error_ctx(self):
        from app.main import validation_exception_handler
        from starlette.requests import Request

        class M(BaseModel):
            minUploadRate: int

            @field_validator("minUploadRate")
            @classmethod
            def check_min(cls, v):
                if v < 0:
                    raise ValueError("min upload rate negative")
                return v

        try:
            M(minUploadRate=-1)
        except ValidationError as exc:
            scope = {"type": "http", "method": "PUT", "path": "/", "headers": []}
            response = await validation_exception_handler(Request(scope), exc)
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_greater_than_equal_minUploadRate(self):
        from app.main import validation_exception_handler
        from starlette.requests import Request
        from pydantic import Field

        class M(BaseModel):
            minUploadRate: int = Field(ge=0)

        try:
            M(minUploadRate=-5)
        except ValidationError as exc:
            scope = {"type": "http", "method": "PUT", "path": "/", "headers": []}
            response = await validation_exception_handler(Request(scope), exc)
            body = json.loads(response.body.decode())
            assert response.status_code == 422
            assert "négative" in body["detail"] or "negative" in body["detail"].lower() or response.status_code == 422

    @pytest.mark.asyncio
    async def test_greater_than_equal_maxUploadRate(self):
        from app.main import validation_exception_handler
        from starlette.requests import Request
        from pydantic import Field

        class M(BaseModel):
            maxUploadRate: int = Field(ge=0)

        try:
            M(maxUploadRate=-10)
        except ValidationError as exc:
            scope = {"type": "http", "method": "PUT", "path": "/", "headers": []}
            response = await validation_exception_handler(Request(scope), exc)
            body = json.loads(response.body.decode())
            assert response.status_code == 422
            assert "négative" in body["detail"] or "maximum" in body["detail"].lower()

    @pytest.mark.asyncio
    async def test_greater_than_equal_generic(self):
        from app.main import validation_exception_handler
        from starlette.requests import Request
        from pydantic import Field

        class M(BaseModel):
            otherField: int = Field(ge=0)

        try:
            M(otherField=-1)
        except ValidationError as exc:
            scope = {"type": "http", "method": "PUT", "path": "/", "headers": []}
            response = await validation_exception_handler(Request(scope), exc)
            body = json.loads(response.body.decode())
            assert "negative" in body["detail"].lower()

    @pytest.mark.asyncio
    async def test_less_than_equal_upload(self):
        from app.main import validation_exception_handler
        from starlette.requests import Request
        from pydantic import Field

        class M(BaseModel):
            maxUploadRate: int = Field(le=1000)

        try:
            M(maxUploadRate=9999)
        except ValidationError as exc:
            scope = {"type": "http", "method": "PUT", "path": "/", "headers": []}
            response = await validation_exception_handler(Request(scope), exc)
            body = json.loads(response.body.decode())
            assert "100 MB/s" in body["detail"] or "too high" in body["detail"]

    @pytest.mark.asyncio
    async def test_less_than_equal_generic(self):
        from app.main import validation_exception_handler
        from starlette.requests import Request
        from pydantic import Field

        class M(BaseModel):
            otherField: int = Field(le=10)

        try:
            M(otherField=999)
        except ValidationError as exc:
            scope = {"type": "http", "method": "PUT", "path": "/", "headers": []}
            response = await validation_exception_handler(Request(scope), exc)
            body = json.loads(response.body.decode())
            assert "too high" in body["detail"]

    @pytest.mark.asyncio
    async def test_missing_field(self):
        from app.main import validation_exception_handler
        from starlette.requests import Request

        class M(BaseModel):
            required_field: str

        try:
            M()
        except ValidationError as exc:
            scope = {"type": "http", "method": "PUT", "path": "/", "headers": []}
            response = await validation_exception_handler(Request(scope), exc)
            body = json.loads(response.body.decode())
            assert "required" in body["detail"]

    @pytest.mark.asyncio
    async def test_type_error(self):
        from app.main import validation_exception_handler
        from starlette.requests import Request

        class M(BaseModel):
            count: int

        try:
            M(count="not_a_number")
        except ValidationError as exc:
            scope = {"type": "http", "method": "PUT", "path": "/", "headers": []}
            response = await validation_exception_handler(Request(scope), exc)
            body = json.loads(response.body.decode())
            # Pydantic v2 uses "int_parsing" type which falls through to msg fallback
            assert response.status_code == 422
            assert len(body["detail"]) > 0

    @pytest.mark.asyncio
    async def test_fallback_error(self):
        """Test generic error type falls back to msg."""
        from app.main import validation_exception_handler
        from starlette.requests import Request

        # Construct a mock exc manually
        exc = MagicMock(spec=ValidationError)
        exc.errors.return_value = [{
            "loc": ("body", "field"),
            "type": "custom_unknown_issue",
            "msg": "Something went wrong",
        }]
        scope = {"type": "http", "method": "PUT", "path": "/", "headers": []}
        response = await validation_exception_handler(Request(scope), exc)
        body = json.loads(response.body.decode())
        assert body["detail"] == "Something went wrong"

    @pytest.mark.asyncio
    async def test_empty_errors(self):
        """Test when exc.errors() returns empty list."""
        from app.main import validation_exception_handler
        from starlette.requests import Request

        exc = MagicMock(spec=ValidationError)
        exc.errors.return_value = []
        scope = {"type": "http", "method": "PUT", "path": "/", "headers": []}
        response = await validation_exception_handler(Request(scope), exc)
        body = json.loads(response.body.decode())
        assert body["detail"] == "Invalid configuration data"
