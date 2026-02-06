"""
Tests for discretion settings configuration
"""
from app.models.schemas import ConfigSchema
import pytest


def test_config_schema_with_discretion_settings():
    """Test that ConfigSchema accepts all discretion settings"""
    config_data = {
        "minUploadRate": 50,
        "maxUploadRate": 200,
        "simultaneousSeed": 15,
        "client": "qbittorrent-4.6.0.client",
        "keepTorrentWithZeroLeechers": True,
        "uploadRatioTarget": 2.0,
        "seedingDurationLimit": 24.0,
        # Discretion settings
        "announceInterval": 60,
        "announceJitter": 20,
        "minStatsUpdateInterval": 4,
        "enableSpeedVariation": True,
        "speedVariationPercent": 15
    }
    
    config = ConfigSchema(**config_data)
    
    assert config.minUploadRate == 50
    assert config.maxUploadRate == 200
    assert config.announceInterval == 60
    assert config.announceJitter == 20
    assert config.minStatsUpdateInterval == 4
    assert config.enableSpeedVariation == True
    assert config.speedVariationPercent == 15


def test_discretion_settings_validation():
    """Test validation of discretion settings bounds"""
    base_config = {
        "minUploadRate": 30,
        "maxUploadRate": 160,
        "simultaneousSeed": 20,
        "client": "qbittorrent-4.6.0.client",
        "keepTorrentWithZeroLeechers": True,
        "uploadRatioTarget": -1.0,
        "seedingDurationLimit": -1.0,
    }
    
    # Test announce interval bounds
    with pytest.raises(ValueError):
        ConfigSchema(**{**base_config, "announceInterval": 10})  # Too low
    
    with pytest.raises(ValueError):
        ConfigSchema(**{**base_config, "announceInterval": 400})  # Too high
    
    # Test jitter bounds
    with pytest.raises(ValueError):
        ConfigSchema(**{**base_config, "announceJitter": -1})  # Negative
    
    with pytest.raises(ValueError):
        ConfigSchema(**{**base_config, "announceJitter": 200})  # Too high
    
    # Test stats update interval bounds
    with pytest.raises(ValueError):
        ConfigSchema(**{**base_config, "minStatsUpdateInterval": 0})  # Too low
    
    with pytest.raises(ValueError):
        ConfigSchema(**{**base_config, "minStatsUpdateInterval": 35})  # Too high
    
    # Test speed variation bounds
    with pytest.raises(ValueError):
        ConfigSchema(**{**base_config, "speedVariationPercent": -1})  # Negative
    
    with pytest.raises(ValueError):
        ConfigSchema(**{**base_config, "speedVariationPercent": 60})  # Too high


def test_discretion_settings_defaults():
    """Test that discretion settings have proper defaults"""
    config_data = {
        "minUploadRate": 30,
        "maxUploadRate": 160,
        "simultaneousSeed": 20,
        "client": "qbittorrent-4.6.0.client",
        "keepTorrentWithZeroLeechers": True,
        "uploadRatioTarget": -1.0,
        "seedingDurationLimit": -1.0,
    }
    
    config = ConfigSchema(**config_data)
    
    # Check that defaults are applied
    assert config.announceInterval == 30
    assert config.announceJitter == 30
    assert config.minStatsUpdateInterval == 3
    assert config.enableSpeedVariation == True
    assert config.speedVariationPercent == 20


if __name__ == "__main__":
    pytest.main([__file__])