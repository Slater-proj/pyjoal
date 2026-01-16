"""
Tests for the Version Checker Service
"""
import pytest
from unittest.mock import patch, Mock, AsyncMock
from datetime import datetime, timedelta
import json
from pathlib import Path
import tempfile
import os

from app.services.version_checker import VersionChecker


class TestVersionChecker:
    
    def setup_method(self):
        """Setup test fixtures"""
        self.version_checker = VersionChecker()
        # Use a temp file for testing
        self.temp_dir = tempfile.mkdtemp()
        self.version_checker.cache_file = Path(self.temp_dir) / "test_version_cache.json"
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        if self.version_checker.cache_file.exists():
            self.version_checker.cache_file.unlink()
        os.rmdir(self.temp_dir)
    
    def test_version_comparison(self):
        """Test version comparison logic"""
        # Test newer version available
        assert self.version_checker._compare_versions("1.4.0", "1.5.0") == True
        assert self.version_checker._compare_versions("1.5.0", "1.5.1") == True
        assert self.version_checker._compare_versions("1.5.0", "2.0.0") == True
        
        # Test same version
        assert self.version_checker._compare_versions("1.5.0", "1.5.0") == False
        
        # Test older version (no update needed)
        assert self.version_checker._compare_versions("1.5.0", "1.4.0") == False
        assert self.version_checker._compare_versions("2.0.0", "1.9.9") == False
        
        # Test unknown version
        assert self.version_checker._compare_versions("1.5.0", "unknown") == False
        assert self.version_checker._compare_versions("1.5.0", "") == False
    
    def test_is_dev_version(self):
        """Test development version detection"""
        # Test dev version (current > latest)
        assert self.version_checker._is_dev_version("1.5.0", "1.4.0") == True
        assert self.version_checker._is_dev_version("2.0.0", "1.9.9") == True
        
        # Test stable version (current <= latest)
        assert self.version_checker._is_dev_version("1.4.0", "1.5.0") == False
        assert self.version_checker._is_dev_version("1.5.0", "1.5.0") == False
        
        # Test unknown latest version (assume dev)
        assert self.version_checker._is_dev_version("1.5.0", "unknown") == True
        assert self.version_checker._is_dev_version("1.5.0", "") == True
    
    def test_cache_operations(self):
        """Test cache read/write operations"""
        # Test empty cache
        assert self.version_checker._read_cache() is None
        
        # Test write and read cache
        test_data = {
            "current_version": "1.5.0",
            "latest_version": "1.5.1",
            "update_available": True,
            "last_check": datetime.now().isoformat()
        }
        
        self.version_checker._write_cache(test_data)
        cached_data = self.version_checker._read_cache()
        
        assert cached_data is not None
        assert cached_data["data"] == test_data
        assert "timestamp" in cached_data
    
    def test_cache_validity(self):
        """Test cache validity checking"""
        # Test valid cache (recent)
        valid_cache = {
            "timestamp": datetime.now().isoformat(),
            "data": {"test": "data"}
        }
        assert self.version_checker._is_cache_valid(valid_cache) == True
        
        # Test invalid cache (old)
        old_cache = {
            "timestamp": (datetime.now() - timedelta(hours=25)).isoformat(),
            "data": {"test": "data"}
        }
        assert self.version_checker._is_cache_valid(old_cache) == False
        
        # Test invalid cache format
        assert self.version_checker._is_cache_valid({}) == False
        assert self.version_checker._is_cache_valid({"timestamp": "invalid"}) == False
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_fetch_latest_version_success(self, mock_client):
        """Test successful GitHub API fetch"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tag_name": "v1.5.1",
            "html_url": "https://github.com/repo/releases/tag/v1.5.1",
            "body": "Release notes for v1.5.1",
            "published_at": "2026-01-16T12:00:00Z"
        }
        
        mock_async_client = AsyncMock()
        mock_async_client.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_async_client
        
        result = await self.version_checker._fetch_latest_version()
        
        assert result["current_version"] == "1.5.0"
        assert result["latest_version"] == "1.5.1"
        assert result["update_available"] == True
        assert result["release_url"] == "https://github.com/repo/releases/tag/v1.5.1"
        assert result["is_dev_version"] == False
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_fetch_latest_version_dev_version(self, mock_client):
        """Test fetch when current version is ahead (dev version)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tag_name": "v1.4.0",  # Older than current 1.5.0
            "html_url": "https://github.com/repo/releases/tag/v1.4.0",
            "body": "Release notes for v1.4.0",
            "published_at": "2026-01-15T12:00:00Z"
        }
        
        mock_async_client = AsyncMock()
        mock_async_client.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_async_client
        
        result = await self.version_checker._fetch_latest_version()
        
        assert result["current_version"] == "1.5.0"
        assert result["latest_version"] == "1.4.0"
        assert result["update_available"] == False
        assert result["is_dev_version"] == True
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_fetch_latest_version_error(self, mock_client):
        """Test GitHub API error handling"""
        mock_async_client = AsyncMock()
        mock_async_client.get.side_effect = Exception("Network error")
        mock_client.return_value.__aenter__.return_value = mock_async_client
        
        result = await self.version_checker._fetch_latest_version()
        
        assert result["current_version"] == "1.5.0"
        assert result["latest_version"] == "unknown"
        assert result["update_available"] == False
        assert result["is_dev_version"] == True
        assert result["error"] == "Unable to check for updates (API rate limit or network issue)"
    
    @pytest.mark.asyncio
    async def test_get_version_info_with_cache(self):
        """Test version info retrieval with valid cache"""
        # Setup valid cache
        cached_data = {
            "current_version": "1.5.0",
            "latest_version": "1.5.1",
            "update_available": True,
            "last_check": datetime.now().isoformat()
        }
        self.version_checker._write_cache(cached_data)
        
        result = await self.version_checker.get_version_info()
        
        assert result == cached_data
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_version_info_cache_expired(self, mock_client):
        """Test version info retrieval with expired cache"""
        # Setup expired cache
        old_data = {
            "current_version": "1.5.0",
            "latest_version": "1.4.0",
            "update_available": False
        }
        old_cache = {
            "timestamp": (datetime.now() - timedelta(hours=25)).isoformat(),
            "data": old_data
        }
        
        with open(self.version_checker.cache_file, 'w') as f:
            json.dump(old_cache, f)
        
        # Mock new fetch
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tag_name": "v1.5.1",
            "html_url": "https://github.com/repo/releases/tag/v1.5.1",
            "body": "New release",
            "published_at": "2026-01-16T12:00:00Z"
        }
        
        mock_async_client = AsyncMock()
        mock_async_client.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_async_client
        
        result = await self.version_checker.get_version_info()
        
        # Should fetch new data, not use expired cache
        assert result["latest_version"] == "1.5.1"
        assert result["update_available"] == True
    
    def test_default_version_info(self):
        """Test default version info structure"""
        default_info = self.version_checker._get_default_version_info()
        
        required_keys = [
            "current_version", "latest_version", "update_available",
            "release_url", "release_notes", "published_at",
            "last_check", "is_dev_version", "error"
        ]
        
        for key in required_keys:
            assert key in default_info
        
        assert default_info["current_version"] == "1.5.0"
        assert default_info["latest_version"] == "unknown"
        assert default_info["update_available"] == False
        assert default_info["is_dev_version"] == True