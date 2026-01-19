"""
UDP Tracker Protocol Implementation (BEP 15)
https://www.bittorrent.org/beps/bep_0015.html

Supports ~40% of BitTorrent trackers that use UDP protocol.
"""
import asyncio
import struct
import random
import socket
import logging
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlparse
from dataclasses import dataclass
from enum import IntEnum

logger = logging.getLogger(__name__)


class UDPAction(IntEnum):
    """UDP tracker protocol actions"""
    CONNECT = 0
    ANNOUNCE = 1
    SCRAPE = 2
    ERROR = 3


class UDPEvent(IntEnum):
    """UDP tracker announce events"""
    NONE = 0
    COMPLETED = 1
    STARTED = 2
    STOPPED = 3


@dataclass
class UDPAnnounceResponse:
    """Response from UDP tracker announce"""
    action: int
    transaction_id: int
    interval: int
    leechers: int
    seeders: int
    peers: list  # List of (ip, port) tuples


@dataclass
class UDPScrapeResponse:
    """Response from UDP tracker scrape"""
    seeders: int
    completed: int
    leechers: int


class UDPTrackerError(Exception):
    """UDP Tracker protocol error"""
    pass


class UDPTracker:
    """
    UDP Tracker client implementing BEP 15.
    
    Protocol flow:
    1. Connect: Send connection request, receive connection_id
    2. Announce: Send announce with connection_id, receive peer list
    
    Connection ID is valid for 1 minute according to spec.
    """
    
    # Protocol constants
    PROTOCOL_ID = 0x41727101980  # Magic constant for connect
    CONNECT_TIMEOUT = 15
    ANNOUNCE_TIMEOUT = 15
    MAX_RETRIES = 3
    CONNECTION_ID_LIFETIME = 60  # seconds
    
    def __init__(self, tracker_url: str):
        """
        Initialize UDP tracker client.
        
        Args:
            tracker_url: UDP tracker URL (udp://tracker.example.com:1337/announce)
        """
        self.tracker_url = tracker_url
        parsed = urlparse(tracker_url)
        
        if parsed.scheme != 'udp':
            raise ValueError(f"Not a UDP tracker URL: {tracker_url}")
        
        self.host = parsed.hostname
        self.port = parsed.port or 80
        self.path = parsed.path or '/announce'
        
        # Connection state
        self._connection_id: Optional[int] = None
        self._connection_time: Optional[float] = None
        self._socket: Optional[socket.socket] = None
        
        logger.debug(f"UDP Tracker initialized: {self.host}:{self.port}")
    
    def _is_connection_valid(self) -> bool:
        """Check if current connection ID is still valid (within 1 minute)"""
        if self._connection_id is None or self._connection_time is None:
            return False
        
        import time
        elapsed = time.time() - self._connection_time
        return elapsed < self.CONNECTION_ID_LIFETIME
    
    def _generate_transaction_id(self) -> int:
        """Generate random 32-bit transaction ID"""
        return random.randint(0, 0xFFFFFFFF)
    
    async def _send_and_receive(
        self, 
        data: bytes, 
        timeout: float,
        expected_action: int
    ) -> bytes:
        """
        Send UDP packet and wait for response.
        
        Implements retry logic with exponential backoff per BEP 15:
        - Wait 15 * 2^n seconds for each retry
        """
        loop = asyncio.get_event_loop()
        
        # Create socket if needed
        if self._socket is None:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setblocking(False)
        
        # Resolve hostname
        try:
            addr_info = await loop.getaddrinfo(
                self.host, self.port, 
                family=socket.AF_INET, 
                type=socket.SOCK_DGRAM
            )
            if not addr_info:
                raise UDPTrackerError(f"Could not resolve {self.host}")
            
            addr = addr_info[0][4]
        except Exception as e:
            raise UDPTrackerError(f"DNS resolution failed: {e}")
        
        last_error = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                # Calculate timeout: 15 * 2^n seconds
                current_timeout = timeout * (2 ** attempt)
                if current_timeout > 60:
                    current_timeout = 60  # Cap at 60 seconds
                
                # Send request
                await loop.sock_sendto(self._socket, data, addr)
                logger.debug(f"UDP sent {len(data)} bytes to {addr}, attempt {attempt + 1}")
                
                # Wait for response with timeout
                try:
                    response = await asyncio.wait_for(
                        loop.sock_recv(self._socket, 2048),
                        timeout=current_timeout
                    )
                    
                    if len(response) < 8:
                        raise UDPTrackerError(f"Response too short: {len(response)} bytes")
                    
                    # Verify action
                    action = struct.unpack('>I', response[0:4])[0]
                    
                    if action == UDPAction.ERROR:
                        error_msg = response[8:].decode('utf-8', errors='replace')
                        raise UDPTrackerError(f"Tracker error: {error_msg}")
                    
                    if action != expected_action:
                        raise UDPTrackerError(f"Unexpected action: {action}, expected {expected_action}")
                    
                    return response
                    
                except asyncio.TimeoutError:
                    logger.debug(f"UDP timeout (attempt {attempt + 1}/{self.MAX_RETRIES})")
                    last_error = "Timeout"
                    continue
                    
            except Exception as e:
                last_error = str(e)
                logger.debug(f"UDP error (attempt {attempt + 1}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(1)
                continue
        
        raise UDPTrackerError(f"Failed after {self.MAX_RETRIES} attempts: {last_error}")
    
    async def connect(self) -> int:
        """
        Perform UDP tracker connect handshake.
        
        Returns:
            connection_id to use for subsequent requests
        """
        if self._is_connection_valid():
            return self._connection_id
        
        transaction_id = self._generate_transaction_id()
        
        # Build connect request (16 bytes)
        # protocol_id (8 bytes) + action (4 bytes) + transaction_id (4 bytes)
        request = struct.pack(
            '>QII',
            self.PROTOCOL_ID,
            UDPAction.CONNECT,
            transaction_id
        )
        
        logger.debug(f"UDP Connect: {self.host}:{self.port}")
        
        response = await self._send_and_receive(
            request, 
            self.CONNECT_TIMEOUT,
            UDPAction.CONNECT
        )
        
        # Parse connect response (16 bytes)
        # action (4 bytes) + transaction_id (4 bytes) + connection_id (8 bytes)
        if len(response) < 16:
            raise UDPTrackerError(f"Connect response too short: {len(response)}")
        
        action, resp_transaction_id, connection_id = struct.unpack('>IIQ', response[:16])
        
        if resp_transaction_id != transaction_id:
            raise UDPTrackerError(f"Transaction ID mismatch: {resp_transaction_id} != {transaction_id}")
        
        self._connection_id = connection_id
        import time
        self._connection_time = time.time()
        
        logger.debug(f"UDP Connected: connection_id={connection_id}")
        
        return connection_id
    
    async def announce(
        self,
        info_hash: bytes,
        peer_id: str,
        port: int,
        uploaded: int,
        downloaded: int,
        left: int,
        event: Optional[str] = None,
        key: Optional[int] = None,
        numwant: int = 200
    ) -> UDPAnnounceResponse:
        """
        Send announce request to UDP tracker.
        
        Args:
            info_hash: 20-byte torrent info hash
            peer_id: 20-byte peer ID string
            port: Listen port
            uploaded: Total bytes uploaded
            downloaded: Total bytes downloaded
            left: Bytes remaining
            event: Event type (started, stopped, completed, or None)
            key: Random key for tracker
            numwant: Number of peers wanted
            
        Returns:
            UDPAnnounceResponse with peers and stats
        """
        # Ensure we have valid connection
        connection_id = await self.connect()
        
        transaction_id = self._generate_transaction_id()
        
        # Convert event string to enum
        event_code = UDPEvent.NONE
        if event == 'started':
            event_code = UDPEvent.STARTED
        elif event == 'stopped':
            event_code = UDPEvent.STOPPED
        elif event == 'completed':
            event_code = UDPEvent.COMPLETED
        
        # Generate key if not provided
        if key is None:
            key = random.randint(0, 0xFFFFFFFF)
        elif isinstance(key, str):
            # Convert hex string key to int
            try:
                key = int(key, 16) & 0xFFFFFFFF
            except ValueError:
                key = random.randint(0, 0xFFFFFFFF)
        
        # Ensure peer_id is exactly 20 bytes
        peer_id_bytes = peer_id.encode('latin-1')[:20].ljust(20, b'\x00')
        
        # Build announce request (98 bytes)
        # connection_id (8) + action (4) + transaction_id (4) + info_hash (20) +
        # peer_id (20) + downloaded (8) + left (8) + uploaded (8) + event (4) +
        # ip (4) + key (4) + num_want (4) + port (2)
        request = struct.pack(
            '>QII20s20sQQQIIIiH',
            connection_id,
            UDPAction.ANNOUNCE,
            transaction_id,
            info_hash,
            peer_id_bytes,
            downloaded,
            left,
            uploaded,
            event_code,
            0,  # IP address (0 = let tracker determine)
            key,
            numwant,
            port
        )
        
        logger.debug(f"UDP Announce: event={event}, uploaded={uploaded}, left={left}")
        
        response = await self._send_and_receive(
            request,
            self.ANNOUNCE_TIMEOUT,
            UDPAction.ANNOUNCE
        )
        
        # Parse announce response (minimum 20 bytes + peers)
        # action (4) + transaction_id (4) + interval (4) + leechers (4) + seeders (4) + peers (6 each)
        if len(response) < 20:
            raise UDPTrackerError(f"Announce response too short: {len(response)}")
        
        action, resp_transaction_id, interval, leechers, seeders = struct.unpack(
            '>IIIII', response[:20]
        )
        
        if resp_transaction_id != transaction_id:
            raise UDPTrackerError(f"Transaction ID mismatch: {resp_transaction_id} != {transaction_id}")
        
        # Parse peers (6 bytes each: 4 bytes IP + 2 bytes port)
        peers = []
        peer_data = response[20:]
        for i in range(0, len(peer_data), 6):
            if i + 6 <= len(peer_data):
                ip_bytes = peer_data[i:i+4]
                port_bytes = peer_data[i+4:i+6]
                
                ip = socket.inet_ntoa(ip_bytes)
                peer_port = struct.unpack('>H', port_bytes)[0]
                
                if peer_port > 0:  # Skip invalid ports
                    peers.append((ip, peer_port))
        
        logger.info(f"✅ UDP Announce successful: {seeders} seeders, {leechers} leechers, {len(peers)} peers, interval={interval}s")
        
        return UDPAnnounceResponse(
            action=action,
            transaction_id=resp_transaction_id,
            interval=interval,
            leechers=leechers,
            seeders=seeders,
            peers=peers
        )
    
    async def scrape(self, info_hashes: list[bytes]) -> Dict[bytes, UDPScrapeResponse]:
        """
        Scrape tracker for torrent stats.
        
        Args:
            info_hashes: List of 20-byte info hashes to scrape
            
        Returns:
            Dict mapping info_hash to UDPScrapeResponse
        """
        if not info_hashes:
            return {}
        
        # Ensure connection
        connection_id = await self.connect()
        
        transaction_id = self._generate_transaction_id()
        
        # Build scrape request
        # connection_id (8) + action (4) + transaction_id (4) + info_hashes (20 each)
        request = struct.pack(
            '>QII',
            connection_id,
            UDPAction.SCRAPE,
            transaction_id
        )
        
        for info_hash in info_hashes:
            request += info_hash[:20]
        
        logger.debug(f"UDP Scrape: {len(info_hashes)} torrent(s)")
        
        response = await self._send_and_receive(
            request,
            self.ANNOUNCE_TIMEOUT,
            UDPAction.SCRAPE
        )
        
        # Parse scrape response
        # action (4) + transaction_id (4) + [seeders (4) + completed (4) + leechers (4)] * n
        if len(response) < 8:
            raise UDPTrackerError(f"Scrape response too short: {len(response)}")
        
        action, resp_transaction_id = struct.unpack('>II', response[:8])
        
        if resp_transaction_id != transaction_id:
            raise UDPTrackerError(f"Transaction ID mismatch")
        
        results = {}
        scrape_data = response[8:]
        
        for i, info_hash in enumerate(info_hashes):
            offset = i * 12
            if offset + 12 <= len(scrape_data):
                seeders, completed, leechers = struct.unpack(
                    '>III', scrape_data[offset:offset+12]
                )
                results[info_hash] = UDPScrapeResponse(
                    seeders=seeders,
                    completed=completed,
                    leechers=leechers
                )
        
        logger.debug(f"UDP Scrape completed: {len(results)} result(s)")
        
        return results
    
    def close(self):
        """Close the UDP socket"""
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        
        self._connection_id = None
        self._connection_time = None


def is_udp_tracker(tracker_url: str) -> bool:
    """Check if a tracker URL is UDP"""
    return tracker_url.lower().startswith('udp://')


def parse_udp_tracker_url(tracker_url: str) -> Tuple[str, int]:
    """
    Parse UDP tracker URL to host and port.
    
    Args:
        tracker_url: UDP tracker URL
        
    Returns:
        Tuple of (host, port)
    """
    parsed = urlparse(tracker_url)
    return (parsed.hostname, parsed.port or 80)
