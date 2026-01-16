"""
Seeder Service
Manages multiple torrent seeders and orchestrates announces
"""
import asyncio
import logging
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
import json

from app.core.config import settings
from app.core.bittorrent_client import BitTorrentClient, get_default_client
from app.core.torrent_parser import Torrent, load_torrents_from_directory
from app.core.tracker_announcer import TrackerAnnouncer
from app.services.websocket_manager import websocket_manager
from app.services.history_service import history_service, EventType

logger = logging.getLogger(__name__)


class SeederService:
    """Service to manage torrent seeding"""
    
    def __init__(self):
        """Initialize seeder service"""
        self.client: Optional[BitTorrentClient] = None
        self.announcers: Dict[str, TrackerAnnouncer] = {}
        self.is_running: bool = False
        self.started_at: Optional[datetime] = None
        self._config: Dict = {}
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Failed torrents tracking
        self.failed_torrents: Dict[str, Dict] = {}  # filename -> error info
    
    async def initialize(self):
        """Initialize service"""
        from app.core.bittorrent_client import list_available_clients
        
        logger.info("🚀 Initializing Seeder Service...")
        
        # Load configuration
        await self.load_config()
        logger.info(f"   Configuration loaded: {self._config}")
        
        # Get available clients
        available_clients = list_available_clients()
        logger.info(f"   Available clients: {', '.join(available_clients) if available_clients else 'NONE'}")
        
        if not available_clients:
            logger.critical("❌ NO CLIENT FILES FOUND!")
            raise RuntimeError(
                "❌ ERREUR CRITIQUE: Aucun fichier client (.client) trouvé dans le dossier 'clients/'\n"
                "   Veuillez ajouter au moins un fichier .client pour démarrer l'application."
            )
        
        # Get configured client
        configured_client = self._config.get("client", settings.DEFAULT_CLIENT)
        logger.info(f"   Configured client: {configured_client}")
        
        # Validate configured client exists
        if configured_client not in available_clients:
            fallback_client = available_clients[0]
            logger.warning(f"⚠️  Client configuré '{configured_client}' introuvable")
            logger.info(f"🔄 Utilisation du client par défaut: {fallback_client}")
            configured_client = fallback_client
            # Update config with valid client
            self._config["client"] = configured_client
            await self.save_config()
        
        # Initialize client
        try:
            self.client = BitTorrentClient(configured_client)
            logger.info(f"📱 Client loaded: {self.client.name} {self.client.version}")
            logger.debug(f"   User-Agent: {self.client.get_user_agent()}")
            logger.debug(f"   Upload rate range: {settings.MIN_UPLOAD_RATE}-{settings.MAX_UPLOAD_RATE} KB/s")
        except Exception as e:
            logger.critical(f"❌ Failed to load client '{configured_client}': {e}")
            raise RuntimeError(f"❌ Impossible de charger le client '{configured_client}': {e}")
        
        # Load existing torrents
        await self.load_torrents()
        
        logger.info("✅ Seeder Service initialized successfully")
    
    async def load_config(self):
        """Load configuration from file"""
        config_file = settings.CONFIG_DIR / "config.json"
        
        if config_file.exists():
            logger.debug(f"📝 Loading config from: {config_file}")
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            logger.debug(f"   Config loaded: {self._config}")
        else:
            # Create default config
            logger.info("🆕 Creating default configuration")
            self._config = {
                "minUploadRate": settings.MIN_UPLOAD_RATE,
                "maxUploadRate": settings.MAX_UPLOAD_RATE,
                "simultaneousSeed": settings.SIMULTANEOUS_SEED,
                "client": settings.DEFAULT_CLIENT,
                "keepTorrentWithZeroLeechers": settings.KEEP_TORRENT_WITH_ZERO_LEECHERS,
                "uploadRatioTarget": settings.UPLOAD_RATIO_TARGET,
                "seedingDurationLimit": settings.SEEDING_DURATION_LIMIT,
                # Discretion settings
                "announceInterval": settings.ANNOUNCE_INTERVAL,
                "announceJitter": settings.ANNOUNCE_JITTER,
                "minStatsUpdateInterval": settings.MIN_STATS_UPDATE_INTERVAL,
                "enableSpeedVariation": settings.ENABLE_SPEED_VARIATION,
                "speedVariationPercent": settings.SPEED_VARIATION_PERCENT
            }
            await self.save_config()
            logger.info(f"   Default config created: {self._config}")
    
    async def save_config(self):
        """Save configuration to file atomically"""
        import tempfile
        import shutil
        
        config_file = settings.CONFIG_DIR / "config.json"
        
        try:
            # Create config dir if it doesn't exist
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temporary file first (atomic operation)
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', 
                                          dir=config_file.parent, delete=False) as temp_file:
                json.dump(self._config, temp_file, indent=2)
                temp_file.flush()  # Ensure data is written
                temp_file_path = temp_file.name
            
            # Atomically replace the config file
            shutil.move(temp_file_path, config_file)
            logger.debug(f"✅ Config saved to {config_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save config to {config_file}: {e}")
            # Clean up temp file if it exists
            try:
                if 'temp_file_path' in locals():
                    Path(temp_file_path).unlink(missing_ok=True)
            except:
                pass
            raise e
    
    async def load_torrents(self):
        """Load torrents from directory"""
        logger.debug(f"📂 Loading torrents from: {settings.TORRENTS_DIR}")
        
        # Custom loading to capture failures
        torrents = []
        torrent_files = list(settings.TORRENTS_DIR.glob("*.torrent"))
        
        for torrent_file in torrent_files:
            try:
                torrent = Torrent(torrent_file)
                torrents.append(torrent)
                
                # Remove from failed list if it now works
                if torrent_file.name in self.failed_torrents:
                    del self.failed_torrents[torrent_file.name]
                    logger.info(f"✅ Previously failed torrent now works: {torrent_file.name}")
                    
            except Exception as e:
                # Store failed torrent info temporarily
                error_msg = str(e)
                self.failed_torrents[torrent_file.name] = {
                    "filename": torrent_file.name,
                    "error": error_msg,
                    "timestamp": datetime.utcnow(),
                    "size": torrent_file.stat().st_size if torrent_file.exists() else 0
                }
                
                # Log error with details
                logger.error(f"❌ Failed to load {torrent_file.name}: {error_msg}")
                
                # Add to history with detailed error
                from app.services.history_service import history_service, EventType
                history_service.add_entry(
                    EventType.TORRENT_LOAD_FAILED,
                    f"Failed to load torrent: {torrent_file.name}",
                    {
                        "filename": torrent_file.name,
                        "error": error_msg,
                        "size": torrent_file.stat().st_size if torrent_file.exists() else 0,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                
                # Send toast notification to frontend
                from app.services.websocket_manager import websocket_manager
                import asyncio
                asyncio.create_task(websocket_manager.broadcast({
                    "type": "torrent_load_error",
                    "data": {
                        "filename": torrent_file.name,
                        "error": error_msg,
                        "message": f"Failed to load {torrent_file.name}: {error_msg}"
                    }
                }))
        
        # Add successful torrents
        new_count = 0
        for torrent in torrents:
            if torrent.info_hash not in self.announcers:
                await self.add_torrent(torrent)
                new_count += 1
        
        total_files = len(torrent_files)
        failed_count = len(self.failed_torrents)
        logger.info(f"📂 Loaded {len(torrents)}/{total_files} torrent(s) ({new_count} new, {failed_count} failed)")
    
    def has_torrents(self) -> bool:
        """Check if any torrents are available"""
        return len(self.announcers) > 0 or len(load_torrents_from_directory(settings.TORRENTS_DIR)) > 0
    
    async def add_torrent(self, torrent: Torrent):
        """Add a torrent to seed"""
        if torrent.info_hash in self.announcers:
            logger.debug(f"Torrent already added: {torrent.name}")
            return
        
        if not self.client:
            logger.error("Cannot add torrent: client not initialized")
            raise ValueError("Client not initialized")
        
        logger.info(f"➕ Adding torrent: {torrent.name}")
        logger.debug(f"   Info hash: {torrent.info_hash}")
        logger.debug(f"   Size: {torrent.size / (1024**3):.2f} GB")
        logger.debug(f"   Tracker: {torrent.primary_tracker}")
        
        # Create announcer with discretion config
        announcer = TrackerAnnouncer(
            torrent, 
            self.client, 
            discretion_config={
                "announce_interval": self._config.get("announceInterval", settings.ANNOUNCE_INTERVAL),
                "announce_jitter": self._config.get("announceJitter", settings.ANNOUNCE_JITTER),
                "min_stats_update_interval": self._config.get("minStatsUpdateInterval", settings.MIN_STATS_UPDATE_INTERVAL),
                "enable_speed_variation": self._config.get("enableSpeedVariation", settings.ENABLE_SPEED_VARIATION),
                "speed_variation_percent": self._config.get("speedVariationPercent", settings.SPEED_VARIATION_PERCENT)
            }
        )
        self.announcers[torrent.info_hash] = announcer
        
        # Start if service is running
        if self.is_running:
            await self._start_announcer_if_needed(announcer)
        
        # Log torrent added
        history_service.add_entry(
            EventType.TORRENT_ADDED,
            f"Added torrent: {torrent.name}",
            {"info_hash": torrent.info_hash, "size": torrent.size}
        )
        
        # Notify via WebSocket
        await websocket_manager.broadcast({
            "type": "torrent_added",
            "data": self._get_torrent_info(torrent.info_hash)
        })
        
        # Send updated torrents list
        await websocket_manager.broadcast({
            "type": "torrents_update",
            "data": {
                "torrents": self.get_torrents()
            }
        })
        
        logger.info(f"✅ Torrent added successfully: {torrent.name[:50]}")
    
    async def remove_torrent(self, info_hash: str):
        """Remove a torrent"""
        if info_hash not in self.announcers:
            logger.warning(f"Cannot remove torrent: {info_hash} not found")
            return
        
        announcer = self.announcers[info_hash]
        logger.info(f"➖ Removing torrent: {announcer.torrent.name}")
        
        # Stop announcer
        if announcer.is_running:
            logger.debug(f"   Stopping announcer...")
            await announcer.stop()
        
        # Remove from dict
        del self.announcers[info_hash]
        
        # Log torrent removed
        history_service.add_entry(
            EventType.TORRENT_REMOVED,
            f"Removed torrent: {announcer.torrent.name}",
            {"info_hash": info_hash}
        )
        
        # Archive torrent file (move to archived folder)
        archived_dir = settings.TORRENTS_DIR / "archived"
        archived_dir.mkdir(exist_ok=True)
        
        torrent_path = announcer.torrent.path
        if torrent_path and torrent_path.exists():
            archived_path = archived_dir / torrent_path.name
            torrent_path.rename(archived_path)
            logger.debug(f"   Torrent file archived to: {archived_path}")
        
        # Notify via WebSocket
        await websocket_manager.broadcast({
            "type": "torrent_removed",
            "data": {"info_hash": info_hash}
        })
        
        # Send updated torrents list
        await websocket_manager.broadcast({
            "type": "torrents_update",
            "data": {
                "torrents": self.get_torrents()
            }
        })
        
        logger.info(f"✅ Torrent removed: {info_hash[:8]}...")
    
    async def start(self):
        """Start seeding"""
        if self.is_running:
            logger.warning("Seeding already running")
            return
        
        logger.info("▶️  Starting seeding service...")
        self.is_running = True
        self.started_at = datetime.utcnow()
        
        # Log system start
        history_service.add_entry(
            EventType.SYSTEM_START,
            "Seeding started",
            {"torrents_count": len(self.announcers)}
        )
        
        # Start announcers based on simultaneousSeed config
        simultaneous_seed = self._config.get("simultaneousSeed", settings.SIMULTANEOUS_SEED)
        announcers_to_start = list(self.announcers.values())[:simultaneous_seed]
        
        logger.info(f"   Starting {len(announcers_to_start)}/{len(self.announcers)} torrent(s)")
        logger.info(f"   Simultaneous seed limit: {simultaneous_seed}")
        logger.info(f"   Upload rate: {settings.MIN_UPLOAD_RATE}-{settings.MAX_UPLOAD_RATE} KB/s")
        
        for announcer in announcers_to_start:
            await announcer.start()
        
        # Start monitor task
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.debug("   Monitor task started")
        
        # Notify via WebSocket
        await websocket_manager.broadcast({
            "type": "seeding_started",
            "data": {"started_at": self.started_at.isoformat()}
        })
        
        logger.info(f"✅ Seeding started successfully ({len(announcers_to_start)} active)")
    
    async def stop(self):
        """Stop seeding"""
        if not self.is_running:
            logger.warning("Seeding already stopped")
            return
        
        logger.info("⏸️  Stopping seeding service...")
        self.is_running = False
        
        # Log system stop
        history_service.add_entry(
            EventType.SYSTEM_STOP,
            "Seeding stopped"
        )
        
        # Stop monitor task
        if self._monitor_task:
            logger.debug("   Stopping monitor task...")
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        # Stop all announcers
        active_count = sum(1 for a in self.announcers.values() if a.is_running)
        logger.info(f"   Stopping {active_count} active announcer(s)...")
        tasks = [announcer.stop() for announcer in self.announcers.values()]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Notify via WebSocket
        await websocket_manager.broadcast({
            "type": "seeding_stopped",
            "data": {
                "startedAt": self.started_at.isoformat(),
                "activeTorrents": len([a for a in self.announcers.values() if a.is_running])
            }
        })
        
        # Send initial torrents state
        await websocket_manager.broadcast({
            "type": "torrents_update", 
            "data": {
                "torrents": self.get_torrents()
            }
        })
        
        logger.info("✅ Seeding stopped successfully")
    
    async def _start_announcer_if_needed(self, announcer: TrackerAnnouncer):
        """Start announcer if we have capacity"""
        simultaneous_seed = self._config.get("simultaneousSeed", settings.SIMULTANEOUS_SEED)
        running_count = sum(1 for a in self.announcers.values() if a.is_running)
        
        if running_count < simultaneous_seed:
            await announcer.start()
    
    async def _monitor_loop(self):
        """Monitor torrents and send updates"""
        try:
            while self.is_running:
                await asyncio.sleep(5)  # Update every 5 seconds
                
                # Get current data
                stats = self.get_stats()
                torrents = self.get_torrents()
                
                # DO NOT force synchronous stats update - let each announcer update independently
                # This was causing all torrents to update speeds at the same time (security issue)
                
                logger.debug(f"🔄 Monitor update: {stats['activeTorrents']} active, {len(torrents)} total torrents, total speed: {stats['uploadSpeed']/1024:.1f} KB/s")
                
                # Send global stats update
                await websocket_manager.broadcast({
                    "type": "stats_update",
                    "data": stats
                })
                
                # Send individual torrent updates
                await websocket_manager.broadcast({
                    "type": "torrents_update",
                    "data": {
                        "torrents": torrents
                    }
                })
                
                # Log torrent statuses for debugging
                for torrent in torrents:
                    if torrent.get("isRunning"):
                        logger.debug(f"   📈 {torrent['name'][:30]}: {torrent['uploadSpeed']/1024:.1f} KB/s, {torrent['seeders']}S/{torrent['leechers']}L")
                
                # Check ratio targets
                await self._check_ratio_targets()
                
                # Check for new torrents
                await self.load_torrents()
                
        except asyncio.CancelledError:
            pass
    
    async def _check_ratio_targets(self):
        """Check if any torrents reached ratio target or duration limit"""
        ratio_target = self._config.get("uploadRatioTarget", -1.0)
        duration_limit = self._config.get("seedingDurationLimit", -1.0)
        keep_zero_leechers = self._config.get("keepTorrentWithZeroLeechers", True)
        
        to_remove = []
        
        for info_hash, announcer in self.announcers.items():
            stats = announcer.get_stats()
            torrent = announcer.torrent
            
            # Check ratio target (if enabled)
            if ratio_target > 0 and stats["ratio"] >= ratio_target:
                history_service.add_entry(
                    EventType.TORRENT_ARCHIVED_RATIO,
                    f"Archived {torrent.name} - ratio target reached ({stats['ratio']:.2f} >= {ratio_target})",
                    {"info_hash": info_hash, "ratio": stats["ratio"], "target": ratio_target, "reason": "ratio_target"}
                )
                to_remove.append(info_hash)
                continue
            
            # Check duration limit (if enabled) - use actual seeding time in seconds, convert limit from hours
            if duration_limit > 0:
                seeding_time_hours = stats["seedingTime"] / 3600  # Convert seconds to hours
                if seeding_time_hours >= duration_limit:
                    history_service.add_entry(
                        EventType.TORRENT_ARCHIVED_TIME,
                        f"Archived {torrent.name} - duration limit reached ({seeding_time_hours:.1f}h >= {duration_limit}h)",
                        {"info_hash": info_hash, "seeding_hours": seeding_time_hours, "limit": duration_limit, "reason": "duration_limit"}
                    )
                    to_remove.append(info_hash)
                    continue
            
            # Check zero peers
            if not keep_zero_leechers and stats["seeders"] == 0 and stats["leechers"] == 0:
                to_remove.append(info_hash)
        
        # Remove torrents (archive them)
        for info_hash in to_remove:
            await self._archive_torrent(info_hash)
    
    async def _archive_torrent(self, info_hash: str):
        """Archive a torrent (move to archived folder instead of deleting)"""
        if info_hash not in self.announcers:
            return
        
        announcer = self.announcers[info_hash]
        torrent = announcer.torrent
        
        logger.info(f"📦 Archiving torrent: {torrent.name}")
        
        # Stop announcer
        if announcer.is_running:
            await announcer.stop()
        
        # Remove from dict
        del self.announcers[info_hash]
        
        # Move torrent file to archived folder
        archived_dir = settings.TORRENTS_DIR / "archived"
        archived_dir.mkdir(exist_ok=True)
        
        if torrent.path.exists():
            archived_path = archived_dir / torrent.path.name
            torrent.path.rename(archived_path)
            logger.info(f"✅ Torrent archived: {torrent.name}")
        else:
            logger.warning(f"   Torrent file not found: {torrent.path}")
        
        # Notify via WebSocket
        await websocket_manager.broadcast({
            "type": "torrent_archived",
            "data": {"info_hash": info_hash, "name": torrent.name}
        })
    
    def get_config(self) -> Dict:
        """Get current configuration"""
        return self._config.copy()
    
    async def update_config(self, new_config: Dict):
        """Update configuration"""
        logger.info(f"⚙️  Updating configuration: {new_config}")
        
        # Validate config before applying
        try:
            # Create a backup of current config
            backup_config = self._config.copy()
            
            # Validate numeric values
            if "minUploadRate" in new_config:
                rate = new_config["minUploadRate"]
                if not isinstance(rate, (int, float)) or rate < 0:
                    raise ValueError(f"Invalid minUploadRate: {rate} (must be >= 0)")
                    
            if "maxUploadRate" in new_config:
                rate = new_config["maxUploadRate"]
                if not isinstance(rate, (int, float)) or rate < 0:
                    raise ValueError(f"Invalid maxUploadRate: {rate} (must be >= 0)")
                    
            if "uploadRatioTarget" in new_config:
                ratio = new_config["uploadRatioTarget"]
                if not isinstance(ratio, (int, float)) or (ratio < -1 and ratio != -1):
                    raise ValueError(f"Invalid uploadRatioTarget: {ratio} (must be -1 or >= 0)")
                    
            if "seedingDurationLimit" in new_config:
                duration = new_config["seedingDurationLimit"]
                if not isinstance(duration, (int, float)) or (duration < -1 and duration != -1):
                    raise ValueError(f"Invalid seedingDurationLimit: {duration} (must be -1 or >= 0)")
            
            # Update configuration
            self._config.update(new_config)
            await self.save_config()
            logger.info("✅ Configuration saved successfully")
            
            # Log config update
            history_service.add_entry(
                EventType.CONFIG_UPDATED,
                "Configuration updated",
                new_config
            )
            
        except Exception as save_error:
            logger.error(f"❌ Failed to save config: {save_error}")
            # Restore backup if save failed
            self._config = backup_config
            raise save_error
        
        # Update settings after successful save
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
            
            # Reload client if changed
            if "client" in new_config and new_config["client"] != self.client.client_file:
                try:
                    self.client = BitTorrentClient(new_config["client"])
                    logger.info(f"✅ Switched to client: {self.client.name} {self.client.version}")
                except Exception as e:
                    logger.error(f"⚠️  Failed to switch client: {e}")
        except Exception as settings_error:
            logger.error(f"⚠️  Failed to update settings: {settings_error}")
            # Don't fail the whole operation for settings update issues
    
    def get_torrents(self) -> List[Dict]:
        """Get working torrents info (failed torrents are handled via toast/history)"""
        torrents = []
        
        # Add only working torrents
        for info_hash in self.announcers.keys():
            torrents.append(self._get_torrent_info(info_hash))
        
        return torrents
    
    def _get_torrent_info(self, info_hash: str) -> Dict:
        """Get single torrent info"""
        announcer = self.announcers.get(info_hash)
        if not announcer:
            return {}
        
        stats = announcer.get_stats()
        torrent = announcer.torrent
        
        # Determine status
        if not announcer.is_running:
            status = "STOPPED"
        elif stats.get("lastError"):
            status = "ERROR"
        elif stats.get("seeders", 0) > 0 or stats.get("leechers", 0) > 0:
            status = "ACTIVE"
        else:
            status = "IDLE"
        
        return {
            "id": info_hash,
            "name": torrent.name,
            "size": torrent.size,
            "uploaded": stats["uploaded"],
            "uploadSpeed": stats["uploadSpeed"],
            "ratio": stats["ratio"],
            "seeders": stats["seeders"],
            "leechers": stats["leechers"],
            "state": "seeding" if announcer.is_running else "stopped",
            "addedAt": torrent.added_at.isoformat(),
            "lastAnnounce": stats["lastAnnounce"].isoformat() if stats["lastAnnounce"] else None,
            "nextAnnounce": stats["nextAnnounce"].isoformat() if stats["nextAnnounce"] else None,
            "tracker": torrent.primary_tracker,
            "seedingTime": stats["seedingTime"],
            "lastError": stats.get("lastError"),
            "errorCount": stats.get("errorCount", 0),
            "lastErrorTime": stats["lastErrorTime"].isoformat() if stats.get("lastErrorTime") else None,
            "isHealthy": stats.get("isHealthy", True),
            "status": status,
            "isRunning": announcer.is_running
        }
    
    def get_stats(self) -> Dict:
        """Get service statistics"""
        total_uploaded = sum(
            a.uploaded for a in self.announcers.values()
        )
        total_speed = sum(
            a.upload_speed for a in self.announcers.values() if a.is_running
        )
        active_count = sum(
            1 for a in self.announcers.values() if a.is_running
        )
        
        uptime = None
        if self.started_at:
            uptime = int((datetime.utcnow() - self.started_at).total_seconds())
        
        return {
            "isRunning": self.is_running,
            "activeTorrents": active_count,
            "totalTorrents": len(self.announcers),
            "totalUploaded": total_uploaded,
            "totalDownloaded": 0,
            "uploadSpeed": int(total_speed),  # Convert to int for schema compliance
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "uptime": uptime
        }


# Global service instance
seeder_service = SeederService()
