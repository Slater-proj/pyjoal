"""
Tracker Announcer
Handles announces to BitTorrent trackers
"""
import asyncio
import random
from typing import Optional, Dict
from datetime import datetime, timedelta
import httpx

from app.core.bittorrent_client import BitTorrentClient
from app.core.torrent_parser import Torrent
from app.models.schemas import AnnounceResponse
from app.core.config import settings
from app.services.history_service import history_service, EventType


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
        
        # State
        self.is_running: bool = False
        self._announce_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start announcing"""
        if self.is_running:
            return
        
        self.is_running = True
        self._announce_task = asyncio.create_task(self._announce_loop())
    
    async def stop(self):
        """Stop announcing"""
        if not self.is_running:
            return
        
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
            # Send started event
            await self._send_announce(event="started")
            
            while self.is_running:
                # Wait for next announce
                await asyncio.sleep(self.announce_interval)
                
                # Update stats
                self._update_stats()
                
                # Send regular announce
                await self._send_announce()
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"❌ Announce error for {self.torrent.name}: {e}")
    
    def _update_stats(self):
        """Update upload stats"""
        # Simulate upload
        min_rate, max_rate = self.client.get_upload_rate_range()
        self.upload_speed = random.randint(min_rate, max_rate)
        
        # Add to uploaded total (interval * speed)
        self.uploaded += self.upload_speed * self.announce_interval
        
        # We never download
        self.downloaded = 0
        self.left = 0  # We "have" the complete file
    
    async def _send_announce(self, event: Optional[str] = None):
        """Send announce to tracker"""
        tracker_url = self.torrent.primary_tracker
        if not tracker_url:
            return
        
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
        
        try:
            # Setup proxy if configured
            proxies = None
            if settings.HTTP_PROXY_HOST and settings.HTTP_PROXY_PORT:
                proxies = {
                    "http://": f"http://{settings.HTTP_PROXY_HOST}:{settings.HTTP_PROXY_PORT}",
                    "https://": f"http://{settings.HTTP_PROXY_HOST}:{settings.HTTP_PROXY_PORT}",
                }
            
            async with httpx.AsyncClient(
                headers=self.client.get_request_headers(),
                proxies=proxies,
                timeout=30.0
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Parse bencoded response
                data = response.content
                self._parse_announce_response(data)
                
                self.last_announce = datetime.utcnow()
                
                # Calculate next announce with jitter
                jitter = random.randint(-settings.ANNOUNCE_JITTER, settings.ANNOUNCE_JITTER)
                self.next_announce = self.last_announce + timedelta(
                    seconds=self.announce_interval + jitter
                )
                
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
                
                print(f"✅ Announced {self.torrent.name}: {self.seeders}S/{self.leechers}L")
                
        except Exception as e:
            # Log failed announce
            history_service.add_entry(
                EventType.ANNOUNCE_FAILED,
                f"Announce failed for {self.torrent.name}",
                {"torrent": self.torrent.name, "error": str(e)}
            )
            print(f"⚠️  Announce failed for {self.torrent.name}: {e}")
    
    def _parse_announce_response(self, data: bytes):
        """Parse tracker response"""
        try:
            import bencodepy
            response = bencodepy.decode(data)
            
            # Update interval
            if b'interval' in response:
                self.announce_interval = response[b'interval']
            
            # Update peer counts
            self.seeders = response.get(b'complete', 0)
            self.leechers = response.get(b'incomplete', 0)
            
        except Exception as e:
            print(f"⚠️  Failed to parse announce response: {e}")
    
    def get_stats(self) -> Dict:
        """Get current stats"""
        return {
            "uploaded": self.uploaded,
            "downloaded": self.downloaded,
            "uploadSpeed": self.upload_speed,
            "seeders": self.seeders,
            "leechers": self.leechers,
            "lastAnnounce": self.last_announce,
            "nextAnnounce": self.next_announce,
            "ratio": self.uploaded / self.torrent.size if self.torrent.size > 0 else 0.0
        }
