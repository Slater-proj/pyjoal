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


def test_discretion_settings():
    """Test that discretion settings have valid defaults"""
    assert settings.ANNOUNCE_INTERVAL >= 15
    assert settings.ANNOUNCE_JITTER >= 0
    assert settings.MIN_STATS_UPDATE_INTERVAL >= 1
    assert isinstance(settings.ENABLE_SPEED_VARIATION, bool)
    assert 0 <= settings.SPEED_VARIATION_PERCENT <= 50


def test_announce_timing_logic():
    """Test that announce timing configuration is logical"""
    # Jitter shouldn't be larger than the base interval
    assert settings.ANNOUNCE_JITTER <= settings.ANNOUNCE_INTERVAL
    # Minimum interval should be reasonable
    assert settings.MIN_STATS_UPDATE_INTERVAL < settings.ANNOUNCE_INTERVAL
