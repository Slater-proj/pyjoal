"""
Version checker service for PyJOAL
Checks for updates from GitHub releases with daily caching
"""
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
import json
import os
from pathlib import Path

class VersionChecker:
    def __init__(self):
        self.cache_file = Path("/tmp/pyjoal_version_check.json")
        self.cache_duration = timedelta(hours=24)  # Check once per day
        self.github_api_url = "https://api.github.com/repos/anthonyraymond/pyjoal/releases/latest"
        self.current_version = "1.5.0"  # Current version
        
    async def get_version_info(self) -> Dict:
        """Get version info with daily caching"""
        try:
            # Check cache first
            cached_info = self._read_cache()
            if cached_info and self._is_cache_valid(cached_info):
                return cached_info["data"]
                
            # Fetch from GitHub
            version_info = await self._fetch_latest_version()
            
            # Cache the result
            self._write_cache(version_info)
            
            return version_info
            
        except Exception as e:
            print(f"Version check error: {e}")
            # Return cached data even if expired, or default
            cached_info = self._read_cache()
            if cached_info:
                return cached_info["data"]
            return self._get_default_version_info()
    
    async def _fetch_latest_version(self) -> Dict:
        """Fetch latest version from GitHub API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.github_api_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    latest_version = data.get("tag_name", "").replace("v", "")
                    
                    return {
                        "current_version": self.current_version,
                        "latest_version": latest_version,
                        "update_available": self._compare_versions(self.current_version, latest_version),
                        "release_url": data.get("html_url", ""),
                        "release_notes": data.get("body", "")[:200] + "..." if len(data.get("body", "")) > 200 else data.get("body", ""),
                        "published_at": data.get("published_at", ""),
                        "last_check": datetime.now().isoformat(),
                        "is_dev_version": self._is_dev_version(self.current_version, latest_version)
                    }
                else:
                    return self._get_default_version_info()
        except Exception as e:
            print(f"GitHub API error: {e}")
            return self._get_default_version_info()
    
    def _compare_versions(self, current: str, latest: str) -> bool:
        """Simple version comparison (works for semantic versioning)"""
        try:
            # Handle "unknown" latest version (dev case)
            if latest == "unknown" or not latest:
                return False
            
            current_parts = [int(x) for x in current.split(".")]
            latest_parts = [int(x) for x in latest.split(".")]
            
            # Pad shorter version with zeros
            max_length = max(len(current_parts), len(latest_parts))
            current_parts += [0] * (max_length - len(current_parts))
            latest_parts += [0] * (max_length - len(latest_parts))
            
            return latest_parts > current_parts
        except:
            return False
    
    def _is_dev_version(self, current: str, latest: str) -> bool:
        """Check if current version is ahead of latest GitHub release (dev version)"""
        try:
            if latest == "unknown" or not latest:
                return True  # Assume dev version if can't check GitHub
            
            current_parts = [int(x) for x in current.split(".")]
            latest_parts = [int(x) for x in latest.split(".")]
            
            # Pad shorter version with zeros
            max_length = max(len(current_parts), len(latest_parts))
            current_parts += [0] * (max_length - len(current_parts))
            latest_parts += [0] * (max_length - len(latest_parts))
            
            return current_parts > latest_parts  # Current is ahead of GitHub
        except:
            return True  # Assume dev version on error
    
    def _read_cache(self) -> Optional[Dict]:
        """Read cached version info"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return None
    
    def _write_cache(self, data: Dict):
        """Write version info to cache"""
        try:
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "data": data
            }
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f)
        except:
            pass
    
    def _is_cache_valid(self, cached_info: Dict) -> bool:
        """Check if cache is still valid (within 24h)"""
        try:
            cache_time = datetime.fromisoformat(cached_info["timestamp"])
            return datetime.now() - cache_time < self.cache_duration
        except:
            return False
    
    def _get_default_version_info(self) -> Dict:
        """Default version info when GitHub is unreachable"""
        return {
            "current_version": self.current_version,
            "latest_version": "unknown",
            "update_available": False,
            "release_url": "",
            "release_notes": "",
            "published_at": "",
            "last_check": datetime.now().isoformat(),
            "is_dev_version": True,  # Mark as dev version
            "error": "Unable to check for updates (API rate limit or network issue)"
        }

# Global instance
version_checker = VersionChecker()