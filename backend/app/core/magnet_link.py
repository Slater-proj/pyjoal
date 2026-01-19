"""
Magnet Link Support (Phase 5.3)
Parses magnet links and retrieves torrent metadata from DHT/trackers.
"""
import re
import hashlib
import logging
from typing import Optional, Dict, List, Tuple
from urllib.parse import urlparse, parse_qs, unquote
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MagnetInfo:
    """Parsed magnet link information"""
    info_hash: str  # 40-char hex string
    info_hash_bytes: bytes  # 20 bytes
    name: Optional[str] = None
    trackers: List[str] = None
    size: Optional[int] = None
    
    def __post_init__(self):
        if self.trackers is None:
            self.trackers = []


class MagnetLinkError(Exception):
    """Error parsing or handling magnet link"""
    pass


def parse_magnet_link(magnet_uri: str) -> MagnetInfo:
    """
    Parse a magnet link and extract torrent information.
    
    Magnet URI format (BEP 9):
    magnet:?xt=urn:btih:<info_hash>&dn=<name>&tr=<tracker>&xl=<size>
    
    Args:
        magnet_uri: Magnet link string
        
    Returns:
        MagnetInfo with parsed data
        
    Raises:
        MagnetLinkError: If link is invalid
    """
    if not magnet_uri.startswith('magnet:?'):
        raise MagnetLinkError("Invalid magnet link: must start with 'magnet:?'")
    
    # Parse query string
    query_string = magnet_uri[8:]  # Remove 'magnet:?'
    params = parse_qs(query_string)
    
    # Extract info hash (required)
    xt = params.get('xt', [])
    if not xt:
        raise MagnetLinkError("Missing xt (info hash) parameter")
    
    info_hash = None
    for xt_val in xt:
        if xt_val.startswith('urn:btih:'):
            hash_part = xt_val[9:]  # Remove 'urn:btih:'
            
            # Handle both hex (40 chars) and base32 (32 chars) formats
            if len(hash_part) == 40:
                # Hex format
                info_hash = hash_part.lower()
            elif len(hash_part) == 32:
                # Base32 format - decode to hex
                import base64
                try:
                    decoded = base64.b32decode(hash_part.upper())
                    info_hash = decoded.hex()
                except Exception as e:
                    raise MagnetLinkError(f"Invalid base32 info hash: {e}")
            else:
                raise MagnetLinkError(f"Invalid info hash length: {len(hash_part)}")
            break
    
    if not info_hash:
        raise MagnetLinkError("Could not extract info hash from magnet link")
    
    # Validate info hash is valid hex
    try:
        info_hash_bytes = bytes.fromhex(info_hash)
        if len(info_hash_bytes) != 20:
            raise MagnetLinkError(f"Info hash must be 20 bytes, got {len(info_hash_bytes)}")
    except ValueError as e:
        raise MagnetLinkError(f"Invalid info hash hex: {e}")
    
    # Extract display name (optional)
    dn = params.get('dn', [])
    name = unquote(dn[0]) if dn else f"Magnet-{info_hash[:8]}"
    
    # Extract trackers (optional but useful)
    trackers = []
    tr = params.get('tr', [])
    for tracker in tr:
        tracker_url = unquote(tracker)
        if tracker_url and tracker_url not in trackers:
            trackers.append(tracker_url)
    
    # Extract size (optional)
    xl = params.get('xl', [])
    size = None
    if xl:
        try:
            size = int(xl[0])
        except ValueError:
            pass
    
    return MagnetInfo(
        info_hash=info_hash,
        info_hash_bytes=info_hash_bytes,
        name=name,
        trackers=trackers,
        size=size
    )


def is_magnet_link(uri: str) -> bool:
    """Check if a string is a magnet link"""
    return uri.strip().lower().startswith('magnet:?')


def create_magnet_link(
    info_hash: str,
    name: Optional[str] = None,
    trackers: Optional[List[str]] = None,
    size: Optional[int] = None
) -> str:
    """
    Create a magnet link from components.
    
    Args:
        info_hash: 40-char hex info hash
        name: Display name
        trackers: List of tracker URLs
        size: Size in bytes
        
    Returns:
        Magnet URI string
    """
    from urllib.parse import quote
    
    parts = [f"magnet:?xt=urn:btih:{info_hash}"]
    
    if name:
        parts.append(f"dn={quote(name)}")
    
    if size:
        parts.append(f"xl={size}")
    
    if trackers:
        for tracker in trackers:
            parts.append(f"tr={quote(tracker)}")
    
    return "&".join(parts)


class MagnetTorrent:
    """
    Pseudo-torrent created from magnet link.
    Compatible with Torrent class interface for seeding.
    
    Note: Without full metadata, we can only do basic operations.
    For ratio simulation, we need to fake/estimate the size.
    """
    
    def __init__(self, magnet_info: MagnetInfo, estimated_size: Optional[int] = None):
        """
        Create pseudo-torrent from magnet info.
        
        Args:
            magnet_info: Parsed magnet link data
            estimated_size: Estimated torrent size (for ratio calculation)
        """
        self.info_hash = magnet_info.info_hash
        self.info_hash_bytes = magnet_info.info_hash_bytes
        self.name = magnet_info.name
        self.trackers = magnet_info.trackers
        self.announce_list = [[t] for t in magnet_info.trackers]  # Each tracker in own tier
        
        # Size handling
        if magnet_info.size:
            self.size = magnet_info.size
        elif estimated_size:
            self.size = estimated_size
        else:
            # Default estimate: 1 GB (will be updated when we get metadata)
            self.size = 1024 * 1024 * 1024
        
        self._is_magnet = True
        self._metadata_received = False
        
        logger.info(f"Created MagnetTorrent: {self.name} ({self.info_hash[:8]}...)")
    
    @property
    def primary_tracker(self) -> Optional[str]:
        """Get primary tracker URL"""
        return self.trackers[0] if self.trackers else None
    
    @classmethod
    def from_uri(cls, magnet_uri: str, estimated_size: Optional[int] = None) -> 'MagnetTorrent':
        """
        Create MagnetTorrent from magnet URI string.
        
        Args:
            magnet_uri: Magnet link
            estimated_size: Optional size estimate
            
        Returns:
            MagnetTorrent instance
        """
        magnet_info = parse_magnet_link(magnet_uri)
        return cls(magnet_info, estimated_size)
    
    def update_metadata(self, name: Optional[str] = None, size: Optional[int] = None):
        """Update torrent metadata (e.g., after DHT lookup)"""
        if name:
            self.name = name
        if size:
            self.size = size
        self._metadata_received = True
    
    def __repr__(self) -> str:
        return f"MagnetTorrent(name={self.name}, hash={self.info_hash[:8]}..., size={self.size})"
