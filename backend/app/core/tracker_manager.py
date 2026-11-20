"""
Tracker Manager
Handles multi-tracker tier management (BEP 12), tracker selection,
success/failure tracking, and scraping.
Extracted from tracker_announcer.py for better modularity.
"""
import random
import logging
from typing import Optional, Dict, List

import httpx

from app.core.torrent_parser import Torrent
from app.core.bittorrent_client import BitTorrentClient
from app.core.udp_tracker import UDPTracker, is_udp_tracker
from app.core.config import settings

logger = logging.getLogger(__name__)


class TrackerManager:
    """Manages multi-tracker tiers, selection, and scraping for a torrent."""

    # Consecutive failures before a tracker is skipped
    MAX_FAILURES = 3

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
        self._udp_proxy_warned: bool = False

        # Trackers that permanently refused this torrent (unregistered, bad
        # passkey...): never announced to again until reset_rejections()
        self._rejected: set = set()

    @staticmethod
    def _proxy_configured() -> bool:
        return bool(settings.HTTP_PROXY_HOST and settings.HTTP_PROXY_PORT)

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
        """Return the tracker to announce to (BEP 12).

        Trackers are tried in tier order; within a tier, the first tracker
        that has not failed repeatedly is used.  A successful tracker is moved
        to the front of its tier (see mark_tracker_success), so we *stick* to
        it on subsequent announces.  We only move on after failures.

        (The previous implementation advanced an index on every call, so a
        multi-tracker torrent rotated to a different tracker on each announce:
        trackers received regular announces without ever seeing 'started',
        and 'stopped' went to whichever tracker was next.)
        """
        if not self._tracker_tiers:
            return self.torrent.primary_tracker

        # UDP announces cannot go through the HTTP proxy: when a proxy is
        # configured, prefer any healthy HTTP(S) tracker so the real IP is not
        # exposed; fall back to UDP only if nothing else is available.
        if self._proxy_configured():
            for tier in self._tracker_tiers:
                for tracker in tier:
                    if (not is_udp_tracker(tracker) and tracker not in self._rejected
                            and self._tracker_failures.get(tracker, 0) < self.MAX_FAILURES):
                        return tracker
            if not self._udp_proxy_warned:
                logger.warning(
                    f"⚠️ {self.torrent.name[:40]}: only UDP trackers available - "
                    "UDP announces bypass the HTTP proxy (real IP visible to the tracker)"
                )
                self._udp_proxy_warned = True

        for tier in self._tracker_tiers:
            for tracker in tier:
                if tracker not in self._rejected and self._tracker_failures.get(tracker, 0) < self.MAX_FAILURES:
                    return tracker

        # Every tracker failed repeatedly: forget failures and start over
        # (permanently rejecting trackers stay excluded)
        logger.debug(f"All trackers failed for {self.torrent.name[:30]}, resetting failure counters")
        self._tracker_failures.clear()
        for tier in self._tracker_tiers:
            for tracker in tier:
                if tracker not in self._rejected:
                    return tracker
        return self.torrent.primary_tracker

    def mark_tracker_rejected(self, tracker_url: str):
        """The tracker permanently refused this torrent (BEP 3 'failure reason')."""
        self._rejected.add(tracker_url)
        logger.debug(f"Tracker permanently rejected torrent: {tracker_url}")

    def all_trackers_rejected(self) -> bool:
        """True when every known tracker permanently refused the torrent."""
        known = {t for tier in self._tracker_tiers for t in tier}
        if not known and self.torrent.primary_tracker:
            known = {self.torrent.primary_tracker}
        return bool(known) and known <= self._rejected

    def reset_rejections(self):
        """Forget permanent rejections (user explicitly resumed the torrent)."""
        self._rejected.clear()
        self._tracker_failures.clear()

    def mark_tracker_success(self, tracker_url: str):
        """Mark tracker as successful (reset failure count, move to front of tier)."""
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
            
            proxy_kwargs = {}
            if self._proxy_configured():
                proxy_kwargs['proxy'] = f"http://{settings.HTTP_PROXY_HOST}:{settings.HTTP_PROXY_PORT}"
            async with httpx.AsyncClient(timeout=15.0, headers=headers,
                                         verify=settings.TRACKER_VERIFY_SSL, **proxy_kwargs) as client:
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
