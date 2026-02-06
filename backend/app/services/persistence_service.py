"""
Persistence Service
Saves and restores per-torrent stats (uploaded, seeding_time, added_at) across restarts.
Data is stored in CONFIG_DIR/torrent_stats.json keyed by info_hash.
"""
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger(__name__)

# Auto-save interval in seconds
AUTOSAVE_INTERVAL = 60


class PersistenceService:
    """Persist torrent stats to disk so they survive container restarts."""

    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}
        self._dirty: bool = False
        self._save_task: Optional[asyncio.Task] = None
        self._file_path: Path = settings.CONFIG_DIR / "torrent_stats.json"

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    def load(self):
        """Load persisted data from disk (synchronous, call at init)."""
        if not self._file_path.exists():
            logger.info("📂 No persisted torrent stats found, starting fresh")
            self._data = {}
            return

        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
            logger.info(f"📂 Loaded persisted stats for {len(self._data)} torrent(s)")
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"❌ Failed to load torrent stats: {e}")
            self._data = {}

    def save(self):
        """Write current data to disk (synchronous)."""
        try:
            tmp_path = self._file_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, default=str)
            tmp_path.replace(self._file_path)
            self._dirty = False
            logger.debug(f"💾 Persisted stats for {len(self._data)} torrent(s)")
        except OSError as e:
            logger.error(f"❌ Failed to save torrent stats: {e}")

    # ------------------------------------------------------------------
    # Per-torrent accessors
    # ------------------------------------------------------------------

    def get(self, info_hash: str) -> Optional[Dict[str, Any]]:
        """Get persisted data for a torrent, or None if not found."""
        return self._data.get(info_hash)

    def update(self, info_hash: str, *, uploaded: int, seeding_time: float,
               added_at: str, torrent_name: str = ""):
        """Update or create persisted data for a torrent."""
        self._data[info_hash] = {
            "uploaded": uploaded,
            "seeding_time": seeding_time,
            "added_at": added_at,
            "torrent_name": torrent_name,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._dirty = True

    def remove(self, info_hash: str):
        """Remove persisted data for a torrent (clean slate if re-added)."""
        if info_hash in self._data:
            name = self._data[info_hash].get("torrent_name", info_hash[:8])
            del self._data[info_hash]
            self._dirty = True
            logger.info(f"🗑️ Cleared persisted stats for: {name}")
            self.save()

    # ------------------------------------------------------------------
    # Auto-save loop
    # ------------------------------------------------------------------

    async def start_autosave(self):
        """Start periodic auto-save background task."""
        # Cancel any stale task from a previous event loop
        if self._save_task is not None:
            self._save_task.cancel()
            self._save_task = None
        try:
            self._save_task = asyncio.create_task(self._autosave_loop())
            logger.info(f"💾 Persistence auto-save started (every {AUTOSAVE_INTERVAL}s)")
        except RuntimeError:
            logger.debug("Cannot start autosave: no running event loop")

    async def stop_autosave(self):
        """Stop auto-save and do a final flush."""
        if self._save_task:
            try:
                self._save_task.cancel()
                await self._save_task
            except (asyncio.CancelledError, RuntimeError):
                pass
            self._save_task = None
        if self._dirty:
            self.save()

    async def _autosave_loop(self):
        try:
            while True:
                await asyncio.sleep(AUTOSAVE_INTERVAL)
                if self._dirty:
                    self.save()
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------
    # Bulk helpers
    # ------------------------------------------------------------------

    def cleanup_missing(self, active_hashes: set):
        """Remove entries for torrents that no longer exist (optional)."""
        removed = [h for h in list(self._data) if h not in active_hashes]
        for h in removed:
            name = self._data[h].get("torrent_name", h[:8])
            del self._data[h]
            logger.debug(f"🧹 Cleaned stale stats for: {name}")
        if removed:
            self._dirty = True


# Singleton
persistence_service = PersistenceService()
