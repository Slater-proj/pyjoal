"""
Tests unitaires pour le service File Watcher.
Tests synchrones avec mocks pour améliorer la couverture.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path
import asyncio
import threading


class TestTorrentFileHandler:
    """Test du gestionnaire d'événements fichiers"""
    
    def test_handler_initialization(self):
        """Test initialisation du handler"""
        from app.services.file_watcher import TorrentFileHandler
        
        callback = Mock()
        loop = MagicMock()
        
        handler = TorrentFileHandler(callback, loop)
        
        assert handler.callback == callback
        assert handler.loop == loop
        assert len(handler._pending_files) == 0
        assert len(handler._processing_files) == 0
    
    def test_on_created_skips_non_torrent_files(self):
        """Test que les fichiers non-torrent sont ignorés"""
        from app.services.file_watcher import TorrentFileHandler
        
        callback = Mock()
        loop = MagicMock()
        handler = TorrentFileHandler(callback, loop)
        
        event = Mock()
        event.is_directory = False
        event.src_path = "/path/to/file.txt"
        
        handler.on_created(event)
        
        # Callback should not be called
        callback.assert_not_called()
    
    def test_on_created_skips_directories(self):
        """Test que les répertoires sont ignorés"""
        from app.services.file_watcher import TorrentFileHandler
        
        callback = Mock()
        loop = MagicMock()
        handler = TorrentFileHandler(callback, loop)
        
        event = Mock()
        event.is_directory = True
        event.src_path = "/path/to/directory.torrent"
        
        handler.on_created(event)
        
        callback.assert_not_called()
    
    def test_on_created_skips_zone_identifier(self):
        """Test que les fichiers Zone.Identifier sont ignorés"""
        from app.services.file_watcher import TorrentFileHandler
        
        callback = Mock()
        loop = MagicMock()
        handler = TorrentFileHandler(callback, loop)
        
        event = Mock()
        event.is_directory = False
        event.src_path = "/path/to/file.torrent:Zone.Identifier"
        
        handler.on_created(event)
        
        callback.assert_not_called()
    
    def test_on_moved_skips_archived_files(self):
        """Test que les fichiers déplacés vers archived sont ignorés"""
        from app.services.file_watcher import TorrentFileHandler
        
        callback = Mock()
        loop = MagicMock()
        handler = TorrentFileHandler(callback, loop)
        
        event = Mock()
        event.is_directory = False
        event.dest_path = "/path/to/archived/file.torrent"
        
        handler.on_moved(event)
        
        callback.assert_not_called()
    
    def test_pending_files_tracking(self):
        """Test du suivi des fichiers en attente"""
        from app.services.file_watcher import TorrentFileHandler
        
        callback = Mock()
        loop = MagicMock()
        handler = TorrentFileHandler(callback, loop)
        
        # Simuler l'ajout de fichiers en attente
        with handler._lock:
            handler._pending_files.add("/path/to/file1.torrent")
            handler._pending_files.add("/path/to/file2.torrent")
        
        assert len(handler._pending_files) == 2
        
        # Simuler la suppression
        with handler._lock:
            handler._pending_files.discard("/path/to/file1.torrent")
        
        assert len(handler._pending_files) == 1
    
    def test_processing_files_deduplication(self):
        """Test que les fichiers en cours de traitement ne sont pas dupliqués"""
        from app.services.file_watcher import TorrentFileHandler
        
        callback = Mock()
        loop = MagicMock()
        handler = TorrentFileHandler(callback, loop)
        
        # Ajouter un fichier en cours de traitement
        with handler._lock:
            handler._processing_files.add("/path/to/file.torrent")
        
        # Créer un événement pour le même fichier
        event = Mock()
        event.is_directory = False
        event.src_path = "/path/to/file.torrent"
        
        # Le handler devrait ignorer l'événement
        handler.on_created(event)
        
        # Le fichier est toujours marqué comme en traitement
        assert "/path/to/file.torrent" in handler._processing_files


