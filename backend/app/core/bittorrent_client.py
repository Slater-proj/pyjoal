"""
BitTorrent Client Emulation
Parses and uses .client files to emulate different BitTorrent clients
"""
import json
import random
import hashlib
from pathlib import Path
from typing import Dict, Optional, List
from urllib.parse import quote

from app.core.config import settings


class BitTorrentClient:
    """BitTorrent client emulator"""
    
    def __init__(self, client_file: str):
        """Initialize client from .client file"""
        self.client_file = client_file
        self.config: Dict = {}
        self._load_client_config()
        
    def _load_client_config(self):
        """Load client configuration from file"""
        client_path = settings.CLIENTS_DIR / self.client_file
        
        if not client_path.exists():
            raise FileNotFoundError(f"Client file not found: {self.client_file}")
        
        with open(client_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
    
    def generate_peer_id(self, info_hash: str) -> str:
        """Generate peer ID based on client configuration"""
        version = self.config.get("peerIdPattern", {})
        prefix = version.get("prefix", "-JOAL00-")
        
        # Generate random suffix
        suffix = ''.join(random.choices('0123456789ABCDEF', k=12))
        
        return prefix + suffix
    
    def get_user_agent(self) -> str:
        """Get User-Agent string"""
        return self.config.get("userAgent", "JOAL/3.0")
    
    def get_request_headers(self) -> Dict[str, str]:
        """Get HTTP headers for tracker requests"""
        headers = {
            "User-Agent": self.get_user_agent(),
            "Accept": "*/*",
            "Accept-Encoding": "gzip",
            "Connection": "close"
        }
        
        # Add custom headers from client config
        custom_headers = self.config.get("requestHeaders", {})
        headers.update(custom_headers)
        
        return headers
    
    def build_announce_url(
        self,
        tracker_url: str,
        info_hash: bytes,
        peer_id: str,
        port: int,
        uploaded: int,
        downloaded: int,
        left: int,
        event: Optional[str] = None
    ) -> str:
        """Build tracker announce URL"""
        params = {
            "info_hash": info_hash,
            "peer_id": peer_id.encode('latin-1'),
            "port": str(port),
            "uploaded": str(uploaded),
            "downloaded": str(downloaded),
            "left": str(left),
            "compact": "1",
            "numwant": str(self.config.get("numwant", 200)),
            "key": self._generate_key(),
            "supportcrypto": "1",
        }
        
        if event:
            params["event"] = event
        
        # URL encode parameters
        query_parts = []
        for key, value in params.items():
            if isinstance(value, bytes):
                encoded_value = quote(value, safe='')
            else:
                encoded_value = value
            query_parts.append(f"{key}={encoded_value}")
        
        separator = "&" if "?" in tracker_url else "?"
        return f"{tracker_url}{separator}{'&'.join(query_parts)}"
    
    def _generate_key(self) -> str:
        """Generate random key for tracker"""
        return ''.join(random.choices('0123456789ABCDEF', k=8))
    
    def get_upload_rate_range(self) -> tuple[int, int]:
        """Get upload rate range for this client"""
        return (
            settings.MIN_UPLOAD_RATE * 1024,  # Convert to bytes
            settings.MAX_UPLOAD_RATE * 1024
        )
    
    @property
    def name(self) -> str:
        """Get client name"""
        return self.config.get("name", "Unknown Client")
    
    @property
    def version(self) -> str:
        """Get client version"""
        return self.config.get("version", "0.0.0")
    
    def __repr__(self) -> str:
        return f"BitTorrentClient({self.name} {self.version})"


def list_available_clients() -> List[str]:
    """List all available .client files (sorted alphabetically)"""
    clients_dir = settings.CLIENTS_DIR
    if not clients_dir.exists():
        return []
    
    # Sort clients alphabetically for consistent ordering
    clients = sorted([f.name for f in clients_dir.glob("*.client")])
    return clients


def get_default_client() -> BitTorrentClient:
    """Get default BitTorrent client"""
    return BitTorrentClient(settings.DEFAULT_CLIENT)
