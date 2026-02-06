"""
Config Manager
Handles loading, saving, and validating seeder configuration
"""
import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Dict

from app.core.config import settings

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages application configuration persistence and validation"""

    def __init__(self):
        self._config: Dict = {}

    @property
    def config(self) -> Dict:
        return self._config

    def get(self, key: str, default=None):
        return self._config.get(key, default)

    def update_dict(self, new_values: Dict):
        """Update internal dict (caller handles persistence)"""
        self._config.update(new_values)

    async def load(self):
        """Load configuration from file"""
        config_file = settings.CONFIG_DIR / "config.json"

        if config_file.exists():
            logger.debug(f"📝 Loading config from: {config_file}")
            with open(config_file, "r", encoding="utf-8") as f:
                self._config = json.load(f)
            logger.debug(f"   Config loaded: {self._config}")
        else:
            logger.info("🆕 Creating default configuration")
            self._config = self._default_config()
            await self.save()
            logger.info(f"   Default config created: {self._config}")

    async def save(self):
        """Save configuration to file atomically"""
        config_file = settings.CONFIG_DIR / "config.json"
        temp_file_path = None

        try:
            config_file.parent.mkdir(parents=True, exist_ok=True)

            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=config_file.parent,
                delete=False,
            ) as temp_file:
                json.dump(self._config, temp_file, indent=2)
                temp_file.flush()
                temp_file_path = temp_file.name

            shutil.move(temp_file_path, config_file)
            logger.debug(f"✅ Config saved to {config_file}")

        except Exception as e:
            logger.error(f"❌ Failed to save config to {config_file}: {e}")
            try:
                if temp_file_path:
                    Path(temp_file_path).unlink(missing_ok=True)
            except Exception:
                pass
            raise e

    def validate(self, new_config: Dict):
        """Validate configuration values, raises ValueError on invalid input"""
        if "minUploadRate" in new_config:
            rate = new_config["minUploadRate"]
            if not isinstance(rate, (int, float)) or rate < 0:
                raise ValueError(f"Invalid minUploadRate: {rate} (must be >= 0)")

        if "maxUploadRate" in new_config:
            rate = new_config["maxUploadRate"]
            if not isinstance(rate, (int, float)) or rate < 0:
                raise ValueError(f"Invalid maxUploadRate: {rate} (must be >= 0)")

        if "uploadRatioTarget" in new_config:
            ratio = new_config["uploadRatioTarget"]
            if not isinstance(ratio, (int, float)) or (ratio < -1 and ratio != -1):
                raise ValueError(f"Invalid uploadRatioTarget: {ratio} (must be -1 or >= 0)")

        if "seedingDurationLimit" in new_config:
            duration = new_config["seedingDurationLimit"]
            if not isinstance(duration, (int, float)) or (duration < -1 and duration != -1):
                raise ValueError(f"Invalid seedingDurationLimit: {duration} (must be -1 or >= 0)")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _default_config() -> Dict:
        return {
            "minUploadRate": settings.MIN_UPLOAD_RATE,
            "maxUploadRate": settings.MAX_UPLOAD_RATE,
            "simultaneousSeed": settings.SIMULTANEOUS_SEED,
            "client": settings.DEFAULT_CLIENT,
            "keepTorrentWithZeroLeechers": settings.KEEP_TORRENT_WITH_ZERO_LEECHERS,
            "uploadRatioTarget": settings.UPLOAD_RATIO_TARGET,
            "seedingDurationLimit": settings.SEEDING_DURATION_LIMIT,
            # Discretion settings
            "announceInterval": settings.ANNOUNCE_INTERVAL,
            "announceJitter": settings.ANNOUNCE_JITTER,
            "minStatsUpdateInterval": settings.MIN_STATS_UPDATE_INTERVAL,
            "enableSpeedVariation": settings.ENABLE_SPEED_VARIATION,
            "speedVariationPercent": settings.SPEED_VARIATION_PERCENT,
            # Torrent Behavior Mode
            "seedingOnlyMode": settings.SEEDING_ONLY_MODE,
        }
