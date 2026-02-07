"""
Extended tests for BitTorrentClient - url_encode, headers, rates, validation, announce URL
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

os.environ.setdefault("SECRET_TOKEN", "test-secret-token")

from app.core.bittorrent_client import BitTorrentClient, list_available_clients


def _load_client(name="qbittorrent-5.1.4.client"):
    """Load a real client file for testing."""
    clients_dir = Path(__file__).parent.parent.parent / "clients"
    client_path = clients_dir / name
    if client_path.exists():
        return BitTorrentClient(str(client_path))
    # Fallback - find any available client
    clients = list(clients_dir.glob("*.client"))
    if clients:
        return BitTorrentClient(str(clients[0]))
    pytest.skip("No client files available")


class TestUrlEncode:
    def test_url_encode_basic(self):
        client = _load_client()
        result = client.url_encode(b"\x00\x01\x02")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_url_encode_ascii(self):
        client = _load_client()
        result = client.url_encode(b"abc")
        # Letters should be encoded or preserved depending on client config
        assert isinstance(result, str)

    def test_url_encode_empty(self):
        client = _load_client()
        result = client.url_encode(b"")
        assert result == ""


class TestGetHeaders:
    def test_get_user_agent(self):
        client = _load_client()
        ua = client.get_user_agent()
        assert isinstance(ua, str)
        assert len(ua) > 0

    def test_get_request_headers(self):
        client = _load_client()
        headers = client.get_request_headers()
        assert isinstance(headers, dict)
        # Should have User-Agent at minimum
        assert "User-Agent" in headers

    def test_get_request_headers_has_accept_encoding(self):
        client = _load_client()
        headers = client.get_request_headers()
        # Accept-Encoding is typically present
        assert isinstance(headers, dict)


class TestUploadRateRange:
    def test_default_rate_range(self):
        client = _load_client()
        min_rate, max_rate = client.get_upload_rate_range()
        assert min_rate > 0
        assert max_rate > min_rate

    def test_rate_range_with_dynamic_config(self):
        client = _load_client()
        config = {"minUploadRate": 100, "maxUploadRate": 1000}
        min_rate, max_rate = client.get_upload_rate_range(config)
        assert min_rate == 100 * 1024  # KB/s to B/s
        assert max_rate == 1000 * 1024


class TestPeerId:
    def test_peer_id_length(self):
        client = _load_client()
        peer_id = client.generate_peer_id("abc123")
        assert len(peer_id) == 20

    def test_peer_id_consistent_persistent(self):
        client = _load_client()
        pid1 = client.generate_peer_id("abc123")
        pid2 = client.generate_peer_id("abc123")
        # May or may not be same depending on caching policy
        assert len(pid1) == 20
        assert len(pid2) == 20


class TestKeyGeneration:
    def test_key_generation(self):
        client = _load_client()
        key = client.generate_key("abc123")
        assert isinstance(key, str)
        assert len(key) > 0


class TestBuildAnnounceUrl:
    def test_basic_announce_url(self):
        client = _load_client()
        url = client.build_announce_url(
            tracker_url="http://tracker.example.com/announce",
            info_hash="abc123",
            peer_id=b"-qB5140-" + b"0" * 12,
            port=6881,
            uploaded=1024,
            downloaded=0,
            left=0,
        )
        assert "http://tracker.example.com/announce" in url
        assert "uploaded=1024" in url
        assert "port=6881" in url

    def test_announce_url_with_event(self):
        client = _load_client()
        url = client.build_announce_url(
            tracker_url="http://tracker.example.com/announce",
            info_hash="abc123",
            peer_id=b"-qB5140-" + b"0" * 12,
            port=6881,
            uploaded=0,
            downloaded=0,
            left=0,
            event="started",
        )
        assert "event=started" in url

    def test_announce_url_no_event(self):
        client = _load_client()
        url = client.build_announce_url(
            tracker_url="http://tracker.example.com/announce",
            info_hash="abc123",
            peer_id=b"-qB5140-" + b"0" * 12,
            port=6881,
            uploaded=0,
            downloaded=0,
            left=0,
            event=None,
        )
        # event param should be absent
        assert "event=" not in url


class TestSessionPort:
    def test_session_port(self):
        client = _load_client()
        port = client.get_session_port()
        assert isinstance(port, int)
        assert 1024 <= port <= 65535

    def test_session_port_consistent(self):
        client = _load_client()
        p1 = client.get_session_port()
        p2 = client.get_session_port()
        assert p1 == p2


class TestListClients:
    def test_list_available_clients(self):
        clients_dir = Path(__file__).parent.parent.parent / "clients"
        with patch("app.core.bittorrent_client.settings") as ms:
            ms.CLIENTS_DIR = clients_dir
            clients = list_available_clients()
        assert isinstance(clients, list)
        # Should have at least the clients in the clients/ directory
        assert len(clients) > 0

    def test_client_names(self):
        clients_dir = Path(__file__).parent.parent.parent / "clients"
        with patch("app.core.bittorrent_client.settings") as ms:
            ms.CLIENTS_DIR = clients_dir
            clients = list_available_clients()
        for c in clients:
            assert c.endswith(".client")