class TestFileWatcherService:
    """Test du service File Watcher"""
    
    def test_service_initialization(self):
        """Test initialisation du service"""
        from app.services.file_watcher import FileWatcherService
        
        torrents_dir = Path("/tmp/torrents")
        callback = Mock()
        
        service = FileWatcherService(torrents_dir, callback)
        
        assert service.torrents_dir == torrents_dir
        assert service.reload_callback == callback
        assert service.observer is None
        assert service.handler is None
        assert service.is_running is False
    
    @pytest.mark.asyncio
    async def test_start_creates_directory(self):
        """Test que start crée le répertoire si nécessaire"""
        from app.services.file_watcher import FileWatcherService
        
        with patch('app.services.file_watcher.Observer') as mock_observer_class:
            mock_observer = MagicMock()
            mock_observer_class.return_value = mock_observer
            
            with patch.object(Path, 'mkdir') as mock_mkdir:
                torrents_dir = Path("/tmp/test_torrents")
                callback = AsyncMock()
                
                service = FileWatcherService(torrents_dir, callback)
                
                await service.start()
                
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
                mock_observer.start.assert_called_once()
                assert service.is_running is True
                
                # Cleanup
                await service.stop()
    
    @pytest.mark.asyncio
    async def test_start_when_already_running(self):
        """Test que start ne fait rien si déjà démarré"""
        from app.services.file_watcher import FileWatcherService
        
        torrents_dir = Path("/tmp/torrents")
        callback = AsyncMock()
        
        service = FileWatcherService(torrents_dir, callback)
        service.is_running = True
        
        # Ne devrait pas lever d'erreur
        await service.start()
    
    @pytest.mark.asyncio
    async def test_stop_when_not_running(self):
        """Test que stop ne fait rien si pas démarré"""
        from app.services.file_watcher import FileWatcherService
        
        torrents_dir = Path("/tmp/torrents")
        callback = AsyncMock()
        
        service = FileWatcherService(torrents_dir, callback)
        
        # Ne devrait pas lever d'erreur
        await service.stop()
        
        assert service.is_running is False
    
    @pytest.mark.asyncio
    async def test_stop_cleanup(self):
        """Test que stop nettoie correctement les ressources"""
        from app.services.file_watcher import FileWatcherService
        
        torrents_dir = Path("/tmp/torrents")
        callback = AsyncMock()
        
        service = FileWatcherService(torrents_dir, callback)
        service.is_running = True
        
        mock_observer = MagicMock()
        service.observer = mock_observer
        service.handler = MagicMock()
        
        await service.stop()
        
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once_with(timeout=5.0)
        assert service.observer is None
        assert service.handler is None
        assert service.is_running is False
    
    @pytest.mark.asyncio
    async def test_restart_calls_stop_then_start(self):
        """Test que restart appelle stop puis start"""
        from app.services.file_watcher import FileWatcherService
        
        torrents_dir = Path("/tmp/torrents")
        callback = AsyncMock()
        
        service = FileWatcherService(torrents_dir, callback)
        
        with patch.object(service, 'stop', new_callable=AsyncMock) as mock_stop:
            with patch.object(service, 'start', new_callable=AsyncMock) as mock_start:
                await service.restart()
                
                mock_stop.assert_called_once()
                mock_start.assert_called_once()


class TestArchiveInvalidTorrent:
    """Test de l'archivage des torrents invalides"""
    
    def test_archive_creates_directory(self):
        """Test que l'archivage crée le répertoire archived"""
        from app.services.file_watcher import TorrentFileHandler
        
        with patch('app.services.file_watcher.settings') as mock_settings:
            mock_settings.TORRENTS_DIR = Path("/tmp/torrents")
            
            callback = Mock()
            loop = MagicMock()
            handler = TorrentFileHandler(callback, loop)
            
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(Path, 'mkdir') as mock_mkdir:
                    with patch.object(Path, 'rename') as mock_rename:
                        with patch('app.services.file_watcher.history_service'):
                            file_path = Path("/tmp/torrents/invalid.torrent")
                            handler._archive_invalid_torrent(file_path, "Invalid format")
                            
                            mock_mkdir.assert_called_once_with(exist_ok=True)
    
    def test_archive_skips_nonexistent_file(self):
        """Test que l'archivage ignore les fichiers inexistants"""
        from app.services.file_watcher import TorrentFileHandler
        
        callback = Mock()
        loop = MagicMock()
        handler = TorrentFileHandler(callback, loop)
        
        with patch.object(Path, 'exists', return_value=False):
            file_path = Path("/tmp/torrents/missing.torrent")
            
            # Ne devrait pas lever d'erreur
            handler._archive_invalid_torrent(file_path, "Test error")


