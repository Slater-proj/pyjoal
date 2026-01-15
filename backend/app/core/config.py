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
    UI_PATH_PREFIX: str = Field(..., description="UI path prefix for obfuscation")
    
    # Paths (absolute paths for Docker compatibility)
    CONFIG_DIR: Path = Field(default=Path("/app/config"), description="Configuration directory")
    TORRENTS_DIR: Path = Field(default=Path("/app/torrents"), description="Torrents directory")
    CLIENTS_DIR: Path = Field(default=Path("/app/clients"), description="Clients directory")
    
    # BitTorrent Config
    MIN_UPLOAD_RATE: int = Field(default=30, description="Minimum upload rate (kB/s)")
    MAX_UPLOAD_RATE: int = Field(default=160, description="Maximum upload rate (kB/s)")
    SIMULTANEOUS_SEED: int = Field(default=20, description="Simultaneous seeds")
    KEEP_TORRENT_WITH_ZERO_LEECHERS: bool = Field(default=True, description="Keep torrents with no peers")
    UPLOAD_RATIO_TARGET: float = Field(default=-1.0, description="Upload ratio target (-1 = never remove)")
    SEEDING_DURATION_LIMIT: float = Field(default=-1.0, description="Seeding duration limit in hours (-1 = no limit)")
    DEFAULT_CLIENT: str = Field(default="qbittorrent-4.6.0.client", description="Default client file")
    
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
    
    # Announce intervals
    ANNOUNCE_INTERVAL: int = Field(default=30, description="Base announce interval (seconds)")
    ANNOUNCE_JITTER: int = Field(default=10, description="Random jitter for announces (seconds)")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

# Ensure directories exist
settings.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
settings.TORRENTS_DIR.mkdir(parents=True, exist_ok=True)
settings.CLIENTS_DIR.mkdir(parents=True, exist_ok=True)
