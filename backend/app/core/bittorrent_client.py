"""
BitTorrent Client Emulation
Parses and uses .client files to emulate different BitTorrent clients
Compatible with JOAL client file format
"""
import json
import random
import re
import string
from typing import Dict, Optional, List
from urllib.parse import quote

from app.core.config import settings

import logging
logger = logging.getLogger(__name__)


class BitTorrentClient:
    """BitTorrent client emulator - JOAL compatible"""
    
    def __init__(self, client_file: str):
        """Initialize client from .client file"""
        self.client_file = client_file
        self.config: Dict = {}
        self._load_client_config()
        
        # Consistent port for all torrents (more realistic)
        self._session_port = random.randint(49152, 65535)
        
        # Session-persistent key (for clients with refreshOn: NEVER)
        self._session_key: Optional[str] = None
        
        # Cache for torrent-specific keys and peer_ids
        self._torrent_keys: Dict[str, str] = {}
        self._torrent_peer_ids: Dict[str, str] = {}
        
    def _load_client_config(self):
        """Load client configuration from file"""
        client_path = settings.CLIENTS_DIR / self.client_file
        
        if not client_path.exists():
            raise FileNotFoundError(f"Client file not found: {self.client_file}")
        
        with open(client_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        logger.info(f"📱 Loaded client config: {self.name} {self.version}")
        logger.debug(f"   Key algorithm: {self.config.get('keyGenerator', {}).get('algorithm', {}).get('type', 'UNKNOWN')}")
        logger.debug(f"   PeerId algorithm: {self.config.get('peerIdGenerator', {}).get('algorithm', {}).get('type', 'UNKNOWN')}")
    
    # ========== PEER ID GENERATION ==========
    
    def generate_peer_id(self, info_hash: str) -> str:
        """Generate peer ID based on client configuration (JOAL compatible)
        
        Peer ID is ALWAYS exactly 20 bytes.
        """
        peer_id_config = self.config.get("peerIdGenerator", {})
        refresh_on = peer_id_config.get("refreshOn", "NEVER")
        
        # Check cache based on refresh policy
        if refresh_on == "NEVER":
            # Same peer_id for entire session (all torrents)
            cache_key = "_session_"
        elif refresh_on == "TORRENT_PERSISTENT":
            # Same peer_id per torrent across restarts
            cache_key = info_hash
        else:  # TORRENT_VOLATILE
            # New peer_id each time
            cache_key = None
        
        if cache_key and cache_key in self._torrent_peer_ids:
            return self._torrent_peer_ids[cache_key]
        
        # Generate new peer_id
        algorithm = peer_id_config.get("algorithm", {})
        algo_type = algorithm.get("type", "REGEX")
        
        if algo_type == "REGEX":
            peer_id = self._generate_peer_id_regex(algorithm)
        elif algo_type == "RANDOM_POOL_WITH_CHECKSUM":
            peer_id = self._generate_peer_id_pool_checksum(algorithm)
        else:
            # Fallback to old method
            peer_id = self._generate_peer_id_legacy()
        
        # Ensure exactly 20 bytes
        peer_id = self._ensure_20_bytes(peer_id)
        
        # Cache if needed
        if cache_key:
            self._torrent_peer_ids[cache_key] = peer_id
        
        logger.debug(f"🔑 Generated peer_id: {peer_id} (length={len(peer_id)})")
        return peer_id
    
    def _generate_peer_id_regex(self, algorithm: Dict) -> str:
        """Generate peer_id from regex pattern (qBittorrent, Deluge style)"""
        pattern = algorithm.get("pattern", "-JOAL00-[A-Za-z0-9]{12}")
        
        # Parse the pattern to extract prefix and character class
        # Pattern format: "-qB5140-[A-Za-z0-9_~\\(\\)\\!\\.\\*-]{12}"
        match = re.match(r'^([^[]+)\[([^\]]+)\]\{(\d+)\}$', pattern)
        
        if match:
            prefix = match.group(1)
            char_class = match.group(2)
            length = int(match.group(3))
            
            # Build character set from class
            chars = self._parse_char_class(char_class)
            suffix = ''.join(random.choices(chars, k=length))
            
            return prefix + suffix
        else:
            # Fallback: just use the pattern as prefix + random
            logger.warning(f"Could not parse peer_id pattern: {pattern}")
            return self._generate_peer_id_legacy()
    
    def _parse_char_class(self, char_class: str) -> str:
        """Parse regex character class like A-Za-z0-9_~"""
        chars = ""
        i = 0
        while i < len(char_class):
            if i + 2 < len(char_class) and char_class[i + 1] == '-':
                # Range like A-Z
                start = char_class[i]
                end = char_class[i + 2]
                chars += ''.join(chr(c) for c in range(ord(start), ord(end) + 1))
                i += 3
            elif char_class[i] == '\\' and i + 1 < len(char_class):
                # Escaped character
                chars += char_class[i + 1]
                i += 2
            else:
                chars += char_class[i]
                i += 1
        return chars
    
    def _generate_peer_id_pool_checksum(self, algorithm: Dict) -> str:
        """Generate peer_id with checksum (Transmission style)"""
        prefix = algorithm.get("prefix", "-TR3000-")
        pool = algorithm.get("charactersPool", "0123456789abcdefghijklmnopqrstuvwxyz")
        base = algorithm.get("base", 36)
        
        # Generate 11 random characters from pool
        random_part = ''.join(random.choices(pool, k=11))
        
        # Calculate checksum (last character)
        # Transmission uses: sum of all chars mod base
        checksum_value = sum(pool.index(c) if c in pool else 0 for c in random_part) % base
        checksum_char = pool[checksum_value]
        
        return prefix + random_part + checksum_char
    
    def _generate_peer_id_legacy(self) -> str:
        """Legacy peer_id generation (fallback)"""
        peer_id_pattern = self.config.get("peerIdPattern", {})
        prefix = peer_id_pattern.get("prefix", "-JOAL00-")
        suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        return prefix + suffix
    
    def _ensure_20_bytes(self, peer_id: str) -> str:
        """Ensure peer_id is exactly 20 bytes"""
        encoded = peer_id.encode('latin-1')
        if len(encoded) < 20:
            # Pad with random chars
            padding = ''.join(random.choices(string.ascii_letters + string.digits, k=20 - len(encoded)))
            peer_id = peer_id + padding
        elif len(encoded) > 20:
            peer_id = peer_id[:20]
        return peer_id
    
    # ========== KEY GENERATION ==========
    
    def generate_key(self, info_hash: str) -> str:
        """Generate key for tracker based on client configuration (JOAL compatible)"""
        key_config = self.config.get("keyGenerator", {})
        refresh_on = key_config.get("refreshOn", "TORRENT_PERSISTENT")
        
        # Check cache based on refresh policy
        if refresh_on == "NEVER":
            if self._session_key is None:
                self._session_key = self._generate_key_internal(key_config)
            return self._session_key
        elif refresh_on == "TORRENT_PERSISTENT":
            if info_hash not in self._torrent_keys:
                self._torrent_keys[info_hash] = self._generate_key_internal(key_config)
            return self._torrent_keys[info_hash]
        else:  # TORRENT_VOLATILE or other
            return self._generate_key_internal(key_config)
    
    def _generate_key_internal(self, key_config: Dict) -> str:
        """Generate key based on algorithm"""
        algorithm = key_config.get("algorithm", {})
        algo_type = algorithm.get("type", "HASH_NO_LEADING_ZERO")
        key_case = key_config.get("keyCase", "upper")
        
        if algo_type == "HASH_NO_LEADING_ZERO":
            key = self._generate_key_hash_no_leading_zero(algorithm)
        elif algo_type == "DIGIT_RANGE_TRANSFORMED_TO_HEX_WITHOUT_LEADING_ZEROES":
            key = self._generate_key_digit_range_hex(algorithm)
        elif algo_type == "HASH":
            key = self._generate_key_hash(algorithm)
        else:
            # Fallback
            key = ''.join(random.choices('0123456789ABCDEF', k=8))
        
        # Apply case
        if key_case == "upper":
            key = key.upper()
        elif key_case == "lower":
            key = key.lower()
        
        logger.debug(f"🔐 Generated key: {key} (algo={algo_type})")
        return key
    
    def _generate_key_hash_no_leading_zero(self, algorithm: Dict) -> str:
        """Generate key using HASH_NO_LEADING_ZERO algorithm (qBittorrent, Deluge)"""
        length = algorithm.get("length", 8)
        
        # Generate random hex string without leading zero
        while True:
            key = ''.join(random.choices('0123456789ABCDEF', k=length))
            if not key.startswith('0'):
                return key
    
    def _generate_key_digit_range_hex(self, algorithm: Dict) -> str:
        """Generate key using DIGIT_RANGE_TRANSFORMED_TO_HEX (Transmission)"""
        lower = algorithm.get("inclusiveLowerBound", 1)
        upper = algorithm.get("inclusiveUpperBound", 2147483647)
        
        # Generate random number in range and convert to hex without leading zeros
        value = random.randint(lower, upper)
        key = format(value, 'x')  # lowercase hex without 0x prefix
        
        return key
    
    def _generate_key_hash(self, algorithm: Dict) -> str:
        """Generate key using simple HASH algorithm"""
        length = algorithm.get("length", 8)
        return ''.join(random.choices('0123456789ABCDEF', k=length))
    
    # ========== URL ENCODING ==========
    
    def url_encode(self, data: bytes) -> str:
        """URL encode bytes according to client's encoding rules"""
        url_encoder = self.config.get("urlEncoder", {})
        exclusion_pattern = url_encoder.get("encodingExclusionPattern", "[A-Za-z0-9]")
        hex_case = url_encoder.get("encodedHexCase", "lower")
        
        # Build set of characters to NOT encode
        safe_chars = self._parse_char_class(exclusion_pattern.strip('[]'))
        
        result = []
        for byte in data:
            char = chr(byte)
            if char in safe_chars:
                result.append(char)
            else:
                # URL encode this byte
                if hex_case == "upper":
                    result.append(f'%{byte:02X}')
                else:
                    result.append(f'%{byte:02x}')
        
        return ''.join(result)
    
    # ========== HEADERS ==========
    
    def get_user_agent(self) -> str:
        """Get User-Agent string"""
        # New format (array)
        headers = self.config.get("requestHeaders", [])
        if isinstance(headers, list):
            for header in headers:
                if header.get("name", "").lower() == "user-agent":
                    return header.get("value", "")
        
        # Old format (string)
        return self.config.get("userAgent", "JOAL/3.0")
    
    def get_request_headers(self) -> Dict[str, str]:
        """Get HTTP headers for tracker requests (JOAL compatible)"""
        headers = {}
        
        # New format (array of {name, value})
        raw_headers = self.config.get("requestHeaders", [])
        if isinstance(raw_headers, list):
            for header in raw_headers:
                name = header.get("name", "")
                value = header.get("value", "")
                if name and value:
                    headers[name] = value
        elif isinstance(raw_headers, dict):
            # Old format (dict)
            headers = {
                "User-Agent": self.get_user_agent(),
                "Accept": "*/*",
                "Accept-Encoding": "gzip",
                "Connection": "close"
            }
            headers.update(raw_headers)
        
        return headers
    
    # ========== ANNOUNCE URL BUILDING ==========
    
    def build_announce_url(
        self,
        tracker_url: str,
        info_hash: bytes,
        peer_id: str,
        port: int,
        uploaded: int,
        downloaded: int,
        left: int,
        event: Optional[str] = None,
        numwant: Optional[int] = None,
        key: Optional[str] = None
    ) -> str:
        """Build tracker announce URL using client's query template (JOAL compatible)"""
        
        # Get query template
        query_template = self.config.get("query", "")
        
        if not query_template:
            # Fallback to legacy method
            return self._build_announce_url_legacy(
                tracker_url, info_hash, peer_id, port, 
                uploaded, downloaded, left, event
            )
        
        # URL encode info_hash (binary -> URL encoded)
        encoded_info_hash = self.url_encode(info_hash)
        
        # URL encode peer_id if needed
        peer_id_config = self.config.get("peerIdGenerator", {})
        if peer_id_config.get("shouldUrlEncode", False):
            encoded_peer_id = self.url_encode(peer_id.encode('latin-1'))
        else:
            encoded_peer_id = peer_id
        
        # Determine numwant
        if numwant is None:
            if event == "stopped":
                numwant = self.config.get("numwantOnStop", 0)
            else:
                numwant = self.config.get("numwant", 200)
        
        # Generate key if not provided
        if key is None:
            # We need info_hash as hex for key generation
            info_hash_hex = info_hash.hex()
            key = self.generate_key(info_hash_hex)
        
        # Build query from template
        query = query_template
        query = query.replace("{infohash}", encoded_info_hash)
        query = query.replace("{peerid}", encoded_peer_id)
        query = query.replace("{port}", str(port))
        query = query.replace("{uploaded}", str(uploaded))
        query = query.replace("{downloaded}", str(downloaded))
        query = query.replace("{left}", str(left))
        query = query.replace("{numwant}", str(numwant))
        query = query.replace("{key}", key)
        
        # Handle event (remove if empty)
        if event:
            query = query.replace("{event}", event)
        else:
            # Remove event parameter entirely if no event
            # Remove patterns like "event={event}&" or "&event={event}"
            query = re.sub(r'&?event=\{event\}&?', '', query)
            query = re.sub(r'^&|&$', '', query)  # Clean up leading/trailing &
        
        # Handle optional IPv6 placeholder
        query = query.replace("{ipv6}", "")
        query = re.sub(r'&?ipv6=&?', '', query)
        query = re.sub(r'^&|&$', '', query)
        
        # Build final URL
        separator = "&" if "?" in tracker_url else "?"
        url = f"{tracker_url}{separator}{query}"
        
        logger.debug(f"📤 Built announce URL: {url[:100]}...")
        return url
    
    def _build_announce_url_legacy(
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
        """Legacy URL building (fallback)"""
        params = {
            "info_hash": info_hash,
            "peer_id": peer_id.encode('latin-1'),
            "port": str(port),
            "uploaded": str(uploaded),
            "downloaded": str(downloaded),
            "left": str(left),
            "compact": "1",
            "numwant": str(self.config.get("numwant", 200)),
            "key": self.generate_key(info_hash.hex()),
            "supportcrypto": "1",
        }
        
        if event:
            params["event"] = event
        
        query_parts = []
        for key, value in params.items():
            if isinstance(value, bytes):
                encoded_value = quote(value, safe='')
            else:
                encoded_value = value
            query_parts.append(f"{key}={encoded_value}")
        
        separator = "&" if "?" in tracker_url else "?"
        return f"{tracker_url}{separator}{'&'.join(query_parts)}"
    
    def get_upload_rate_range(self, dynamic_config: dict = None) -> tuple[int, int]:
        """Get upload rate range for this client with dynamic config support"""
        if dynamic_config:
            # Use dynamic configuration if provided (from seeder_service)
            min_rate = dynamic_config.get("minUploadRate", settings.MIN_UPLOAD_RATE)
            max_rate = dynamic_config.get("maxUploadRate", settings.MAX_UPLOAD_RATE)
        else:
            # Fallback to static settings
            min_rate = settings.MIN_UPLOAD_RATE
            max_rate = settings.MAX_UPLOAD_RATE
            
        return (
            min_rate * 1024,  # Convert KB/s to bytes/s
            max_rate * 1024
        )
    
    def get_session_port(self) -> int:
        """Get consistent port for this client session (realistic behavior)"""
        return self._session_port
    
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