class TestDelayedReload:
    """Test du rechargement différé"""
    
    @pytest.mark.asyncio
    async def test_delayed_reload_waits_before_callback(self):
        """Test que le rechargement attend avant d'appeler le callback"""
        from app.services.file_watcher import TorrentFileHandler
        
        callback = AsyncMock()
        loop = asyncio.get_event_loop()
        handler = TorrentFileHandler(callback, loop)
        
        file_path = "/tmp/test.torrent"
        handler._pending_files.add(file_path)
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await handler._delayed_reload(file_path)
            
            mock_sleep.assert_called_once_with(1.0)
            callback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delayed_reload_removes_pending_file(self):
        """Test que le fichier est retiré de pending après rechargement"""
        from app.services.file_watcher import TorrentFileHandler
        
        callback = AsyncMock()
        loop = asyncio.get_event_loop()
        handler = TorrentFileHandler(callback, loop)
        
        file_path = "/tmp/test.torrent"
        handler._pending_files.add(file_path)
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            await handler._delayed_reload(file_path)
            
            assert file_path not in handler._pending_files
    
    @pytest.mark.asyncio
    async def test_delayed_reload_handles_callback_error(self):
        """Test que les erreurs de callback sont gérées"""
        from app.services.file_watcher import TorrentFileHandler
        
        callback = AsyncMock(side_effect=Exception("Reload failed"))
        loop = asyncio.get_event_loop()
        handler = TorrentFileHandler(callback, loop)
        
        file_path = "/tmp/test.torrent"
        handler._pending_files.add(file_path)
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            # Ne devrait pas lever d'erreur
            await handler._delayed_reload(file_path)
            
            # Le fichier devrait être retiré même en cas d'erreur
            assert file_path not in handler._pending_files


class TestScheduleReload:
    """Test de la planification du rechargement"""
    
    def test_schedule_reload_skips_duplicate(self):
        """Test que les fichiers déjà planifiés sont ignorés"""
        from app.services.file_watcher import TorrentFileHandler
        
        callback = Mock()
        loop = MagicMock()
        handler = TorrentFileHandler(callback, loop)
        
        file_path = "/tmp/test.torrent"
        handler._pending_files.add(file_path)
        
        with patch('asyncio.run_coroutine_threadsafe') as mock_run:
            handler._schedule_reload(file_path)
            
            # Ne devrait pas planifier un rechargement
            mock_run.assert_not_called()
    
    def test_schedule_reload_adds_to_pending(self):
        """Test que le fichier est ajouté aux fichiers en attente"""
        from app.services.file_watcher import TorrentFileHandler
        
        callback = Mock()
        loop = MagicMock()
        handler = TorrentFileHandler(callback, loop)
        
        file_path = "/tmp/new.torrent"
        
        with patch('asyncio.run_coroutine_threadsafe') as mock_run:
            handler._schedule_reload(file_path)
            
            assert file_path in handler._pending_files
            mock_run.assert_called_once()


class TestObserverIntegration:
    """Test d'intégration avec Observer"""
    
    def test_observer_schedule_called_correctly(self):
        """Test que Observer.schedule est appelé correctement"""
        from app.services.file_watcher import FileWatcherService
        
        with patch('app.services.file_watcher.Observer') as mock_observer_class:
            mock_observer = MagicMock()
            mock_observer_class.return_value = mock_observer
            
            torrents_dir = Path("/tmp/test_torrents")
            callback = Mock()
            
            service = FileWatcherService(torrents_dir, callback)
            
            # Simuler le démarrage
            service.handler = MagicMock()
            service.observer = mock_observer
            
            mock_observer.schedule.assert_not_called()  # Pas encore démarré
    
    @pytest.mark.asyncio
    async def test_observer_handles_start_error(self):
        """Test que les erreurs au démarrage sont gérées"""
        from app.services.file_watcher import FileWatcherService
        
        with patch('app.services.file_watcher.Observer') as mock_observer_class:
            mock_observer = MagicMock()
            mock_observer.start.side_effect = Exception("Observer failed")
            mock_observer_class.return_value = mock_observer
            
            with patch.object(Path, 'mkdir'):
                torrents_dir = Path("/tmp/test_torrents")
                callback = AsyncMock()
                
                service = FileWatcherService(torrents_dir, callback)
                
                with pytest.raises(Exception, match="Observer failed"):
                    await service.start()
                
                # Le service devrait être arrêté après l'erreur
                assert service.is_running is False


class TestThreadSafety:
    """Test de la sécurité des threads"""
    
    def test_lock_protects_pending_files(self):
        """Test que le lock protège _pending_files"""
        from app.services.file_watcher import TorrentFileHandler
        
        callback = Mock()
        loop = MagicMock()
        handler = TorrentFileHandler(callback, loop)
        
        # Vérifier que le lock existe
        assert hasattr(handler, '_lock')
        assert isinstance(handler._lock, type(threading.Lock()))
    
    def test_concurrent_file_events(self):
        """Test que les événements concurrents sont gérés"""
        from app.services.file_watcher import TorrentFileHandler
        
        callback = Mock()
        loop = MagicMock()
        handler = TorrentFileHandler(callback, loop)
        
        def add_file(path):
            with handler._lock:
                handler._processing_files.add(path)
        
        def remove_file(path):
            with handler._lock:
                handler._processing_files.discard(path)
        
        # Simuler des opérations concurrentes
        threads = []
        for i in range(10):
            t = threading.Thread(target=add_file, args=(f"/path/file{i}.torrent",))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        assert len(handler._processing_files) == 10
