"""
Tests for authentication module
"""
import pytest
from fastapi import HTTPException
from unittest.mock import patch

from app.core.auth import verify_token
from app.core.config import settings


@pytest.mark.asyncio
async def test_verify_token_valid_header():
    """Test valid token in header"""
    with patch.object(settings, 'SECRET_TOKEN', 'test-token'):
        result = await verify_token(header_token='test-token')
        assert result == 'test-token'


@pytest.mark.asyncio
async def test_verify_token_valid_query():
    """Test valid token in query parameter"""
    with patch.object(settings, 'SECRET_TOKEN', 'test-token'):
        result = await verify_token(query_token='test-token')
        assert result == 'test-token'


@pytest.mark.asyncio
async def test_verify_token_invalid():
    """Test invalid token"""
    with patch.object(settings, 'SECRET_TOKEN', 'test-token'):
        with pytest.raises(HTTPException) as exc_info:
            await verify_token(header_token='wrong-token')
        assert exc_info.value.status_code == 401
        assert "Invalid authentication token" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_verify_token_missing():
    """Test missing token"""
    with patch.object(settings, 'SECRET_TOKEN', 'test-token'):
        with pytest.raises(HTTPException) as exc_info:
            await verify_token()
        assert exc_info.value.status_code == 401
        assert "Missing authentication token" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_verify_token_header_priority():
    """Test that header token takes priority over query token"""
    with patch.object(settings, 'SECRET_TOKEN', 'correct-token'):
        result = await verify_token(header_token='correct-token', query_token='wrong-token')
        assert result == 'correct-token'