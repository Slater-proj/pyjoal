"""
Tracker Manager
Handles multi-tracker tier management (BEP 12), tracker selection,
success/failure tracking, and scraping.
Extracted from tracker_announcer.py for better modularity.
"""
import random
import logging
import time
from typing import Optional, Dict, List

import httpx

from app.core.torrent_parser import Torrent
from app.core.bittorrent_client import BitTorrentClient
from app.core.udp_tracker import UDPTracker, is_udp_tracker

logger = logging.getLogger(__name__)


class TrackerManager:
    """Manages multi-tracker tiers, selection, and scraping for a torrent."""
    
    def __init__(self, torrent: Torrent, client: BitTorrentClient):
        """Initialize tracker manager.
        
        Args:
            torrent: Torrent instance
            client: BitTorrentClient instance
        """
        self.torrent = torrent
        self.client = client
        
        # Multi-tracker support (announce-list tiers — BEP 12)
        self._tracker_tiers: List[List[str]] = self._build_tracker_tiers()
        self._current_tier: int = 0
        self._current_tracker_idx: int = 0
        self._tracker_failures: Dict[str, int] = {}
        
        # UDP tracker instances cache
        self._udp_trackers: Dict[str, UDPTracker] = {}
    
    def _build_tracker_tiers(self) -> List[List[str]]:
        """Build tracker tiers from announce-list (BEP 12)."""
        tiers = []
        
        if hasattr(self.torrent, 'announce_list') and self.torrent.announce_list:
            for tier in self.torrent.announce_list:
                if isinstance(tier, list):
                    valid_trackers = [t for t in tier if t and isinstance(t, str)]
                    if valid_trackers:
                        random.shuffle(valid_trackers)
                        tiers.append(valid_trackers)
                elif isinstance(tier, str) and tier:
                    tiers.append([tier])
        
        if not tiers and self.torrent.primary_tracker:
            tiers.append([self.torrent.primary_tracker])
        
        logger.debug(f"Built {len(tiers)} tracker tier(s) for {self.torrent.name[:30]}")
        return tiers
    
    def get_next_tracker(self) -> Optional[str]:
        """Get next tracker to try (respecting tiers)."""
        if not self._tracker_tiers:
            return self.torrent.primary_tracker
        
        while self._current_tier < len(self._tracker_tiers):
            tier = self._tracker_tiers[self._current_tier]
            
            while self._current_tracker_idx < len(tier):
                tracker = tier[self._current_tracker_idx]
                self._current_tracker_idx += 1
                
                if self._tracker_failures.get(tracker, 0) < 3:
                    return tracker
            
            self._current_tier += 1
            self._current_tracker_idx = 0
        
        # Reset and start over
        self._current_tier = 0
        self._current_tracker_idx = 0
        
        if self._tracker_tiers and self._tracker_tiers[0]:
            return self._tracker_tiers[0][0]
        
        return self.torrent.primary_tracker
    
    def mark_tracker_success(self, tracker_url: str):
        """Mark tracker as successful (reset failure count)."""
        self._tracker_failures[tracker_url] = 0
        for tier in self._tracker_tiers:
            if tracker_url in tier:
                tier.remove(tracker_url)
                tier.insert(0, tracker_url)
                break
    
    def mark_tracker_failure(self, tracker_url: str):
        """Mark tracker as failed."""
        self._tracker_failures[tracker_url] = self._tracker_failures.get(tracker_url, 0) + 1
        logger.debug(f"Tracker failure #{self._tracker_failures[tracker_url]}: {tracker_url}")
    
    def get_or_create_udp_tracker(self, tracker_url: str) -> UDPTracker:
        """Get or create a UDP tracker client for the given URL."""
        if tracker_url not in self._udp_trackers:
            self._udp_trackers[tracker_url] = UDPTracker(tracker_url)
        return self._udp_trackers[tracker_url]
    
    # ================================================================
    # Scraping
    # ================================================================
    
    async def scrape_tracker(self, info_hash_bytes: bytes) -> Optional[Dict[str, int]]:
        """Scrape tracker for torrent stats (seeders/leechers)."""
        tracker_url = self.get_next_tracker()
        if not tracker_url:
            return None
        
        try:
            if is_udp_tracker(tracker_url):
                return await self._scrape_udp(tracker_url, info_hash_bytes)
            else:
                return await self._scrape_http(tracker_url, info_hash_bytes)
        except Exception as e:
            logger.debug(f"Scrape failed for {tracker_url}: {e}")
            return None
    
    async def _scrape_udp(self, tracker_url: str, info_hash_bytes: bytes) -> Optional[Dict[str, int]]:
        """Scrape UDP tracker."""
        try:
            udp_tracker = self.get_or_create_udp_tracker(tracker_url)
            results = await udp_tracker.scrape([info_hash_bytes])
            
            if info_hash_bytes in results:
                scrape = results[info_hash_bytes]
                return {
                    'seeders': scrape.seeders,
                    'leechers': scrape.leechers,
                    'completed': scrape.completed
                }
        except Exception as e:
            logger.debug(f"UDP scrape failed: {e}")
        
        return None
    
    async def _scrape_http(self, tracker_url: str, info_hash_bytes: bytes) -> Optional[Dict[str, int]]:
        """Scrape HTTP tracker."""
        try:
            scrape_url = tracker_url.replace('/announce', '/scrape')
            if scrape_url == tracker_url:
                return None
            
            encoded_hash = self.client.url_encode(info_hash_bytes)
            scrape_url = f"{scrape_url}?info_hash={encoded_hash}"
            
            headers = self.client.get_request_headers()
            
            async with httpx.AsyncClient(timeout=15.0, headers=headers, verify=False) as client:
                response = await client.get(scrape_url)
                
                if response.status_code == 200:
                    return self._parse_scrape_response(response.content)
        except Exception as e:
            logger.debug(f"HTTP scrape failed: {e}")
        
        return None
    
    @staticmethod
    def _parse_scrape_response(data: bytes) -> Optional[Dict[str, int]]:
        """Parse HTTP scrape response."""
        try:
            import bencodepy
            decoded = bencodepy.decode(data)
            
            if b'files' in decoded:
                files = decoded[b'files']
                for info_hash, stats in files.items():
                    return {
                        'seeders': stats.get(b'complete', 0),
                        'leechers': stats.get(b'incomplete', 0),
                        'completed': stats.get(b'downloaded', 0)
                    }
        except Exception as e:
            logger.debug(f"Scrape parse error: {e}")
        
        return None
