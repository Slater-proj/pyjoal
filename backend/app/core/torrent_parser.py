"""
Torrent File Parser
Handles .torrent file parsing and metadata extraction with intelligent caching
"""
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone
import bencodepy
import logging

from app.core.cache_manager import cache_manager

logger = logging.getLogger(__name__)


class Torrent:
    """Represents a .torrent file"""
    
    def __init__(self, torrent_path: Path):
        """Initialize torrent from file with caching support"""
        self.path = torrent_path
        self.filename = torrent_path.name
        self.data: Dict = {}
        self.info_hash: str = ""
        self.name: str = ""
        self.size: int = 0
        self.trackers: List[str] = []
        self.added_at: datetime = datetime.now(timezone.utc)
        
        # Generate cache key based on path and modification time
        stat = self.path.stat()
        self._cache_key = f"{self.path}:{stat.st_mtime}:{stat.st_size}"
        
        self._parse_with_cache()
    
    def _parse_with_cache(self):
        """Parse torrent file with intelligent caching"""
        # Try to get from cache first
        cached_metadata = cache_manager.get_torrent_metadata(self._cache_key)
        
        if cached_metadata:
            # Use cached data
            self._load_from_cache(cached_metadata)
            logger.debug(f"📦 Torrent metadata loaded from cache: {self.filename}")
            return
        
        # Cache miss - parse from file
        logger.debug(f"🔍 Parsing torrent file (cache miss): {self.filename}")
        self._parse_from_file()
        
        # Cache the results
        metadata = self._get_cacheable_metadata()
        cache_manager.set_torrent_metadata(self._cache_key, metadata)
        logger.debug(f"💾 Torrent metadata cached: {self.filename}")
    
    def _load_from_cache(self, cached_metadata: Dict):
        """Load torrent data from cached metadata"""
        self.info_hash = cached_metadata['info_hash']
        self.name = cached_metadata['name']
        self.size = cached_metadata['size']
        self.trackers = cached_metadata['trackers']
        # Don't cache the full data dict (memory optimization)
    
    def _get_cacheable_metadata(self) -> Dict:
        """Get metadata safe for caching (without large data)"""
        return {
            'info_hash': self.info_hash,
            'name': self.name,
            'size': self.size,
            'trackers': self.trackers,
            'filename': self.filename,
            'parsed_at': datetime.now(timezone.utc).isoformat()
        }
    
    def _parse_from_file(self):
        """Parse torrent file from disk (original logic)"""
        try:
            with open(self.path, 'rb') as f:
                self.data = bencodepy.decode(f.read())
            
            # Extract info hash
            info = self.data[b'info']
            info_encoded = bencodepy.encode(info)
            self.info_hash = hashlib.sha1(info_encoded).hexdigest()
            
            # Extract name
            self.name = info.get(b'name', b'Unknown').decode('utf-8', errors='ignore')
            
            # Calculate total size
            if b'files' in info:
                # Multi-file torrent
                self.size = sum(f[b'length'] for f in info[b'files'])
            else:
                # Single file torrent
                self.size = info.get(b'length', 0)
            
            # Extract trackers
            self._extract_trackers()
            
        except Exception as e:
            raise ValueError(f"Failed to parse torrent: {e}")
    
    def _extract_trackers(self):
        """Extract tracker URLs from torrent (with tier support for BEP 12)"""
        trackers = []
        announce_list = []  # List of tiers, each tier is a list of trackers
        
        # Single tracker (main announce)
        if b'announce' in self.data:
            main_tracker = self.data[b'announce'].decode('utf-8', errors='ignore')
            trackers.append(main_tracker)
        
        # Tracker list (announce-list) with tier support (BEP 12)
        if b'announce-list' in self.data:
            for tier in self.data[b'announce-list']:
                tier_trackers = []
                for tracker in tier:
                    url = tracker.decode('utf-8', errors='ignore')
                    if url and url not in trackers:
                        trackers.append(url)
                    if url:
                        tier_trackers.append(url)
                if tier_trackers:
                    announce_list.append(tier_trackers)
        
        # If no announce-list but have main tracker, create single tier
        if not announce_list and trackers:
            announce_list = [[t] for t in trackers]
        
        self.trackers = trackers
        self.announce_list = announce_list  # BEP 12 tier structure
    
    @property
    def info_hash_bytes(self) -> bytes:
        """Get info hash as bytes"""
        return bytes.fromhex(self.info_hash)
    
    @property
    def primary_tracker(self) -> Optional[str]:
        """Get primary tracker URL"""
        return self.trackers[0] if self.trackers else None
    
    def __repr__(self) -> str:
        return f"Torrent(name={self.name}, size={self.size}, hash={self.info_hash[:8]}...)"


def load_torrents_from_directory(directory: Path) -> List[Torrent]:
    """Load all .torrent files from directory"""
    torrents = []
    
    logger.info(f"📂 Scanning directory: {directory}")
    logger.debug(f"   Directory exists: {directory.exists()}")
    
    if not directory.exists():
        logger.warning("   ⚠️  Directory does not exist!")
        return torrents
    
    # List all files in directory for debugging
    all_files = list(directory.iterdir()) if directory.exists() else []
    torrent_files = list(directory.glob("*.torrent"))
    
    logger.info(f"   Total files: {len(all_files)}")
    logger.info(f"   Torrent files: {len(torrent_files)}")
    
    if all_files:
        logger.debug("   Files found:")
        for f in all_files:
            logger.debug(f"     - {f.name} ({'torrent' if f.name.endswith('.torrent') else 'other'})")
    
    for torrent_file in torrent_files:
        try:
            logger.debug(f"   📄 Loading: {torrent_file.name}")
            torrent = Torrent(torrent_file)
            torrents.append(torrent)
            logger.info(f"      ✅ Success: {torrent.name}")
        except Exception as e:
            logger.error(f"      ❌ Failed to load {torrent_file.name}: {e}")
    
    logger.info(f"   📊 Loaded {len(torrents)} torrent(s)")
    return torrents
