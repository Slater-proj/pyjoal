"""
Basic test for configuration
"""
import pytest
from app.core.config import settings


def test_settings_initialization():
    """Test that settings can be initialized"""
    assert settings.PORT >= 0
    assert settings.MIN_UPLOAD_RATE >= 0
    assert settings.MAX_UPLOAD_RATE >= settings.MIN_UPLOAD_RATE


def test_directories_exist():
    """Test that required directories exist"""
    assert settings.CONFIG_DIR.exists()
    assert settings.TORRENTS_DIR.exists()
    assert settings.CLIENTS_DIR.exists()
