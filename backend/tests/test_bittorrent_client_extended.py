"""
Extended tests for BitTorrentClient - url_encode, headers, rates, announce URL, session port, list clients
"""
import pytest
import json
import os
from unittest.mock import patch
from pathlib import Path

os.environ.setdefault("SECRET_TOKEN", "test-secret-token")

from app.core.bittorrent_client import BitTorrentClient, list_available_clients


def _minimal_config(**overrides):
    config = {
        "name": "TestClient",
        "version": "1.0",
        "peerIdGenerator": {
            "refreshOn": "NEVER",
            "algorithm": {"type": "REGEX", "pattern": "-TC1000-[A-Za-z0-9]{12}"},
        },
        "keyGenerator": {
            "refreshOn": "NEVER",
            "algorithm": {"type": "HASH", "length": 8},
        },
        "query": "info_hash={infohash}&peer_id={peerid}&port={port}&uploaded={uploaded}&downloaded={downloaded}&left={left}&numwant={numwant}&key={key}&event={event}",
        "numwant": 200,
        "numwantOnStop": 0,
        "requestHeaders": [
            {"name": "User-Agent", "value": "TestClient/1.0"},
            {"name": "Accept-Encoding", "value": "gzip"},
            {"name": "Connection", "value": "close"},
        ],
    }
    config.update(overrides)
    return config


def _make_client(tmp_path, **overrides):
    cfg = _minimal_config(**overrides)
    client_file = tmp_path / "test.client"
    client_file.write_text(json.dumps(cfg))
    with patch("app.core.bittorrent_client.settings") as ms:
        ms.CLIENTS_DIR = tmp_path
        return BitTorrentClient("test.client")


class TestUrlEncode:
    def test_url_encode_basic(self, tmp_path):
        client = _make_client(tmp_path)
        result = client.url_encode(b"\x00\x01\x02")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_url_encode_ascii(self, tmp_path):
        client = _make_client(tmp_path)
        result = client.url_encode(b"abc")
        assert isinstance(result, str)

    def test_url_encode_empty(self, tmp_path):
        client = _make_client(tmp_path)
        result = client.url_encode(b"")
        assert result == ""


class TestGetHeaders:
    def test_get_user_agent(self, tmp_path):
        client = _make_client(tmp_path)
        ua = client.get_user_agent()
        assert ua == "TestClient/1.0"

    def test_get_request_headers(self, tmp_path):
        client = _make_client(tmp_path)
        headers = client.get_request_headers()
        assert isinstance(headers, dict)
        assert "User-Agent" in headers

    def test_get_request_headers_values(self, tmp_path):
        client = _make_client(tmp_path)
        headers = client.get_request_headers()
        assert headers["Accept-Encoding"] == "gzip"
        assert headers["Connection"] == "close"


class TestUploadRateRange:
    def test_default_rate_range(self, tmp_path):
        client = _make_client(tmp_path)
        min_rate, max_rate = client.get_upload_rate_range()
        assert min_rate >= 0
        assert max_rate >= min_rate

    def test_rate_range_with_dynamic_config(self, tmp_path):
        client = _make_client(tmp_path)
        config = {"minUploadRate": 100, "maxUploadRate": 1000}
        min_rate, max_rate = client.get_upload_rate_range(config)
        assert min_rate == 100 * 1024
        assert max_rate == 1000 * 1024


class TestPeerId:
    def test_peer_id_length(self, tmp_path):
        client = _make_client(tmp_path)
        peer_id = client.generate_peer_id("abc123")
        assert len(peer_id) == 20

    def test_peer_id_is_string(self, tmp_path):
        client = _make_client(tmp_path)
        peer_id = client.generate_peer_id("abc123")
        assert isinstance(peer_id, str)


class TestKeyGeneration:
    def test_key_generation(self, tmp_path):
        client = _make_client(tmp_path)
        key = client.generate_key("abc123")
        assert isinstance(key, str)
        assert len(key) > 0


class TestBuildAnnounceUrl:
    def test_basic_announce_url(self, tmp_path):
        client = _make_client(tmp_path)
        url = client.build_announce_url(
            tracker_url="http://tracker.example.com/announce",
            info_hash=b"\xab\xc1\x23" + b"\x00" * 17,
            peer_id="-TC1000-" + "A" * 12,
            port=6881,
            uploaded=1024,
            downloaded=0,
            left=0,
        )
        assert "http://tracker.example.com/announce" in url
        assert "uploaded=1024" in url
        assert "port=6881" in url

    def test_announce_url_with_event(self, tmp_path):
        client = _make_client(tmp_path)
        url = client.build_announce_url(
            tracker_url="http://tracker.example.com/announce",
            info_hash=b"\xab\xc1\x23" + b"\x00" * 17,
            peer_id="-TC1000-" + "A" * 12,
            port=6881,
            uploaded=0,
            downloaded=0,
            left=0,
            event="started",
        )
        assert "event=started" in url

    def test_announce_url_no_event(self, tmp_path):
        client = _make_client(tmp_path)
        url = client.build_announce_url(
            tracker_url="http://tracker.example.com/announce",
            info_hash=b"\xab\xc1\x23" + b"\x00" * 17,
            peer_id="-TC1000-" + "A" * 12,
            port=6881,
            uploaded=0,
            downloaded=0,
            left=0,
            event=None,
        )
        assert "{event}" not in url


class TestSessionPort:
    def test_session_port(self, tmp_path):
        client = _make_client(tmp_path)
        port = client.get_session_port()
        assert isinstance(port, int)
        assert 1024 <= port <= 65535

    def test_session_port_consistent(self, tmp_path):
        client = _make_client(tmp_path)
        p1 = client.get_session_port()
        p2 = client.get_session_port()
        assert p1 == p2


class TestListClients:
    def test_list_available_clients(self, tmp_path):
        import json
        cfg = _minimal_config(name="C1", version="1.0")
        (tmp_path / "test1.client").write_text(json.dumps(cfg))
        cfg2 = _minimal_config(name="C2", version="2.0")
        (tmp_path / "test2.client").write_text(json.dumps(cfg2))
        with patch("app.core.bittorrent_client.settings") as ms:
            ms.CLIENTS_DIR = tmp_path
            clients = list_available_clients()
        assert isinstance(clients, list)
        assert len(clients) == 2

    def test_client_names_extension(self, tmp_path):
        import json
        cfg = _minimal_config()
        (tmp_path / "foo.client").write_text(json.dumps(cfg))
        with patch("app.core.bittorrent_client.settings") as ms:
            ms.CLIENTS_DIR = tmp_path
            clients = list_available_clients()
        for c in clients:
            assert c.endswith(".client")


class TestClientProperties:
    def test_name(self, tmp_path):
        client = _make_client(tmp_path, name="qBittorrent")
        assert client.name == "qBittorrent"

    def test_version(self, tmp_path):
        client = _make_client(tmp_path, version="5.1.4")
        assert client.version == "5.1.4"

    def test_numwant(self, tmp_path):
        client = _make_client(tmp_path, numwant=150)
        assert client.config["numwant"] == 150

    def test_numwant_on_stop(self, tmp_path):
        client = _make_client(tmp_path, numwantOnStop=0)
        assert client.config["numwantOnStop"] == 0
