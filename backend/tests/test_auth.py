"""
Tests for authentication module
"""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException

# Add the parent directory to the path so we can import app modules
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.auth import verify_token


@pytest.mark.asyncio
async def test_verify_token_valid_header():
    """Test valid token in header"""
    # Mock settings directly
    with patch('app.core.auth.settings') as mock_settings:
        mock_settings.SECRET_TOKEN = 'test-token'
        result = await verify_token(header_token='test-token')
        assert result == 'test-token'


@pytest.mark.asyncio
async def test_verify_token_valid_query():
    """Test valid token in query parameter"""
    with patch('app.core.auth.settings') as mock_settings:
        mock_settings.SECRET_TOKEN = 'test-token'
        result = await verify_token(header_token=None, query_token='test-token')
        assert result == 'test-token'


@pytest.mark.asyncio
async def test_verify_token_invalid():
    """Test invalid token"""
    with patch('app.core.auth.settings') as mock_settings:
        mock_settings.SECRET_TOKEN = 'test-token'
        with pytest.raises(HTTPException) as exc_info:
            await verify_token(header_token='wrong-token')
        assert exc_info.value.status_code == 401
        assert "Invalid authentication token" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_verify_token_missing():
    """Test missing token"""
    with patch('app.core.auth.settings') as mock_settings:
        mock_settings.SECRET_TOKEN = 'test-token'
        with pytest.raises(HTTPException) as exc_info:
            await verify_token(header_token=None, query_token=None)
        assert exc_info.value.status_code == 401
        assert "Missing authentication token" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_verify_token_header_priority():
    """Test that header token takes priority over query token"""
    with patch('app.core.auth.settings') as mock_settings:
        mock_settings.SECRET_TOKEN = 'correct-token'
        result = await verify_token(header_token='correct-token', query_token='wrong-token')
        assert result == 'correct-token'