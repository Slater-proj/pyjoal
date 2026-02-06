"""
Tests for config_manager module
"""
import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.services.config_manager import ConfigManager


class TestConfigManagerInit:
    """Tests for ConfigManager initialization"""

    def test_init_empty_config(self):
        cm = ConfigManager()
        assert cm.config == {}

    def test_get_returns_default(self):
        cm = ConfigManager()
        assert cm.get("nonexistent", "default_val") == "default_val"

    def test_get_returns_value(self):
        cm = ConfigManager()
        cm._config = {"key": "value"}
        assert cm.get("key") == "value"

    def test_update_dict(self):
        cm = ConfigManager()
        cm._config = {"a": 1}
        cm.update_dict({"b": 2, "a": 10})
        assert cm.config == {"a": 10, "b": 2}


class TestConfigManagerValidation:
    """Tests for validate method"""

    def test_valid_config(self):
        cm = ConfigManager()
        # Should not raise
        cm.validate({"minUploadRate": 30, "maxUploadRate": 160})

    def test_invalid_min_upload_rate_negative(self):
        cm = ConfigManager()
        with pytest.raises(ValueError, match="minUploadRate"):
            cm.validate({"minUploadRate": -5})

    def test_invalid_min_upload_rate_string(self):
        cm = ConfigManager()
        with pytest.raises(ValueError, match="minUploadRate"):
            cm.validate({"minUploadRate": "fast"})

    def test_invalid_max_upload_rate(self):
        cm = ConfigManager()
        with pytest.raises(ValueError, match="maxUploadRate"):
            cm.validate({"maxUploadRate": -10})

    def test_upload_ratio_target_valid(self):
        cm = ConfigManager()
        cm.validate({"uploadRatioTarget": -1})  # disabled
        cm.validate({"uploadRatioTarget": 0})
        cm.validate({"uploadRatioTarget": 2.5})

    def test_upload_ratio_target_invalid(self):
        cm = ConfigManager()
        with pytest.raises(ValueError, match="uploadRatioTarget"):
            cm.validate({"uploadRatioTarget": "abc"})

    def test_seeding_duration_limit_valid(self):
        cm = ConfigManager()
        cm.validate({"seedingDurationLimit": -1})  # disabled
        cm.validate({"seedingDurationLimit": 0})
        cm.validate({"seedingDurationLimit": 3600})

    def test_seeding_duration_limit_invalid(self):
        cm = ConfigManager()
        with pytest.raises(ValueError, match="seedingDurationLimit"):
            cm.validate({"seedingDurationLimit": "never"})


