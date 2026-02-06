"""
Tracker Announcer
Handles announces to BitTorrent trackers (HTTP and UDP).

Orchestrates stats simulation (StatsSimulator) and tracker management (TrackerManager).
"""
import asyncio
import random
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import httpx

from app.core.bittorrent_client import BitTorrentClient
from app.core.torrent_parser import Torrent
from app.core.udp_tracker import UDPTrackerError, is_udp_tracker
from app.core.config import settings
from app.core.stats_simulator import StatsSimulator
from app.core.tracker_manager import TrackerManager
from app.services.history_service import history_service, EventType
from app.services.stealth_service import stealth_service

logger = logging.getLogger(__name__)


class TrackerAnnouncer:
    """Handles tracker announces for a torrent.
    
    Delegates stats simulation to StatsSimulator and tracker tier
    management to TrackerManager.
    """
    
    def __init__(self, torrent: Torrent, client: BitTorrentClient, discretion_config: Optional[Dict] = None):
        """Initialize announcer with optional discretion settings."""
        self.torrent = torrent
        self.client = client
        self.peer_id = client.generate_peer_id(torrent.info_hash)
        self.port = client.get_session_port()
        
        # Discretion configuration
        self.discretion_config = discretion_config or {}
        self.announce_interval = self.discretion_config.get("announce_interval", settings.ANNOUNCE_INTERVAL)
        self.announce_jitter = self.discretion_config.get("announce_jitter", settings.ANNOUNCE_JITTER)
        
        logger.debug(f"Discretion config for {torrent.name[:30]}: interval={self.announce_interval}s, jitter=±{self.announce_jitter}s")
        
        # --- Delegates ---
        self.stats = StatsSimulator(torrent.name, torrent.size, self.discretion_config)
        self.tracker_mgr = TrackerManager(torrent, client)
        
        # Initialize stats based on mode
        if self.stats.seeding_only_mode:
            self.stats.simulate_natural_seeding_start()
        else:
            self.stats.simulate_natural_download_start()
        
        # Peers info (updated from tracker responses)
        self.seeders: int = 0
        self.leechers: int = 0
        
        # Timing
        self.last_announce: Optional[datetime] = None
        self.next_announce: Optional[datetime] = None
        
        # Seeding time tracking (in seconds)
        self.seeding_time: int = 0
        self._seeding_started_at: Optional[datetime] = None
        
        # State
        self.is_running: bool = False
        self._announce_task: Optional[asyncio.Task] = None
        
        # Error tracking
        self.last_error: Optional[str] = None
        self.error_count: int = 0
        self.last_error_time: Optional[datetime] = None
        
        # Retry logic for stealth
        self.consecutive_failures: int = 0
        self.max_retries: int = 5
        self.base_retry_delay: int = 30
        self.last_retry_attempt: Optional[datetime] = None
        self._in_backoff: bool = False
        
        # Stealth profile for this session
        self.stealth_profile = stealth_service.get_session_profile(torrent.info_hash)
        
        # Track real announce success for speed calculation
        self._last_successful_announce: Optional[float] = None
        self._last_successful_uploaded: int = 0
    
    # ================================================================
    # Backward-compatible property accessors (delegate to stats)
    # ================================================================
    
    @property
    def uploaded(self) -> int:
        return self.stats.uploaded
    
    @uploaded.setter
    def uploaded(self, value: int):
        self.stats.uploaded = value
    
    @property
    def downloaded(self) -> int:
        return self.stats.downloaded
    
    @downloaded.setter
    def downloaded(self, value: int):
        self.stats.downloaded = value
    
    @property
    def left(self) -> int:
        return self.stats.left
    
    @left.setter
    def left(self, value: int):
        self.stats.left = value
    
    @property
    def upload_speed(self) -> float:
        return self.stats.upload_speed
    
    @upload_speed.setter
    def upload_speed(self, value: float):
        self.stats.upload_speed = value
    
    @property
    def _initial_seeding(self) -> bool:
        return self.stats._initial_seeding
    
    @_initial_seeding.setter
    def _initial_seeding(self, value: bool):
        self.stats._initial_seeding = value
    
    @property
    def _is_in_fake_pause(self) -> bool:
        return self.stats._is_in_fake_pause
    
    @property
    def _current_speed_tier(self) -> str:
        return self.stats._current_speed_tier
    
    @property
    def _peak_hours(self) -> tuple:
        return self.stats._peak_hours
    
    @property
    def _pause_until(self) -> Optional[datetime]:
        return self.stats._pause_until
    
    @property
    def _next_speed_change(self) -> Optional[datetime]:
        return self.stats._next_speed_change
    
    @property
    def seeding_only_mode(self) -> bool:
        return self.stats.seeding_only_mode
    
    @property
    def min_stats_update_interval(self) -> int:
        return self.stats.min_stats_update_interval
    
    @property
    def enable_speed_variation(self) -> bool:
        return self.stats.enable_speed_variation
    
    @property
    def speed_variation_percent(self) -> int:
        return self.stats.speed_variation_percent
    
    @property
    def reduced_speed_kbps(self) -> int:
        return self.stats.reduced_speed_kbps
    
    # Backward-compatible tracker manager proxies (accessed by tests)
    @property
    def _tracker_tiers(self):
        return self.tracker_mgr._tracker_tiers
    
    @property
    def _udp_trackers(self):
        return self.tracker_mgr._udp_trackers
    
    @property
    def _tracker_failures(self):
        return self.tracker_mgr._tracker_failures
    
    # ================================================================
    # Lifecycle
    # ================================================================
    
    async def start(self):
        """Start announcing."""
        if self.is_running:
            logger.debug(f"Announcer already running for {self.torrent.name}")
            return
        
        logger.info(f"🚀 Starting announcer for: {self.torrent.name}")
        logger.debug(f"   Torrent size: {self.torrent.size / (1024**3):.2f} GB")
        logger.debug(f"   Tracker: {self.torrent.primary_tracker}")
        logger.debug(f"   Peer ID: {self.peer_id}")
        logger.debug(f"   Port: {self.port}")
        
        self.is_running = True
        self._seeding_started_at = datetime.now(timezone.utc)
        
        if self._initial_seeding:
            logger.debug("   📋 Sending 'completed' event - torrent finished downloading")
            await self._send_announce(event="completed")
            self._initial_seeding = False
        
        if self.upload_speed == 0:
            self.upload_speed = self.stats.get_activity_based_upload_speed(self.client)
            logger.debug(f"   Initial upload speed: {self.upload_speed / 1024:.2f} KB/s")
        
        self._announce_task = asyncio.create_task(self._announce_loop())
    
    async def stop(self):
        """Stop announcing."""
        if not self.is_running:
            logger.debug(f"Announcer already stopped for {self.torrent.name}")
            return
        
        logger.info(f"⏹️  Stopping announcer for: {self.torrent.name}")
        logger.debug(f"   Total uploaded: {self.uploaded / (1024**2):.2f} MB")
        logger.debug(f"   Final ratio: {self.uploaded / self.torrent.size if self.torrent.size > 0 else 0:.3f}")
        
        if self._seeding_started_at:
            elapsed = (datetime.now(timezone.utc) - self._seeding_started_at).total_seconds()
            self.seeding_time += int(elapsed)
            self._seeding_started_at = None
        
        self.is_running = False
        
        if self._announce_task:
            self._announce_task.cancel()
            try:
                await self._announce_task
            except asyncio.CancelledError:
                pass
        
        await self._send_announce(event="stopped")
    
    # ================================================================
    # Announce loop
    # ================================================================
    
    async def _announce_loop(self):
        """Main announce loop."""
        try:
            logger.info(f"📢 Starting announce loop for: {self.torrent.name}")
            await self._send_announce(event="started")
            
            while self.is_running:
                actual_interval = stealth_service.get_natural_announce_interval(
                    self.torrent.info_hash, 
                    self.announce_interval
                )
                
                if self._in_backoff and self.last_retry_attempt:
                    backoff_time = self._calculate_backoff_delay()
                    time_since_last_retry = (datetime.now(timezone.utc) - self.last_retry_attempt).total_seconds()
                    if time_since_last_retry < backoff_time:
                        remaining_backoff = int(backoff_time - time_since_last_retry)
                        actual_interval = max(actual_interval, remaining_backoff)
                        logger.debug(f"🛡️ In backoff period, waiting {remaining_backoff}s more")
                
                if stealth_service.should_simulate_temporary_disconnect(self.torrent.info_hash):
                    disconnect_duration = stealth_service.get_disconnect_duration()
                    logger.debug(f"🎭 Simulating natural disconnect for {disconnect_duration}s")
                    actual_interval += disconnect_duration
                
                logger.debug(f"⏰ Natural interval: {actual_interval}s for {self.torrent.name}")
                await asyncio.sleep(actual_interval)
                
                if not self.is_running:
                    break
                
                self._update_stats_with_stealth()
                logger.debug(f"📊 Stats updated for {self.torrent.name}: uploaded={self.uploaded / (1024**2):.2f} MB, speed={self.upload_speed / 1024:.2f} KB/s")
                
                await self._send_announce_with_retry()
                
        except asyncio.CancelledError:
            logger.debug(f"Announce loop cancelled for {self.torrent.name}")
        except Exception as e:
            logger.error(f"❌ Announce error for {self.torrent.name}: {e}", exc_info=True)
            self._record_error(f"Announce loop error: {str(e)}")
    
    # ================================================================
    # Stats delegation
    # ================================================================
    
    def _update_stats(self):
        """Update upload stats with realistic behavior based on mode."""
        self.stats.update_stats(self.client, self.is_running)
    
    def _update_stats_for_display(self):
        """Update stats for UI display."""
        self.stats.update_stats_for_display(self.client, self.is_running, self.seeders, self.leechers)
    
    def _update_stats_with_stealth(self):
        """Update stats with stealth service natural variations."""
        self.stats.update_stats_with_stealth(
            self.client, stealth_service, self.torrent.info_hash, self.is_running,
            self.seeders, self.leechers
        )
    
    def _get_activity_based_upload_speed(self) -> int:
        """Get upload speed based on user activity patterns."""
        return self.stats.get_activity_based_upload_speed(self.client, self.seeders, self.leechers)
    
    def _is_user_active_hour(self) -> bool:
        """Check if current time is within user's peak activity hours."""
        return self.stats.is_user_active_hour()
    
    def _update_individual_state(self):
        """Update individual torrent state (pause/speed tier)."""
        self.stats.update_individual_state()
    
    def _simulate_natural_seeding_start(self):
        """Simulate realistic seeding start behavior."""
        self.stats.simulate_natural_seeding_start()
    
    def _simulate_natural_download_start(self):
        """Simulate realistic download start behavior."""
        self.stats.simulate_natural_download_start()
    
    def _is_in_downloading_phase(self) -> bool:
        """Check if torrent is still in downloading phase."""
        return self.stats.is_in_downloading_phase()
    
    def _simulate_occasional_network_errors(self) -> bool:
        """Simulate realistic network errors."""
        return self.stats.simulate_occasional_network_errors()
    
    # ================================================================
    # Tracker delegation
    # ================================================================
    
    def _build_tracker_tiers(self):
        return self.tracker_mgr._build_tracker_tiers()
    
    def _get_next_tracker(self):
        return self.tracker_mgr.get_next_tracker()
    
    def _mark_tracker_success(self, tracker_url: str):
        self.tracker_mgr.mark_tracker_success(tracker_url)
    
    def _mark_tracker_failure(self, tracker_url: str):
        self.tracker_mgr.mark_tracker_failure(tracker_url)
    
    async def scrape_tracker(self):
        return await self.tracker_mgr.scrape_tracker(self.torrent.info_hash_bytes)
    
    # ================================================================
    # Announce methods
    # ================================================================
    
    async def _send_announce(self, event: Optional[str] = None):
        """Send announce to tracker (legacy HTTP path)."""
        tracker_url = self.torrent.primary_tracker
        if not tracker_url:
            logger.warning(f"No tracker URL for {self.torrent.name}")
            return
        
        event_str = f" ({event})" if event else ""
        logger.info(f"📡 Sending announce{event_str} for: {self.torrent.name[:50]}")
        
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
        
        logger.debug("📤 Announce parameters:")
        logger.debug(f"   Tracker: {tracker_url}")
        logger.debug(f"   Info hash: {self.torrent.info_hash}")
        logger.debug(f"   Uploaded: {self.uploaded / (1024**2):.2f} MB")
        if event:
            logger.debug(f"   Event: {event}")
        
        if self._simulate_occasional_network_errors():
            return
            
        try:
            proxies = None
            if settings.HTTP_PROXY_HOST and settings.HTTP_PROXY_PORT:
                proxy_url = f"http://{settings.HTTP_PROXY_HOST}:{settings.HTTP_PROXY_PORT}"
                proxies = {"http://": proxy_url, "https://": proxy_url}
            
            headers = self.client.get_request_headers()
            
            async with httpx.AsyncClient(
                headers=headers, proxies=proxies, timeout=30.0, verify=False
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                self._parse_announce_response(response.content)
                
                self.last_announce = datetime.now(timezone.utc)
                jitter = random.randint(-self.announce_jitter, self.announce_jitter)
                self.next_announce = self.last_announce + timedelta(
                    seconds=self.announce_interval + jitter
                )
                
                logger.info(f"✅ Announce successful for {self.torrent.name[:50]}")
                logger.info(f"   Peers: {self.seeders} seeders, {self.leechers} leechers")
                
                if self.last_error:
                    self.last_error = None
                    self.last_error_time = None
                
                self._last_successful_announce = time.time()
                self._last_successful_uploaded = self.uploaded
                
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
            history_service.add_entry(
                EventType.ANNOUNCE_FAILED,
                f"Announce failed for {self.torrent.name}",
                {"torrent": self.torrent.name, "error": f"HTTP {e.response.status_code}"}
            )
        except httpx.TimeoutException as e:
            logger.error(f"⏱️  Timeout announcing {self.torrent.name}: {e}")
            self._record_error(f"Timeout: {str(e)}")
            history_service.add_entry(
                EventType.ANNOUNCE_FAILED,
                f"Announce timeout for {self.torrent.name}",
                {"torrent": self.torrent.name, "error": "Timeout"}
            )
        except Exception as e:
            logger.error(f"❌ Announce error for {self.torrent.name}: {e}", exc_info=True)
            self._record_error(f"Announce error: {str(e)}")
            history_service.add_entry(
                EventType.ANNOUNCE_FAILED,
                f"Announce failed for {self.torrent.name}",
                {"torrent": self.torrent.name, "error": str(e)}
            )
    
    async def _send_announce_with_retry(self, event: Optional[str] = None):
        """Send announce with intelligent retry logic."""
        max_attempts = self.max_retries + 1
        
        for attempt in range(max_attempts):
            try:
                await self._send_announce_stealth(event)
                self.consecutive_failures = 0
                self._in_backoff = False
                return
            except Exception as e:
                self.consecutive_failures += 1
                error_msg = str(e)
                is_last_attempt = attempt == max_attempts - 1
                
                if is_last_attempt:
                    self._record_error_silent(f"Final retry failed: {error_msg}")
                    logger.warning(f"🛡️ All {max_attempts} announce attempts failed for {self.torrent.name}: {error_msg}")
                    break
                else:
                    backoff_delay = self._calculate_backoff_delay()
                    self._in_backoff = True
                    self.last_retry_attempt = datetime.now(timezone.utc)
                    logger.debug(f"🛡️ Announce attempt {attempt + 1} failed, retrying in {backoff_delay}s: {error_msg}")
                    await asyncio.sleep(backoff_delay)

    async def _send_announce_stealth(self, event: Optional[str] = None):
        """Send announce using client's JOAL-compatible format (HTTP or UDP)."""
        tracker_url = self._get_next_tracker()
        if not tracker_url:
            raise Exception("No tracker available")
        
        if is_udp_tracker(tracker_url):
            await self._send_announce_udp(tracker_url, event)
            return
        
        await self._send_announce_http(tracker_url, event)
    
    async def _send_announce_http(self, tracker_url: str, event: Optional[str] = None):
        """Send HTTP announce using client's JOAL-compatible format."""
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
        
        headers = self.client.get_request_headers()
        timeout = httpx.Timeout(30.0)
        
        async with httpx.AsyncClient(timeout=timeout, headers=headers, verify=False, follow_redirects=True, max_redirects=5) as client:
            logger.debug(f"🎭 HTTP Announce to {tracker_url}")
            logger.debug(f"   Client: {self.client.name} {self.client.version}")
            
            start_time = time.time()
            response = await client.get(url)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code != 200:
                self._mark_tracker_failure(tracker_url)
                raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")
            
            self._parse_announce_response(response.content)
            self._mark_tracker_success(tracker_url)
            
            self.last_announce = datetime.now(timezone.utc)
            jitter = random.randint(-self.announce_jitter, self.announce_jitter)
            self.next_announce = self.last_announce + timedelta(
                seconds=self.announce_interval + jitter
            )
            
            logger.info(f"✅ HTTP Announce successful ({response_time:.0f}ms) for {self.torrent.name[:40]}")
            logger.info(f"   Peers: {self.seeders}S/{self.leechers}L | Uploaded: {self.uploaded / (1024**2):.2f} MB")
            
            history_service.add_entry(
                EventType.ANNOUNCE_SUCCESS,
                f"Announce successful for {self.torrent.name}",
                {
                    "tracker": tracker_url, 
                    "protocol": "HTTP",
                    "response_time_ms": int(response_time),
                    "seeders": self.seeders,
                    "leechers": self.leechers
                }
            )
    
    async def _send_announce_udp(self, tracker_url: str, event: Optional[str] = None):
        """Send UDP announce (BEP 15)."""
        try:
            udp_tracker = self.tracker_mgr.get_or_create_udp_tracker(tracker_url)
            
            logger.debug(f"📡 UDP Announce to {tracker_url}")
            start_time = time.time()
            
            key = self.client.generate_key(self.torrent.info_hash)
            key_int = int(key, 16) if isinstance(key, str) else key
            
            response = await udp_tracker.announce(
                info_hash=self.torrent.info_hash_bytes,
                peer_id=self.peer_id,
                port=self.port,
                uploaded=self.uploaded,
                downloaded=self.downloaded,
                left=self.left,
                event=event,
                key=key_int,
                numwant=200
            )
            
            response_time = (time.time() - start_time) * 1000
            
            self.seeders = response.seeders
            self.leechers = response.leechers
            
            if 60 <= response.interval <= 3600:
                self.announce_interval = response.interval
            
            self._mark_tracker_success(tracker_url)
            
            self.last_announce = datetime.now(timezone.utc)
            jitter = random.randint(-self.announce_jitter, self.announce_jitter)
            self.next_announce = self.last_announce + timedelta(
                seconds=self.announce_interval + jitter
            )
            
            logger.info(f"✅ UDP Announce successful ({response_time:.0f}ms) for {self.torrent.name[:40]}")
            logger.info(f"   Peers: {self.seeders}S/{self.leechers}L | Uploaded: {self.uploaded / (1024**2):.2f} MB")
            
            history_service.add_entry(
                EventType.ANNOUNCE_SUCCESS,
                f"UDP Announce successful for {self.torrent.name}",
                {
                    "tracker": tracker_url,
                    "protocol": "UDP",
                    "response_time_ms": int(response_time),
                    "seeders": self.seeders,
                    "leechers": self.leechers,
                    "peers_received": len(response.peers)
                }
            )
            
        except UDPTrackerError as e:
            self._mark_tracker_failure(tracker_url)
            logger.warning(f"❌ UDP Announce failed: {e}")
            raise Exception(f"UDP error: {e}")
        except Exception as e:
            self._mark_tracker_failure(tracker_url)
            logger.warning(f"❌ UDP Announce error: {e}")
            raise
    
    # ================================================================
    # Response parsing
    # ================================================================
    
    def _parse_announce_response(self, data: bytes):
        """Parse tracker response (BEP 3/23 - supports compact and non-compact)."""
        try:
            import bencodepy
            
            try:
                response = bencodepy.decode(data)
            except Exception as decode_err:
                logger.warning(f"Bencode decode error, trying recovery: {decode_err}")
                if b'd' in data and b'e' in data:
                    start = data.find(b'd')
                    response = bencodepy.decode(data[start:])
                else:
                    raise
            
            if b'failure reason' in response:
                reason = response[b'failure reason']
                if isinstance(reason, bytes):
                    reason = reason.decode('utf-8', errors='ignore')
                logger.error(f"❌ Tracker returned failure: {reason}")
                self._record_error(f"Tracker failure: {reason}")
                return
            
            if b'warning message' in response:
                warning = response[b'warning message']
                if isinstance(warning, bytes):
                    warning = warning.decode('utf-8', errors='ignore')
                logger.warning(f"⚠️ Tracker warning: {warning}")
            
            if b'min interval' in response:
                min_interval = response[b'min interval']
                if isinstance(min_interval, int) and min_interval > 0:
                    self.announce_interval = max(self.announce_interval, min_interval)
            
            if b'interval' in response:
                interval = response[b'interval']
                if isinstance(interval, int) and interval > 0:
                    old_interval = self.announce_interval
                    self.announce_interval = max(60, min(interval, 3600))
                    if old_interval != self.announce_interval:
                        logger.info(f"⏰ Announce interval updated: {old_interval}s -> {self.announce_interval}s")
            
            old_seeders = self.seeders
            old_leechers = self.leechers
            
            self.seeders = response.get(b'complete', response.get(b'seeders', 0))
            self.leechers = response.get(b'incomplete', response.get(b'leechers', 0))
            
            if not isinstance(self.seeders, int):
                self.seeders = 0
            if not isinstance(self.leechers, int):
                self.leechers = 0
            
            logger.debug(f"   Seeders: {old_seeders} -> {self.seeders}")
            logger.debug(f"   Leechers: {old_leechers} -> {self.leechers}")
            
            peer_count = 0
            if b'peers' in response:
                peers = response[b'peers']
                if isinstance(peers, bytes):
                    peer_count = len(peers) // 6
                elif isinstance(peers, list):
                    peer_count = len(peers)
            
            if b'peers6' in response:
                peers6 = response[b'peers6']
                if isinstance(peers6, bytes):
                    peer_count += len(peers6) // 18
            
            if b'external ip' in response:
                ext_ip = response[b'external ip']
                if isinstance(ext_ip, bytes) and len(ext_ip) == 4:
                    import socket
                    ip_str = socket.inet_ntoa(ext_ip)
                    logger.debug(f"   Tracker sees our IP as: {ip_str}")
            
            if b'tracker id' in response:
                self._tracker_id = response[b'tracker id']
                
        except Exception as e:
            logger.error(f"⚠️  Failed to parse announce response: {e}", exc_info=True)
    
    # ================================================================
    # Error handling / retry
    # ================================================================
    
    def _record_error(self, error_message: str):
        """Record error for display in UI."""
        self.last_error = error_message
        self.error_count += 1
        self.last_error_time = datetime.now(timezone.utc)
        logger.debug(f"Error recorded for {self.torrent.name}: {error_message}")

    def _record_error_silent(self, error_message: str):
        """Record error silently (only after all retries exhausted)."""
        self.last_error = error_message
        self.error_count += 1
        self.last_error_time = datetime.now(timezone.utc)
        logger.debug(f"Silent error recorded for {self.torrent.name}: {error_message}")
    
    def _calculate_backoff_delay(self) -> int:
        """Calculate exponential backoff delay."""
        delay = self.base_retry_delay * (2 ** (self.consecutive_failures - 1))
        max_delay = 300
        delay = min(delay, max_delay)
        jitter = random.uniform(0.8, 1.2)
        return int(delay * jitter)
    
    # ================================================================
    # Status / stats for UI
    # ================================================================
    
    def get_stats(self) -> Dict:
        """Get current stats with stealth information."""
        current_seeding_time = max(0, self.seeding_time)
        
        if self.is_running and self._seeding_started_at:
            session_duration = (datetime.now(timezone.utc) - self._seeding_started_at).total_seconds()
            session_duration = max(0, int(session_duration))
            current_seeding_time += session_duration
        
        stealth_stats = stealth_service.get_session_stats(self.torrent.info_hash)
        
        base_stats = {
            "uploaded": self.uploaded,
            "downloaded": self.downloaded,
            "uploadSpeed": int(self.upload_speed),
            "seeders": self.seeders,
            "leechers": self.leechers,
            "lastAnnounce": self.last_announce,
            "nextAnnounce": self.next_announce,
            "ratio": self.uploaded / self.torrent.size if self.torrent.size > 0 else 0.0,
            "seedingTime": current_seeding_time,
            "lastError": self.last_error,
            "errorCount": self.error_count,
            "lastErrorTime": self.last_error_time,
            "isHealthy": self.last_error is None or (
                self.last_announce is not None and 
                self.last_error_time is not None and 
                self.last_announce > self.last_error_time
            )
        }
        
        if stealth_stats:
            base_stats["stealth"] = {
                "client": stealth_stats.get("client", "Unknown"),
                "sessionDuration": stealth_stats.get("session_duration_hours", 0),
                "activityPattern": stealth_stats.get("activity_pattern", "steady"),
                "connectionStability": stealth_stats.get("connection_stability", 95.0),
                "consecutiveFailures": self.consecutive_failures,
                "inBackoff": self._in_backoff
            }
        
        base_stats["status"] = self.get_status_info()
        
        return base_stats
    
    def get_status_info(self) -> Dict[str, Any]:
        """Get detailed status information for UI display."""
        status_info = self.stats.get_status_info()
        
        # Override current_speed with actual client-aware speed
        current_speed = self._get_activity_based_upload_speed()
        status_info['current_speed'] = current_speed
        status_info['speed_formatted'] = f"{current_speed // 1024} kB/s" if current_speed >= 1024 else f"{current_speed} B/s"
        
        return status_info
