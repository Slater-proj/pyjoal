"""
File Watcher Service
Monitors the torrents directory for new files and automatically loads them
"""
import asyncio
import logging
import time
from pathlib import Path
from typing import Optional, Callable, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from concurrent.futures import ThreadPoolExecutor
import threading
from app.core.torrent_validator import validate_torrent_file
from app.services.history_service import history_service, EventType
from app.core.config import settings

logger = logging.getLogger(__name__)


class TorrentFileHandler(FileSystemEventHandler):
    """Handle file system events for torrent files"""
    
    def __init__(self, callback: Callable, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self.callback = callback
        self.loop = loop
        self._pending_files: Set[str] = set()
        self._processing_files: Set[str] = set()  # Files currently being validated
        self._lock = threading.Lock()
    
    def on_created(self, event):
        """Handle file creation events"""
        if not event.is_directory and event.src_path.endswith('.torrent'):
            # Skip Windows Zone.Identifier files
            if ':Zone.Identifier' in event.src_path:
                logger.debug(f"Skipping Zone.Identifier file: {event.src_path}")
                return
            
            # Skip if already being processed (avoid duplicates)
            with self._lock:
                if event.src_path in self._processing_files:
                    logger.debug(f"Skipping duplicate event for: {event.src_path}")
                    return
                self._processing_files.add(event.src_path)
            
            try:
                file_path = Path(event.src_path)
                
                # Wait for file to be fully written (especially on NAS/network shares)
                time.sleep(1.0)  # 1 second delay for slow NAS
                
                # Check file still exists (might have been moved/deleted)
                if not file_path.exists():
                    logger.debug(f"File no longer exists, skipping: {event.src_path}")
                    return
                
                # Full validation with retries (includes header check)
                is_valid, error_message = validate_torrent_file(file_path)
                if is_valid:
                    logger.info(f"📁 Valid torrent file detected: {event.src_path}")
                    self._schedule_reload(event.src_path)
                else:
                    logger.error(f"❌ Invalid torrent: {file_path.name} - {error_message}")
                    self._archive_invalid_torrent(file_path, error_message)
            finally:
                with self._lock:
                    self._processing_files.discard(event.src_path)
    
    def on_moved(self, event):
        """Handle file move/rename events"""
        if not event.is_directory and event.dest_path.endswith('.torrent'):
            # Skip if file was moved to archived folder
            if '/archived/' in event.dest_path or '\\archived\\' in event.dest_path:
                logger.debug(f"Skipping archived file: {event.dest_path}")
                return
            
            file_path = Path(event.dest_path)
            
            # Full validation with retries
            is_valid, error_message = validate_torrent_file(file_path)
            if is_valid:
                logger.info(f"📁 Valid torrent file moved/renamed: {event.dest_path}")
                self._schedule_reload(event.dest_path)
            else:
                logger.error(f"❌ Invalid torrent moved/renamed: {file_path.name} - {error_message}")
                self._archive_invalid_torrent(file_path, error_message)
    
    def _archive_invalid_torrent(self, file_path: Path, error_message: str):
        """Archive invalid torrent and add to history"""
        try:
            # Check if file still exists before archiving
            if not file_path.exists():
                logger.debug(f"File already gone, skipping archive: {file_path.name}")
                return
            
            # Add to history with detailed error
            history_service.add_entry(
                EventType.TORRENT_LOAD_FAILED,
                f"❌ Invalid torrent archived: {file_path.name}",
                {
                    "filename": file_path.name,
                    "file_path": str(file_path),
                    "error": error_message,
                    "reason_detail": error_message,
                    "action": "auto_archived"
                }
            )
            
            # Archive the invalid file
            archived_dir = settings.TORRENTS_DIR / "archived"
            archived_dir.mkdir(exist_ok=True)
            archived_path = archived_dir / file_path.name
            
            if file_path.exists():
                file_path.rename(archived_path)
                logger.info(f"📦 Invalid torrent auto-archived: {file_path.name} -> archived/")
            
        except Exception as e:
            logger.error(f"Failed to archive invalid torrent {file_path.name}: {e}")
    
    def _schedule_reload(self, file_path: str):
        """Schedule reload operation in the main event loop"""
        with self._lock:
            if file_path in self._pending_files:
                return  # Already scheduled
            self._pending_files.add(file_path)
        
        # Schedule in main thread's event loop with delay
        asyncio.run_coroutine_threadsafe(
            self._delayed_reload(file_path), 
            self.loop
        )
    
    async def _delayed_reload(self, file_path: str):
        """Delayed reload with debouncing"""
        try:
            await asyncio.sleep(1.0)  # Wait 1 second to ensure file is fully written
            
            with self._lock:
                self._pending_files.discard(file_path)
            
            await self.callback()
            logger.info(f"✅ Auto-reload completed for: {Path(file_path).name}")
            
        except Exception as e:
            logger.error(f"❌ Auto-reload failed for {Path(file_path).name}: {e}")
            with self._lock:
                self._pending_files.discard(file_path)


class FileWatcherService:
    """Service to watch torrents directory for changes"""
    
    def __init__(self, torrents_dir: Path, reload_callback: Callable):
        self.torrents_dir = torrents_dir
        self.reload_callback = reload_callback
        self.observer: Optional[Observer] = None
        self.handler: Optional[TorrentFileHandler] = None
        self.is_running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    async def start(self):
        """Start watching the torrents directory"""
        if self.is_running:
            logger.warning("File watcher is already running")
            return
        
        try:
            logger.info(f"🔍 Starting file watcher for: {self.torrents_dir}")
            
            # Store the current event loop
            self._loop = asyncio.get_running_loop()
            
            # Ensure directory exists
            self.torrents_dir.mkdir(parents=True, exist_ok=True)
            
            # Create handler and observer
            self.handler = TorrentFileHandler(self.reload_callback, self._loop)
            self.observer = Observer()
            self.observer.schedule(self.handler, str(self.torrents_dir), recursive=False)
            
            # Start observer in a separate thread
            self.observer.start()
            self.is_running = True
            
            logger.info("✅ File watcher started successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to start file watcher: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop watching the torrents directory"""
        if not self.is_running:
            return
        
        try:
            logger.info("⏹️ Stopping file watcher...")
            
            if self.observer:
                self.observer.stop()
                self.observer.join(timeout=5.0)
                self.observer = None
            
            self.handler = None
            self.is_running = False
            
            logger.info("✅ File watcher stopped")
            
        except Exception as e:
            logger.error(f"❌ Error stopping file watcher: {e}")
    
    async def restart(self):
        """Restart the file watcher"""
        logger.info("🔄 Restarting file watcher...")
        await self.stop()
        await self.start()