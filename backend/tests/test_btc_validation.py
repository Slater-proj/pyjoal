"""Tests for BitTorrentClient validation, _parse_char_class, and peer_id algorithms."""
import pytest
import json
import os
from unittest.mock import patch

os.environ.setdefault("SECRET_TOKEN", "test-secret-token")

from app.core.bittorrent_client import BitTorrentClient


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
        "query": "info_hash={infohash}&peer_id={peerid}&port={port}&uploaded={uploaded}&downloaded={downloaded}&left={left}",
        "numwant": 200,
        "numwantOnStop": 0,
        "requestHeaders": [
            {"name": "User-Agent", "value": "TestClient/1.0"},
            {"name": "Accept-Encoding", "value": "gzip"},
        ],
    }
    config.update(overrides)
    return config


def _make_client(tmp_path, **overrides):
    cfg = _minimal_config(**overrides)
    f = tmp_path / "test.client"
    f.write_text(json.dumps(cfg))
    with patch("app.core.bittorrent_client.settings") as ms:
        ms.CLIENTS_DIR = tmp_path
        return BitTorrentClient("test.client")


# ── _validate_joal_format ──────────────────────────────────────────────

class TestValidateJoalFormat:
    def test_valid_config(self, tmp_path):
        client = _make_client(tmp_path)
        errors = client._validate_joal_format()
        assert errors == []

    def test_missing_name(self, tmp_path):
        cfg = _minimal_config()
        del cfg["name"]
        f = tmp_path / "test.client"
        f.write_text(json.dumps(cfg))
        with patch("app.core.bittorrent_client.settings") as ms:
            ms.CLIENTS_DIR = tmp_path
            with pytest.raises(ValueError, match="missing required field"):
                BitTorrentClient("test.client")

    def test_missing_keyGenerator(self, tmp_path):
        cfg = _minimal_config()
        del cfg["keyGenerator"]
        f = tmp_path / "test.client"
        f.write_text(json.dumps(cfg))
        with patch("app.core.bittorrent_client.settings") as ms:
            ms.CLIENTS_DIR = tmp_path
            with pytest.raises(ValueError):
                BitTorrentClient("test.client")

    def test_keyGenerator_not_dict(self, tmp_path):
        cfg = _minimal_config(keyGenerator="not_a_dict")
        f = tmp_path / "test.client"
        f.write_text(json.dumps(cfg))
        with patch("app.core.bittorrent_client.settings") as ms:
            ms.CLIENTS_DIR = tmp_path
            with pytest.raises(ValueError, match="must be an object"):
                BitTorrentClient("test.client")

    def test_keyGenerator_no_algorithm(self, tmp_path):
        cfg = _minimal_config(keyGenerator={"refreshOn": "NEVER"})
        f = tmp_path / "test.client"
        f.write_text(json.dumps(cfg))
        with patch("app.core.bittorrent_client.settings") as ms:
            ms.CLIENTS_DIR = tmp_path
            with pytest.raises(ValueError, match="algorithm is required"):
                BitTorrentClient("test.client")

    def test_peerIdGenerator_not_dict(self, tmp_path):
        cfg = _minimal_config(peerIdGenerator="nope")
        f = tmp_path / "test.client"
        f.write_text(json.dumps(cfg))
        with patch("app.core.bittorrent_client.settings") as ms:
            ms.CLIENTS_DIR = tmp_path
            with pytest.raises(ValueError, match="must be an object"):
                BitTorrentClient("test.client")

    def test_requestHeaders_not_list(self, tmp_path):
        cfg = _minimal_config(requestHeaders="not_a_list")
        f = tmp_path / "test.client"
        f.write_text(json.dumps(cfg))
        with patch("app.core.bittorrent_client.settings") as ms:
            ms.CLIENTS_DIR = tmp_path
            with pytest.raises(ValueError, match="must be an array"):
                BitTorrentClient("test.client")

    def test_requestHeaders_item_missing_name(self, tmp_path):
        cfg = _minimal_config(requestHeaders=[{"value": "bar"}])
        f = tmp_path / "test.client"
        f.write_text(json.dumps(cfg))
        with patch("app.core.bittorrent_client.settings") as ms:
            ms.CLIENTS_DIR = tmp_path
            with pytest.raises(ValueError, match="must have"):
                BitTorrentClient("test.client")

    def test_query_empty_string(self, tmp_path):
        cfg = _minimal_config(query="")
        f = tmp_path / "test.client"
        f.write_text(json.dumps(cfg))
        with patch("app.core.bittorrent_client.settings") as ms:
            ms.CLIENTS_DIR = tmp_path
            with pytest.raises(ValueError, match="non-empty string"):
                BitTorrentClient("test.client")

    def test_query_missing_placeholder(self, tmp_path):
        cfg = _minimal_config(query="uploaded={uploaded}&downloaded={downloaded}&left={left}")
        f = tmp_path / "test.client"
        f.write_text(json.dumps(cfg))
        with patch("app.core.bittorrent_client.settings") as ms:
            ms.CLIENTS_DIR = tmp_path
            with pytest.raises(ValueError, match="must contain"):
                BitTorrentClient("test.client")


# ── _parse_char_class ──────────────────────────────────────────────────

