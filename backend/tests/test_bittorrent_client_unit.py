"""
Tests for bittorrent_client.py - Client emulation and peer ID generation
"""
import pytest
from unittest.mock import Mock, patch, mock_open
import json
from pathlib import Path

from app.core.bittorrent_client import BitTorrentClient


class TestBitTorrentClientInit:
    """Test BitTorrentClient initialization"""
    
    def test_load_valid_client_file(self, tmp_path):
        """Test loading a valid client configuration file"""
        client_config = {
            "name": "qBittorrent",
            "version": "4.6.0",
            "peerIdGenerator": {
                "refreshOn": "NEVER",
                "algorithm": {
                    "type": "REGEX",
                    "pattern": "-qB4060-[A-Za-z0-9]{12}"
                }
            },
            "keyGenerator": {
                "refreshOn": "NEVER",
                "algorithm": {
                    "type": "HASH",
                    "length": 8
                }
            },
            "query": "info_hash={infohash}&peer_id={peerid}&port={port}"
        }
        
        client_file = tmp_path / "test.client"
        client_file.write_text(json.dumps(client_config))
        
        with patch('app.core.bittorrent_client.settings') as mock_settings:
            mock_settings.CLIENTS_DIR = tmp_path
            client = BitTorrentClient("test.client")
        
        assert client.name == "qBittorrent"
        assert client.version == "4.6.0"
    
    def test_load_nonexistent_file_raises_error(self, tmp_path):
        """Test loading non-existent file raises FileNotFoundError"""
        with patch('app.core.bittorrent_client.settings') as mock_settings:
            mock_settings.CLIENTS_DIR = tmp_path
            
            with pytest.raises(FileNotFoundError):
                BitTorrentClient("nonexistent.client")


class TestPeerIdGeneration:
    """Test peer ID generation algorithms"""
    
    def test_peer_id_is_20_bytes(self, tmp_path):
        """Test that generated peer ID is exactly 20 bytes"""
        client_config = {
            "name": "TestClient",
            "version": "1.0",
            "peerIdGenerator": {
                "refreshOn": "NEVER",
                "algorithm": {
                    "type": "REGEX",
                    "pattern": "-TC1000-[A-Za-z0-9]{12}"
                }
            },
            "keyGenerator": {"refreshOn": "NEVER", "algorithm": {"type": "HASH", "length": 8}},
            "query": ""
        }
        
        client_file = tmp_path / "test.client"
        client_file.write_text(json.dumps(client_config))
        
        with patch('app.core.bittorrent_client.settings') as mock_settings:
            mock_settings.CLIENTS_DIR = tmp_path
            client = BitTorrentClient("test.client")
        
        peer_id = client.generate_peer_id("a" * 40)
        assert len(peer_id) == 20
    
    def test_peer_id_caching_never(self, tmp_path):
        """Test peer ID is cached with refreshOn=NEVER"""
        client_config = {
            "name": "TestClient",
            "version": "1.0",
            "peerIdGenerator": {
                "refreshOn": "NEVER",
                "algorithm": {
                    "type": "REGEX",
                    "pattern": "-TC1000-[A-Za-z0-9]{12}"
                }
            },
            "keyGenerator": {"refreshOn": "NEVER", "algorithm": {"type": "HASH", "length": 8}},
            "query": ""
        }
        
        client_file = tmp_path / "test.client"
        client_file.write_text(json.dumps(client_config))
        
        with patch('app.core.bittorrent_client.settings') as mock_settings:
            mock_settings.CLIENTS_DIR = tmp_path
            client = BitTorrentClient("test.client")
        
        # Same peer_id for different torrents when refreshOn=NEVER
        peer_id_1 = client.generate_peer_id("a" * 40)
        peer_id_2 = client.generate_peer_id("b" * 40)
        assert peer_id_1 == peer_id_2
    
    def test_peer_id_caching_torrent_persistent(self, tmp_path):
        """Test peer ID is cached per torrent with refreshOn=TORRENT_PERSISTENT"""
        client_config = {
            "name": "TestClient",
            "version": "1.0",
            "peerIdGenerator": {
                "refreshOn": "TORRENT_PERSISTENT",
                "algorithm": {
                    "type": "REGEX",
                    "pattern": "-TC1000-[A-Za-z0-9]{12}"
                }
            },
            "keyGenerator": {"refreshOn": "NEVER", "algorithm": {"type": "HASH", "length": 8}},
            "query": ""
        }
        
        client_file = tmp_path / "test.client"
        client_file.write_text(json.dumps(client_config))
        
        with patch('app.core.bittorrent_client.settings') as mock_settings:
            mock_settings.CLIENTS_DIR = tmp_path
            client = BitTorrentClient("test.client")
        
        # Different peer_id per torrent
        peer_id_1 = client.generate_peer_id("a" * 40)
        peer_id_2 = client.generate_peer_id("b" * 40)
        
        # But same peer_id for same torrent
        peer_id_1_again = client.generate_peer_id("a" * 40)
        
        assert peer_id_1 != peer_id_2
        assert peer_id_1 == peer_id_1_again


class TestKeyGeneration:
    """Test key generation algorithms"""
    
    def test_key_generation_hash(self, tmp_path):
        """Test HASH key generation"""
        client_config = {
            "name": "TestClient",
            "version": "1.0",
            "peerIdGenerator": {
                "refreshOn": "NEVER",
                "algorithm": {"type": "REGEX", "pattern": "-TC1000-[A-Za-z0-9]{12}"}
            },
            "keyGenerator": {
                "refreshOn": "NEVER",
                "algorithm": {
                    "type": "HASH",
                    "length": 8
                }
            },
            "query": ""
        }
        
        client_file = tmp_path / "test.client"
        client_file.write_text(json.dumps(client_config))
        
        with patch('app.core.bittorrent_client.settings') as mock_settings:
            mock_settings.CLIENTS_DIR = tmp_path
            client = BitTorrentClient("test.client")
        
        key = client.generate_key("a" * 40)
        assert key is not None
        assert isinstance(key, str)