class TestConfigManagerLoad:
    """Tests for load method"""

    @pytest.mark.asyncio
    async def test_load_creates_default_when_no_file(self, tmp_path):
        cm = ConfigManager()
        with patch("app.services.config_manager.settings") as mock_settings:
            mock_settings.CONFIG_DIR = tmp_path
            mock_settings.MIN_UPLOAD_RATE = 30
            mock_settings.MAX_UPLOAD_RATE = 160
            mock_settings.SIMULTANEOUS_SEED = 20
            mock_settings.DEFAULT_CLIENT = "qbittorrent-5.1.4.client"
            mock_settings.KEEP_TORRENT_WITH_ZERO_LEECHERS = True
            mock_settings.UPLOAD_RATIO_TARGET = -1.0
            mock_settings.SEEDING_DURATION_LIMIT = -1.0
            mock_settings.ANNOUNCE_INTERVAL = 30
            mock_settings.ANNOUNCE_JITTER = 30
            mock_settings.MIN_STATS_UPDATE_INTERVAL = 3
            mock_settings.ENABLE_SPEED_VARIATION = True
            mock_settings.SPEED_VARIATION_PERCENT = 20
            mock_settings.SEEDING_ONLY_MODE = True
            mock_settings.PAUSE_DURATION_MIN = 30
            mock_settings.PAUSE_DURATION_MAX = 180
            mock_settings.REDUCED_SPEED_DURATION_MIN = 60
            mock_settings.REDUCED_SPEED_DURATION_MAX = 240
            mock_settings.STATE_CHANGE_INTERVAL_MIN = 2
            mock_settings.STATE_CHANGE_INTERVAL_MAX = 8
            mock_settings.REDUCED_SPEED_KBPS = 5
            mock_settings.PEER_SPEED_TIERS_ENABLED = True
            mock_settings.PEER_TIER1_MAX_PEERS = 20
            mock_settings.PEER_TIER1_SPEED_PERCENT = 15
            mock_settings.PEER_TIER2_MAX_PEERS = 50
            mock_settings.PEER_TIER2_SPEED_PERCENT = 35
            mock_settings.PEER_TIER3_MAX_PEERS = 100
            mock_settings.PEER_TIER3_SPEED_PERCENT = 60
            mock_settings.PEER_TIER4_MAX_PEERS = 200
            mock_settings.PEER_TIER4_SPEED_PERCENT = 80
            mock_settings.PEER_TIER5_SPEED_PERCENT = 100

            await cm.load()

        assert cm.config["minUploadRate"] == 30
        assert cm.config["maxUploadRate"] == 160
        # Check file was created
        assert (tmp_path / "config.json").exists()

    @pytest.mark.asyncio
    async def test_load_reads_existing_file(self, tmp_path):
        config_data = {"minUploadRate": 50, "maxUploadRate": 200}
        (tmp_path / "config.json").write_text(json.dumps(config_data))

        cm = ConfigManager()
        with patch("app.services.config_manager.settings") as mock_settings:
            mock_settings.CONFIG_DIR = tmp_path
            await cm.load()

        assert cm.config == config_data


class TestConfigManagerSave:
    """Tests for save method"""

    @pytest.mark.asyncio
    async def test_save_writes_file(self, tmp_path):
        cm = ConfigManager()
        cm._config = {"minUploadRate": 42}

        with patch("app.services.config_manager.settings") as mock_settings:
            mock_settings.CONFIG_DIR = tmp_path
            await cm.save()

        saved = json.loads((tmp_path / "config.json").read_text())
        assert saved["minUploadRate"] == 42

    @pytest.mark.asyncio
    async def test_save_creates_parent_dir(self, tmp_path):
        cm = ConfigManager()
        cm._config = {"key": "val"}
        nested_dir = tmp_path / "sub" / "dir"

        with patch("app.services.config_manager.settings") as mock_settings:
            mock_settings.CONFIG_DIR = nested_dir
            await cm.save()

        assert (nested_dir / "config.json").exists()


class TestDefaultConfig:
    """Tests for _default_config static method"""

    def test_default_config_has_required_keys(self):
        with patch("app.services.config_manager.settings") as mock_settings:
            mock_settings.MIN_UPLOAD_RATE = 30
            mock_settings.MAX_UPLOAD_RATE = 160
            mock_settings.SIMULTANEOUS_SEED = 20
            mock_settings.DEFAULT_CLIENT = "qbittorrent-5.1.4.client"
            mock_settings.KEEP_TORRENT_WITH_ZERO_LEECHERS = True
            mock_settings.UPLOAD_RATIO_TARGET = -1.0
            mock_settings.SEEDING_DURATION_LIMIT = -1.0
            mock_settings.ANNOUNCE_INTERVAL = 30
            mock_settings.ANNOUNCE_JITTER = 30
            mock_settings.MIN_STATS_UPDATE_INTERVAL = 3
            mock_settings.ENABLE_SPEED_VARIATION = True
            mock_settings.SPEED_VARIATION_PERCENT = 20
            mock_settings.SEEDING_ONLY_MODE = True

            config = ConfigManager._default_config()

        expected_keys = [
            "minUploadRate", "maxUploadRate", "simultaneousSeed",
            "client", "keepTorrentWithZeroLeechers", "uploadRatioTarget",
            "seedingDurationLimit", "announceInterval", "announceJitter",
            "minStatsUpdateInterval", "enableSpeedVariation",
            "speedVariationPercent", "seedingOnlyMode",
        ]
        for key in expected_keys:
            assert key in config, f"Missing key: {key}"