class TestParseCharClass:
    def test_simple_range(self, tmp_path):
        client = _make_client(tmp_path)
        result = client._parse_char_class("a-z")
        assert "a" in result
        assert "z" in result
        assert len(result) == 26

    def test_multiple_ranges(self, tmp_path):
        client = _make_client(tmp_path)
        result = client._parse_char_class("A-Za-z0-9")
        assert len(result) == 62  # 26+26+10

    def test_single_chars(self, tmp_path):
        client = _make_client(tmp_path)
        result = client._parse_char_class("abc")
        assert result == "abc"

    def test_escaped_char(self, tmp_path):
        client = _make_client(tmp_path)
        result = client._parse_char_class("\\-")
        assert "-" in result


# ── Peer ID algorithms ─────────────────────────────────────────────────

class TestPeerIdPoolChecksum:
    def test_transmission_style(self, tmp_path):
        cfg = _minimal_config(
            peerIdGenerator={
                "refreshOn": "NEVER",
                "algorithm": {
                    "type": "RANDOM_POOL_WITH_CHECKSUM",
                    "prefix": "-TR3000-",
                    "charactersPool": "0123456789abcdefghijklmnopqrstuvwxyz",
                    "base": 36,
                },
            }
        )
        f = tmp_path / "test.client"
        f.write_text(json.dumps(cfg))
        with patch("app.core.bittorrent_client.settings") as ms:
            ms.CLIENTS_DIR = tmp_path
            client = BitTorrentClient("test.client")
        pid = client.generate_peer_id("abc123")
        assert len(pid) == 20
        assert pid.startswith("-TR3000-")


class TestKeyAlgorithms:
    def test_hash_no_leading_zero(self, tmp_path):
        cfg = _minimal_config(
            keyGenerator={
                "refreshOn": "NEVER",
                "algorithm": {"type": "HASH_NO_LEADING_ZERO", "length": 8},
            }
        )
        f = tmp_path / "test.client"
        f.write_text(json.dumps(cfg))
        with patch("app.core.bittorrent_client.settings") as ms:
            ms.CLIENTS_DIR = tmp_path
            client = BitTorrentClient("test.client")
        key = client.generate_key("abc123")
        assert len(key) == 8
        assert not key.startswith("0")

    def test_digit_range_hex(self, tmp_path):
        cfg = _minimal_config(
            keyGenerator={
                "refreshOn": "NEVER",
                "algorithm": {
                    "type": "DIGIT_RANGE_TRANSFORMED_TO_HEX_WITHOUT_LEADING_ZEROES",
                    "inclusiveLowerBound": 1,
                    "inclusiveUpperBound": 2147483647,
                },
            }
        )
        f = tmp_path / "test.client"
        f.write_text(json.dumps(cfg))
        with patch("app.core.bittorrent_client.settings") as ms:
            ms.CLIENTS_DIR = tmp_path
            client = BitTorrentClient("test.client")
        key = client.generate_key("abc123")
        assert isinstance(key, str)
        assert len(key) > 0

    def test_hash_algorithm(self, tmp_path):
        client = _make_client(tmp_path)  # uses HASH by default
        key = client.generate_key("abc123")
        assert len(key) == 8


# ── Build announce URL edge cases ──────────────────────────────────────

class TestBuildAnnounceUrlEdge:
    def test_stopped_event_uses_numwant_on_stop(self, tmp_path):
        client = _make_client(
            tmp_path, numwantOnStop=0,
            query="info_hash={infohash}&peer_id={peerid}&port={port}&uploaded={uploaded}&downloaded={downloaded}&left={left}&numwant={numwant}&key={key}&event={event}",
        )
        url = client.build_announce_url(
            tracker_url="http://t.example.com/announce",
            info_hash=b"\xab\xcd" + b"\x00" * 18,
            peer_id="-TC1000-AAAAAAAAAAAA",
            port=6881, uploaded=0, downloaded=0, left=0,
            event="stopped",
        )
        assert "numwant=0" in url

    def test_url_encode_peer_id(self, tmp_path):
        cfg = _minimal_config(
            query="info_hash={infohash}&peer_id={peerid}&port={port}&uploaded={uploaded}&downloaded={downloaded}&left={left}&numwant={numwant}&key={key}&event={event}",
        )
        cfg["peerIdGenerator"]["shouldUrlEncode"] = True
        f = tmp_path / "test.client"
        f.write_text(json.dumps(cfg))
        with patch("app.core.bittorrent_client.settings") as ms:
            ms.CLIENTS_DIR = tmp_path
            client = BitTorrentClient("test.client")
        url = client.build_announce_url(
            tracker_url="http://t.example.com/announce",
            info_hash=b"\x01\x02" + b"\x00" * 18,
            peer_id="-TC1000-AAAAAAAAAAAA",
            port=6881, uploaded=0, downloaded=0, left=0,
        )
        assert isinstance(url, str)

    def test_tracker_url_with_query(self, tmp_path):
        client = _make_client(tmp_path)
        url = client.build_announce_url(
            tracker_url="http://t.example.com/announce?passkey=1234",
            info_hash=b"\xab\xcd" + b"\x00" * 18,
            peer_id="-TC1000-AAAAAAAAAAAA",
            port=6881, uploaded=0, downloaded=0, left=0,
        )
        # Should use & as separator since ? already exists
        assert "?passkey=1234&" in url
