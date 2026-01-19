"""
Tests for magnet_link.py - Magnet link parsing
"""
import pytest
import base64

from app.core.magnet_link import (
    parse_magnet_link,
    MagnetInfo,
    MagnetLinkError,
    MagnetTorrent
)


class TestMagnetLinkParsing:
    """Test magnet link parsing"""
    
    def test_parse_basic_magnet_hex_hash(self):
        """Test parsing magnet with hex info hash"""
        magnet = "magnet:?xt=urn:btih:a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"
        
        info = parse_magnet_link(magnet)
        
        assert info.info_hash == "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"
        assert len(info.info_hash) == 40
    
    def test_parse_magnet_with_name(self):
        """Test parsing magnet with display name"""
        magnet = "magnet:?xt=urn:btih:a94a8fe5ccb19ba61c4c0873d391e987982fbbd3&dn=Test%20Torrent"
        
        info = parse_magnet_link(magnet)
        
        assert info.info_hash == "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"
        assert info.name == "Test Torrent"
    
    def test_parse_magnet_with_trackers(self):
        """Test parsing magnet with tracker URLs"""
        magnet = (
            "magnet:?xt=urn:btih:a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"
            "&tr=http://tracker1.com/announce"
            "&tr=udp://tracker2.com:6969/announce"
        )
        
        info = parse_magnet_link(magnet)
        
        assert info.info_hash == "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"
        assert len(info.trackers) == 2
        assert "http://tracker1.com/announce" in info.trackers
        assert "udp://tracker2.com:6969/announce" in info.trackers
    
    def test_parse_magnet_with_size(self):
        """Test parsing magnet with file size"""
        magnet = "magnet:?xt=urn:btih:a94a8fe5ccb19ba61c4c0873d391e987982fbbd3&xl=1073741824"
        
        info = parse_magnet_link(magnet)
        
        assert info.info_hash == "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"
        assert info.size == 1073741824
    
    def test_parse_magnet_base32_hash(self):
        """Test parsing magnet with base32 info hash"""
        # Create a known base32 hash
        hex_hash = "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"
        bytes_hash = bytes.fromhex(hex_hash)
        base32_hash = base64.b32encode(bytes_hash).decode('ascii').rstrip('=')
        
        magnet = f"magnet:?xt=urn:btih:{base32_hash}"
        
        info = parse_magnet_link(magnet)
        
        assert info.info_hash == hex_hash
    
    def test_parse_complete_magnet(self):
        """Test parsing complete magnet with all params"""
        magnet = (
            "magnet:?xt=urn:btih:a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"
            "&dn=Ubuntu%2024.04%20Desktop"
            "&xl=5368709120"
            "&tr=http://tracker.ubuntu.com/announce"
            "&tr=udp://tracker.opentrackr.org:1337/announce"
        )
        
        info = parse_magnet_link(magnet)
        
        assert info.info_hash == "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"
        assert info.name == "Ubuntu 24.04 Desktop"
        assert info.size == 5368709120
        assert len(info.trackers) >= 2


class TestMagnetLinkErrors:
    """Test magnet link error handling"""
    
    def test_invalid_prefix_raises_error(self):
        """Test non-magnet URI raises error"""
        with pytest.raises(MagnetLinkError) as exc_info:
            parse_magnet_link("http://example.com")
        
        assert "must start with 'magnet:?'" in str(exc_info.value)
    
    def test_missing_info_hash_raises_error(self):
        """Test magnet without xt parameter raises error"""
        with pytest.raises(MagnetLinkError) as exc_info:
            parse_magnet_link("magnet:?dn=Test")
        
        assert "Missing xt" in str(exc_info.value) or "info hash" in str(exc_info.value).lower()
    
    def test_invalid_hash_length_raises_error(self):
        """Test invalid hash length raises error"""
        with pytest.raises(MagnetLinkError) as exc_info:
            parse_magnet_link("magnet:?xt=urn:btih:tooshort")
        
        assert "Invalid" in str(exc_info.value)


class TestMagnetValidation:
    """Test magnet link validation functions"""
    
    def test_is_valid_magnet_true(self):
        """Test valid magnet returns parsed info"""
        magnet = "magnet:?xt=urn:btih:a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"
        
        info = parse_magnet_link(magnet)
        assert info is not None
        assert info.info_hash == "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"
    
    def test_is_valid_magnet_false(self):
        """Test invalid magnet raises errors"""
        with pytest.raises(MagnetLinkError):
            parse_magnet_link("http://example.com")
        
        with pytest.raises(MagnetLinkError):
            parse_magnet_link("magnet:?dn=Test")


class TestInfoHashExtraction:
    """Test info hash extraction"""
    
    def test_extract_info_hash(self):
        """Test extracting info hash from magnet"""
        magnet = "magnet:?xt=urn:btih:a94a8fe5ccb19ba61c4c0873d391e987982fbbd3&dn=Test"
        
        info = parse_magnet_link(magnet)
        
        assert info.info_hash == "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"
    
    def test_extract_info_hash_case_insensitive(self):
        """Test info hash extraction is case insensitive"""
        magnet = "magnet:?xt=urn:btih:A94A8FE5CCB19BA61C4C0873D391E987982FBBD3"
        
        info = parse_magnet_link(magnet)
        
        assert info.info_hash == "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"


class TestMagnetInfoDataclass:
    """Test MagnetInfo dataclass"""
    
    def test_magnet_info_creation(self):
        """Test creating MagnetInfo"""
        info = MagnetInfo(
            info_hash="a" * 40,
            info_hash_bytes=bytes.fromhex("a" * 40),
            name="Test",
            trackers=["http://tracker.com/announce"]
        )
        
        assert info.info_hash == "a" * 40
        assert info.name == "Test"
        assert len(info.trackers) == 1
    
    def test_magnet_info_default_trackers(self):
        """Test MagnetInfo initializes empty tracker list"""
        info = MagnetInfo(
            info_hash="b" * 40,
            info_hash_bytes=bytes.fromhex("b" * 40)
        )
        
        assert info.trackers == []
