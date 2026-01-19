"""
Tracker Announcer
Handles announces to BitTorrent trackers (HTTP and UDP)
"""
import asyncio
import random
import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import httpx

from app.core.bittorrent_client import BitTorrentClient
from app.core.torrent_parser import Torrent
from app.core.udp_tracker import UDPTracker, is_udp_tracker, UDPTrackerError
from app.core.config import settings
from app.services.history_service import history_service, EventType
from app.services.stealth_service import stealth_service

logger = logging.getLogger(__name__)


class TrackerAnnouncer:
    """Handles tracker announces for a torrent"""
    
    def __init__(self, torrent: Torrent, client: BitTorrentClient, discretion_config: Optional[Dict] = None):
        """Initialize announcer with optional discretion settings"""
        self.torrent = torrent
        self.client = client
        self.peer_id = client.generate_peer_id(torrent.info_hash)
        self.port = client.get_session_port()  # Use consistent session port
        
        # Discretion configuration
        self.discretion_config = discretion_config or {}
        self.announce_interval = self.discretion_config.get("announce_interval", settings.ANNOUNCE_INTERVAL)
        self.announce_jitter = self.discretion_config.get("announce_jitter", settings.ANNOUNCE_JITTER)
        self.min_stats_update_interval = self.discretion_config.get("min_stats_update_interval", settings.MIN_STATS_UPDATE_INTERVAL)
        self.enable_speed_variation = self.discretion_config.get("enable_speed_variation", settings.ENABLE_SPEED_VARIATION)
        self.speed_variation_percent = self.discretion_config.get("speed_variation_percent", settings.SPEED_VARIATION_PERCENT)
        
        # 🎯 Torrent Behavior Mode
        self.seeding_only_mode = self.discretion_config.get("seedingOnlyMode", settings.SEEDING_ONLY_MODE)
        
        # 🎭 Realistic Behavior Timing (in minutes/hours for human-like behavior)
        self.pause_duration_min = self.discretion_config.get("pauseDurationMin", settings.PAUSE_DURATION_MIN)  # minutes
        self.pause_duration_max = self.discretion_config.get("pauseDurationMax", settings.PAUSE_DURATION_MAX)  # minutes
        self.reduced_speed_duration_min = self.discretion_config.get("reducedSpeedDurationMin", settings.REDUCED_SPEED_DURATION_MIN)  # minutes
        self.reduced_speed_duration_max = self.discretion_config.get("reducedSpeedDurationMax", settings.REDUCED_SPEED_DURATION_MAX)  # minutes
        self.state_change_interval_min = self.discretion_config.get("stateChangeIntervalMin", settings.STATE_CHANGE_INTERVAL_MIN)  # hours
        self.state_change_interval_max = self.discretion_config.get("stateChangeIntervalMax", settings.STATE_CHANGE_INTERVAL_MAX)  # hours
        self.reduced_speed_kbps = self.discretion_config.get("reducedSpeedKbps", settings.REDUCED_SPEED_KBPS)  # kB/s
        
        logger.debug(f"Discretion config for {torrent.name[:30]}: interval={self.announce_interval}s, jitter=±{self.announce_jitter}s, min_update={self.min_stats_update_interval}s")
        
        # Enhanced realistic stats simulation
        # ⚠️ IMPORTANT: Torrent is already downloaded, we're only seeding!
        self.uploaded: int = 0  # Start with 0 upload (will increase during seeding)
        self.downloaded: int = torrent.size  # Already fully downloaded
        self.left: int = 0  # Nothing left to download
        self.upload_speed: int = 0
        
        # Realistic behavior simulation based on mode
        if self.seeding_only_mode:
            # Mode: Seeding Only (torrents already downloaded by real client)
            self._simulate_natural_seeding_start()
        else:
            # Mode: Download Simulation (simulate full download cycle)
            self._simulate_natural_download_start()
        
        # Peers info
        self.seeders: int = 0
        self.leechers: int = 0
        
        # Timing
        self.last_announce: Optional[datetime] = None
        self.next_announce: Optional[datetime] = None
        # Use instance config instead of global settings
        # self.announce_interval is set in __init__ from discretion_config
        
        # Seeding time tracking (in seconds)
        self.seeding_time: int = 0
        self._seeding_started_at: Optional[datetime] = None
        
        # State
        self.is_running: bool = False
        self._announce_task: Optional[asyncio.Task] = None
        self._is_downloading: bool = True  # Start in downloading phase
        self._download_completion_time: Optional[datetime] = None
        
        # Error tracking
        self.last_error: Optional[str] = None
        self.error_count: int = 0
        self.last_error_time: Optional[datetime] = None
        
        # 🛡️ Retry logic for stealth
        self.consecutive_failures: int = 0
        self.max_retries: int = 5
        self.base_retry_delay: int = 30  # Base delay in seconds
        self.last_retry_attempt: Optional[datetime] = None
        self._in_backoff: bool = False
        
        # 🎭 Stealth profile for this session
        self.stealth_profile = stealth_service.get_session_profile(torrent.info_hash)
        
        # Track real announce success for speed calculation
        self._last_successful_announce: Optional[datetime] = None
        self._last_successful_uploaded: int = 0
        
        # 📡 UDP tracker support
        self._udp_trackers: Dict[str, UDPTracker] = {}
        
        # 🔄 Multi-tracker support (announce-list tiers)
        self._tracker_tiers: List[List[str]] = self._build_tracker_tiers()
        self._current_tier: int = 0
        self._current_tracker_idx: int = 0
        self._tracker_failures: Dict[str, int] = {}  # Track failures per tracker
    
    def _build_tracker_tiers(self) -> List[List[str]]:
        """Build tracker tiers from announce-list (BEP 12)"""
        tiers = []
        
        # Check if torrent has announce-list
        if hasattr(self.torrent, 'announce_list') and self.torrent.announce_list:
            for tier in self.torrent.announce_list:
                if isinstance(tier, list):
                    valid_trackers = [t for t in tier if t and isinstance(t, str)]
                    if valid_trackers:
                        # Randomize order within tier (per spec)
                        random.shuffle(valid_trackers)
                        tiers.append(valid_trackers)
                elif isinstance(tier, str) and tier:
                    tiers.append([tier])
        
        # Fallback to primary tracker if no announce-list
        if not tiers and self.torrent.primary_tracker:
            tiers.append([self.torrent.primary_tracker])
        
        logger.debug(f"Built {len(tiers)} tracker tier(s) for {self.torrent.name[:30]}")
        return tiers
    
    def _get_next_tracker(self) -> Optional[str]:
        """Get next tracker to try (respecting tiers)"""
        if not self._tracker_tiers:
            return self.torrent.primary_tracker
        
        # Try current tier first
        while self._current_tier < len(self._tracker_tiers):
            tier = self._tracker_tiers[self._current_tier]
            
            while self._current_tracker_idx < len(tier):
                tracker = tier[self._current_tracker_idx]
                self._current_tracker_idx += 1
                
                # Skip trackers that have failed too many times
                if self._tracker_failures.get(tracker, 0) < 3:
                    return tracker
            
            # Move to next tier
            self._current_tier += 1
            self._current_tracker_idx = 0
        
        # Reset and start over if all tiers exhausted
        self._current_tier = 0
        self._current_tracker_idx = 0
        
        # Return first tracker
        if self._tracker_tiers and self._tracker_tiers[0]:
            return self._tracker_tiers[0][0]
        
        return self.torrent.primary_tracker
    
    def _mark_tracker_success(self, tracker_url: str):
        """Mark tracker as successful (reset failure count)"""
        self._tracker_failures[tracker_url] = 0
        # Move successful tracker to front of its tier
        for tier in self._tracker_tiers:
            if tracker_url in tier:
                tier.remove(tracker_url)
                tier.insert(0, tracker_url)
                break
    
    def _mark_tracker_failure(self, tracker_url: str):
        """Mark tracker as failed"""
        self._tracker_failures[tracker_url] = self._tracker_failures.get(tracker_url, 0) + 1
        logger.debug(f"Tracker failure #{self._tracker_failures[tracker_url]}: {tracker_url}")
    
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
        
        # 🎯 Send initial "completed" event (natural behavior after download)
        if self._initial_seeding:
            logger.debug("   📋 Sending 'completed' event - torrent finished downloading")
            await self._send_announce(event="completed")
            self._initial_seeding = False
        
        # Initialize upload speed if not set
        if self.upload_speed == 0:
            # Start with activity-based speed
            self.upload_speed = self._get_activity_based_upload_speed()
            logger.debug(f"   Initial upload speed: {self.upload_speed / 1024:.2f} KB/s")
        
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
                # 🎭 Use intelligent stealth timing instead of basic jitter
                actual_interval = stealth_service.get_natural_announce_interval(
                    self.torrent.info_hash, 
                    self.announce_interval
                )
                
                # 🛡️ Check if in backoff period due to failures
                if self._in_backoff and self.last_retry_attempt:
                    backoff_time = self._calculate_backoff_delay()
                    time_since_last_retry = (datetime.utcnow() - self.last_retry_attempt).total_seconds()
                    if time_since_last_retry < backoff_time:
                        remaining_backoff = int(backoff_time - time_since_last_retry)
                        actual_interval = max(actual_interval, remaining_backoff)
                        logger.debug(f"🛡️ In backoff period, waiting {remaining_backoff}s more")
                
                # 🎲 Natural disconnection simulation
                if stealth_service.should_simulate_temporary_disconnect(self.torrent.info_hash):
                    disconnect_duration = stealth_service.get_disconnect_duration()
                    logger.debug(f"🎭 Simulating natural disconnect for {disconnect_duration}s")
                    actual_interval += disconnect_duration
                
                logger.debug(f"⏰ Natural interval: {actual_interval}s for {self.torrent.name}")
                await asyncio.sleep(actual_interval)
                
                if not self.is_running:
                    break
                
                # Update stats with stealth variations
                self._update_stats_with_stealth()
                logger.debug(f"📊 Stats updated for {self.torrent.name}: uploaded={self.uploaded / (1024**2):.2f} MB, speed={self.upload_speed / 1024:.2f} KB/s")
                
                # 🛡️ Send announce with retry logic
                await self._send_announce_with_retry()
                
        except asyncio.CancelledError:
            logger.debug(f"Announce loop cancelled for {self.torrent.name}")
        except Exception as e:
            logger.error(f"❌ Announce error for {self.torrent.name}: {e}", exc_info=True)
            self._record_error(f"Announce loop error: {str(e)}")
    
    def _update_stats(self):
        """Update upload stats with realistic behavior based on mode
        
        ⚠️ IMPORTANT: Cette méthode est appelée régulièrement pour simuler le seeding.
        Elle calcule: vitesse upload, bytes uploadés, ratio, etc.
        """
        if not self.is_running:
            return
        
        current_time = time.time()
        
        # Initialiser _last_stats_update si pas encore fait
        if not hasattr(self, '_last_stats_update') or self._last_stats_update is None:
            self._last_stats_update = current_time
            self._last_upload_time = current_time
            logger.debug(f"📊 Stats tracking initialized for {self.torrent.name[:30]}")
        
        # Vérifier l'intervalle minimum entre mises à jour
        time_since_last = current_time - self._last_stats_update
        if time_since_last < self.min_stats_update_interval:
            return
        
        self._last_stats_update = current_time
        
        # Handle downloading phase (if download simulation mode enabled)
        if not self.seeding_only_mode and self._is_in_downloading_phase():
            self._update_download_stats()
            return
            
        # 🌱 SEEDING: Calculer la vitesse et les bytes uploadés
        # Récupérer la vitesse basée sur l'activité et la config
        current_speed = self._get_activity_based_upload_speed()
        
        # Appliquer variation si activée (fluctuations naturelles)
        if self.enable_speed_variation and current_speed > 0:
            variation_factor = 1.0 + random.uniform(
                -self.speed_variation_percent / 100.0,
                self.speed_variation_percent / 100.0
            )
            current_speed = int(current_speed * variation_factor)
        
        # Calculer le temps écoulé depuis la dernière mise à jour
        if hasattr(self, '_last_upload_time') and self._last_upload_time is not None:
            time_interval = current_time - self._last_upload_time
        else:
            time_interval = 3  # Défaut pour le premier appel (3 secondes = intervalle du monitor)
        
        self._last_upload_time = current_time
        
        # 📈 CALCUL DES BYTES UPLOADÉS
        # C'est ici que le "fake seeding" se passe réellement
        if current_speed > 0:
            # Limiter l'intervalle à 10s max pour éviter des sauts énormes
            capped_interval = min(time_interval, 10)
            upload_delta = int(current_speed * capped_interval)
            
            # Ajouter au total uploadé
            self.uploaded += upload_delta
            
            logger.info(f"📈 UPLOAD: {self.torrent.name[:25]} +{upload_delta/1024:.1f}KB ({current_speed/1024:.1f}KB/s × {capped_interval:.1f}s) = Total: {self.uploaded/(1024*1024):.2f}MB")
            
            # Track upload progress for natural seeding patterns
            if hasattr(self, '_seeding_session_start') and self._seeding_session_start:
                self._total_seeding_time = (datetime.utcnow() - self._seeding_session_start).total_seconds()
        else:
            logger.debug(f"⚠️ Speed=0 for {self.torrent.name[:30]} - no upload this interval")
            
        # 🎯 METTRE À JOUR LA VITESSE D'UPLOAD
        self.upload_speed = float(current_speed)
        
        # S'assurer que downloaded/left sont corrects (mode seeding)
        self.downloaded = self.torrent.size
        self.left = 0
    
    def _update_stats_for_display(self):
        """Mise à jour des stats pour l'affichage UI - appelée par le monitor loop
        
        Cette méthode est appelée toutes les 3 secondes par le monitor pour
        garantir que l'UI affiche des valeurs qui changent.
        """
        if not self.is_running:
            self.upload_speed = 0
            return
        
        current_time = time.time()
        
        # Initialiser si nécessaire
        if not hasattr(self, '_display_update_time') or self._display_update_time is None:
            self._display_update_time = current_time
            self._last_upload_time = current_time
            self._last_stats_update = current_time
        
        # Calculer le temps écoulé
        time_interval = current_time - self._display_update_time
        self._display_update_time = current_time
        
        # Obtenir une nouvelle vitesse (qui va varier à chaque appel)
        current_speed = self._get_activity_based_upload_speed()
        
        # Appliquer variation
        if self.enable_speed_variation and current_speed > 0:
            variation = random.uniform(-self.speed_variation_percent/100, self.speed_variation_percent/100)
            current_speed = int(current_speed * (1 + variation))
        
        # Calculer les bytes uploadés
        upload_delta = 0  # Initialiser avant utilisation
        if current_speed > 0 and time_interval > 0:
            capped_interval = min(time_interval, 10)
            upload_delta = int(current_speed * capped_interval)
            self.uploaded += upload_delta
            
            logger.debug(f"📊 Display update: {self.torrent.name[:20]} speed={current_speed/1024:.0f}KB/s, +{upload_delta/1024:.1f}KB, total={self.uploaded/(1024*1024):.2f}MB")
        
        # Mettre à jour la vitesse affichée
        self.upload_speed = float(current_speed)
        
        # Mettre à jour les timestamps
        self._last_upload_time = current_time
        self._last_stats_update = current_time
        
        logger.debug(f"🌱 Seeding stats for {self.torrent.name[:30]}:")
        logger.debug(f"   Speed: {current_speed / 1024:.2f} KB/s (activity-based) - Time delta: {time_interval:.1f}s")
        if current_speed > 0:
            logger.debug(f"   Session time: {self._total_seeding_time / 3600:.1f}h")
            logger.debug(f"   Upload delta this interval: {upload_delta / 1024:.2f} KB")
            logger.debug(f"   Total uploaded: {self.uploaded / (1024**2):.2f} MB")
            logger.debug(f"   Ratio: {self.uploaded / self.torrent.size if self.torrent.size > 0 else 0:.3f}")
        else:
            logger.debug("   Speed is 0 - no upload progress made")
    
    def _update_download_stats(self):
        """Update download stats during download simulation phase"""
        current_time = time.time()
        
        # Realistic download speed (usually much faster than upload)
        download_speed = self._get_realistic_download_speed()
        
        # Calculate download progress
        if hasattr(self, '_last_download_time'):
            time_interval = current_time - self._last_download_time
        else:
            time_interval = 5  # Default for first call
            
        self._last_download_time = current_time
        
        # Calculate bytes downloaded in this interval
        download_delta = download_speed * min(time_interval, 10)  # Cap at 10s intervals
        
        # Update progress
        self.downloaded = min(self.downloaded + download_delta, self.torrent.size)
        self.left = max(0, self.torrent.size - self.downloaded)
        
        # Small amount of upload during download (normal peer behavior)
        upload_speed = max(download_speed * 0.1, 1024)  # 10% of download speed
        upload_delta = upload_speed * min(time_interval, 10)
        self.uploaded += upload_delta
        
        # Set speeds
        self.download_speed = float(download_speed)
        self.upload_speed = float(upload_speed)
        
        logger.debug(f"📥 Download stats for {self.torrent.name[:30]}:")
        logger.debug(f"   Progress: {(self.downloaded/self.torrent.size)*100:.1f}% ({self.left/(1024**2):.2f} MB left)")
        logger.debug(f"   DL Speed: {download_speed/1024:.2f} KB/s, UL Speed: {upload_speed/1024:.2f} KB/s")
    
    def _get_realistic_download_speed(self) -> int:
        """Get realistic download speed during download simulation"""
        # Base download speed (usually much faster than upload)
        min_dl, max_dl = self.client.get_download_rate_range() if hasattr(self.client, 'get_download_rate_range') else (102400, 1048576)  # 100KB/s - 1MB/s
        
        base_speed = random.randint(min_dl, max_dl)
        
        # Adjust based on activity patterns
        hour = datetime.utcnow().hour
        if hour in self._peak_hours:
            base_speed = int(base_speed * 1.2)  # Faster during peak hours
        elif hour < 6 or hour > 22:  # Late night/early morning
            base_speed = int(base_speed * 0.8)  # Slower during off hours
            
        return max(base_speed, 10240)  # Minimum 10KB/s
    
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
        logger.debug("📤 Announce parameters:")
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
        
        # Simulate occasional network errors for realism
        if self._simulate_occasional_network_errors():
            return  # Skip this announce due to simulated error
            
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
                logger.debug("   Sending HTTP GET request...")
                response = await client.get(url)
                logger.debug(f"   Response status: {response.status_code}")
                response.raise_for_status()
                
                # Parse bencoded response
                data = response.content
                logger.debug(f"   Response size: {len(data)} bytes")
                self._parse_announce_response(data)
                
                self.last_announce = datetime.utcnow()
                
                # Calculate next announce with configured jitter
                jitter = random.randint(-self.announce_jitter, self.announce_jitter)
                self.next_announce = self.last_announce + timedelta(
                    seconds=self.announce_interval + jitter
                )
                
                logger.info(f"✅ Announce successful for {self.torrent.name[:50]}")
                logger.info(f"   Peers: {self.seeders} seeders, {self.leechers} leechers")
                logger.info(f"   Uploaded: {self.uploaded / (1024**2):.2f} MB (speed: {self.upload_speed / 1024:.2f} KB/s)")
                logger.info(f"   Next announce in {self.announce_interval + jitter}s")
                
                # Clear any previous error on success
                if self.last_error:
                    logger.debug(f"Clearing previous error for {self.torrent.name}")
                    self.last_error = None
                    self.last_error_time = None
                
                # Record successful announce for real speed calculation
                self._last_successful_announce = time.time()
                self._last_successful_uploaded = self.uploaded
                logger.debug(f"📈 Recorded successful announce: uploaded={self.uploaded}, time={self._last_successful_announce}")
                
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
            self._record_error(f"Timeout: {str(e)}")
            history_service.add_entry(
                EventType.ANNOUNCE_FAILED,
                f"Announce timeout for {self.torrent.name}",
                {"torrent": self.torrent.name, "error": "Timeout"}
            )
        except Exception as e:
            logger.error(f"❌ Announce error for {self.torrent.name}: {e}", exc_info=True)
            self._record_error(f"Announce error: {str(e)}")
            # Log failed announce
            history_service.add_entry(
                EventType.ANNOUNCE_FAILED,
                f"Announce failed for {self.torrent.name}",
                {"torrent": self.torrent.name, "error": str(e)}
            )
    
    def _parse_announce_response(self, data: bytes):
        """Parse tracker response (BEP 3/23 - supports compact and non-compact)"""
        try:
            import bencodepy
            
            # Handle potential encoding issues
            try:
                response = bencodepy.decode(data)
            except Exception as decode_err:
                # Try to salvage partial response
                logger.warning(f"Bencode decode error, trying recovery: {decode_err}")
                # Some trackers send malformed responses with extra data
                if b'd' in data and b'e' in data:
                    # Find the bencoded dict boundaries
                    start = data.find(b'd')
                    response = bencodepy.decode(data[start:])
                else:
                    raise
            
            logger.debug(f"📥 Parsing tracker response for {self.torrent.name[:30]}")
            
            # Check for failure
            if b'failure reason' in response:
                reason = response[b'failure reason']
                if isinstance(reason, bytes):
                    reason = reason.decode('utf-8', errors='ignore')
                logger.error(f"❌ Tracker returned failure: {reason}")
                self._record_error(f"Tracker failure: {reason}")
                return
            
            # Check for warning (non-fatal)
            if b'warning message' in response:
                warning = response[b'warning message']
                if isinstance(warning, bytes):
                    warning = warning.decode('utf-8', errors='ignore')
                logger.warning(f"⚠️ Tracker warning: {warning}")
            
            # Update interval (use min_interval if provided for politeness)
            if b'min interval' in response:
                min_interval = response[b'min interval']
                if isinstance(min_interval, int) and min_interval > 0:
                    self.announce_interval = max(self.announce_interval, min_interval)
            
            if b'interval' in response:
                interval = response[b'interval']
                if isinstance(interval, int) and interval > 0:
                    old_interval = self.announce_interval
                    # Respect tracker's interval but cap at reasonable bounds
                    self.announce_interval = max(60, min(interval, 3600))
                    if old_interval != self.announce_interval:
                        logger.info(f"⏰ Announce interval updated: {old_interval}s -> {self.announce_interval}s")
            
            # Update peer counts
            old_seeders = self.seeders
            old_leechers = self.leechers
            
            # Handle different key names used by trackers
            self.seeders = response.get(b'complete', response.get(b'seeders', 0))
            self.leechers = response.get(b'incomplete', response.get(b'leechers', 0))
            
            # Ensure they're integers
            if not isinstance(self.seeders, int):
                self.seeders = 0
            if not isinstance(self.leechers, int):
                self.leechers = 0
            
            logger.debug(f"   Interval: {self.announce_interval}s")
            logger.debug(f"   Seeders: {old_seeders} -> {self.seeders}")
            logger.debug(f"   Leechers: {old_leechers} -> {self.leechers}")
            
            # Parse peer list (BEP 23 compact format or BEP 3 dictionary format)
            peer_count = 0
            if b'peers' in response:
                peers = response[b'peers']
                if isinstance(peers, bytes):
                    # Compact format (BEP 23): 6 bytes per peer (4 IP + 2 port)
                    peer_count = len(peers) // 6
                    logger.debug(f"   Received {peer_count} peer(s) (compact IPv4)")
                elif isinstance(peers, list):
                    # Dictionary format (BEP 3)
                    peer_count = len(peers)
                    logger.debug(f"   Received {peer_count} peer(s) (dictionary format)")
            
            # IPv6 peers (BEP 7)
            if b'peers6' in response:
                peers6 = response[b'peers6']
                if isinstance(peers6, bytes):
                    # Compact IPv6: 18 bytes per peer (16 IP + 2 port)
                    peer6_count = len(peers6) // 18
                    logger.debug(f"   Received {peer6_count} IPv6 peer(s)")
                    peer_count += peer6_count
            
            # External IP reported by tracker (useful for debugging)
            if b'external ip' in response:
                ext_ip = response[b'external ip']
                if isinstance(ext_ip, bytes) and len(ext_ip) == 4:
                    import socket
                    ip_str = socket.inet_ntoa(ext_ip)
                    logger.debug(f"   Tracker sees our IP as: {ip_str}")
            
            # Tracker ID for subsequent announces
            if b'tracker id' in response:
                self._tracker_id = response[b'tracker id']
                logger.debug("   Tracker ID received")
            
        except Exception as e:
            logger.error(f"⚠️  Failed to parse announce response: {e}", exc_info=True)
    
    def _record_error(self, error_message: str):
        """Record error for display in UI"""
        self.last_error = error_message
        self.error_count += 1
        self.last_error_time = datetime.utcnow()
        logger.debug(f"Error recorded for {self.torrent.name}: {error_message}")

    def _update_stats_with_stealth(self):
        """Update stats with stealth service natural variations"""
        if not self.is_running:
            return
        
        # Check if enough time has passed for realistic update
        current_time = time.time()
        if hasattr(self, '_last_stats_update'):
            time_since_last = current_time - self._last_stats_update
            if time_since_last < self.min_stats_update_interval:
                return
        
        self._last_stats_update = current_time
        
        # Handle downloading phase (if download simulation mode enabled)
        if not self.seeding_only_mode and self._is_in_downloading_phase():
            self._update_download_stats()
            return
            
        # 🌱 Enhanced seeding behavior with stealth variations
        base_speed = self._get_activity_based_upload_speed()
        
        # 🎭 Apply stealth service natural speed variations
        current_speed = stealth_service.get_natural_speed_variation(
            base_speed, 
            self.torrent.info_hash
        )
        
        # Calculate realistic upload progress
        if current_speed > 0:
            if hasattr(self, '_last_upload_time'):
                time_interval = current_time - self._last_upload_time
            else:
                time_interval = 5  # Default for first call
            
            self._last_upload_time = current_time
            
            # Calculate bytes uploaded in this interval
            upload_delta = current_speed * min(time_interval, 10)  # Cap at 10s intervals
            self.uploaded += upload_delta
            
            # Track upload progress for natural seeding patterns
            if hasattr(self, '_seeding_session_start'):
                self._total_seeding_time = (datetime.utcnow() - self._seeding_session_start).total_seconds()
            
        # Set upload speed
        self.upload_speed = float(current_speed)
        
        # Ensure downloaded/left stay correct (seeding mode)
        self.downloaded = self.torrent.size
        self.left = 0
        
        logger.debug(f"🎭 Stealth seeding stats for {self.torrent.name[:30]}:")
        logger.debug(f"   Speed: {current_speed / 1024:.2f} KB/s (stealth-enhanced)")

    async def _send_announce_with_retry(self, event: Optional[str] = None):
        """Send announce with intelligent retry logic"""
        max_attempts = self.max_retries + 1
        
        for attempt in range(max_attempts):
            try:
                # 🎭 Use stealth profile for User-Agent and port
                await self._send_announce_stealth(event)
                
                # ✅ Success - reset failure tracking
                self.consecutive_failures = 0
                self._in_backoff = False
                return
                
            except Exception as e:
                self.consecutive_failures += 1
                error_msg = str(e)
                
                # 🛡️ Silent retry logic - don't expose errors on early attempts
                is_last_attempt = attempt == max_attempts - 1
                
                if is_last_attempt:
                    # Only record error on final failure
                    self._record_error_silent(f"Final retry failed: {error_msg}")
                    logger.warning(f"🛡️ All {max_attempts} announce attempts failed for {self.torrent.name}: {error_msg}")
                    break
                else:
                    # Silent retry with backoff
                    backoff_delay = self._calculate_backoff_delay()
                    self._in_backoff = True
                    self.last_retry_attempt = datetime.utcnow()
                    
                    logger.debug(f"🛡️ Announce attempt {attempt + 1} failed, retrying in {backoff_delay}s: {error_msg}")
                    await asyncio.sleep(backoff_delay)

    async def _send_announce_stealth(self, event: Optional[str] = None):
        """Send announce using client's JOAL-compatible format (HTTP or UDP)"""
        tracker_url = self._get_next_tracker()
        if not tracker_url:
            raise Exception("No tracker available")
        
        # Check if UDP tracker
        if is_udp_tracker(tracker_url):
            await self._send_announce_udp(tracker_url, event)
            return
        
        # HTTP tracker
        await self._send_announce_http(tracker_url, event)
    
    async def _send_announce_http(self, tracker_url: str, event: Optional[str] = None):
        """Send HTTP announce using client's JOAL-compatible format"""
        # 🎭 Build announce URL using client's query template (JOAL compatible)
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
        
        # 🎭 Use client's configured headers
        headers = self.client.get_request_headers()
        
        timeout = httpx.Timeout(30.0)
        
        async with httpx.AsyncClient(timeout=timeout, headers=headers, verify=False, follow_redirects=True, max_redirects=5) as client:
            logger.debug(f"🎭 HTTP Announce to {tracker_url}")
            logger.debug(f"   Client: {self.client.name} {self.client.version}")
            logger.debug(f"   Port: {self.port}")
            logger.debug(f"   Peer ID: {self.peer_id}")
            logger.debug(f"   URL: {url[:150]}...")
            
            start_time = time.time()
            response = await client.get(url)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code != 200:
                self._mark_tracker_failure(tracker_url)
                raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")
            
            # Parse and handle response
            self._parse_announce_response(response.content)
            
            # Mark success
            self._mark_tracker_success(tracker_url)
            
            # Update timing
            self.last_announce = datetime.utcnow()
            jitter = random.randint(-self.announce_jitter, self.announce_jitter)
            self.next_announce = self.last_announce + timedelta(
                seconds=self.announce_interval + jitter
            )
            
            logger.info(f"✅ HTTP Announce successful ({response_time:.0f}ms) for {self.torrent.name[:40]}")
            logger.info(f"   Peers: {self.seeders}S/{self.leechers}L | Uploaded: {self.uploaded / (1024**2):.2f} MB")
            
            # Record success in history
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
        """Send UDP announce (BEP 15)"""
        try:
            # Get or create UDP tracker client
            if tracker_url not in self._udp_trackers:
                self._udp_trackers[tracker_url] = UDPTracker(tracker_url)
            
            udp_tracker = self._udp_trackers[tracker_url]
            
            logger.debug(f"📡 UDP Announce to {tracker_url}")
            logger.debug(f"   Event: {event}")
            logger.debug(f"   Uploaded: {self.uploaded / (1024**2):.2f} MB")
            
            start_time = time.time()
            
            # Generate key for this session
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
            
            # Update stats from response
            self.seeders = response.seeders
            self.leechers = response.leechers
            
            # Use interval from tracker if reasonable
            if 60 <= response.interval <= 3600:
                self.announce_interval = response.interval
            
            # Mark success
            self._mark_tracker_success(tracker_url)
            
            # Update timing
            self.last_announce = datetime.utcnow()
            jitter = random.randint(-self.announce_jitter, self.announce_jitter)
            self.next_announce = self.last_announce + timedelta(
                seconds=self.announce_interval + jitter
            )
            
            logger.info(f"✅ UDP Announce successful ({response_time:.0f}ms) for {self.torrent.name[:40]}")
            logger.info(f"   Peers: {self.seeders}S/{self.leechers}L | Uploaded: {self.uploaded / (1024**2):.2f} MB")
            
            # Record success in history
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
    
    async def scrape_tracker(self) -> Optional[Dict[str, int]]:
        """Scrape tracker for torrent stats (seeders/leechers)"""
        tracker_url = self._get_next_tracker()
        if not tracker_url:
            return None
        
        try:
            if is_udp_tracker(tracker_url):
                return await self._scrape_udp(tracker_url)
            else:
                return await self._scrape_http(tracker_url)
        except Exception as e:
            logger.debug(f"Scrape failed for {tracker_url}: {e}")
            return None
    
    async def _scrape_udp(self, tracker_url: str) -> Optional[Dict[str, int]]:
        """Scrape UDP tracker"""
        try:
            if tracker_url not in self._udp_trackers:
                self._udp_trackers[tracker_url] = UDPTracker(tracker_url)
            
            udp_tracker = self._udp_trackers[tracker_url]
            results = await udp_tracker.scrape([self.torrent.info_hash_bytes])
            
            if self.torrent.info_hash_bytes in results:
                scrape = results[self.torrent.info_hash_bytes]
                return {
                    'seeders': scrape.seeders,
                    'leechers': scrape.leechers,
                    'completed': scrape.completed
                }
        except Exception as e:
            logger.debug(f"UDP scrape failed: {e}")
        
        return None
    
    async def _scrape_http(self, tracker_url: str) -> Optional[Dict[str, int]]:
        """Scrape HTTP tracker"""
        try:
            # Convert announce URL to scrape URL
            scrape_url = tracker_url.replace('/announce', '/scrape')
            if scrape_url == tracker_url:
                return None  # Not a standard tracker URL
            
            # Add info_hash parameter
            encoded_hash = self.client.url_encode(self.torrent.info_hash_bytes)
            scrape_url = f"{scrape_url}?info_hash={encoded_hash}"
            
            headers = self.client.get_request_headers()
            
            async with httpx.AsyncClient(timeout=15.0, headers=headers, verify=False) as client:
                response = await client.get(scrape_url)
                
                if response.status_code == 200:
                    # Parse bencoded response
                    return self._parse_scrape_response(response.content)
        except Exception as e:
            logger.debug(f"HTTP scrape failed: {e}")
        
        return None
    
    def _parse_scrape_response(self, data: bytes) -> Optional[Dict[str, int]]:
        """Parse HTTP scrape response"""
        try:
            import bencodepy
            decoded = bencodepy.decode(data)
            
            if b'files' in decoded:
                files = decoded[b'files']
                # Get first (should be only) file
                for info_hash, stats in files.items():
                    return {
                        'seeders': stats.get(b'complete', 0),
                        'leechers': stats.get(b'incomplete', 0),
                        'completed': stats.get(b'downloaded', 0)
                    }
        except Exception as e:
            logger.debug(f"Scrape parse error: {e}")
        
        return None

    def _calculate_backoff_delay(self) -> int:
        """Calculate exponential backoff delay"""
        # Exponential backoff: base_delay * 2^(failures-1)
        delay = self.base_retry_delay * (2 ** (self.consecutive_failures - 1))
        
        # Cap at maximum delay and add jitter
        max_delay = 300  # 5 minutes max
        delay = min(delay, max_delay)
        
        # Add jitter (±20%) to avoid synchronized retries
        jitter = random.uniform(0.8, 1.2)
        return int(delay * jitter)

    def _record_error_silent(self, error_message: str):
        """Record error silently (only after all retries exhausted)"""
        self.last_error = error_message
        self.error_count += 1
        self.last_error_time = datetime.utcnow()
        logger.debug(f"Silent error recorded for {self.torrent.name}: {error_message}")
    
    def get_stats(self) -> Dict:
        """Get current stats with stealth information
        
        ⚠️ IMPORTANT: Cette méthode retourne les stats pour l'affichage UI.
        Le seeding_time doit être calculé de manière fiable.
        """
        # 📊 CALCUL DU SEEDING TIME
        # seeding_time = temps accumulé des sessions précédentes + session courante
        current_seeding_time = max(0, self.seeding_time)  # Base: sessions précédentes
        
        if self.is_running and self._seeding_started_at:
            # Session en cours - ajouter le temps depuis le début
            session_duration = (datetime.utcnow() - self._seeding_started_at).total_seconds()
            session_duration = max(0, int(session_duration))  # Assurer positif et int
            current_seeding_time += session_duration
        
        # Log pour debug
        logger.debug(f"⏱️ Seeding time: {self.torrent.name[:25]} = {current_seeding_time}s ({current_seeding_time//60}m{current_seeding_time % 60}s)")
        
        # Get stealth session information
        stealth_stats = stealth_service.get_session_stats(self.torrent.info_hash)
        
        base_stats = {
            "uploaded": self.uploaded,
            "downloaded": self.downloaded,
            "uploadSpeed": int(self.upload_speed),  # Convert to int for schema compliance
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
        
        # Add stealth information
        if stealth_stats:
            base_stats["stealth"] = {
                "client": stealth_stats.get("client", "Unknown"),
                "sessionDuration": stealth_stats.get("session_duration_hours", 0),
                "activityPattern": stealth_stats.get("activity_pattern", "steady"),
                "connectionStability": stealth_stats.get("connection_stability", 95.0),
                "consecutiveFailures": self.consecutive_failures,
                "inBackoff": self._in_backoff
            }
        
        # Add detailed status information
        base_stats["status"] = self.get_status_info()
        
        return base_stats
    
    def get_status_info(self) -> Dict[str, Any]:
        """Get detailed status information for UI display"""
        # Check individual torrent pause state
        self._update_individual_state()
        
        current_speed = self._get_activity_based_upload_speed()
        
        # Calculate time until next state change
        time_until_change = 0
        change_source = "speed"
        if hasattr(self, '_is_in_fake_pause') and self._is_in_fake_pause and self._pause_until:
            time_until_change = max(0, int((self._pause_until - datetime.utcnow()).total_seconds()))
            change_source = "pause_end"
        elif hasattr(self, '_next_speed_change'):
            time_until_change = max(0, int((self._next_speed_change - datetime.utcnow()).total_seconds()))
            change_source = "tier_change"
        
        # Determine status based on individual torrent state
        if hasattr(self, '_is_in_fake_pause') and self._is_in_fake_pause:
            status = "pause_fake"
            status_text = "Paused"
        elif current_speed == 0:
            status = "pause_fake"
            status_text = "Paused"
        elif hasattr(self, '_current_speed_tier'):
            if self._current_speed_tier == 'high':
                status = "seeding_active"
                status_text = "Active seeding"
            elif self._current_speed_tier == 'medium':
                status = "seeding_active"
                status_text = "Normal seeding"
            else:
                status = "seeding_low"
                status_text = "Reduced seeding"
        elif self._is_user_active_hour():
            status = "seeding_active"
            status_text = "Active seeding"
        else:
            status = "seeding_low"
            status_text = "Reduced seeding"
        
        # Format time until change (show hours if > 60 min)
        if time_until_change >= 3600:
            hours = time_until_change // 3600
            mins = (time_until_change % 3600) // 60
            time_formatted = f"{hours}h {mins}m"
        elif time_until_change >= 60:
            time_formatted = f"{time_until_change // 60}m"
        elif time_until_change > 0:
            time_formatted = f"{time_until_change}s"
        else:
            time_formatted = "Soon"
        
        return {
            'status': status,
            'status_text': status_text,
            'current_speed': current_speed,
            'speed_formatted': f"{current_speed // 1024} kB/s" if current_speed >= 1024 else f"{current_speed} B/s",
            'time_until_speed_change': time_until_change,
            'time_until_change_formatted': time_formatted,
            'change_reason': change_source,
            'speed_tier': getattr(self, '_current_speed_tier', 'medium'),
            'is_active_hour': self._is_user_active_hour(),
            'peak_hours': f"{self._peak_hours[0]}h-{self._peak_hours[1]}h"
        }
    
    def _update_individual_state(self):
        """Update individual torrent state (pause/speed tier) independently
        
        🎭 Realistic human behavior:
        - State changes happen every few HOURS, not minutes
        - Pauses last 30min to 3 hours (configurable)
        - Reduced speed periods last 1-4 hours (configurable)
        """
        now = datetime.utcnow()
        
        # Check if we need to enter/exit pause
        if hasattr(self, '_is_in_fake_pause'):
            if self._is_in_fake_pause:
                # Check if pause should end
                if self._pause_until and now >= self._pause_until:
                    self._is_in_fake_pause = False
                    self._pause_until = None
                    # Schedule next state change (hours, not minutes!)
                    hours_until_change = random.randint(self.state_change_interval_min, self.state_change_interval_max)
                    self._next_pause_time = now + timedelta(hours=hours_until_change)
                    logger.info(f"▶️ {self.torrent.name[:25]} resuming from pause, next state change in {hours_until_change}h")
            else:
                # Check if we should enter pause (based on scheduled time)
                if hasattr(self, '_next_pause_time') and now >= self._next_pause_time:
                    # Random choice: pause or switch to reduced speed
                    # 20% chance to pause, 40% reduced, 40% normal
                    roll = random.random()
                    if roll < 0.2:
                        # Enter pause for configurable duration (minutes)
                        pause_minutes = random.randint(self.pause_duration_min, self.pause_duration_max)
                        self._is_in_fake_pause = True
                        self._pause_until = now + timedelta(minutes=pause_minutes)
                        self._current_speed_tier = 'paused'
                        logger.info(f"⏸️ {self.torrent.name[:25]} entering pause for {pause_minutes}min ({pause_minutes/60:.1f}h)")
                    elif roll < 0.6:
                        # Switch to reduced speed for configurable duration
                        reduced_minutes = random.randint(self.reduced_speed_duration_min, self.reduced_speed_duration_max)
                        self._current_speed_tier = 'low'
                        self._next_speed_change = now + timedelta(minutes=reduced_minutes)
                        logger.info(f"🔽 {self.torrent.name[:25]} switching to reduced speed for {reduced_minutes}min ({reduced_minutes/60:.1f}h)")
                    else:
                        # Stay at normal/high speed
                        self._current_speed_tier = random.choice(['high', 'medium'])
                        hours_until_change = random.randint(self.state_change_interval_min, self.state_change_interval_max)
                        self._next_speed_change = now + timedelta(hours=hours_until_change)
                        logger.info(f"🔼 {self.torrent.name[:25]} staying at {self._current_speed_tier} speed for {hours_until_change}h")
                    
                    # Schedule next state evaluation
                    hours_until_next = random.randint(self.state_change_interval_min, self.state_change_interval_max)
                    self._next_pause_time = now + timedelta(hours=hours_until_next)
        
        # Check if speed tier duration has ended (for reduced speed periods)
        if hasattr(self, '_next_speed_change') and not self._is_in_fake_pause:
            if now >= self._next_speed_change and self._current_speed_tier == 'low':
                # Reduced period ended, return to normal
                self._current_speed_tier = random.choice(['high', 'medium'])
                hours_until_change = random.randint(self.state_change_interval_min, self.state_change_interval_max)
                self._next_speed_change = now + timedelta(hours=hours_until_change)
                logger.info(f"🔼 {self.torrent.name[:25]} reduced period ended, back to {self._current_speed_tier}")
    
    def _simulate_natural_download_start(self):
        """Simulate realistic download start behavior - full download cycle simulation"""
        
        # Simulate partial download state
        completion_percentage = random.uniform(0.0, 0.95)  # Start at 0-95% completed
        self.downloaded = int(self.torrent.size * completion_percentage)
        self.left = self.torrent.size - self.downloaded
        self.uploaded = 0  # Start with minimal upload
        
        # Download will complete in realistic timeframe (5-60 minutes)
        download_duration_minutes = random.randint(5, 60)
        self._download_completion_time = datetime.utcnow() + timedelta(minutes=download_duration_minutes)
        self._seeding_session_start = self._download_completion_time
        
        # Track download state
        self._is_downloading = True
        self._initial_seeding = False  # Will transition later
        self._total_seeding_time = 0
        self._last_speed_change = datetime.utcnow()
        
        # Natural patterns (for later seeding phase)
        self._peak_hours = self._determine_user_peak_hours()
        self._user_activity_pattern = self._generate_user_activity_pattern()
        
        # 🎭 Individual torrent pause behavior (each torrent pauses independently)
        # First state change after a few HOURS (realistic human behavior)
        hours_until_first_change = random.randint(self.state_change_interval_min, self.state_change_interval_max)
        self._next_pause_time = datetime.utcnow() + timedelta(hours=hours_until_first_change)
        self._pause_duration = 0
        self._pause_until = None
        self._is_in_fake_pause = False
        
        # 🎯 Individual speed state - start at normal/high speed
        self._next_speed_change = datetime.utcnow() + timedelta(hours=hours_until_first_change)
        self._current_speed_tier = random.choice(['high', 'medium'])  # Start active, not reduced
        
        logger.debug(f"📥 Natural download start for {self.torrent.name[:30]}: {completion_percentage:.1%} completed, {self.left / (1024**2):.2f} MB remaining")
    
    def _simulate_natural_seeding_start(self):
        """Simulate realistic seeding start behavior - torrent already downloaded"""
        # Torrent is already 100% downloaded (user placed .torrent file after download)
        self.downloaded = self.torrent.size
        self.left = 0
        self.uploaded = 0  # Start seeding with 0 upload
        
        # Simulate when download actually completed (recent past)
        # Real users typically start seeding within minutes of download completion
        completion_delay_minutes = random.randint(1, 30)  # 1-30 minutes ago
        self._download_completion_time = datetime.utcnow() - timedelta(minutes=completion_delay_minutes)
        self._seeding_session_start = datetime.utcnow()
        
        # Initialize seeding characteristics
        self._initial_seeding = True  # First announces show "completed" event
        self._is_downloading = False  # Pure seeding mode
        self._total_seeding_time = 0
        self._last_speed_change = datetime.utcnow()
        
        # Natural seeding patterns
        self._peak_hours = self._determine_user_peak_hours()
        self._user_activity_pattern = self._generate_user_activity_pattern()
        
        # 🎭 Individual torrent pause behavior - realistic timing (HOURS not seconds!)
        # First state change after a configurable number of hours
        hours_until_first_change = random.randint(self.state_change_interval_min, self.state_change_interval_max)
        self._next_pause_time = datetime.utcnow() + timedelta(hours=hours_until_first_change)
        self._pause_duration = 0
        self._pause_until = None
        self._is_in_fake_pause = False
        
        # 🎯 Individual speed state - start at normal/high speed (most realistic)
        self._next_speed_change = datetime.utcnow() + timedelta(hours=hours_until_first_change)
        self._current_speed_tier = random.choice(['high', 'medium'])  # Start active
        
        logger.info(f"🌱 {self.torrent.name[:30]}: seeding start, tier={self._current_speed_tier}, next state change in {hours_until_first_change}h")
    
    def _is_in_downloading_phase(self) -> bool:
        """Check if torrent is still in realistic downloading phase"""
        if not self._is_downloading:
            return False
        
        # Transition to seeding after some realistic time (5-30 minutes)
        if self._download_completion_time:
            seeding_start_delay = random.randint(5, 30)  # minutes
            should_start_seeding = datetime.utcnow() > (self._download_completion_time + timedelta(minutes=seeding_start_delay))
            
            if should_start_seeding:
                self._is_downloading = False
                self.left = 0  # Complete download
                logger.debug(f"🔄 {self.torrent.name[:30]} transitioned from downloading to seeding")
                
        return self._is_downloading
    
    def _get_realistic_upload_speed_based_on_swarm(self) -> int:
        """Calculate realistic upload speed based on swarm activity"""
        min_rate, max_rate = self.client.get_upload_rate_range()
        
        # Base speed calculation
        base_speed = random.randint(min_rate, max_rate)
        
        # Adjust based on swarm activity
        total_peers = self.seeders + self.leechers
        swarm_factor = 1.0
        
        if total_peers == 0:
            # Dead swarm - very low speed
            swarm_factor = 0.1
        elif self.leechers == 0:
            # No leechers - reduce speed significantly  
            swarm_factor = 0.3
        elif self.leechers > self.seeders * 2:
            # High demand - increase speed
            swarm_factor = 1.3
        elif self.leechers < self.seeders * 0.5:
            # Low demand - reduce speed
            swarm_factor = 0.7
        
        # Apply swarm factor
        realistic_speed = int(base_speed * swarm_factor)
        
        # Ensure within bounds
        return max(int(min_rate * 0.1), min(max_rate, realistic_speed))
        
    def _simulate_occasional_network_errors(self) -> bool:
        """Simulate realistic network errors (1-3% chance)"""
        error_chance = random.uniform(0.01, 0.03)  # 1-3% chance
        if random.random() < error_chance:
            error_types = [
                "Connection timeout",
                "DNS resolution failed", 
                "Network unreachable",
                "Connection reset by peer"
            ]
            simulated_error = random.choice(error_types)
            logger.debug(f"🎭 Simulating network error for {self.torrent.name[:30]}: {simulated_error}")
            self._record_error(f"Simulated: {simulated_error}")
            return True
        return False
    
    def _determine_user_peak_hours(self) -> tuple:
        """Determine user's typical active hours (when upload speeds are higher)"""
        # Simulate different user types
        user_types = [
            (18, 24),  # Evening user (6PM-12AM)
            (20, 2),   # Night owl (8PM-2AM) 
            (9, 17),   # Day user (9AM-5PM)
            (7, 11),   # Morning user (7AM-11AM)
        ]
        return random.choice(user_types)
    
    def _generate_user_activity_pattern(self) -> dict:
        """Generate realistic user activity pattern"""
        return {
            'active_days': random.randint(4, 7),  # Active 4-7 days per week
            'session_length': random.randint(2, 12),  # 2-12 hour sessions
            'break_frequency': random.uniform(0.1, 0.3),  # 10-30% chance of temporary breaks
            'speed_consistency': random.uniform(0.6, 0.9)  # How consistent upload speeds are
        }
    
    def _is_user_active_hour(self) -> bool:
        """Check if current time is within user's peak activity hours"""
        current_hour = datetime.utcnow().hour
        start_hour, end_hour = self._peak_hours
        
        is_active = False
        if start_hour < end_hour:
            is_active = start_hour <= current_hour <= end_hour
        else:  # Crosses midnight
            is_active = current_hour >= start_hour or current_hour <= end_hour
        
        # Add some flexibility - user might be active outside defined hours too
        # 20% chance of being "active" even outside defined hours to prevent zero uploads
        if not is_active:
            is_active = random.random() < 0.2
        
        return is_active
    
    def _get_activity_based_upload_speed(self) -> int:
        """Get upload speed based on user activity patterns with dynamic config
        
        ⚠️ IMPORTANT: Returns speed in bytes/sec.
        
        Speed tiers:
        - 'paused' / _is_in_fake_pause: 0 bytes/sec
        - 'low' (reduced): configured reduced_speed_kbps (default 5 KB/s)
        - 'medium': 30-60% of max speed
        - 'high': 60-100% of max speed
        """
        # Check if torrent is in fake pause state - return 0 speed
        if hasattr(self, '_is_in_fake_pause') and self._is_in_fake_pause:
            logger.debug(f"💤 {self.torrent.name[:20]} is in fake pause - speed = 0")
            return 0
        
        # Get dynamic config from seeder_service
        from app.services.seeder_service import seeder_service
        dynamic_config = seeder_service._config if seeder_service else None
        min_rate, max_rate = self.client.get_upload_rate_range(dynamic_config)
        
        # Check current speed tier
        current_tier = getattr(self, '_current_speed_tier', 'medium')
        
        if current_tier == 'low':
            # 🔽 Reduced speed: use configured low speed (default 5 KB/s)
            # Add small variation (±2 KB/s) for realism
            reduced_speed_bytes = self.reduced_speed_kbps * 1024  # Convert KB/s to bytes/s
            variation = random.randint(-2048, 2048)  # ±2 KB/s variation
            speed = max(1024, reduced_speed_bytes + variation)  # Minimum 1 KB/s
            logger.debug(f"🔽 {self.torrent.name[:20]} reduced speed: {speed/1024:.1f} KB/s (tier: low)")
            return int(speed)
        
        elif current_tier == 'medium':
            # 🔸 Medium speed: 30-60% of max
            effective_min = int(max_rate * 0.3)
            effective_max = int(max_rate * 0.6)
        
        else:  # 'high' or default
            # 🔼 High speed: 60-100% of max
            effective_min = int(max_rate * 0.6)
            effective_max = max_rate
        
        # Ensure limits are valid
        effective_min = max(min_rate, effective_min)
        effective_max = max(effective_min, min(max_rate, effective_max))
        
        # Generate random speed within tier range
        speed = random.randint(effective_min, effective_max)
        
        logger.debug(f"🎯 {self.torrent.name[:20]}: {speed/1024:.0f} KB/s (tier: {current_tier}, range: {effective_min/1024:.0f}-{effective_max/1024:.0f})")
        
        return speed

