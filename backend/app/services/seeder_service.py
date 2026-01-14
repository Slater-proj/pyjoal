"""
Seeder Service
Manages multiple torrent seeders and orchestrates announces
"""
import asyncio
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
    
    async def initialize(self):
        """Initialize service"""
        from app.core.bittorrent_client import list_available_clients
        
        # Load configuration
        await self.load_config()
        
        # Get available clients
        available_clients = list_available_clients()
        if not available_clients:
            raise RuntimeError(
                "❌ ERREUR CRITIQUE: Aucun fichier client (.client) trouvé dans le dossier 'clients/'\n"
                "   Veuillez ajouter au moins un fichier .client pour démarrer l'application."
            )
        
        # Get configured client
        configured_client = self._config.get("client", settings.DEFAULT_CLIENT)
        
        # Validate configured client exists
        if configured_client not in available_clients:
            fallback_client = available_clients[0]
            print(f"⚠️  Client configuré '{configured_client}' introuvable")
            print(f"🔄 Utilisation du client par défaut: {fallback_client}")
            configured_client = fallback_client
            # Update config with valid client
            self._config["client"] = configured_client
            await self.save_config()
        
        # Initialize client
        try:
            self.client = BitTorrentClient(configured_client)
            print(f"📱 Client chargé: {self.client.name} {self.client.version}")
        except Exception as e:
            raise RuntimeError(f"❌ Impossible de charger le client '{configured_client}': {e}")
        
        # Load existing torrents
        await self.load_torrents()
    
    async def load_config(self):
        """Load configuration from file"""
        config_file = settings.CONFIG_DIR / "config.json"
        
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        else:
            # Create default config
            self._config = {
                "minUploadRate": settings.MIN_UPLOAD_RATE,
                "maxUploadRate": settings.MAX_UPLOAD_RATE,
                "simultaneousSeed": settings.SIMULTANEOUS_SEED,
                "client": settings.DEFAULT_CLIENT,
                "keepTorrentWithZeroLeechers": settings.KEEP_TORRENT_WITH_ZERO_LEECHERS,
                "uploadRatioTarget": settings.UPLOAD_RATIO_TARGET,
                "seedingDurationLimit": settings.SEEDING_DURATION_LIMIT
            }
            await self.save_config()
    
    async def save_config(self):
        """Save configuration to file"""
        config_file = settings.CONFIG_DIR / "config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2)
    
    async def load_torrents(self):
        """Load torrents from directory"""
        torrents = load_torrents_from_directory(settings.TORRENTS_DIR)
        
        for torrent in torrents:
            if torrent.info_hash not in self.announcers:
                await self.add_torrent(torrent)
        
        print(f"📂 Loaded {len(torrents)} torrent(s)")
    
    async def add_torrent(self, torrent: Torrent):
        """Add a torrent to seed"""
        if torrent.info_hash in self.announcers:
            return
        
        if not self.client:
            raise ValueError("Client not initialized")
        
        announcer = TrackerAnnouncer(torrent, self.client)
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
        
        print(f"➕ Added torrent: {torrent.name}")
    
    async def remove_torrent(self, info_hash: str):
        """Remove a torrent"""
        if info_hash not in self.announcers:
            return
        
        announcer = self.announcers[info_hash]
        
        # Stop announcer
        if announcer.is_running:
            await announcer.stop()
        
        # Remove from dict
        del self.announcers[info_hash]
        
        # Log torrent removed
        history_service.add_entry(
            EventType.TORRENT_REMOVED,
            f"Removed torrent: {announcer.torrent.name}",
            {"info_hash": info_hash}
        )
        
        # Delete torrent file
        torrent_file = settings.TORRENTS_DIR / f"{info_hash}.torrent"
        if torrent_file.exists():
            torrent_file.unlink()
        
        # Notify via WebSocket
        await websocket_manager.broadcast({
            "type": "torrent_removed",
            "data": {"info_hash": info_hash}
        })
        
        print(f"➖ Removed torrent: {info_hash[:8]}...")
    
    async def start(self):
        """Start seeding"""
        if self.is_running:
            return
        
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
        
        for announcer in announcers_to_start:
            await announcer.start()
        
        # Start monitor task
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        
        # Notify via WebSocket
        await websocket_manager.broadcast({
            "type": "seeding_started",
            "data": {"started_at": self.started_at.isoformat()}
        })
        
        print(f"▶️  Started seeding {len(announcers_to_start)} torrent(s)")
    
    async def stop(self):
        """Stop seeding"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Log system stop
        history_service.add_entry(
            EventType.SYSTEM_STOP,
            "Seeding stopped"
        )
        
        # Stop monitor task
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        # Stop all announcers
        tasks = [announcer.stop() for announcer in self.announcers.values()]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Notify via WebSocket
        await websocket_manager.broadcast({
            "type": "seeding_stopped",
            "data": {}
        })
        
        print("⏸️  Stopped seeding")
    
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
                
                # Send stats update
                await websocket_manager.broadcast({
                    "type": "stats_update",
                    "data": self.get_stats()
                })
                
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
        now = datetime.utcnow()
        
        for info_hash, announcer in self.announcers.items():
            stats = announcer.get_stats()
            torrent = announcer.torrent
            
            # Check ratio target (if enabled)
            if ratio_target > 0 and stats["ratio"] >= ratio_target:
                history_service.add_entry(
                    EventType.TORRENT_REMOVED,
                    f"Ratio target reached for {torrent.name}",
                    {"info_hash": info_hash, "ratio": stats["ratio"], "target": ratio_target}
                )
                to_remove.append(info_hash)
                continue
            
            # Check duration limit (if enabled) - in hours
            if duration_limit > 0:
                seeding_duration = (now - torrent.added_at).total_seconds() / 3600  # Convert to hours
                if seeding_duration >= duration_limit:
                    history_service.add_entry(
                        EventType.TORRENT_REMOVED,
                        f"Duration limit reached for {torrent.name}",
                        {"info_hash": info_hash, "duration_hours": seeding_duration, "limit": duration_limit}
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
            print(f"📦 Archived torrent: {torrent.name}")
        
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
        self._config.update(new_config)
        await self.save_config()
        
        # Log config update
        history_service.add_entry(
            EventType.CONFIG_UPDATED,
            "Configuration updated",
            new_config
        )
        
        # Update settings
        if "minUploadRate" in new_config:
            settings.MIN_UPLOAD_RATE = new_config["minUploadRate"]
        if "maxUploadRate" in new_config:
            settings.MAX_UPLOAD_RATE = new_config["maxUploadRate"]
        if "seedingDurationLimit" in new_config:
            settings.SEEDING_DURATION_LIMIT = new_config["seedingDurationLimit"]
        
        # Reload client if changed
        if "client" in new_config and new_config["client"] != self.client.client_file:
            try:
                self.client = BitTorrentClient(new_config["client"])
                print(f"📱 Switched to client: {self.client.name} {self.client.version}")
            except Exception as e:
                print(f"⚠️  Failed to switch client: {e}")
    
    def get_torrents(self) -> List[Dict]:
        """Get all torrents info"""
        return [
            self._get_torrent_info(info_hash)
            for info_hash in self.announcers.keys()
        ]
    
    def _get_torrent_info(self, info_hash: str) -> Dict:
        """Get single torrent info"""
        announcer = self.announcers.get(info_hash)
        if not announcer:
            return {}
        
        stats = announcer.get_stats()
        torrent = announcer.torrent
        
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
            "tracker": torrent.primary_tracker
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
            "uploadSpeed": total_speed,
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "uptime": uptime
        }


# Global service instance
seeder_service = SeederService()
