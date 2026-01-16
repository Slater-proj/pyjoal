"""
Pydantic models for request/response schemas
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
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
    minUploadRate: int = Field(ge=0, le=100000, description="Min upload rate (kB/s)")
    maxUploadRate: int = Field(ge=0, le=100000, description="Max upload rate (kB/s)")
    simultaneousSeed: int = Field(ge=1, le=1000, description="Simultaneous seeds")
    client: str = Field(description="Client file name")
    keepTorrentWithZeroLeechers: bool = Field(description="Keep torrents with no peers")
    uploadRatioTarget: float = Field(description="Upload ratio target (-1 = never)")
    seedingDurationLimit: float = Field(default=-1.0, description="Seeding duration limit in hours (-1 = no limit)")
    
    @validator("minUploadRate")
    def validate_min_rate(cls, v):
        if v < 0:
            raise ValueError("La vitesse minimum ne peut pas être négative")
        if v > 100000:
            raise ValueError("La vitesse minimum ne peut pas dépasser 100 MB/s (100000 KB/s)")
        return v
    
    @validator("maxUploadRate")
    def validate_max_rate(cls, v, values):
        if v < 0:
            raise ValueError("La vitesse maximum ne peut pas être négative")
        if v > 100000:
            raise ValueError("La vitesse maximum ne peut pas dépasser 100 MB/s (100000 KB/s)")
        if "minUploadRate" in values and v > 0 and v < values["minUploadRate"]:
            raise ValueError(f"La vitesse maximum ({v} KB/s) doit être supérieure ou égale à la vitesse minimum ({values['minUploadRate']} KB/s)")
        return v
    
    @validator("simultaneousSeed")
    def validate_simultaneous_seed(cls, v):
        if v < 1:
            raise ValueError("Le nombre de seeds simultanés doit être au moins 1")
        if v > 1000:
            raise ValueError("Le nombre de seeds simultanés ne peut pas dépasser 1000")
        return v
    
    @validator("uploadRatioTarget")
    def validate_ratio(cls, v):
        if v < -1:
            raise ValueError("Le ratio cible doit être -1 (illimité) ou un nombre positif")
        return v
    
    @validator("seedingDurationLimit")
    def validate_duration(cls, v):
        if v < -1:
            raise ValueError("La durée de seed doit être -1 (illimitée) ou un nombre positif")
        if v > 8760:  # 1 year in hours
            raise ValueError("La durée de seed ne peut pas dépasser 8760 heures (1 an)")
        return v


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
    lastAnnounce: Optional[datetime] = Field(description="Last announce time")
    nextAnnounce: Optional[datetime] = Field(description="Next announce time")
    tracker: Optional[str] = Field(description="Tracker URL")


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
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Error response"""
    error: str = Field(description="Error message")
    detail: Optional[str] = Field(description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SuccessResponse(BaseModel):
    """Success response"""
    success: bool = Field(default=True)
    message: str = Field(description="Success message")
    data: Optional[dict] = Field(default=None, description="Response data")
