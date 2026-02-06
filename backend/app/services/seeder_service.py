"""
Seeder Service
Manages multiple torrent seeders and orchestrates announces with intelligent caching.

Delegates configuration management to ConfigManager and torrent lifecycle to TorrentManager.
"""
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

from app.core.config import settings
from app.core.bittorrent_client import BitTorrentClient
from app.core.torrent_parser import Torrent
from app.core.tracker_announcer import TrackerAnnouncer
from app.services.websocket_manager import websocket_manager
from app.services.history_service import history_service, EventType
from app.core.cache_manager import cache_manager
from app.services.resource_optimizer import resource_optimizer
from app.services.config_manager import ConfigManager
from app.services.torrent_manager import TorrentManager
from app.services.persistence_service import persistence_service
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)

# Import file watcher (lazy import to avoid circular dependencies)
try:
    from app.services.file_watcher import FileWatcherService
    FILE_WATCHER_AVAILABLE = True
except ImportError:
    FileWatcherService = None
    FILE_WATCHER_AVAILABLE = False
    logger.warning("File watcher not available - torrents won't auto-reload")


class SeederService:
    """Service to manage torrent seeding with thread safety.

    Composes:
    - ConfigManager  - config persistence & validation
    - TorrentManager - torrent load / add / remove / archive / ratio checks
    """

    def __init__(self):
        self.client: Optional[BitTorrentClient] = None
        self.is_running: bool = False
        self.started_at: Optional[datetime] = None
        self._lock = asyncio.Lock()
        self._monitor_task: Optional[asyncio.Task] = None

        # Delegates
        self._cfg = ConfigManager()
        self._tm = TorrentManager()

        # File watcher for auto-reload
        self.file_watcher = None

    # ------------------------------------------------------------------
    # Backward-compatible properties
    # ------------------------------------------------------------------

    @property
    def _config(self) -> Dict:
        return self._cfg.config

    @_config.setter
    def _config(self, value: Dict):
        self._cfg._config = value

    @property
    def announcers(self) -> Dict[str, TrackerAnnouncer]:
        return self._tm.announcers

    @announcers.setter
    def announcers(self, value):
        self._tm.announcers = value

    @property
    def failed_torrents(self) -> Dict[str, Dict]:
        return self._tm.failed_torrents

    @failed_torrents.setter
    def failed_torrents(self, value):
        self._tm.failed_torrents = value

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    async def initialize(self):
        """Initialize service"""
        from app.core.bittorrent_client import list_available_clients

        logger.info("Initializing Seeder Service...")

        persistence_service.load()
        notification_service.load()
        await self._cfg.load()
        logger.info(f"   Configuration loaded: {self._config}")

        available_clients = list_available_clients()
        logger.info(f"   Available clients: {', '.join(available_clients) if available_clients else 'NONE'}")

        if not available_clients:
            logger.critical("NO CLIENT FILES FOUND!")
            raise RuntimeError(
                "CRITICAL ERROR: No client files (.client) found in 'clients/' folder\n"
                "   Please add at least one .client file to start the application."
            )

        configured_client = self._config.get("client", settings.DEFAULT_CLIENT)
        logger.info(f"   Configured client: {configured_client}")

        if configured_client not in available_clients:
            fallback_client = self._find_best_fallback_client(configured_client, available_clients)
            logger.warning(f"Configured client '{configured_client}' not found")
            logger.info(f"Automatic fallback to: {fallback_client}")
            logger.info(f"   Other available clients: {', '.join(available_clients)}")
            configured_client = fallback_client
            self._cfg._config["client"] = configured_client
            await self._cfg.save()
            logger.info("Configuration updated automatically")

        try:
            self.client = BitTorrentClient(configured_client)
            logger.info(f"Client loaded: {self.client.name} {self.client.version}")
            logger.debug(f"   User-Agent: {self.client.get_user_agent()}")
            logger.debug(f"   Upload rate range: {settings.MIN_UPLOAD_RATE}-{settings.MAX_UPLOAD_RATE} KB/s")
        except Exception as e:
            logger.critical(f"Failed to load client '{configured_client}': {e}")
            raise RuntimeError(f"Impossible de charger le client '{configured_client}': {e}")

        # Torrent loading is deferred to background task for faster startup
        await self._init_file_watcher()
        await persistence_service.start_autosave()
        logger.info("Seeder Service initialized successfully (torrents loaded in background)")

    # ------------------------------------------------------------------
    # Config delegation
    # ------------------------------------------------------------------

    async def load_config(self):
        await self._cfg.load()

    async def save_config(self):
        await self._cfg.save()

    def get_config(self) -> Dict:
        return self._cfg.config.copy()

    async def update_config(self, new_config: Dict):
        """Update configuration with validation and live reload"""
        logger.info(f"Updating configuration: {new_config}")

        backup_config = self._config.copy()
        try:
            self._cfg.validate(new_config)
            self._cfg.update_dict(new_config)
            await self._cfg.save()
            logger.info("Configuration saved successfully")

            history_service.add_entry(EventType.CONFIG_UPDATED, "Configuration updated", new_config)
        except Exception as save_error:
            logger.error(f"Failed to save config: {save_error}")
            self._cfg._config = backup_config
            raise save_error

        try:
            if "minUploadRate" in new_config:
                settings.MIN_UPLOAD_RATE = new_config["minUploadRate"]
                logger.debug(f"   Min upload rate: {settings.MIN_UPLOAD_RATE} KB/s")
            if "maxUploadRate" in new_config:
                settings.MAX_UPLOAD_RATE = new_config["maxUploadRate"]
                logger.debug(f"   Max upload rate: {settings.MAX_UPLOAD_RATE} KB/s")
            if "seedingDurationLimit" in new_config:
                settings.SEEDING_DURATION_LIMIT = new_config["seedingDurationLimit"]
                logger.debug(f"   Seeding duration limit: {settings.SEEDING_DURATION_LIMIT}h")

            if "client" in new_config and new_config["client"] != self.client.client_file:
                try:
                    self.client = BitTorrentClient(new_config["client"])
                    logger.info(f"Switched to client: {self.client.name} {self.client.version}")
                except Exception as e:
                    logger.error(f"Failed to switch client: {e}")
        except Exception as settings_error:
            logger.error(f"Failed to update settings: {settings_error}")

    # ------------------------------------------------------------------
    # Torrent delegation
    # ------------------------------------------------------------------

    async def load_torrents(self):
        await self._tm.load_torrents(
            client=self.client,
            config=self._config,
            is_running=self.is_running,
            start_callback=self._start_announcer_if_needed,
        )

    def has_torrents(self) -> bool:
        return self._tm.has_torrents()

    async def add_torrent(self, torrent: Torrent):
        await self._tm.add_torrent(
            torrent,
            client=self.client,
            config=self._config,
            is_running=self.is_running,
            start_callback=self._start_announcer_if_needed,
        )

    async def remove_torrent(self, info_hash: str):
        persistence_service.remove(info_hash)
        await self._tm.remove_torrent(info_hash)

    def get_torrents(self) -> List[Dict]:
        return self._tm.get_torrents()

    # ------------------------------------------------------------------
    # Start / Stop
    # ------------------------------------------------------------------

    async def start(self):
        """Start seeding with race condition protection"""
        async with self._lock:
            if self.is_running:
                logger.warning("Seeding already running")
                return
            logger.info("Starting seeding service...")
            self.is_running = True
            self.started_at = datetime.now(timezone.utc)

        history_service.add_entry(
            EventType.SYSTEM_START,
            "Seeding started",
            {"torrents_count": len(self.announcers)},
        )

        simultaneous_seed = self._config.get("simultaneousSeed", settings.SIMULTANEOUS_SEED)
        announcers_to_start = list(self.announcers.values())[:simultaneous_seed]

        logger.info(f"   Starting {len(announcers_to_start)}/{len(self.announcers)} torrent(s)")
        logger.info(f"   Simultaneous seed limit: {simultaneous_seed}")
        logger.info(f"   Upload rate: {settings.MIN_UPLOAD_RATE}-{settings.MAX_UPLOAD_RATE} KB/s")

        for announcer in announcers_to_start:
            await announcer.start()

        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("   Monitor task started (updates every 3s)")

        if not hasattr(self, "_resource_optimizer_task"):
            self._resource_optimizer_task = asyncio.create_task(resource_optimizer.periodic_optimization())
            logger.info("   Resource optimizer started")

        await websocket_manager.broadcast({"type": "seeding_started", "data": {"started_at": self.started_at.isoformat()}})
        logger.info(f"Seeding started successfully ({len(announcers_to_start)} active)")

        # Send notification
        await notification_service.notify_system_start(len(announcers_to_start))

    async def stop(self):
        """Stop seeding"""
        if not self.is_running:
            logger.warning("Seeding already stopped")
            return

        logger.info("Stopping seeding service...")
        self.is_running = False

        history_service.add_entry(EventType.SYSTEM_STOP, "Seeding stopped")

        if self._monitor_task:
            logger.debug("   Stopping monitor task...")
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        if hasattr(self, "_resource_optimizer_task") and self._resource_optimizer_task:
            logger.debug("   Stopping resource optimizer...")
            self._resource_optimizer_task.cancel()
            try:
                await self._resource_optimizer_task
            except asyncio.CancelledError:
                pass

        if self.file_watcher:
            logger.debug("   Stopping file watcher...")
            await self.file_watcher.stop()

        # Persist stats before stopping announcers
        self._persist_all_stats()
        await persistence_service.stop_autosave()

        active_count = sum(1 for a in self.announcers.values() if a.is_running)
        logger.info(f"   Stopping {active_count} active announcer(s)...")
        tasks = [announcer.stop() for announcer in self.announcers.values()]
        await asyncio.gather(*tasks, return_exceptions=True)

        await websocket_manager.broadcast(
            {
                "type": "seeding_stopped",
                "data": {
                    "startedAt": self.started_at.isoformat(),
                    "activeTorrents": len([a for a in self.announcers.values() if a.is_running]),
                },
            }
        )
        await websocket_manager.broadcast({"type": "torrents_update", "data": {"torrents": self.get_torrents()}})
        logger.info("Seeding stopped successfully")

        # Send notification and close client
        await notification_service.notify_system_stop()
        await notification_service.close()

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict:
        total_uploaded = sum(a.uploaded for a in self.announcers.values())
        total_speed = sum(a.upload_speed for a in self.announcers.values() if a.is_running)
        active_count = sum(1 for a in self.announcers.values() if a.is_running)

        uptime = None
        if self.started_at:
            uptime = int((datetime.now(timezone.utc) - self.started_at).total_seconds())

        return {
            "isRunning": self.is_running,
            "activeTorrents": active_count,
            "totalTorrents": len(self.announcers),
            "totalUploaded": int(total_uploaded),
            "totalDownloaded": 0,
            "uploadSpeed": int(total_speed),
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "uptime": uptime,
        }

    def get_stats_cached(self) -> Dict:
        cached_stats = cache_manager.get_aggregated_stats("global_stats")
        if cached_stats:
            logger.debug("Stats loaded from cache")
            return cached_stats
        stats = self.get_stats()
        cache_manager.set_aggregated_stats("global_stats", stats)
        logger.debug("Stats computed and cached")
        return stats

    def get_torrents_cached(self) -> List[Dict]:
        cached_torrents = cache_manager.get_aggregated_stats("torrents_list")
        if cached_torrents:
            logger.debug("Torrents list loaded from cache")
            return cached_torrents
        torrents = self.get_torrents()
        cache_manager.set_aggregated_stats("torrents_list", torrents)
        logger.debug("Torrents list computed and cached")
        return torrents

    def _get_torrent_info(self, info_hash: str) -> Dict:
        """Proxy kept for any external callers"""
        return self._tm.get_torrent_info(info_hash)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _persist_all_stats(self):
        """Snapshot current stats to persistence for all torrents."""
        for info_hash, announcer in self.announcers.items():
            stats = announcer.get_stats()
            persistence_service.update(
                info_hash,
                uploaded=int(stats["uploaded"]),
                seeding_time=stats["seedingTime"],
                added_at=announcer.torrent.added_at.isoformat(),
                torrent_name=announcer.torrent.name,
            )

    @staticmethod
    def _find_best_fallback_client(missing_client: str, available_clients: list) -> str:
        """Find the best fallback client when the configured one is missing"""
        if not available_clients:
            raise RuntimeError("No available clients for fallback")

        try:
            missing_parts = missing_client.replace(".client", "").split("-")
            if len(missing_parts) >= 2:
                missing_name = missing_parts[0]

                same_client_candidates = [c for c in available_clients if c.startswith(missing_name)]
                if same_client_candidates:
                    same_client_candidates.sort(reverse=True)
                    return same_client_candidates[0]

                preferred_order = ["qbittorrent", "deluge", "transmission"]
                for preferred in preferred_order:
                    candidates = [c for c in available_clients if c.startswith(preferred)]
                    if candidates:
                        candidates.sort(reverse=True)
                        return candidates[0]
        except Exception as e:
            logger.debug(f"Error parsing client name '{missing_client}': {e}")

        available_clients.sort(reverse=True)
        return available_clients[0]

    async def _start_announcer_if_needed(self, announcer: TrackerAnnouncer):
        simultaneous_seed = self._config.get("simultaneousSeed", settings.SIMULTANEOUS_SEED)
        running_count = sum(1 for a in self.announcers.values() if a.is_running)
        if running_count < simultaneous_seed:
            await announcer.start()

    # ------------------------------------------------------------------
    # Monitor loop
    # ------------------------------------------------------------------

    async def _monitor_loop(self):
        """Monitor torrents and send updates - real-time"""
        logger.info("Monitor loop started!")
        try:
            update_count = 0
            while self.is_running:
                await asyncio.sleep(3)
                update_count += 1

                try:
                    for announcer in self.announcers.values():
                        if announcer.is_running:
                            try:
                                announcer._update_stats_for_display()
                            except Exception as e:
                                logger.error(f"Error updating stats for {announcer.torrent.name}: {e}")

                    stats = self.get_stats()
                    torrents = self.get_torrents()

                    logger.debug(
                        f"Monitor #{update_count}: {stats['activeTorrents']} active, "
                        f"speed={stats['uploadSpeed'] / 1024:.1f} KB/s, "
                        f"uploaded={stats['totalUploaded'] / (1024 * 1024):.2f} MB"
                    )

                    await websocket_manager.broadcast({"type": "stats_update", "data": stats})
                    await websocket_manager.broadcast({"type": "torrents_update", "data": {"torrents": torrents}})

                    if update_count % 5 == 0:
                        for torrent in torrents:
                            if torrent.get("isRunning"):
                                logger.debug(
                                    f"   {torrent['name'][:30]}: "
                                    f"speed={torrent['uploadSpeed'] / 1024:.1f}KB/s, "
                                    f"uploaded={torrent['uploaded'] / (1024 * 1024):.2f}MB, "
                                    f"ratio={torrent['ratio']:.3f}, "
                                    f"time={torrent['seedingTime']}s"
                                )

                    await self._tm.check_ratio_targets(self._config)
                    cache_manager.periodic_cleanup()
                    await self.load_torrents()

                    # Persist stats every ~30s (every 10 iterations)
                    if update_count % 10 == 0:
                        self._persist_all_stats()

                except Exception as e:
                    logger.error(f"Monitor loop iteration error: {e}", exc_info=True)

        except asyncio.CancelledError:
            logger.info("Monitor loop cancelled")
        except Exception as e:
            logger.error(f"Monitor loop fatal error: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # File watcher
    # ------------------------------------------------------------------

    async def _init_file_watcher(self):
        if not FILE_WATCHER_AVAILABLE:
            logger.info("File watcher disabled - watchdog not available")
            return
        try:
            self.file_watcher = FileWatcherService(settings.TORRENTS_DIR, self._auto_reload_torrents)
            await self.file_watcher.start()
            logger.info("File watcher initialized - new torrents will auto-load")
        except Exception as e:
            logger.warning(f"Failed to initialize file watcher: {e}")
            self.file_watcher = None

    async def _auto_reload_torrents(self):
        try:
            logger.info("Auto-reloading torrents due to file system change...")
            old_count = len(self.announcers)
            await self.load_torrents()
            new_count = len(self.announcers)

            await websocket_manager.broadcast({"type": "torrents_update", "data": {"torrents": self.get_torrents()}})

            message = f"Auto-reload: {old_count} -> {new_count} torrents"
            logger.info(message)
            await websocket_manager.broadcast({"type": "toast", "data": {"message": message, "type": "info"}})
        except Exception as e:
            logger.error(f"Auto-reload failed: {e}")
            await websocket_manager.broadcast({"type": "toast", "data": {"message": f"Auto-reload failed: {e}", "type": "error"}})


# Global service instance
seeder_service = SeederService()
