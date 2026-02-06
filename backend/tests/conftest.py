"""
Pytest configuration and shared fixtures for PyJOAL tests.

IMPORTANT: This file sets environment variables BEFORE importing app modules
to satisfy pydantic-settings requirements.
"""
import os
import sys

# Centralized test secret — all tests should reference this constant
TEST_SECRET_TOKEN = "test-secret-token"

# Set required environment variables BEFORE any app imports
os.environ.setdefault("SECRET_TOKEN", TEST_SECRET_TOKEN)
os.environ.setdefault("UI_PATH_PREFIX", "/test")
os.environ.setdefault("CONFIG_DIR", "/tmp/pyjoal_test/config")
os.environ.setdefault("TORRENTS_DIR", "/tmp/pyjoal_test/torrents")
os.environ.setdefault("CLIENTS_DIR", "/tmp/pyjoal_test/clients")

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app"""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create authentication headers for protected endpoints"""
    return {"X-API-Token": TEST_SECRET_TOKEN}


@pytest.fixture
def invalid_auth_headers():
    """Create invalid authentication headers for testing auth failures"""
    return {"X-API-Token": "invalid-token"}
