"""
Tests for torrent_validator.py — Centralized validation for .torrent files
"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import os

from app.core.torrent_validator import validate_torrent_file, quick_validate_torrent_file


# ================================================================
# Helpers
# ================================================================

def _make_temp_file(content: bytes, suffix: str = ".torrent") -> Path:
    """Create a temporary file with given content and return its Path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.write(fd, content)
    os.close(fd)
    return Path(path)


# Minimal valid bencode that starts with 'd' but will fail Torrent parsing
MINIMAL_BENCODE = b"d4:infod4:name4:test6:lengthi1024e12:piece lengthi262144e6:pieces20:AAAAAAAAAAAAAAAAAAAAe8:announce26:http://tracker.example.com/ae"

# Invalid: HTML error page returned by some web servers
HTML_CONTENT = b"<html><body>404 Not Found</body></html>"

# Invalid: random binary
RANDOM_BINARY = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"


# ================================================================
# validate_torrent_file
# ================================================================

class TestValidateTorrentFile:
    """Tests for the comprehensive validate_torrent_file function."""

    def test_valid_torrent_from_test_data(self):
        """Validate the actual test.torrent file from test-data/."""
        test_torrent = Path(__file__).resolve().parent.parent.parent.parent / "test-data" / "test.torrent"
        if not test_torrent.exists():
            pytest.skip("test-data/test.torrent not available")
        is_valid, msg = validate_torrent_file(test_torrent)
        assert is_valid, f"Expected valid torrent, got: {msg}"
        assert msg == "Valid torrent"

    def test_file_does_not_exist(self, tmp_path):
        """Non-existent file ⇒ (False, 'File does not exist')."""
        missing = tmp_path / "nonexistent.torrent"
        is_valid, msg = validate_torrent_file(missing)
        assert not is_valid
        assert "does not exist" in msg.lower()

    def test_empty_file(self, tmp_path):
        """Empty file (0 bytes) should fail after retries."""
        empty = tmp_path / "empty.torrent"
        empty.write_bytes(b"")
        is_valid, msg = validate_torrent_file(empty, retry_count=1)
        assert not is_valid
        assert "empty" in msg.lower() or "0 bytes" in msg.lower()

    def test_oversized_file(self, tmp_path):
        """File larger than 10 MB should be rejected."""
        big = tmp_path / "huge.torrent"
        big.write_bytes(b"d" + b"\x00" * (11 * 1024 * 1024))
        is_valid, msg = validate_torrent_file(big)
        assert not is_valid
        assert "too large" in msg.lower()

    def test_invalid_header_html(self, tmp_path):
        """HTML content should fail header check."""
        html = tmp_path / "bad.torrent"
        html.write_bytes(HTML_CONTENT)
        is_valid, msg = validate_torrent_file(html)
        assert not is_valid
        assert "not a torrent" in msg.lower()

    def test_invalid_header_png(self, tmp_path):
        """PNG binary should fail header check."""
        png = tmp_path / "image.torrent"
        png.write_bytes(RANDOM_BINARY)
        is_valid, msg = validate_torrent_file(png)
        assert not is_valid
        assert "not a torrent" in msg.lower()

    def test_valid_header_but_bad_bencode(self, tmp_path):
        """Starts with 'd' but is not valid bencode."""
        bad = tmp_path / "garbled.torrent"
        bad.write_bytes(b"d8:garbage_no_end")
        is_valid, msg = validate_torrent_file(bad, retry_count=1)
        assert not is_valid
        assert "failed" in msg.lower() or "parsing" in msg.lower() or "error" in msg.lower()

    def test_in_memory_content_valid(self, tmp_path):
        """Validate using in-memory content with a real torrent."""
        test_torrent = Path(__file__).resolve().parent.parent.parent.parent / "test-data" / "test.torrent"
        if not test_torrent.exists():
            pytest.skip("test-data/test.torrent not available")
        content = test_torrent.read_bytes()
        is_valid, msg = validate_torrent_file(tmp_path / "inmem.torrent", content=content)
        assert is_valid, f"Expected valid, got: {msg}"

    def test_in_memory_content_empty(self, tmp_path):
        """Empty in-memory content should fail."""
        is_valid, msg = validate_torrent_file(tmp_path / "inmem.torrent", content=b"")
        assert not is_valid

    def test_in_memory_oversized(self, tmp_path):
        """In-memory content over 10 MB should fail."""
        content = b"d" + b"\x00" * (11 * 1024 * 1024)
        is_valid, msg = validate_torrent_file(tmp_path / "inmem.torrent", content=content)
        assert not is_valid
        assert "too large" in msg.lower()

    def test_retry_count_respected(self, tmp_path):
        """Retry count should be respected for transient errors."""
        empty = tmp_path / "retry.torrent"
        empty.write_bytes(b"")
        # With retry_count=1, should only try once
        is_valid, msg = validate_torrent_file(empty, retry_count=1)
        assert not is_valid

    def test_retry_count_default(self, tmp_path):
        """Default retry_count is 3."""
        missing = tmp_path / "missing.torrent"
        is_valid, msg = validate_torrent_file(missing)
        assert not is_valid


# ================================================================
# quick_validate_torrent_file
# ================================================================

class TestQuickValidateTorrentFile:
    """Tests for the quick_validate_torrent_file function."""

    def test_valid_torrent(self):
        """A real .torrent should pass quick validation."""
        test_torrent = Path(__file__).resolve().parent.parent.parent.parent / "test-data" / "test.torrent"
        if not test_torrent.exists():
            pytest.skip("test-data/test.torrent not available")
        assert quick_validate_torrent_file(test_torrent) is True

    def test_nonexistent_file(self, tmp_path):
        """Non-existent file ⇒ False."""
        assert quick_validate_torrent_file(tmp_path / "nope.torrent") is False

    def test_empty_file(self, tmp_path):
        """Empty file ⇒ False."""
        empty = tmp_path / "empty.torrent"
        empty.write_bytes(b"")
        assert quick_validate_torrent_file(empty) is False

    def test_html_file(self, tmp_path):
        """HTML content ⇒ False."""
        html = tmp_path / "html.torrent"
        html.write_bytes(HTML_CONTENT)
        assert quick_validate_torrent_file(html) is False

    def test_file_with_valid_header(self, tmp_path):
        """File starting with 'd' passes quick validation (header check only)."""
        f = tmp_path / "starts_d.torrent"
        f.write_bytes(b"d8:testdatae")
        assert quick_validate_torrent_file(f) is True

    def test_zone_identifier_skipped(self, tmp_path):
        """Windows Zone.Identifier alternate data stream files should be skipped."""
        # quick_validate checks if ':Zone.Identifier' is in the path string
        zone_file = tmp_path / "test.torrent:Zone.Identifier"
        # Can't actually create this file on most systems, so we test the string match
        assert quick_validate_torrent_file(Path(str(zone_file))) is False

    def test_exception_handling(self, tmp_path):
        """Permission or other OS errors should return False, not raise."""
        bad_path = tmp_path / "perm.torrent"
        bad_path.write_bytes(b"d4:teste")
        # Simulate an OS error during stat()
        with patch.object(Path, "exists", side_effect=PermissionError("denied")):
            assert quick_validate_torrent_file(bad_path) is False
