"""
Tracker Announcer
Handles announces to BitTorrent trackers
"""
import asyncio
import random
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta
import httpx

from app.core.bittorrent_client import BitTorrentClient
from app.core.torrent_parser import Torrent
from app.models.schemas import AnnounceResponse
from app.core.config import settings
from app.services.history_service import history_service, EventType

logger = logging.getLogger(__name__)


class TrackerAnnouncer:
    """Handles tracker announces for a torrent"""
    
    def __init__(self, torrent: Torrent, client: BitTorrentClient):
        """Initialize announcer"""
        self.torrent = torrent
        self.client = client
        self.peer_id = client.generate_peer_id(torrent.info_hash)
        self.port = random.randint(50000, 60000)
        
        # Stats
        self.uploaded: int = 0
        self.downloaded: int = 0
        self.left: int = torrent.size
        self.upload_speed: int = 0
        
        # Peers info
        self.seeders: int = 0
        self.leechers: int = 0
        
        # Timing
        self.last_announce: Optional[datetime] = None
        self.next_announce: Optional[datetime] = None
        self.announce_interval: int = settings.ANNOUNCE_INTERVAL
        
        # Seeding time tracking (in seconds)
        self.seeding_time: int = 0
        self._seeding_started_at: Optional[datetime] = None
        
        # State
        self.is_running: bool = False
        self._announce_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start announcing"""
        if self.is_running:
            logger.debug(f"Announcer already running for {self.torrent.name}")
            return
        
        logger.info(f"🚀 Starting announcer for: {self.torrent.name}")
        logger.debug(f"   Torrent size: {self.torrent.size / (1024**3):.2f} GB")
        logger.debug(f"   Tracker: {self.torrent.primary_tracker}")
        logger.debug(f"   Peer ID: {self.peer_id}")
        logger.debug(f"   Port: {self.port}")
        
        self.is_running = True
        self._seeding_started_at = datetime.utcnow()  # Start tracking seeding time
        self._announce_task = asyncio.create_task(self._announce_loop())
    
    async def stop(self):
        """Stop announcing"""
        if not self.is_running:
            logger.debug(f"Announcer already stopped for {self.torrent.name}")
            return
        
        logger.info(f"⏹️  Stopping announcer for: {self.torrent.name}")
        logger.debug(f"   Total uploaded: {self.uploaded / (1024**2):.2f} MB")
        logger.debug(f"   Final ratio: {self.uploaded / self.torrent.size if self.torrent.size > 0 else 0:.3f}")
        
        # Accumulate seeding time before stopping
        if self._seeding_started_at:
            elapsed = (datetime.utcnow() - self._seeding_started_at).total_seconds()
            self.seeding_time += int(elapsed)
            self._seeding_started_at = None
        
        self.is_running = False
        
        if self._announce_task:
            self._announce_task.cancel()
            try:
                await self._announce_task
            except asyncio.CancelledError:
                pass
        
        # Send stopped event
        await self._send_announce(event="stopped")
    
    async def _announce_loop(self):
        """Main announce loop"""
        try:
            logger.info(f"📢 Starting announce loop for: {self.torrent.name}")
            
            # Send started event
            await self._send_announce(event="started")
            
            while self.is_running:
                # Wait for next announce
                logger.debug(f"⏰ Waiting {self.announce_interval}s before next announce for {self.torrent.name}")
                await asyncio.sleep(self.announce_interval)
                
                if not self.is_running:
                    break
                
                # Update stats BEFORE announce
                self._update_stats()
                logger.debug(f"📊 Stats updated for {self.torrent.name}: uploaded={self.uploaded / (1024**2):.2f} MB, speed={self.upload_speed / 1024:.2f} KB/s")
                
                # Send regular announce
                await self._send_announce()
                
        except asyncio.CancelledError:
            logger.debug(f"Announce loop cancelled for {self.torrent.name}")
        except Exception as e:
            logger.error(f"❌ Announce error for {self.torrent.name}: {e}", exc_info=True)
    
    def _update_stats(self):
        """Update upload stats"""
        # Simulate upload
        min_rate, max_rate = self.client.get_upload_rate_range()
        previous_speed = self.upload_speed
        self.upload_speed = random.randint(min_rate, max_rate)
        
        # Add to uploaded total (interval * speed in bytes)
        upload_delta = self.upload_speed * self.announce_interval
        self.uploaded += upload_delta
        
        logger.debug(f"📈 Upload stats for {self.torrent.name[:30]}:")
        logger.debug(f"   Speed: {previous_speed / 1024:.2f} KB/s -> {self.upload_speed / 1024:.2f} KB/s")
        logger.debug(f"   Delta: +{upload_delta / (1024**2):.2f} MB")
        logger.debug(f"   Total uploaded: {self.uploaded / (1024**2):.2f} MB")
        logger.debug(f"   Ratio: {self.uploaded / self.torrent.size if self.torrent.size > 0 else 0:.3f}")
        
        # We never download
        self.downloaded = 0
        self.left = 0  # We "have" the complete file
    
    async def _send_announce(self, event: Optional[str] = None):
        """Send announce to tracker"""
        tracker_url = self.torrent.primary_tracker
        if not tracker_url:
            logger.warning(f"No tracker URL for {self.torrent.name}")
            return
        
        event_str = f" ({event})" if event else ""
        logger.info(f"📡 Sending announce{event_str} for: {self.torrent.name[:50]}")
        
        # Build announce URL
        url = self.client.build_announce_url(
            tracker_url=tracker_url,
            info_hash=self.torrent.info_hash_bytes,
            peer_id=self.peer_id,
            port=self.port,
            uploaded=self.uploaded,
            downloaded=self.downloaded,
            left=self.left,
            event=event
        )
        
        # Log announce parameters
        logger.debug(f"📤 Announce parameters:")
        logger.debug(f"   Tracker: {tracker_url}")
        logger.debug(f"   Info hash: {self.torrent.info_hash}")
        logger.debug(f"   Peer ID: {self.peer_id}")
        logger.debug(f"   Port: {self.port}")
        logger.debug(f"   Uploaded: {self.uploaded / (1024**2):.2f} MB")
        logger.debug(f"   Downloaded: {self.downloaded} bytes")
        logger.debug(f"   Left: {self.left} bytes")
        logger.debug(f"   Upload speed: {self.upload_speed / 1024:.2f} KB/s")
        if event:
            logger.debug(f"   Event: {event}")
        
        try:
            # Setup proxy if configured
            proxies = None
            if settings.HTTP_PROXY_HOST and settings.HTTP_PROXY_PORT:
                proxy_url = f"http://{settings.HTTP_PROXY_HOST}:{settings.HTTP_PROXY_PORT}"
                proxies = {
                    "http://": proxy_url,
                    "https://": proxy_url,
                }
                logger.debug(f"   Using proxy: {proxy_url}")
            
            headers = self.client.get_request_headers()
            logger.debug(f"   Headers: {headers}")
            
            async with httpx.AsyncClient(
                headers=headers,
                proxies=proxies,
                timeout=30.0,
                verify=False  # Disable SSL verification for private trackers
            ) as client:
                logger.debug(f"   Sending HTTP GET request...")
                response = await client.get(url)
                logger.debug(f"   Response status: {response.status_code}")
                response.raise_for_status()
                
                # Parse bencoded response
                data = response.content
                logger.debug(f"   Response size: {len(data)} bytes")
                self._parse_announce_response(data)
                
                self.last_announce = datetime.utcnow()
                
                # Calculate next announce with jitter
                jitter = random.randint(-settings.ANNOUNCE_JITTER, settings.ANNOUNCE_JITTER)
                self.next_announce = self.last_announce + timedelta(
                    seconds=self.announce_interval + jitter
                )
                
                logger.info(f"✅ Announce successful for {self.torrent.name[:50]}")
                logger.info(f"   Peers: {self.seeders} seeders, {self.leechers} leechers")
                logger.info(f"   Uploaded: {self.uploaded / (1024**2):.2f} MB (speed: {self.upload_speed / 1024:.2f} KB/s)")
                logger.info(f"   Next announce in {self.announce_interval + jitter}s")
                
                # Log successful announce
                history_service.add_entry(
                    EventType.ANNOUNCE_SUCCESS,
                    f"Announced {self.torrent.name}",
                    {
                        "torrent": self.torrent.name,
                        "seeders": self.seeders,
                        "leechers": self.leechers,
                        "uploaded": self.uploaded,
                        "upload_speed": self.upload_speed
                    }
                )
                
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP error {e.response.status_code} for {self.torrent.name}")
            logger.error(f"   Response: {e.response.text[:500]}")
            # Log failed announce
            history_service.add_entry(
                EventType.ANNOUNCE_FAILED,
                f"Announce failed for {self.torrent.name}",
                {"torrent": self.torrent.name, "error": f"HTTP {e.response.status_code}"}
            )
        except httpx.TimeoutException as e:
            logger.error(f"⏱️  Timeout announcing {self.torrent.name}: {e}")
            history_service.add_entry(
                EventType.ANNOUNCE_FAILED,
                f"Announce timeout for {self.torrent.name}",
                {"torrent": self.torrent.name, "error": "Timeout"}
            )
        except Exception as e:
            logger.error(f"❌ Announce error for {self.torrent.name}: {e}", exc_info=True)
            # Log failed announce
            history_service.add_entry(
                EventType.ANNOUNCE_FAILED,
                f"Announce failed for {self.torrent.name}",
                {"torrent": self.torrent.name, "error": str(e)}
            )
    
    def _parse_announce_response(self, data: bytes):
        """Parse tracker response"""
        try:
            import bencodepy
            response = bencodepy.decode(data)
            
            logger.debug(f"📥 Parsing tracker response for {self.torrent.name[:30]}")
            
            # Check for failure
            if b'failure reason' in response:
                reason = response[b'failure reason'].decode('utf-8', errors='ignore')
                logger.error(f"❌ Tracker returned failure: {reason}")
                return
            
            # Update interval
            if b'interval' in response:
                old_interval = self.announce_interval
                self.announce_interval = response[b'interval']
                if old_interval != self.announce_interval:
                    logger.info(f"⏰ Announce interval updated: {old_interval}s -> {self.announce_interval}s")
            
            # Update peer counts
            old_seeders = self.seeders
            old_leechers = self.leechers
            self.seeders = response.get(b'complete', 0)
            self.leechers = response.get(b'incomplete', 0)
            
            logger.debug(f"   Interval: {self.announce_interval}s")
            logger.debug(f"   Seeders: {old_seeders} -> {self.seeders}")
            logger.debug(f"   Leechers: {old_leechers} -> {self.leechers}")
            
            # Log peer list if present
            if b'peers' in response:
                peers = response[b'peers']
                if isinstance(peers, bytes):
                    peer_count = len(peers) // 6
                    logger.debug(f"   Received {peer_count} peer(s) (compact format)")
                elif isinstance(peers, list):
                    logger.debug(f"   Received {len(peers)} peer(s) (dictionary format)")
            
        except Exception as e:
            logger.error(f"⚠️  Failed to parse announce response: {e}", exc_info=True)
    
    def get_stats(self) -> Dict:
        """Get current stats"""
        # Calculate current seeding time including ongoing session
        current_seeding_time = self.seeding_time
        if self._seeding_started_at:
            current_seeding_time += int((datetime.utcnow() - self._seeding_started_at).total_seconds())
        
        return {
            "uploaded": self.uploaded,
            "downloaded": self.downloaded,
            "uploadSpeed": self.upload_speed,
            "seeders": self.seeders,
            "leechers": self.leechers,
            "lastAnnounce": self.last_announce,
            "nextAnnounce": self.next_announce,
            "ratio": self.uploaded / self.torrent.size if self.torrent.size > 0 else 0.0,
            "seedingTime": current_seeding_time
        }
