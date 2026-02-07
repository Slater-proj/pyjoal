"""
Pydantic models for request/response schemas
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum


class ClientType(str, Enum):
    """Supported BitTorrent clients"""
    QBITTORRENT = "qbittorrent"
    DELUGE = "deluge"
    TRANSMISSION = "transmission"
    UTORRENT = "utorrent"
    RTORRENT = "rtorrent"
    VUZE = "vuze"


class TorrentState(str, Enum):
    """Torrent states"""
    STOPPED = "stopped"
    SEEDING = "seeding"
    ANNOUNCING = "announcing"
    ERROR = "error"


class ConfigSchema(BaseModel):
    """Application configuration schema"""
    minUploadRate: int = Field(ge=0, le=1000000, description="Min upload rate (kB/s)")
    maxUploadRate: int = Field(ge=0, le=1000000, description="Max upload rate (kB/s)")
    simultaneousSeed: int = Field(ge=1, le=1000, description="Simultaneous seeds")
    client: str = Field(description="Client file name")
    keepTorrentWithZeroLeechers: bool = Field(description="Keep torrents with no peers")
    uploadRatioTarget: float = Field(description="Upload ratio target (-1 = never)")
    seedingDurationLimit: float = Field(default=-1.0, description="Seeding duration limit in hours (-1 = no limit)")
    
    # Discretion & Timing Settings
    announceInterval: int = Field(default=1800, ge=60, le=7200, description="Base announce interval (seconds)")
    announceJitter: int = Field(default=120, ge=0, le=600, description="Random jitter for announces (seconds)")
    minStatsUpdateInterval: int = Field(default=2, ge=1, le=30, description="Minimum interval between stats updates (seconds)")
    enableSpeedVariation: bool = Field(default=True, description="Enable realistic speed variations")
    speedVariationPercent: int = Field(default=20, ge=0, le=50, description="Speed variation percentage (±%)")
    
    # Torrent Behavior Mode
    seedingOnlyMode: bool = Field(default=True, description="Pure seeding mode (true) vs download simulation mode (false)")
    
    # 🎭 Realistic Behavior Timing Settings
    pauseDurationMin: int = Field(default=30, ge=1, le=480, description="Minimum pause duration (minutes)")
    pauseDurationMax: int = Field(default=180, ge=1, le=720, description="Maximum pause duration (minutes)")
    reducedSpeedDurationMin: int = Field(default=60, ge=1, le=480, description="Minimum reduced speed duration (minutes)")
    reducedSpeedDurationMax: int = Field(default=240, ge=1, le=720, description="Maximum reduced speed duration (minutes)")
    stateChangeIntervalMin: int = Field(default=2, ge=1, le=24, description="Minimum interval between state changes (hours)")
    stateChangeIntervalMax: int = Field(default=8, ge=1, le=48, description="Maximum interval between state changes (hours)")
    reducedSpeedKbps: int = Field(default=5, ge=1, le=100, description="Upload speed when in reduced mode (kB/s)")
    
    # Peer-based speed tiers
    peerSpeedTiersEnabled: bool = Field(default=True, description="Enable peer-based speed tiers")
    peerTier1MaxPeers: int = Field(default=20, ge=1, le=500, description="Tier 1 upper bound (peer count)")
    peerTier1SpeedPercent: int = Field(default=40, ge=1, le=100, description="Speed % for tier 1")
    peerTier2MaxPeers: int = Field(default=50, ge=1, le=1000, description="Tier 2 upper bound")
    peerTier2SpeedPercent: int = Field(default=55, ge=1, le=100, description="Speed % for tier 2")
    peerTier3MaxPeers: int = Field(default=100, ge=1, le=1000, description="Tier 3 upper bound")
    peerTier3SpeedPercent: int = Field(default=60, ge=1, le=100, description="Speed % for tier 3")
    peerTier4MaxPeers: int = Field(default=200, ge=1, le=2000, description="Tier 4 upper bound")
    peerTier4SpeedPercent: int = Field(default=80, ge=1, le=100, description="Speed % for tier 4")
    peerTier5SpeedPercent: int = Field(default=100, ge=1, le=100, description="Speed % for tier 5 (above tier 4)")
    
    @field_validator("minUploadRate")
    @classmethod
    def validate_min_rate(cls, v: int) -> int:
        if v < 0:
            raise ValueError("La vitesse minimum ne peut pas être négative")
        if v > 1000000:
            raise ValueError("La vitesse minimum ne peut pas dépasser 1000 MB/s (1000000 KB/s)")
        return v
    
    @field_validator("maxUploadRate")
    @classmethod
    def validate_max_rate(cls, v: int) -> int:
        if v < 0:
            raise ValueError("La vitesse maximum ne peut pas être négative")
        if v > 1000000:
            raise ValueError("La vitesse maximum ne peut pas dépasser 1000 MB/s (1000000 KB/s)")
        return v
    
    @field_validator("simultaneousSeed")
    @classmethod
    def validate_simultaneous_seed(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Le nombre de seeds simultanés doit être au moins 1")
        if v > 1000:
            raise ValueError("Le nombre de seeds simultanés ne peut pas dépasser 1000")
        return v
    
    @field_validator("uploadRatioTarget")
    @classmethod
    def validate_ratio(cls, v: float) -> float:
        if v < -1:
            raise ValueError("Le ratio cible doit être -1 (illimité) ou un nombre positif")
        return v
    
    @field_validator("seedingDurationLimit")
    @classmethod
    def validate_duration(cls, v: float) -> float:
        if v < -1:
            raise ValueError("La durée de seed doit être -1 (illimitée) ou un nombre positif")
        if v > 8760:  # 1 year in hours
            raise ValueError("La durée de seed ne peut pas dépasser 8760 heures (1 an)")
        return v


class TorrentStatusInfo(BaseModel):
    """Detailed torrent status information for UI"""
    status: Optional[str] = Field(default=None, description="Status code (seeding_active, seeding_low, pause_fake)")
    status_text: Optional[str] = Field(default=None, description="Human readable status")
    current_speed: Optional[int] = Field(default=0, description="Current speed in kB/s")
    speed_formatted: Optional[str] = Field(default=None, description="Formatted speed string")
    time_until_speed_change: Optional[int] = Field(default=0, description="Time until speed change")
    time_until_change_formatted: Optional[str] = Field(default=None, description="Formatted time until change")
    is_active_hour: Optional[bool] = Field(default=True, description="Is currently in active hours")
    peak_hours: Optional[str] = Field(default=None, description="Peak hours range")


class TorrentInfo(BaseModel):
    """Torrent information"""
    id: str = Field(description="Torrent info hash")
    name: str = Field(description="Torrent name")
    size: int = Field(description="Total size in bytes")
    uploaded: int = Field(description="Bytes uploaded")
    uploadSpeed: int = Field(description="Current upload speed (bytes/s)")
    ratio: float = Field(description="Upload ratio")
    seeders: int = Field(description="Number of seeders")
    leechers: int = Field(description="Number of leechers")
    state: TorrentState = Field(description="Current state")
    addedAt: datetime = Field(description="When torrent was added")
    lastAnnounce: Optional[datetime] = Field(default=None, description="Last announce time")
    nextAnnounce: Optional[datetime] = Field(default=None, description="Next announce time")
    tracker: Optional[str] = Field(default=None, description="Tracker URL")
    createdBy: Optional[str] = Field(default=None, description="Created by field from .torrent")
    # Extended fields
    seedingTime: Optional[int] = Field(default=0, description="Seeding time in seconds")
    lastError: Optional[str] = Field(default=None, description="Last error message")
    errorCount: Optional[int] = Field(default=0, description="Error count")
    lastErrorTime: Optional[datetime] = Field(default=None, description="Last error time")
    isHealthy: Optional[bool] = Field(default=True, description="Is torrent healthy")
    status: Optional[TorrentStatusInfo] = Field(default=None, description="Detailed status info")
    simpleStatus: Optional[str] = Field(default=None, description="Simple status string")
    isRunning: Optional[bool] = Field(default=False, description="Is announcer running")


class TorrentUpload(BaseModel):
    """Torrent file upload"""
    filename: str = Field(description="Torrent filename")
    content: bytes = Field(description="Torrent file content")


class ClientStats(BaseModel):
    """Client statistics"""
    isRunning: bool = Field(description="Is client running")
    activeTorrents: int = Field(description="Number of active torrents")
    totalUploaded: int = Field(description="Total bytes uploaded")
    totalDownloaded: int = Field(description="Total bytes downloaded (always 0)")
    uploadSpeed: int = Field(description="Current total upload speed (bytes/s)")
    startedAt: Optional[datetime] = Field(description="When seeding started")
    uptime: Optional[int] = Field(description="Uptime in seconds")


class AnnounceResponse(BaseModel):
    """Tracker announce response"""
    interval: int = Field(description="Announce interval")
    complete: int = Field(description="Number of seeders")
    incomplete: int = Field(description="Number of leechers")
    peers: List[dict] = Field(default_factory=list, description="Peer list")


class WebSocketMessage(BaseModel):
    """WebSocket message format"""
    type: str = Field(description="Message type")
    data: dict = Field(description="Message data")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ErrorResponse(BaseModel):
    """Error response"""
    error: str = Field(description="Error message")
    detail: Optional[str] = Field(description="Error details")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SuccessResponse(BaseModel):
    """Success response"""
    success: bool = Field(default=True)
    message: str = Field(description="Success message")
    data: Optional[dict] = Field(default=None, description="Response data")
