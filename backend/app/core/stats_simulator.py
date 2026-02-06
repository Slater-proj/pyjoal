"""
Stats Simulator
Handles realistic upload/download statistics simulation for BitTorrent seeding.
Extracted from tracker_announcer.py for better modularity.
"""
import random
import logging
import time
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)


class StatsSimulator:
    """Simulates realistic upload/download statistics for a torrent.
    
    Manages speed tiers, pause states, activity patterns,
    and realistic upload byte calculation.
    """
    
    def __init__(self, torrent_name: str, torrent_size: int, discretion_config: Optional[Dict] = None):
        """Initialize stats simulator.
        
        Args:
            torrent_name: Name of the torrent (for logging)
            torrent_size: Total size of the torrent in bytes
            discretion_config: Optional discretion settings override
        """
        self.torrent_name = torrent_name
        self.torrent_size = torrent_size
        
        config = discretion_config or {}
        
        # Discretion settings
        self.min_stats_update_interval = config.get("min_stats_update_interval", settings.MIN_STATS_UPDATE_INTERVAL)
        self.enable_speed_variation = config.get("enable_speed_variation", settings.ENABLE_SPEED_VARIATION)
        self.speed_variation_percent = config.get("speed_variation_percent", settings.SPEED_VARIATION_PERCENT)
        self.seeding_only_mode = config.get("seedingOnlyMode", settings.SEEDING_ONLY_MODE)
        
        # Realistic Behavior Timing
        self.pause_duration_min = config.get("pauseDurationMin", settings.PAUSE_DURATION_MIN)
        self.pause_duration_max = config.get("pauseDurationMax", settings.PAUSE_DURATION_MAX)
        self.reduced_speed_duration_min = config.get("reducedSpeedDurationMin", settings.REDUCED_SPEED_DURATION_MIN)
        self.reduced_speed_duration_max = config.get("reducedSpeedDurationMax", settings.REDUCED_SPEED_DURATION_MAX)
        self.state_change_interval_min = config.get("stateChangeIntervalMin", settings.STATE_CHANGE_INTERVAL_MIN)
        self.state_change_interval_max = config.get("stateChangeIntervalMax", settings.STATE_CHANGE_INTERVAL_MAX)
        self.reduced_speed_kbps = config.get("reducedSpeedKbps", settings.REDUCED_SPEED_KBPS)
        
        # Stats
        self.uploaded: int = 0
        self.downloaded: int = torrent_size
        self.left: int = 0
        self.upload_speed: float = 0
        
        # Timing state
        self._last_stats_update: Optional[float] = None
        self._last_upload_time: Optional[float] = None
        self._display_update_time: Optional[float] = None
        self._total_seeding_time: float = 0
        self._seeding_session_start: Optional[datetime] = None
        self._last_speed_change: Optional[datetime] = None
        self._download_completion_time: Optional[datetime] = None
        
        # Download simulation
        self._is_downloading: bool = False
        self._initial_seeding: bool = False
        self._last_download_time: Optional[float] = None
        self.download_speed: float = 0
        
        # Pause / speed tier state
        self._is_in_fake_pause: bool = False
        self._pause_until: Optional[datetime] = None
        self._pause_duration: int = 0
        self._next_pause_time: Optional[datetime] = None
        self._next_speed_change: Optional[datetime] = None
        self._current_speed_tier: str = 'medium'
        
        # Activity patterns
        self._peak_hours: tuple = (18, 24)
        self._user_activity_pattern: Dict = {}
    
    # ================================================================
    # Initialization methods
    # ================================================================
    
    def simulate_natural_seeding_start(self):
        """Simulate realistic seeding start behavior - torrent already downloaded."""
        self.downloaded = self.torrent_size
        self.left = 0
        self.uploaded = 0
        
        completion_delay_minutes = random.randint(1, 30)
        self._download_completion_time = datetime.utcnow() - timedelta(minutes=completion_delay_minutes)
        self._seeding_session_start = datetime.utcnow()
        
        self._initial_seeding = True
        self._is_downloading = False
        self._total_seeding_time = 0
        self._last_speed_change = datetime.utcnow()
        
        self._peak_hours = self._determine_user_peak_hours()
        self._user_activity_pattern = self._generate_user_activity_pattern()
        
        hours_until_first_change = random.randint(self.state_change_interval_min, self.state_change_interval_max)
        self._next_pause_time = datetime.utcnow() + timedelta(hours=hours_until_first_change)
        self._pause_duration = 0
        self._pause_until = None
        self._is_in_fake_pause = False
        
        self._next_speed_change = datetime.utcnow() + timedelta(hours=hours_until_first_change)
        self._current_speed_tier = random.choice(['high', 'medium'])
        
        logger.info(f"🌱 {self.torrent_name[:30]}: seeding start, tier={self._current_speed_tier}, next state change in {hours_until_first_change}h")
    
    def simulate_natural_download_start(self):
        """Simulate realistic download start behavior - full download cycle simulation."""
        completion_percentage = random.uniform(0.0, 0.95)
        self.downloaded = int(self.torrent_size * completion_percentage)
        self.left = self.torrent_size - self.downloaded
        self.uploaded = 0
        
        download_duration_minutes = random.randint(5, 60)
        self._download_completion_time = datetime.utcnow() + timedelta(minutes=download_duration_minutes)
        self._seeding_session_start = self._download_completion_time
        
        self._is_downloading = True
        self._initial_seeding = False
        self._total_seeding_time = 0
        self._last_speed_change = datetime.utcnow()
        
        self._peak_hours = self._determine_user_peak_hours()
        self._user_activity_pattern = self._generate_user_activity_pattern()
        
        hours_until_first_change = random.randint(self.state_change_interval_min, self.state_change_interval_max)
        self._next_pause_time = datetime.utcnow() + timedelta(hours=hours_until_first_change)
        self._pause_duration = 0
        self._pause_until = None
        self._is_in_fake_pause = False
        
        self._next_speed_change = datetime.utcnow() + timedelta(hours=hours_until_first_change)
        self._current_speed_tier = random.choice(['high', 'medium'])
        
        logger.debug(f"📥 Natural download start for {self.torrent_name[:30]}: {completion_percentage:.1%} completed, {self.left / (1024**2):.2f} MB remaining")
    
    # ================================================================
    # Stats update methods
    # ================================================================
    
    def update_stats(self, client, is_running: bool, seeders: int = -1, leechers: int = -1):
        """Update upload stats with realistic behavior based on mode.
        
        Args:
            client: BitTorrentClient instance (for rate ranges)
            is_running: Whether the announcer is currently running
            seeders: Number of seeders from tracker (-1 = unknown)
            leechers: Number of leechers from tracker (-1 = unknown)
        """
        if not is_running:
            return
        
        current_time = time.time()
        
        if self._last_stats_update is None:
            self._last_stats_update = current_time
            self._last_upload_time = current_time
            logger.debug(f"📊 Stats tracking initialized for {self.torrent_name[:30]}")
        
        time_since_last = current_time - self._last_stats_update
        if time_since_last < self.min_stats_update_interval:
            return
        
        self._last_stats_update = current_time
        
        if not self.seeding_only_mode and self.is_in_downloading_phase():
            self._update_download_stats(client)
            return
            
        current_speed = self.get_activity_based_upload_speed(client, seeders, leechers)
        
        if self.enable_speed_variation and current_speed > 0:
            variation_factor = 1.0 + random.uniform(
                -self.speed_variation_percent / 100.0,
                self.speed_variation_percent / 100.0
            )
            current_speed = int(current_speed * variation_factor)
        
        if self._last_upload_time is not None:
            time_interval = current_time - self._last_upload_time
        else:
            time_interval = 3
        
        self._last_upload_time = current_time
        
        if current_speed > 0:
            capped_interval = min(time_interval, 10)
            upload_delta = int(current_speed * capped_interval)
            self.uploaded += upload_delta
            
            logger.info(f"📈 UPLOAD: {self.torrent_name[:25]} +{upload_delta/1024:.1f}KB ({current_speed/1024:.1f}KB/s × {capped_interval:.1f}s) = Total: {self.uploaded/(1024*1024):.2f}MB")
            
            if self._seeding_session_start:
                self._total_seeding_time = (datetime.utcnow() - self._seeding_session_start).total_seconds()
        else:
            logger.debug(f"⚠️ Speed=0 for {self.torrent_name[:30]} - no upload this interval")
            
        self.upload_speed = float(current_speed)
        self.downloaded = self.torrent_size
        self.left = 0
    
    def update_stats_for_display(self, client, is_running: bool, seeders: int = -1, leechers: int = -1):
        """Update stats for UI display - called by the monitor loop.
        
        Args:
            client: BitTorrentClient instance
            is_running: Whether the announcer is currently running
            seeders: Number of seeders from tracker (-1 = unknown)
            leechers: Number of leechers from tracker (-1 = unknown)
        """
        if not is_running:
            self.upload_speed = 0
            return
        
        current_time = time.time()
        
        if self._display_update_time is None:
            self._display_update_time = current_time
            self._last_upload_time = current_time
            self._last_stats_update = current_time
        
        time_interval = current_time - self._display_update_time
        self._display_update_time = current_time
        
        current_speed = self.get_activity_based_upload_speed(client, seeders, leechers)
        
        if self.enable_speed_variation and current_speed > 0:
            variation = random.uniform(-self.speed_variation_percent/100, self.speed_variation_percent/100)
            current_speed = int(current_speed * (1 + variation))
        
        upload_delta = 0
        if current_speed > 0 and time_interval > 0:
            capped_interval = min(time_interval, 10)
            upload_delta = int(current_speed * capped_interval)
            self.uploaded += upload_delta
            
            logger.debug(f"📊 Display update: {self.torrent_name[:20]} speed={current_speed/1024:.0f}KB/s, +{upload_delta/1024:.1f}KB, total={self.uploaded/(1024*1024):.2f}MB")
        
        self.upload_speed = float(current_speed)
        self._last_upload_time = current_time
        self._last_stats_update = current_time
        
        logger.debug(f"🌱 Seeding stats for {self.torrent_name[:30]}:")
        logger.debug(f"   Speed: {current_speed / 1024:.2f} KB/s (activity-based) - Time delta: {time_interval:.1f}s")
        if current_speed > 0:
            logger.debug(f"   Session time: {self._total_seeding_time / 3600:.1f}h")
            logger.debug(f"   Upload delta this interval: {upload_delta / 1024:.2f} KB")
            logger.debug(f"   Total uploaded: {self.uploaded / (1024**2):.2f} MB")
            logger.debug(f"   Ratio: {self.uploaded / self.torrent_size if self.torrent_size > 0 else 0:.3f}")
        else:
            logger.debug("   Speed is 0 - no upload progress made")
    
    def update_stats_with_stealth(self, client, stealth_service, torrent_info_hash: str, is_running: bool,
                                    seeders: int = -1, leechers: int = -1):
        """Update stats with stealth service natural variations.
        
        Args:
            client: BitTorrentClient instance
            stealth_service: StealthService instance
            torrent_info_hash: Torrent info hash
            is_running: Whether the announcer is currently running
            seeders: Number of seeders from tracker (-1 = unknown)
            leechers: Number of leechers from tracker (-1 = unknown)
        """
        if not is_running:
            return
        
        current_time = time.time()
        if self._last_stats_update is not None:
            time_since_last = current_time - self._last_stats_update
            if time_since_last < self.min_stats_update_interval:
                return
        
        self._last_stats_update = current_time
        
        if not self.seeding_only_mode and self.is_in_downloading_phase():
            self._update_download_stats(client)
            return
            
        base_speed = self.get_activity_based_upload_speed(client, seeders, leechers)
        
        current_speed = stealth_service.get_natural_speed_variation(
            base_speed, 
            torrent_info_hash
        )
        
        if current_speed > 0:
            if self._last_upload_time is not None:
                time_interval = current_time - self._last_upload_time
            else:
                time_interval = 5
            
            self._last_upload_time = current_time
            
            upload_delta = current_speed * min(time_interval, 10)
            self.uploaded += upload_delta
            
            if self._seeding_session_start:
                self._total_seeding_time = (datetime.utcnow() - self._seeding_session_start).total_seconds()
            
        self.upload_speed = float(current_speed)
        self.downloaded = self.torrent_size
        self.left = 0
        
        logger.debug(f"🎭 Stealth seeding stats for {self.torrent_name[:30]}:")
        logger.debug(f"   Speed: {current_speed / 1024:.2f} KB/s (stealth-enhanced)")
    
    def _update_download_stats(self, client):
        """Update download stats during download simulation phase."""
        current_time = time.time()
        
        download_speed = self._get_realistic_download_speed(client)
        
        if self._last_download_time is not None:
            time_interval = current_time - self._last_download_time
        else:
            time_interval = 5
            
        self._last_download_time = current_time
        
        download_delta = download_speed * min(time_interval, 10)
        
        self.downloaded = min(self.downloaded + download_delta, self.torrent_size)
        self.left = max(0, self.torrent_size - self.downloaded)
        
        upload_speed = max(download_speed * 0.1, 1024)
        upload_delta = upload_speed * min(time_interval, 10)
        self.uploaded += upload_delta
        
        self.download_speed = float(download_speed)
        self.upload_speed = float(upload_speed)
        
        logger.debug(f"📥 Download stats for {self.torrent_name[:30]}:")
        logger.debug(f"   Progress: {(self.downloaded/self.torrent_size)*100:.1f}% ({self.left/(1024**2):.2f} MB left)")
        logger.debug(f"   DL Speed: {download_speed/1024:.2f} KB/s, UL Speed: {upload_speed/1024:.2f} KB/s")
    
    def _get_realistic_download_speed(self, client) -> int:
        """Get realistic download speed during download simulation."""
        min_dl, max_dl = (102400, 1048576)
        if hasattr(client, 'get_download_rate_range'):
            min_dl, max_dl = client.get_download_rate_range()
        
        base_speed = random.randint(min_dl, max_dl)
        
        hour = datetime.utcnow().hour
        if hour in range(self._peak_hours[0], self._peak_hours[1] + 1 if self._peak_hours[0] < self._peak_hours[1] else 25):
            base_speed = int(base_speed * 1.2)
        elif hour < 6 or hour > 22:
            base_speed = int(base_speed * 0.8)
            
        return max(base_speed, 10240)
    
    # ================================================================
    # Speed / Activity methods
    # ================================================================
    
    def get_activity_based_upload_speed(self, client, seeders: int = -1, leechers: int = -1) -> int:
        """Get upload speed based on user activity patterns with dynamic config.
        
        Returns speed in bytes/sec.
        
        Args:
            client: BitTorrentClient instance
            seeders: Number of seeders (-1 = unknown, use base speed)
            leechers: Number of leechers (-1 = unknown, use base speed; 0 = zero upload)
        
        Speed tiers:
        - 'paused' / _is_in_fake_pause: 0 bytes/sec
        - 'low' (reduced): configured reduced_speed_kbps
        - 'medium': 30-60% of max speed
        - 'high': 60-100% of max speed
        """
        # CRITICAL stealth: if we KNOW there are 0 leechers, upload is impossible
        if leechers == 0:
            logger.debug(f"🛡️ {self.torrent_name[:20]}: 0 leechers → speed=0 (stealth)")
            return 0
        
        if self._is_in_fake_pause:
            logger.debug(f"💤 {self.torrent_name[:20]} is in fake pause - speed = 0")
            return 0
        
        from app.services.seeder_service import seeder_service
        dynamic_config = seeder_service._config if seeder_service else None
        min_rate, max_rate = client.get_upload_rate_range(dynamic_config)
        
        current_tier = self._current_speed_tier
        
        if current_tier == 'low':
            reduced_speed_bytes = self.reduced_speed_kbps * 1024
            variation = random.randint(-2048, 2048)
            speed = max(1024, reduced_speed_bytes + variation)
            logger.debug(f"🔽 {self.torrent_name[:20]} reduced speed: {speed/1024:.1f} KB/s (tier: low)")
            return int(speed)
        
        elif current_tier == 'medium':
            effective_min = int(max_rate * 0.3)
            effective_max = int(max_rate * 0.6)
        else:  # 'high' or default
            effective_min = int(max_rate * 0.6)
            effective_max = max_rate
        
        effective_min = max(min_rate, effective_min)
        effective_max = max(effective_min, min(max_rate, effective_max))
        
        speed = random.randint(effective_min, effective_max)
        
        # Apply swarm-aware weighting if peer data is available
        if seeders >= 0 and leechers > 0:
            total_peers = seeders + leechers
            leecher_ratio = leechers / total_peers
            # More leechers relative to seeders = higher demand = more upload opportunity
            swarm_factor = max(0.2, min(1.5, leecher_ratio * leecher_ratio * min(leechers, 10) / 3))
            speed = int(speed * swarm_factor)
            speed = max(1024, speed)
            logger.debug(f"🎯 {self.torrent_name[:20]}: {speed/1024:.0f} KB/s (tier: {current_tier}, swarm: {seeders}S/{leechers}L, factor: {swarm_factor:.2f})")
        else:
            logger.debug(f"🎯 {self.torrent_name[:20]}: {speed/1024:.0f} KB/s (tier: {current_tier}, range: {effective_min/1024:.0f}-{effective_max/1024:.0f})")
        
        return speed
    
    def get_realistic_upload_speed_based_on_swarm(self, client, seeders: int, leechers: int) -> int:
        """Calculate realistic upload speed based on swarm activity.
        
        Critical for stealth: a real BitTorrent client cannot upload if there are
        no leechers, so reporting upload in that case is an instant detection flag.
        """
        # CRITICAL: Zero leechers = zero upload (impossible to upload with no downloaders)
        if leechers == 0:
            logger.debug(f"🛡️ {self.torrent_name[:20]}: 0 leechers → 0 upload (stealth protection)")
            return 0

        min_rate, max_rate = client.get_upload_rate_range()
        
        base_speed = random.randint(min_rate, max_rate)
        
        total_peers = seeders + leechers
        
        # Swarm-weighted speed: more leechers relative to seeders = higher demand = more upload
        if total_peers > 0:
            leecher_ratio = leechers / total_peers
            # Weight proportional to demand: leecher_ratio² * leechers (JOAL formula)
            swarm_factor = max(0.1, min(1.5, leecher_ratio * leecher_ratio * min(leechers, 10) / 3))
        else:
            swarm_factor = 0.1
        
        realistic_speed = int(base_speed * swarm_factor)
        return max(1024, min(max_rate, realistic_speed))
    
    # ================================================================
    # State management (pause, speed tiers, activity)
    # ================================================================
    
    def update_individual_state(self):
        """Update individual torrent state (pause/speed tier) independently.
        
        Realistic human behavior:
        - State changes happen every few HOURS, not minutes
        - Pauses last 30min to 3 hours (configurable)
        - Reduced speed periods last 1-4 hours (configurable)
        """
        now = datetime.utcnow()
        
        if self._is_in_fake_pause:
            if self._pause_until and now >= self._pause_until:
                self._is_in_fake_pause = False
                self._pause_until = None
                hours_until_change = random.randint(self.state_change_interval_min, self.state_change_interval_max)
                self._next_pause_time = now + timedelta(hours=hours_until_change)
                logger.info(f"▶️ {self.torrent_name[:25]} resuming from pause, next state change in {hours_until_change}h")
        else:
            if self._next_pause_time and now >= self._next_pause_time:
                roll = random.random()
                if roll < 0.2:
                    pause_minutes = random.randint(self.pause_duration_min, self.pause_duration_max)
                    self._is_in_fake_pause = True
                    self._pause_until = now + timedelta(minutes=pause_minutes)
                    self._current_speed_tier = 'paused'
                    logger.info(f"⏸️ {self.torrent_name[:25]} entering pause for {pause_minutes}min ({pause_minutes/60:.1f}h)")
                elif roll < 0.6:
                    reduced_minutes = random.randint(self.reduced_speed_duration_min, self.reduced_speed_duration_max)
                    self._current_speed_tier = 'low'
                    self._next_speed_change = now + timedelta(minutes=reduced_minutes)
                    logger.info(f"🔽 {self.torrent_name[:25]} switching to reduced speed for {reduced_minutes}min ({reduced_minutes/60:.1f}h)")
                else:
                    self._current_speed_tier = random.choice(['high', 'medium'])
                    hours_until_change = random.randint(self.state_change_interval_min, self.state_change_interval_max)
                    self._next_speed_change = now + timedelta(hours=hours_until_change)
                    logger.info(f"🔼 {self.torrent_name[:25]} staying at {self._current_speed_tier} speed for {hours_until_change}h")
                
                hours_until_next = random.randint(self.state_change_interval_min, self.state_change_interval_max)
                self._next_pause_time = now + timedelta(hours=hours_until_next)
        
        if self._next_speed_change and not self._is_in_fake_pause:
            if now >= self._next_speed_change and self._current_speed_tier == 'low':
                self._current_speed_tier = random.choice(['high', 'medium'])
                hours_until_change = random.randint(self.state_change_interval_min, self.state_change_interval_max)
                self._next_speed_change = now + timedelta(hours=hours_until_change)
                logger.info(f"🔼 {self.torrent_name[:25]} reduced period ended, back to {self._current_speed_tier}")
    
    def is_in_downloading_phase(self) -> bool:
        """Check if torrent is still in realistic downloading phase."""
        if not self._is_downloading:
            return False
        
        if self._download_completion_time:
            seeding_start_delay = random.randint(5, 30)
            should_start_seeding = datetime.utcnow() > (self._download_completion_time + timedelta(minutes=seeding_start_delay))
            
            if should_start_seeding:
                self._is_downloading = False
                self.left = 0
                logger.debug(f"🔄 {self.torrent_name[:30]} transitioned from downloading to seeding")
                
        return self._is_downloading
    
    def simulate_occasional_network_errors(self) -> bool:
        """Simulate realistic network errors (1-3% chance). Returns True if error simulated."""
        error_chance = random.uniform(0.01, 0.03)
        if random.random() < error_chance:
            error_types = [
                "Connection timeout",
                "DNS resolution failed", 
                "Network unreachable",
                "Connection reset by peer"
            ]
            simulated_error = random.choice(error_types)
            logger.debug(f"🎭 Simulating network error for {self.torrent_name[:30]}: {simulated_error}")
            return True
        return False
    
    # ================================================================
    # Activity pattern helpers
    # ================================================================
    
    def _determine_user_peak_hours(self) -> tuple:
        """Determine user's typical active hours."""
        user_types = [
            (18, 24),
            (20, 2),
            (9, 17),
            (7, 11),
        ]
        return random.choice(user_types)
    
    def _generate_user_activity_pattern(self) -> dict:
        """Generate realistic user activity pattern."""
        return {
            'active_days': random.randint(4, 7),
            'session_length': random.randint(2, 12),
            'break_frequency': random.uniform(0.1, 0.3),
            'speed_consistency': random.uniform(0.6, 0.9)
        }
    
    def is_user_active_hour(self) -> bool:
        """Check if current time is within user's peak activity hours."""
        current_hour = datetime.utcnow().hour
        start_hour, end_hour = self._peak_hours
        
        is_active = False
        if start_hour < end_hour:
            is_active = start_hour <= current_hour <= end_hour
        else:
            is_active = current_hour >= start_hour or current_hour <= end_hour
        
        if not is_active:
            is_active = random.random() < 0.2
        
        return is_active
    
    def get_status_info(self) -> Dict[str, Any]:
        """Get detailed status information for UI display."""
        self.update_individual_state()
        
        # We need client reference for speed - caller should pass it
        # This returns status based on internal state
        current_speed = 0  # Will be overridden by caller if needed
        
        time_until_change = 0
        change_source = "speed"
        if self._is_in_fake_pause and self._pause_until:
            time_until_change = max(0, int((self._pause_until - datetime.utcnow()).total_seconds()))
            change_source = "pause_end"
        elif self._next_speed_change:
            time_until_change = max(0, int((self._next_speed_change - datetime.utcnow()).total_seconds()))
            change_source = "tier_change"
        
        if self._is_in_fake_pause:
            status = "pause_fake"
            status_text = "Paused"
        elif self._current_speed_tier == 'high':
            status = "seeding_active"
            status_text = "Active seeding"
        elif self._current_speed_tier == 'medium':
            status = "seeding_active"
            status_text = "Normal seeding"
        elif self._current_speed_tier == 'low':
            status = "seeding_low"
            status_text = "Reduced seeding"
        elif self.is_user_active_hour():
            status = "seeding_active"
            status_text = "Active seeding"
        else:
            status = "seeding_low"
            status_text = "Reduced seeding"
        
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
            'speed_tier': self._current_speed_tier,
            'is_active_hour': self.is_user_active_hour(),
            'peak_hours': f"{self._peak_hours[0]}h-{self._peak_hours[1]}h"
        }
