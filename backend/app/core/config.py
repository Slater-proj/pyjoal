"""
Application Configuration
Using Pydantic Settings for environment variable management
"""
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional, Any
from pathlib import Path


class Settings(BaseSettings):
    """Application settings"""
    
    # Server
    PORT: int = Field(default=8080, description="Server port")
    DEBUG: bool = Field(default=False, description="Debug mode")
    
    # Security
    SECRET_TOKEN: str = Field(..., description="Secret token for authentication")
    UI_PATH_PREFIX: str = Field(default="/", description="UI path prefix for obfuscation")
    
    # Paths (absolute paths for Docker compatibility)
    CONFIG_DIR: Path = Field(default=Path("/app/config"), description="Configuration directory")
    TORRENTS_DIR: Path = Field(default=Path("/app/torrents"), description="Torrents directory")
    CLIENTS_DIR: Path = Field(default=Path("/app/clients"), description="Clients directory")
    
    # BitTorrent Config
    MIN_UPLOAD_RATE: int = Field(default=30, description="Minimum upload rate (kB/s)")
    MAX_UPLOAD_RATE: int = Field(default=300, description="Maximum upload rate (kB/s)")
    SIMULTANEOUS_SEED: int = Field(default=20, description="Simultaneous seeds")
    KEEP_TORRENT_WITH_ZERO_LEECHERS: bool = Field(default=True, description="Keep torrents with no peers")
    UPLOAD_RATIO_TARGET: float = Field(default=-1.0, description="Upload ratio target (-1 = never remove)")
    SEEDING_DURATION_LIMIT: float = Field(default=-1.0, description="Seeding duration limit in hours (-1 = no limit)")
    DEFAULT_CLIENT: str = Field(default="qbittorrent-5.1.4.client", description="Default client file")
    
    # Proxy
    HTTP_PROXY_HOST: Optional[str] = Field(default=None, description="HTTP proxy host")
    HTTP_PROXY_PORT: Optional[int] = Field(default=None, description="HTTP proxy port")
    
    @field_validator('HTTP_PROXY_HOST', 'HTTP_PROXY_PORT', mode='before')
    @classmethod
    def empty_str_to_none(cls, v: Any) -> Any:
        """Convert empty strings to None"""
        if v == '' or v is None:
            return None
        return v
    
    # Announce intervals (defaults, can be overridden in config) - Optimisé pour la réactivité
    ANNOUNCE_INTERVAL: int = Field(default=15, description="Base announce interval (seconds)")
    ANNOUNCE_JITTER: int = Field(default=15, description="Random jitter for announces (seconds)")
    
    # Discretion Settings - Optimisé pour les mises à jour
    MIN_STATS_UPDATE_INTERVAL: int = Field(default=2, description="Minimum interval between stats updates (seconds)")
    ENABLE_SPEED_VARIATION: bool = Field(default=True, description="Enable realistic speed variations")
    SPEED_VARIATION_PERCENT: int = Field(default=20, description="Speed variation percentage (±%)")
    
    # Torrent Behavior Mode
    SEEDING_ONLY_MODE: bool = Field(default=True, description="Pure seeding mode (true) vs download simulation mode (false)")
    
    # 🎭 Realistic Behavior Timing Settings (more human-like patterns)
    # Pause duration: how long a torrent stays paused (in minutes)
    PAUSE_DURATION_MIN: int = Field(default=30, description="Minimum pause duration (minutes)")
    PAUSE_DURATION_MAX: int = Field(default=180, description="Maximum pause duration (minutes) - up to 3 hours")
    
    # Reduced speed duration: how long a torrent stays in reduced mode (in minutes)
    REDUCED_SPEED_DURATION_MIN: int = Field(default=60, description="Minimum reduced speed duration (minutes)")
    REDUCED_SPEED_DURATION_MAX: int = Field(default=240, description="Maximum reduced speed duration (minutes) - up to 4 hours")
    
    # State change interval: how often state (pause/normal/reduced) changes (in hours)
    STATE_CHANGE_INTERVAL_MIN: int = Field(default=2, description="Minimum interval between state changes (hours)")
    STATE_CHANGE_INTERVAL_MAX: int = Field(default=8, description="Maximum interval between state changes (hours)")
    
    # Reduced speed: the actual speed when in reduced mode (in kB/s)
    REDUCED_SPEED_KBPS: int = Field(default=5, description="Upload speed when in reduced mode (kB/s) - realistic low activity")
    
    # Peer-based speed tiers (percentage of configured speed range based on total peer count)
    PEER_SPEED_TIERS_ENABLED: bool = Field(default=True, description="Enable peer-based speed tiers")
    PEER_TIER1_MAX_PEERS: int = Field(default=20, description="Tier 1 upper bound (0 to this many peers)")
    PEER_TIER1_SPEED_PERCENT: int = Field(default=15, description="Speed percentage for tier 1 (0-100)")
    PEER_TIER2_MAX_PEERS: int = Field(default=50, description="Tier 2 upper bound")
    PEER_TIER2_SPEED_PERCENT: int = Field(default=35, description="Speed percentage for tier 2 (0-100)")
    PEER_TIER3_MAX_PEERS: int = Field(default=100, description="Tier 3 upper bound")
    PEER_TIER3_SPEED_PERCENT: int = Field(default=60, description="Speed percentage for tier 3 (0-100)")
    PEER_TIER4_MAX_PEERS: int = Field(default=200, description="Tier 4 upper bound")
    PEER_TIER4_SPEED_PERCENT: int = Field(default=80, description="Speed percentage for tier 4 (0-100)")
    PEER_TIER5_SPEED_PERCENT: int = Field(default=100, description="Speed percentage for tier 5 / above tier 4 (0-100)")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Ensure directories exist
settings.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
settings.TORRENTS_DIR.mkdir(parents=True, exist_ok=True)
settings.CLIENTS_DIR.mkdir(parents=True, exist_ok=True)