class TestAnnounceUrlBuilding:
    """Test announce URL building"""
    
    def test_build_announce_url(self, tmp_path):
        """Test building announce URL with parameters"""
        client_config = {
            "name": "qBittorrent",
            "version": "4.6.0",
            "peerIdGenerator": {
                "refreshOn": "NEVER",
                "algorithm": {"type": "REGEX", "pattern": "-qB4060-[A-Za-z0-9]{12}"}
            },
            "keyGenerator": {
                "refreshOn": "NEVER",
                "algorithm": {"type": "HASH", "length": 8}
            },
            "query": "info_hash={infohash}&peer_id={peerid}&port={port}&uploaded={uploaded}&downloaded={downloaded}&left={left}&corrupt=0&key={key}&event={event}&numwant={numwant}&compact=1&no_peer_id=1&supportcrypto=1&redundant=0",
            "numwant": 200,
            "numwantOnStop": 0
        }
        
        client_file = tmp_path / "test.client"
        client_file.write_text(json.dumps(client_config))
        
        with patch('app.core.bittorrent_client.settings') as mock_settings:
            mock_settings.CLIENTS_DIR = tmp_path
            client = BitTorrentClient("test.client")
        
        # Use bytes for info_hash as expected by the function
        info_hash_bytes = bytes.fromhex("a" * 40)
        
        url = client.build_announce_url(
            tracker_url="http://tracker.example.com/announce",
            info_hash=info_hash_bytes,
            peer_id="-qB4060-" + "A" * 12,
            port=51413,
            uploaded=1024,
            downloaded=2048,
            left=0,
            event="started"
        )
        
        assert "http://tracker.example.com/announce" in url
        assert "info_hash=" in url
        assert "peer_id=" in url
        assert "port=51413" in url
        assert "uploaded=1024" in url
        assert "event=started" in url


class TestClientProperties:
    """Test client property accessors"""
    
    def test_name_property(self, tmp_path):
        """Test name property returns client name"""
        client_config = {
            "name": "Transmission",
            "version": "4.0.5",
            "peerIdGenerator": {"refreshOn": "NEVER", "algorithm": {"type": "REGEX", "pattern": "-TR4050-[A-Za-z0-9]{12}"}},
            "keyGenerator": {"refreshOn": "NEVER", "algorithm": {"type": "HASH", "length": 8}},
            "query": ""
        }
        
        client_file = tmp_path / "test.client"
        client_file.write_text(json.dumps(client_config))
        
        with patch('app.core.bittorrent_client.settings') as mock_settings:
            mock_settings.CLIENTS_DIR = tmp_path
            client = BitTorrentClient("test.client")
        
        assert client.name == "Transmission"
    
    def test_version_property(self, tmp_path):
        """Test version property returns client version"""
        client_config = {
            "name": "Deluge",
            "version": "2.1.1",
            "peerIdGenerator": {"refreshOn": "NEVER", "algorithm": {"type": "REGEX", "pattern": "-DE2110-[A-Za-z0-9]{12}"}},
            "keyGenerator": {"refreshOn": "NEVER", "algorithm": {"type": "HASH", "length": 8}},
            "query": ""
        }
        
        client_file = tmp_path / "test.client"
        client_file.write_text(json.dumps(client_config))
        
        with patch('app.core.bittorrent_client.settings') as mock_settings:
            mock_settings.CLIENTS_DIR = tmp_path
            client = BitTorrentClient("test.client")
        
        assert client.version == "2.1.1"


class TestSessionPort:
    """Test session port generation"""
    
    def test_session_port_in_valid_range(self, tmp_path):
        """Test session port is in valid ephemeral range"""
        client_config = {
            "name": "TestClient",
            "version": "1.0",
            "peerIdGenerator": {"refreshOn": "NEVER", "algorithm": {"type": "REGEX", "pattern": "-TC1000-[A-Za-z0-9]{12}"}},
            "keyGenerator": {"refreshOn": "NEVER", "algorithm": {"type": "HASH", "length": 8}},
            "query": ""
        }
        
        client_file = tmp_path / "test.client"
        client_file.write_text(json.dumps(client_config))
        
        with patch('app.core.bittorrent_client.settings') as mock_settings:
            mock_settings.CLIENTS_DIR = tmp_path
            client = BitTorrentClient("test.client")
        
        port = client.get_session_port()
        assert 49152 <= port <= 65535
    
    def test_session_port_is_consistent(self, tmp_path):
        """Test session port remains consistent for a client instance"""
        client_config = {
            "name": "TestClient",
            "version": "1.0",
            "peerIdGenerator": {"refreshOn": "NEVER", "algorithm": {"type": "REGEX", "pattern": "-TC1000-[A-Za-z0-9]{12}"}},
            "keyGenerator": {"refreshOn": "NEVER", "algorithm": {"type": "HASH", "length": 8}},
            "query": ""
        }
        
        client_file = tmp_path / "test.client"
        client_file.write_text(json.dumps(client_config))
        
        with patch('app.core.bittorrent_client.settings') as mock_settings:
            mock_settings.CLIENTS_DIR = tmp_path
            client = BitTorrentClient("test.client")
        
        port1 = client.get_session_port()
        port2 = client.get_session_port()
        assert port1 == port2
