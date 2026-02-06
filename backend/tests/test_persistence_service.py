"""
Tests for PersistenceService - Stats persistence across restarts
"""
import json
import pytest
from pathlib import Path
from unittest.mock import patch
from app.services.persistence_service import PersistenceService


@pytest.fixture
def persistence(tmp_path):
    svc = PersistenceService()
    svc._file_path = tmp_path / "torrent_stats.json"
    return svc


class TestPersistenceLoad:
    def test_load_no_file(self, persistence):
        persistence.load()
        assert persistence._data == {}

    def test_load_valid_json(self, persistence):
        data = {"abc123": {"uploaded": 1000, "seeding_time": 3600}}
        persistence._file_path.write_text(json.dumps(data))
        persistence.load()
        assert persistence._data["abc123"]["uploaded"] == 1000

    def test_load_corrupt_json(self, persistence):
        persistence._file_path.write_text("{bad json")
        persistence.load()
        assert persistence._data == {}


class TestPersistenceSave:
    def test_save_creates_file(self, persistence):
        persistence._data = {"abc": {"uploaded": 500}}
        persistence._dirty = True
        persistence.save()
        assert persistence._file_path.exists()
        loaded = json.loads(persistence._file_path.read_text())
        assert loaded["abc"]["uploaded"] == 500

    def test_save_clears_dirty(self, persistence):
        persistence._data = {"abc": {"uploaded": 500}}
        persistence._dirty = True
        persistence.save()
        assert persistence._dirty is False


class TestPersistenceAccessors:
    def test_get_existing(self, persistence):
        persistence._data = {"abc": {"uploaded": 100}}
        assert persistence.get("abc")["uploaded"] == 100

    def test_get_missing(self, persistence):
        assert persistence.get("nonexist") is None

    def test_update(self, persistence):
        persistence.update("abc", uploaded=500, seeding_time=100.0,
                           added_at="2025-01-01", torrent_name="Test")
        assert persistence._data["abc"]["uploaded"] == 500
        assert persistence._dirty is True

    def test_remove(self, persistence):
        persistence._data = {"abc": {"uploaded": 100, "torrent_name": "Test"}}
        persistence._file_path.write_text("{}")  # ensure file exists for save
        persistence.remove("abc")
        assert "abc" not in persistence._data

    def test_remove_nonexistent(self, persistence):
        persistence.remove("nonexist")  # Should not raise


class TestPersistenceCleanup:
    def test_cleanup_missing(self, persistence):
        persistence._data = {
            "active": {"uploaded": 100},
            "stale": {"uploaded": 200},
        }
        persistence.cleanup_missing({"active"})
        assert "stale" not in persistence._data
        assert "active" in persistence._data
        assert persistence._dirty is True

    def test_cleanup_nothing_to_remove(self, persistence):
        persistence._data = {"active": {"uploaded": 100}}
        persistence.cleanup_missing({"active"})
        assert persistence._dirty is False  # Nothing changed


class TestPersistenceAutosave:
    @pytest.mark.asyncio
    async def test_start_stop_autosave(self, persistence):
        await persistence.start_autosave()
        assert persistence._save_task is not None
        await persistence.stop_autosave()
        assert persistence._save_task is None
