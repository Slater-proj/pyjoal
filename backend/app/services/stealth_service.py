"""
Stealth Service - Advanced Anti-Detection
Provides intelligent randomization and natural behavior patterns for maximum discretion
"""
import random
import time
import hashlib
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class UserAgentProfile:
    """BitTorrent client user agent profile"""
    name: str
    pattern: str
    versions: List[str]
    weight: int  # Popularity weight for realistic distribution


class StealthService:
    """Advanced anti-detection service"""
    
    # Realistic User-Agent profiles based on popular clients
    USER_AGENT_PROFILES = [
        UserAgentProfile("qBittorrent", "qBittorrent/{version}", 
                        ["5.1.4", "5.1.3", "5.1.2", "5.0.1"], 35),
        UserAgentProfile("Transmission", "Transmission/{version}", 
                        ["4.0.6", "4.0.5", "4.0.4", "3.00"], 25),
        UserAgentProfile("Deluge", "Deluge/{version}", 
                        ["2.2.1", "2.1.1", "2.0.3"], 20),
        UserAgentProfile("uTorrent", "µTorrent/{version}", 
                        ["3.6.0", "3.5.5", "3.5.0"], 15),
        UserAgentProfile("BitTorrent", "BitTorrent/{version}", 
                        ["7.11.0", "7.10.5", "7.10.0"], 5),
    ]
    
    def __init__(self):
        """Initialize stealth service with caching"""
        self.session_profiles: Dict[str, Dict] = {}  # Per-torrent session data
        self._natural_timing_cache = {}
        # Optimization: Cache expensive calculations
        self._time_factor_cache = {}  # Cache time factors by hour
        self._activity_factor_cache = {}  # Cache activity factors
        self._speed_cache = {}  # Cache speed calculations
        self._cache_timestamp = datetime.utcnow()
        
    def get_session_profile(self, torrent_hash: str) -> Dict:
        """Get or create persistent session profile for torrent"""
        if torrent_hash not in self.session_profiles:
            self.session_profiles[torrent_hash] = self._generate_session_profile(torrent_hash)
        
        return self.session_profiles[torrent_hash]
    
    def _generate_session_profile(self, torrent_hash: str) -> Dict:
        """Generate consistent session profile based on torrent hash"""
        # Use torrent hash as seed for consistent behavior per torrent
        seed_value = int(hashlib.md5(torrent_hash.encode()).hexdigest()[:8], 16)
        random.seed(seed_value)
        
        # Select user agent with realistic probability
        ua_profile = self._select_weighted_user_agent()
        version = random.choice(ua_profile.versions)
        user_agent = ua_profile.pattern.format(version=version)
        
        # Generate session-consistent port (49152-65535 range)
        session_port = random.randint(49152, 65535)
        
        # Natural behavior timing patterns
        base_announce_variance = random.uniform(0.15, 0.35)  # 15-35% variance
        activity_pattern = random.choice(['steady', 'burst', 'declining', 'growing'])
        
        # Reset random seed to normal
        random.seed()
        
        profile = {
            'user_agent': user_agent,
            'client_name': ua_profile.name,
            'session_port': session_port,
            'announce_variance': base_announce_variance,
            'activity_pattern': activity_pattern,
            'session_start': datetime.utcnow(),
            'last_activity_change': datetime.utcnow(),
            'connection_stability': random.uniform(0.85, 0.98),  # 85-98% stability
        }
        
        return profile
    
    def _select_weighted_user_agent(self) -> UserAgentProfile:
        """Select user agent based on realistic market share"""
        total_weight = sum(profile.weight for profile in self.USER_AGENT_PROFILES)
        rand_weight = random.randint(1, total_weight)
        
        current_weight = 0
        for profile in self.USER_AGENT_PROFILES:
            current_weight += profile.weight
            if rand_weight <= current_weight:
                return profile
        
        return self.USER_AGENT_PROFILES[0]  # Fallback
    
    def get_natural_announce_interval(self, torrent_hash: str, base_interval: int) -> int:
        """Calculate natural announce interval with intelligent variance"""
        profile = self.get_session_profile(torrent_hash)
        
        # Time-based natural variations
        current_hour = datetime.now().hour
        time_factor = self._get_time_factor(current_hour)
        
        # Activity pattern influence
        activity_factor = self._get_activity_factor(profile['activity_pattern'], profile['session_start'])
        
        # Base variance from profile
        variance = profile['announce_variance']
        
        # Combine factors for natural behavior
        total_variance = variance * time_factor * activity_factor
        jitter_range = int(base_interval * total_variance)
        
        # Apply jitter with minimum bounds
        jitter = random.randint(-jitter_range, jitter_range)
        final_interval = max(base_interval + jitter, 90)  # Minimum 90s
        
        return final_interval
    
    def _get_time_factor(self, hour: int) -> float:
        """Natural activity variation by time of day - cached"""
        # Optimization: Cache time factors since they only change hourly
        if hour in self._time_factor_cache:
            cache_time = self._time_factor_cache[hour].get('timestamp')
            if cache_time and (datetime.utcnow() - cache_time).total_seconds() < 3600:  # 1 hour cache
                return self._time_factor_cache[hour]['factor']
        
        # Calculate new time factor
        if 18 <= hour <= 23 or 0 <= hour <= 2:
            factor = random.uniform(1.1, 1.3)  # More active
        elif 3 <= hour <= 7:
            factor = random.uniform(0.7, 0.9)  # Less active (night)
        elif 8 <= hour <= 17:
            factor = random.uniform(0.9, 1.1)  # Normal (work hours)
        else:
            factor = 1.0
        
        # Cache the result
        self._time_factor_cache[hour] = {
            'factor': factor,
            'timestamp': datetime.utcnow()
        }
        
        return factor
    
    def _get_activity_factor(self, pattern: str, session_start: datetime) -> float:
        """Activity factor based on seeding pattern and session age"""
        session_age_hours = (datetime.utcnow() - session_start).total_seconds() / 3600
        
        if pattern == 'steady':
            return random.uniform(0.95, 1.05)
        elif pattern == 'burst':
            # High activity initially, then declining
            if session_age_hours < 2:
                return random.uniform(1.2, 1.4)
            else:
                return random.uniform(0.8, 1.0)
        elif pattern == 'declining':
            # Gradually decrease activity
            decline_factor = min(session_age_hours / 24, 0.3)  # Max 30% decline over 24h
            return random.uniform(1.0 - decline_factor, 1.1 - decline_factor)
        elif pattern == 'growing':
            # Gradually increase activity
            growth_factor = min(session_age_hours / 48, 0.2)  # Max 20% growth over 48h
            return random.uniform(1.0 + growth_factor, 1.1 + growth_factor)
        
        return 1.0
    
    def should_simulate_temporary_disconnect(self, torrent_hash: str) -> bool:
        """Decide if torrent should simulate temporary disconnection (natural behavior)"""
        profile = self.get_session_profile(torrent_hash)
        stability = profile['connection_stability']
        
        # Very low chance of temporary disconnect based on stability
        disconnect_chance = (1.0 - stability) * 0.1  # Max 1.5% chance
        return random.random() < disconnect_chance
    
    def get_disconnect_duration(self) -> int:
        """Get natural disconnect duration (seconds)"""
        # Realistic disconnect patterns: 2-15 minutes
        return random.randint(120, 900)
    
    def get_natural_speed_variation(self, base_speed: int, torrent_hash: str) -> int:
        """Apply natural speed variations with caching - optimized"""
        if base_speed <= 0:
            return 0
        
        # Optimization: Cache speed calculations for 30 seconds to reduce CPU
        cache_key = f"{torrent_hash}_{base_speed}_{datetime.now().hour}"
        cached_result = self._speed_cache.get(cache_key)
        
        if cached_result and (datetime.utcnow() - cached_result['timestamp']).total_seconds() < 30:
            return cached_result['speed']
        
        profile = self.get_session_profile(torrent_hash)
        current_hour = datetime.now().hour
        
        # Time-based speed variations (network congestion patterns)
        time_multiplier = self._get_speed_time_multiplier(current_hour)
        
        # Activity pattern influence on speed
        activity_speed_factor = self._get_activity_speed_factor(profile['activity_pattern'])
        
        # Random micro-variations (±5-15%)
        micro_variation = random.uniform(0.85, 1.15)
        
        # Combine all factors
        final_speed = int(base_speed * time_multiplier * activity_speed_factor * micro_variation)
        final_speed = max(final_speed, 0)
        
        # Cache the result
        self._speed_cache[cache_key] = {
            'speed': final_speed,
            'timestamp': datetime.utcnow()
        }
        
        # Cleanup old cache entries (simple GC)
        if len(self._speed_cache) > 1000:  # Limit cache size
            old_keys = [k for k, v in self._speed_cache.items() 
                       if (datetime.utcnow() - v['timestamp']).total_seconds() > 60]
            for k in old_keys[:500]:  # Remove oldest 500
                del self._speed_cache[k]
        
        return final_speed
    
    def _get_speed_time_multiplier(self, hour: int) -> float:
        """Network speed variations by time (realistic ISP patterns)"""
        if 20 <= hour <= 23:  # Peak hours - slower
            return random.uniform(0.7, 0.9)
        elif 0 <= hour <= 6:   # Off-peak - faster
            return random.uniform(1.1, 1.3)
        else:  # Normal hours
            return random.uniform(0.9, 1.1)
    
    def _get_activity_speed_factor(self, pattern: str) -> float:
        """Speed factor based on activity pattern"""
        if pattern == 'burst':
            return random.uniform(1.1, 1.3)
        elif pattern == 'declining':
            return random.uniform(0.8, 1.0)
        elif pattern == 'growing':
            return random.uniform(1.0, 1.2)
        else:  # steady
            return random.uniform(0.95, 1.05)
    
    # ========== PHASE 4: ADVANCED ANTI-DETECTION ==========
    
    def get_gaussian_interval(self, base_interval: int, std_dev_percent: float = 0.15) -> int:
        """
        4.1 - Gaussian timing distribution (non-uniform)
        Returns interval with natural gaussian distribution around base value.
        More realistic than uniform random - real users don't have perfect timing.
        
        Args:
            base_interval: Base interval in seconds
            std_dev_percent: Standard deviation as percentage of base (default 15%)
            
        Returns:
            Interval with gaussian distribution, clamped to reasonable bounds
        """
        import math
        
        # Calculate standard deviation
        std_dev = base_interval * std_dev_percent
        
        # Generate gaussian random value
        interval = random.gauss(base_interval, std_dev)
        
        # Clamp to reasonable bounds (50% to 200% of base)
        min_interval = max(60, base_interval * 0.5)  # At least 60 seconds
        max_interval = base_interval * 2.0
        
        return int(max(min_interval, min(max_interval, interval)))
    
    def simulate_download_to_seed_transition(self, torrent_hash: str, torrent_size: int) -> Dict:
        """
        4.2 - Simulate realistic download→seed transition
        Returns realistic stats for a torrent that just finished downloading.
        
        Real behavior:
        - Download time varies by size and speed
        - Some bytes are often "corrupt" and re-downloaded
        - Upload starts before download completes (superseeding)
        """
        _profile = self.get_session_profile(torrent_hash)  # Keep for potential future use
        
        # Use torrent hash as seed for consistency
        seed = int(hashlib.md5(torrent_hash.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        
        # Simulate download speed (1-50 MB/s realistic range)
        download_speed = rng.uniform(1, 50) * 1024 * 1024  # bytes/s
        download_time = torrent_size / download_speed
        
        # Some data is re-downloaded (0.1-2% typically)
        corrupt_percent = rng.uniform(0.001, 0.02)
        extra_downloaded = int(torrent_size * corrupt_percent)
        total_downloaded = torrent_size + extra_downloaded
        
        # Upload during download (superseeding, usually 5-30% of download)
        upload_during_download_percent = rng.uniform(0.05, 0.30)
        initial_upload = int(torrent_size * upload_during_download_percent)
        
        return {
            'downloaded': total_downloaded,
            'uploaded': initial_upload,
            'corrupt_bytes': extra_downloaded,
            'download_time_seconds': int(download_time),
            'left': 0,  # Completed
            'ratio_at_completion': initial_upload / torrent_size if torrent_size > 0 else 0
        }
    
    def get_rotated_port(self, torrent_hash: str, rotation_interval_hours: int = 24) -> int:
        """
        4.3 - Intelligent port rotation (anti-fingerprint)
        Returns a port that changes periodically but stays consistent within intervals.
        
        Real clients sometimes reconnect with different ports due to:
        - Router reboots, NAT changes
        - Client restarts
        - Network changes
        """
        profile = self.get_session_profile(torrent_hash)
        
        # Calculate which rotation period we're in
        session_age = datetime.utcnow() - profile['session_start']
        rotation_period = int(session_age.total_seconds() / (rotation_interval_hours * 3600))
        
        # Generate port based on hash + rotation period
        port_seed = f"{torrent_hash}_{rotation_period}"
        seed_value = int(hashlib.md5(port_seed.encode()).hexdigest()[:8], 16)
        
        # Generate port in ephemeral range (49152-65535)
        rng = random.Random(seed_value)
        return rng.randint(49152, 65535)
    
    def get_corrupt_field_value(self, torrent_hash: str, total_downloaded: int) -> int:
        """
        4.4 - Corrupt field simulation
        Returns realistic "corrupt" bytes value that some trackers expect.
        
        Real torrents have:
        - Hash check failures (rare)
        - Network errors requiring re-download
        - Piece verification failures
        
        Typically 0.01-0.5% of total data, sometimes 0.
        """
        # Use hash for consistency
        seed = int(hashlib.md5(f"{torrent_hash}_corrupt".encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        
        # 70% chance of no corruption at all (healthy swarm)
        if rng.random() < 0.70:
            return 0
        
        # Generate small corrupt amount (0.01% to 0.5%)
        corrupt_percent = rng.uniform(0.0001, 0.005)
        corrupt_bytes = int(total_downloaded * corrupt_percent)
        
        # Round to piece-like boundaries (16KB typical piece)
        piece_size = 16 * 1024
        corrupt_bytes = (corrupt_bytes // piece_size) * piece_size
        
        return max(0, corrupt_bytes)
    
    def get_crypto_support_flags(self, client_name: str) -> Dict[str, bool]:
        """
        4.5 - Dynamic crypto support based on client
        Returns crypto/encryption flags consistent with the emulated client.
        
        Different clients have different encryption support:
        - qBittorrent: Full MSE/PE support
        - Transmission: RC4 encryption
        - Deluge: Configurable
        """
        crypto_profiles = {
            'qBittorrent': {
                'supportcrypto': True,
                'requirecrypto': False,
                'cryptoport': True,
            },
            'Transmission': {
                'supportcrypto': True,
                'requirecrypto': False,
                'cryptoport': False,
            },
            'Deluge': {
                'supportcrypto': True,
                'requirecrypto': False,
                'cryptoport': True,
            },
            'uTorrent': {
                'supportcrypto': True,
                'requirecrypto': False,
                'cryptoport': True,
            },
            'BitTorrent': {
                'supportcrypto': True,
                'requirecrypto': False,
                'cryptoport': True,
            },
        }
        
        # Find matching profile or default
        for name, flags in crypto_profiles.items():
            if name.lower() in client_name.lower():
                return flags
        
        # Default: basic crypto support
        return {
            'supportcrypto': True,
            'requirecrypto': False,
            'cryptoport': False,
        }
    
    def get_session_stats(self, torrent_hash: str) -> Dict:
        """Get session statistics for monitoring"""
        if torrent_hash not in self.session_profiles:
            return {}
        
        profile = self.session_profiles[torrent_hash]
        session_duration = (datetime.utcnow() - profile['session_start']).total_seconds()
        
        return {
            'client': profile['client_name'],
            'user_agent': profile['user_agent'],
            'session_port': profile['session_port'],
            'activity_pattern': profile['activity_pattern'],
            'session_duration_hours': round(session_duration / 3600, 1),
            'connection_stability': round(profile['connection_stability'] * 100, 1),
        }


# Global stealth service instance
stealth_service = StealthService()