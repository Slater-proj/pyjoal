"""
Torrent File Parser
Handles .torrent file parsing and metadata extraction
"""
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import bencodepy


class Torrent:
    """Represents a .torrent file"""
    
    def __init__(self, torrent_path: Path):
        """Initialize torrent from file"""
        self.path = torrent_path
        self.filename = torrent_path.name
        self.data: Dict = {}
        self.info_hash: str = ""
        self.name: str = ""
        self.size: int = 0
        self.trackers: List[str] = []
        self.added_at: datetime = datetime.utcnow()
        
        self._parse()
    
    def _parse(self):
        """Parse torrent file"""
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
        """Extract tracker URLs from torrent"""
        trackers = []
        
        # Single tracker
        if b'announce' in self.data:
            trackers.append(self.data[b'announce'].decode('utf-8', errors='ignore'))
        
        # Tracker list
        if b'announce-list' in self.data:
            for tier in self.data[b'announce-list']:
                for tracker in tier:
                    url = tracker.decode('utf-8', errors='ignore')
                    if url not in trackers:
                        trackers.append(url)
        
        self.trackers = trackers
    
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
    
    print(f"📂 Scanning directory: {directory}")
    print(f"   Directory exists: {directory.exists()}")
    
    if not directory.exists():
        print("   ⚠️  Directory does not exist!")
        return torrents
    
    # List all files in directory for debugging
    all_files = list(directory.iterdir()) if directory.exists() else []
    torrent_files = list(directory.glob("*.torrent"))
    
    print(f"   Total files: {len(all_files)}")
    print(f"   Torrent files: {len(torrent_files)}")
    
    if all_files:
        print("   Files found:")
        for f in all_files:
            print(f"     - {f.name} ({'torrent' if f.name.endswith('.torrent') else 'other'})")
    
    for torrent_file in torrent_files:
        try:
            print(f"   📄 Loading: {torrent_file.name}")
            torrent = Torrent(torrent_file)
            torrents.append(torrent)
            print(f"      ✅ Success: {torrent.name}")
        except Exception as e:
            print(f"      ❌ Failed to load {torrent_file.name}: {e}")
    
    print(f"   📊 Loaded {len(torrents)} torrent(s)")
    return torrents
