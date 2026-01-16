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
        """Initialize stealth service"""
        self.session_profiles: Dict[str, Dict] = {}  # Per-torrent session data
        self._natural_timing_cache = {}
        
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
        """Natural activity variation by time of day"""
        # Higher activity during evening/night hours (18-24, 0-2)
        if 18 <= hour <= 23 or 0 <= hour <= 2:
            return random.uniform(1.1, 1.3)  # More active
        elif 3 <= hour <= 7:
            return random.uniform(0.7, 0.9)  # Less active (night)
        elif 8 <= hour <= 17:
            return random.uniform(0.9, 1.1)  # Normal (work hours)
        else:
            return 1.0
    
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
        """Apply natural speed variations based on time and activity"""
        if base_speed <= 0:
            return 0
        
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
        
        return max(final_speed, 0)
    
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