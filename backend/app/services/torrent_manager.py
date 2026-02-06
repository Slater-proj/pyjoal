"""
Torrent Manager
Handles loading, adding, removing, and archiving torrents
"""
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.core.config import settings
from app.core.bittorrent_client import BitTorrentClient
from app.core.torrent_parser import Torrent, load_torrents_from_directory
from app.core.torrent_validator import validate_torrent_file
from app.core.tracker_announcer import TrackerAnnouncer
from app.services.websocket_manager import websocket_manager
from app.services.history_service import history_service, EventType

logger = logging.getLogger(__name__)


class TorrentManager:
    """Manages torrent lifecycle: load, add, remove, archive"""

    def __init__(self):
        self.announcers: Dict[str, TrackerAnnouncer] = {}
        self.failed_torrents: Dict[str, Dict] = {}

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def has_torrents(self) -> bool:
        return len(self.announcers) > 0 or len(load_torrents_from_directory(settings.TORRENTS_DIR)) > 0

    def get_torrents(self) -> List[Dict]:
        """Get working torrents info"""
        return [self._get_torrent_info(ih) for ih in self.announcers]

    def get_torrent_info(self, info_hash: str) -> Dict:
        return self._get_torrent_info(info_hash)

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    async def load_torrents(
        self,
        client: BitTorrentClient,
        config: Dict,
        is_running: bool,
        start_callback=None,
    ):
        """Load torrents from directory with validation"""
        logger.debug(f"📂 Loading torrents from: {settings.TORRENTS_DIR}")

        torrents: List[Torrent] = []
        torrent_files = list(settings.TORRENTS_DIR.glob("*.torrent"))

        for torrent_file in torrent_files:
            is_valid, validation_msg = validate_torrent_file(torrent_file)

            if not is_valid:
                logger.error(f"❌ Invalid torrent file {torrent_file.name}: {validation_msg}")
                history_service.add_entry(
                    EventType.TORRENT_LOAD_FAILED,
                    f"❌ Invalid torrent archived: {torrent_file.name}",
                    {
                        "filename": torrent_file.name,
                        "error": validation_msg,
                        "reason_detail": f"File is not a valid .torrent: {validation_msg}",
                        "action": "auto_archived",
                    },
                )

                try:
                    archived_dir = settings.TORRENTS_DIR / "archived"
                    archived_dir.mkdir(exist_ok=True)
                    archived_path = archived_dir / torrent_file.name
                    torrent_file.rename(archived_path)
                    logger.info(f"📦 Invalid torrent auto-archived: {torrent_file.name} -> archived/")
                except Exception as archive_error:
                    logger.error(f"❌ Failed to archive invalid torrent {torrent_file.name}: {archive_error}")
                    self.failed_torrents[torrent_file.name] = {
                        "filename": torrent_file.name,
                        "error": f"Validation failed: {validation_msg} (archive failed: {archive_error})",
                        "timestamp": datetime.now(timezone.utc),
                        "size": torrent_file.stat().st_size if torrent_file.exists() else 0,
                    }
                continue

            try:
                torrent = Torrent(torrent_file)
                torrents.append(torrent)

                if torrent_file.name in self.failed_torrents:
                    del self.failed_torrents[torrent_file.name]
                    logger.info(f"✅ Previously failed torrent now works: {torrent_file.name}")
            except Exception as e:
                error_msg = f"Loading failed: {str(e)}"
                self.failed_torrents[torrent_file.name] = {
                    "filename": torrent_file.name,
                    "error": error_msg,
                    "timestamp": datetime.now(timezone.utc),
                    "size": torrent_file.stat().st_size if torrent_file.exists() else 0,
                }
                logger.error(f"❌ Failed to load {torrent_file.name}: {error_msg}")

                history_service.add_entry(
                    EventType.TORRENT_LOAD_FAILED,
                    f"Failed to load torrent: {torrent_file.name}",
                    {
                        "filename": torrent_file.name,
                        "error": error_msg,
                        "size": torrent_file.stat().st_size if torrent_file.exists() else 0,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

                try:
                    await websocket_manager.broadcast(
                        {
                            "type": "torrent_load_error",
                            "data": {
                                "filename": torrent_file.name,
                                "error": error_msg,
                                "message": f"Failed to load {torrent_file.name}: {error_msg}",
                            },
                        }
                    )
                except Exception as ws_error:
                    logger.debug(f"WebSocket broadcast failed: {ws_error}")

        new_count = 0
        for torrent in torrents:
            if torrent.info_hash not in self.announcers:
                await self.add_torrent(torrent, client, config, is_running, start_callback)
                new_count += 1

        total_files = len(torrent_files)
        failed_count = len(self.failed_torrents)

        if failed_count > 0:
            logger.warning(f"📂 Loaded {len(torrents)}/{total_files} torrent(s) ({new_count} new, {failed_count} failed)")
            for filename, error_info in self.failed_torrents.items():
                logger.debug(f"   ❌ {filename}: {error_info['error']}")
        else:
            logger.info(f"📂 Loaded {len(torrents)}/{total_files} torrent(s) ({new_count} new, {failed_count} failed)")

        logger.debug("✅ load_torrents() completed successfully")

    # ------------------------------------------------------------------
    # Add / Remove / Archive
    # ------------------------------------------------------------------

    async def add_torrent(
        self,
        torrent: Torrent,
        client: BitTorrentClient,
        config: Dict,
        is_running: bool,
        start_callback=None,
    ):
        """Add a torrent to seed"""
        if torrent.info_hash in self.announcers:
            logger.debug(f"Torrent already added: {torrent.name}")
            return

        if not client:
            logger.error("Cannot add torrent: client not initialized")
            raise ValueError("Client not initialized")

        logger.info(f"➕ Adding torrent: {torrent.name}")
        logger.debug(f"   Info hash: {torrent.info_hash}")
        logger.debug(f"   Size: {torrent.size / (1024**3):.2f} GB")
        logger.debug(f"   Tracker: {torrent.primary_tracker}")

        announcer = TrackerAnnouncer(
            torrent,
            client,
            discretion_config={
                "announce_interval": config.get("announceInterval", settings.ANNOUNCE_INTERVAL),
                "announce_jitter": config.get("announceJitter", settings.ANNOUNCE_JITTER),
                "min_stats_update_interval": config.get("minStatsUpdateInterval", settings.MIN_STATS_UPDATE_INTERVAL),
                "enable_speed_variation": config.get("enableSpeedVariation", settings.ENABLE_SPEED_VARIATION),
                "speed_variation_percent": config.get("speedVariationPercent", settings.SPEED_VARIATION_PERCENT),
            },
        )
        self.announcers[torrent.info_hash] = announcer

        if is_running and start_callback:
            await start_callback(announcer)

        history_service.add_entry(
            EventType.TORRENT_ADDED,
            f"Added torrent: {torrent.name}",
            {"info_hash": torrent.info_hash, "size": torrent.size},
        )

        await websocket_manager.broadcast({"type": "torrent_added", "data": self._get_torrent_info(torrent.info_hash)})
        await websocket_manager.broadcast({"type": "torrents_update", "data": {"torrents": self.get_torrents()}})
        logger.info(f"✅ Torrent added successfully: {torrent.name[:50]}")

    async def remove_torrent(self, info_hash: str):
        """Remove a torrent"""
        if info_hash not in self.announcers:
            logger.warning(f"Cannot remove torrent: {info_hash} not found")
            return

        announcer = self.announcers[info_hash]
        logger.info(f"➖ Removing torrent: {announcer.torrent.name}")

        if announcer.is_running:
            logger.debug("   Stopping announcer...")
            await announcer.stop()

        del self.announcers[info_hash]

        history_service.add_entry(
            EventType.TORRENT_REMOVED,
            f"Removed torrent: {announcer.torrent.name}",
            {"info_hash": info_hash},
        )

        archived_dir = settings.TORRENTS_DIR / "archived"
        archived_dir.mkdir(exist_ok=True)
        torrent_path = announcer.torrent.path
        if torrent_path and torrent_path.exists():
            archived_path = archived_dir / torrent_path.name
            torrent_path.rename(archived_path)
            logger.debug(f"   Torrent file archived to: {archived_path}")

        await websocket_manager.broadcast({"type": "torrent_removed", "data": {"info_hash": info_hash}})
        await websocket_manager.broadcast({"type": "torrents_update", "data": {"torrents": self.get_torrents()}})
        logger.info(f"✅ Torrent removed: {info_hash[:8]}...")

    async def archive_torrent(self, info_hash: str, skip_history: bool = False):
        """Archive a torrent (move to archived folder instead of deleting)"""
        if info_hash not in self.announcers:
            return

        announcer = self.announcers[info_hash]
        torrent = announcer.torrent
        stats = announcer.get_stats()

        logger.info(f"📦 Archiving torrent: {torrent.name}")

        if not skip_history:
            history_service.add_entry(
                EventType.TORRENT_ARCHIVED,
                f"📦 Torrent archived: {torrent.name}",
                {
                    "info_hash": info_hash,
                    "torrent_name": torrent.name,
                    "final_ratio": stats.get("ratio", 0),
                    "final_seeding_time": stats.get("seedingTime", 0),
                    "reason": "manual_archive",
                    "archived_at": time.time(),
                },
            )

        if announcer.is_running:
            await announcer.stop()

        del self.announcers[info_hash]

        archived_dir = settings.TORRENTS_DIR / "archived"
        archived_dir.mkdir(exist_ok=True)

        if torrent.path.exists():
            archived_path = archived_dir / torrent.path.name
            torrent.path.rename(archived_path)
            logger.info(f"✅ Torrent archived: {torrent.name}")
        else:
            logger.warning(f"   Torrent file not found: {torrent.path}")

        await websocket_manager.broadcast({"type": "torrent_archived", "data": {"info_hash": info_hash, "name": torrent.name}})

    # ------------------------------------------------------------------
    # Ratio / Duration checks
    # ------------------------------------------------------------------

    async def check_ratio_targets(self, config: Dict):
        """Check if any torrents reached ratio target or duration limit"""
        ratio_target = config.get("uploadRatioTarget", -1.0)
        duration_limit = config.get("seedingDurationLimit", -1.0)
        keep_zero_leechers = config.get("keepTorrentWithZeroLeechers", True)

        to_remove: List[str] = []

        if ratio_target > 0 or duration_limit > 0:
            logger.debug(f"🎯 Checking targets: ratio={ratio_target}, duration={duration_limit}h, keep_zero_leechers={keep_zero_leechers}")

        for info_hash, announcer in self.announcers.items():
            stats = announcer.get_stats()
            torrent = announcer.torrent

            if ratio_target > 0 and stats["ratio"] >= ratio_target:
                history_service.add_entry(
                    EventType.TORRENT_ARCHIVED,
                    f"📦 Archived {torrent.name} - ratio target reached ({stats['ratio']:.2f} >= {ratio_target})",
                    {
                        "info_hash": info_hash,
                        "ratio": stats["ratio"],
                        "target": ratio_target,
                        "reason": "ratio_target",
                        "torrent_name": torrent.name,
                        "reason_detail": f"Ratio {stats['ratio']:.2f} exceeded target of {ratio_target}",
                    },
                )
                to_remove.append(info_hash)
                continue

            if duration_limit > 0:
                seeding_time_hours = stats["seedingTime"] / 3600
                if seeding_time_hours >= duration_limit:
                    history_service.add_entry(
                        EventType.TORRENT_ARCHIVED,
                        f"📦 Archived {torrent.name} - duration limit reached ({seeding_time_hours:.1f}h >= {duration_limit}h)",
                        {
                            "info_hash": info_hash,
                            "seeding_hours": seeding_time_hours,
                            "limit": duration_limit,
                            "reason": "duration_limit",
                            "torrent_name": torrent.name,
                            "reason_detail": f"Seeded for {seeding_time_hours:.1f} hours, limit is {duration_limit} hours",
                        },
                    )
                    to_remove.append(info_hash)
                    continue

            if not keep_zero_leechers and stats["seeders"] == 0 and stats["leechers"] == 0:
                seeding_time_seconds = stats.get("seedingTime", 0)
                grace_period_seconds = 300

                if seeding_time_seconds < grace_period_seconds:
                    logger.debug(
                        f"⏳ Torrent {torrent.name[:30]} has 0 peers but still in grace period "
                        f"({seeding_time_seconds}s < {grace_period_seconds}s)"
                    )
                    continue

                logger.info(
                    f"🚫 Torrent {torrent.name} has no peers after {seeding_time_seconds}s "
                    "and keepTorrentWithZeroLeechers=False, archiving..."
                )
                history_service.add_entry(
                    EventType.TORRENT_ARCHIVED,
                    f"📦 Archived {torrent.name} - no peers available",
                    {
                        "info_hash": info_hash,
                        "seeders": 0,
                        "leechers": 0,
                        "seeding_time": seeding_time_seconds,
                        "reason": "no_peers",
                        "torrent_name": torrent.name,
                        "reason_detail": (
                            f"No seeders or leechers after {seeding_time_seconds // 60} minutes, "
                            "keepTorrentWithZeroLeechers is disabled"
                        ),
                    },
                )
                to_remove.append(info_hash)
                continue

        for info_hash in to_remove:
            announcer = self.announcers[info_hash]
            stats = announcer.get_stats()
            torrent = announcer.torrent

            await websocket_manager.broadcast(
                {
                    "type": "toast",
                    "data": {
                        "message": f"🗃️ Archiving: {torrent.name[:40]}... (ratio: {stats.get('ratio', 0):.2f})",
                        "type": "info",
                    },
                }
            )

            logger.warning(
                f"🗃️ AUTO-ARCHIVING: {torrent.name} - ratio: {stats.get('ratio', 0):.2f}, "
                f"duration: {stats.get('seedingTime', 0) / 3600:.1f}h"
            )
            await self.archive_torrent(info_hash, skip_history=True)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_torrent_info(self, info_hash: str) -> Dict:
        """Get single torrent info"""
        announcer = self.announcers.get(info_hash)
        if not announcer:
            return {}

        stats = announcer.get_stats()
        torrent = announcer.torrent

        if not announcer.is_running:
            status = "STOPPED"
        elif stats.get("lastError"):
            status = "ERROR"
        elif stats.get("seeders", 0) > 0 or stats.get("leechers", 0) > 0:
            status = "ACTIVE"
        else:
            status = "IDLE"

        detailed_status = stats.get("status", {})

        return {
            "id": info_hash,
            "name": torrent.name,
            "size": torrent.size,
            "uploaded": int(stats["uploaded"]),
            "uploadSpeed": int(stats["uploadSpeed"]),
            "ratio": stats["ratio"],
            "seeders": stats["seeders"],
            "leechers": stats["leechers"],
            "state": "seeding" if announcer.is_running else "stopped",
            "addedAt": torrent.added_at.isoformat(),
            "lastAnnounce": stats["lastAnnounce"].isoformat() if stats["lastAnnounce"] else None,
            "nextAnnounce": stats["nextAnnounce"].isoformat() if stats["nextAnnounce"] else None,
            "tracker": torrent.primary_tracker,
            "seedingTime": int(stats["seedingTime"]),
            "lastError": stats.get("lastError"),
            "errorCount": stats.get("errorCount", 0),
            "lastErrorTime": stats["lastErrorTime"].isoformat() if stats.get("lastErrorTime") else None,
            "isHealthy": stats.get("isHealthy", True),
            "status": detailed_status,
            "simpleStatus": status,
            "isRunning": announcer.is_running,
        }
