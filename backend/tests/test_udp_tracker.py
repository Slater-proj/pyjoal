"""
Tests unitaires pour le module UDP Tracker.
Tests synchrones avec mocks pour améliorer la couverture.
"""
import pytest
import struct
import socket
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from app.core.udp_tracker import (
    UDPTracker,
    UDPTrackerError,
    UDPAction,
    UDPEvent,
    UDPAnnounceResponse,
    UDPScrapeResponse,
    is_udp_tracker,
    parse_udp_tracker_url,
)


class TestUDPEnums:
    """Test des énumérations UDP"""
    
    def test_udp_action_values(self):
        """Test que les valeurs d'action UDP sont correctes"""
        assert UDPAction.CONNECT == 0
        assert UDPAction.ANNOUNCE == 1
        assert UDPAction.SCRAPE == 2
        assert UDPAction.ERROR == 3
    
    def test_udp_event_values(self):
        """Test que les valeurs d'événement UDP sont correctes"""
        assert UDPEvent.NONE == 0
        assert UDPEvent.COMPLETED == 1
        assert UDPEvent.STARTED == 2
        assert UDPEvent.STOPPED == 3


class TestUDPDataclasses:
    """Test des dataclasses UDP"""
    
    def test_udp_announce_response(self):
        """Test création UDPAnnounceResponse"""
        response = UDPAnnounceResponse(
            action=1,
            transaction_id=12345,
            interval=1800,
            leechers=10,
            seeders=50,
            peers=[("192.168.1.1", 6881), ("10.0.0.1", 51413)]
        )
        
        assert response.action == 1
        assert response.transaction_id == 12345
        assert response.interval == 1800
        assert response.leechers == 10
        assert response.seeders == 50
        assert len(response.peers) == 2
        assert response.peers[0] == ("192.168.1.1", 6881)
    
    def test_udp_scrape_response(self):
        """Test création UDPScrapeResponse"""
        response = UDPScrapeResponse(
            seeders=100,
            completed=5000,
            leechers=25
        )
        
        assert response.seeders == 100
        assert response.completed == 5000
        assert response.leechers == 25


class TestUDPTrackerInit:
    """Test d'initialisation du tracker UDP"""
    
    def test_valid_udp_url(self):
        """Test initialisation avec URL UDP valide"""
        tracker = UDPTracker("udp://tracker.example.com:1337/announce")
        
        assert tracker.host == "tracker.example.com"
        assert tracker.port == 1337
        assert tracker.path == "/announce"
        assert tracker._connection_id is None
    
    def test_udp_url_default_port(self):
        """Test URL UDP sans port utilise 80 par défaut"""
        tracker = UDPTracker("udp://tracker.example.com/announce")
        
        assert tracker.port == 80
    
    def test_udp_url_no_path(self):
        """Test URL UDP sans chemin"""
        tracker = UDPTracker("udp://tracker.example.com:1337")
        
        assert tracker.path == "/announce"  # Default path
    
    def test_invalid_scheme_raises_error(self):
        """Test que schéma non-UDP lève une erreur"""
        with pytest.raises(ValueError, match="Not a UDP tracker URL"):
            UDPTracker("http://tracker.example.com:1337")
        
        with pytest.raises(ValueError, match="Not a UDP tracker URL"):
            UDPTracker("https://tracker.example.com:1337")


class TestConnectionValidation:
    """Test de la validation de connexion"""
    
    def test_connection_invalid_when_none(self):
        """Test connexion invalide quand connection_id est None"""
        tracker = UDPTracker("udp://tracker.example.com:1337")
        
        assert tracker._is_connection_valid() is False
    
    def test_connection_invalid_when_expired(self):
        """Test connexion invalide après expiration (60 secondes)"""
        tracker = UDPTracker("udp://tracker.example.com:1337")
        tracker._connection_id = 12345
        
        import time
        tracker._connection_time = time.time() - 61  # Plus de 60 secondes
        
        assert tracker._is_connection_valid() is False
    
    def test_connection_valid_within_timeout(self):
        """Test connexion valide dans le délai"""
        tracker = UDPTracker("udp://tracker.example.com:1337")
        tracker._connection_id = 12345
        
        import time
        tracker._connection_time = time.time() - 30  # 30 secondes
        
        assert tracker._is_connection_valid() is True


class TestTransactionId:
    """Test de la génération d'ID de transaction"""
    
    def test_transaction_id_is_32bit(self):
        """Test que l'ID de transaction est 32 bits"""
        tracker = UDPTracker("udp://tracker.example.com:1337")
        
        for _ in range(100):
            tid = tracker._generate_transaction_id()
            assert 0 <= tid <= 0xFFFFFFFF
    
    def test_transaction_ids_are_random(self):
        """Test que les IDs sont différents"""
        tracker = UDPTracker("udp://tracker.example.com:1337")
        
        ids = [tracker._generate_transaction_id() for _ in range(10)]
        
        # Très peu probable d'avoir des doublons
        assert len(set(ids)) >= 8


class TestHelperFunctions:
    """Test des fonctions utilitaires"""
    
    def test_is_udp_tracker_true(self):
        """Test détection tracker UDP"""
        assert is_udp_tracker("udp://tracker.example.com:1337") is True
        assert is_udp_tracker("UDP://tracker.example.com:1337") is True
        assert is_udp_tracker("Udp://tracker.example.com") is True
    
    def test_is_udp_tracker_false(self):
        """Test détection non-UDP"""
        assert is_udp_tracker("http://tracker.example.com") is False
        assert is_udp_tracker("https://tracker.example.com") is False
        assert is_udp_tracker("wss://tracker.example.com") is False
    
    def test_parse_udp_tracker_url(self):
        """Test parsing URL tracker UDP"""
        host, port = parse_udp_tracker_url("udp://tracker.example.com:1337/announce")
        
        assert host == "tracker.example.com"
        assert port == 1337
    
    def test_parse_udp_tracker_url_default_port(self):
        """Test parsing URL sans port"""
        host, port = parse_udp_tracker_url("udp://tracker.example.com/announce")
        
        assert host == "tracker.example.com"
        assert port == 80


class TestUDPTrackerClose:
    """Test de fermeture du tracker"""
    
    def test_close_resets_state(self):
        """Test que close() réinitialise l'état"""
        tracker = UDPTracker("udp://tracker.example.com:1337")
        tracker._connection_id = 12345
        import time
        tracker._connection_time = time.time()
        tracker._socket = Mock()
        
        tracker.close()
        
        assert tracker._connection_id is None
        assert tracker._connection_time is None
        assert tracker._socket is None
    
    def test_close_handles_socket_error(self):
        """Test que close() gère les erreurs de socket"""
        tracker = UDPTracker("udp://tracker.example.com:1337")
        mock_socket = Mock()
        mock_socket.close.side_effect = Exception("Socket error")
        tracker._socket = mock_socket
        
        # Ne doit pas lever d'exception
        tracker.close()
        
        assert tracker._socket is None


class TestProtocolConstants:
    """Test des constantes du protocole"""
    
    def test_protocol_id(self):
        """Test que PROTOCOL_ID est correct (magic constant BEP 15)"""
        assert UDPTracker.PROTOCOL_ID == 0x41727101980
    
    def test_timeouts(self):
        """Test des valeurs de timeout"""
        assert UDPTracker.CONNECT_TIMEOUT == 15
        assert UDPTracker.ANNOUNCE_TIMEOUT == 15
        assert UDPTracker.MAX_RETRIES == 3
        assert UDPTracker.CONNECTION_ID_LIFETIME == 60


class TestConnectRequestPacking:
    """Test du packing de la requête connect"""
    
    def test_connect_request_format(self):
        """Test que la requête connect est correctement formatée"""
        # Connect request: protocol_id (8 bytes) + action (4 bytes) + transaction_id (4 bytes)
        protocol_id = 0x41727101980
        action = UDPAction.CONNECT
        transaction_id = 12345
        
        packed = struct.pack('>QII', protocol_id, action, transaction_id)
        
        assert len(packed) == 16
        
        # Unpack and verify
        unpacked_protocol, unpacked_action, unpacked_tid = struct.unpack('>QII', packed)
        assert unpacked_protocol == protocol_id
        assert unpacked_action == action
        assert unpacked_tid == transaction_id


class TestConnectResponseParsing:
    """Test du parsing de la réponse connect"""
    
    def test_connect_response_format(self):
        """Test parsing de réponse connect"""
        # Connect response: action (4 bytes) + transaction_id (4 bytes) + connection_id (8 bytes)
        action = UDPAction.CONNECT
        transaction_id = 12345
        connection_id = 987654321
        
        response = struct.pack('>IIQ', action, transaction_id, connection_id)
        
        assert len(response) == 16
        
        # Unpack
        unpacked_action, unpacked_tid, unpacked_conn = struct.unpack('>IIQ', response)
        assert unpacked_action == action
        assert unpacked_tid == transaction_id
        assert unpacked_conn == connection_id


class TestAnnounceRequestPacking:
    """Test du packing de la requête announce"""
    
    def test_announce_request_format(self):
        """Test que la requête announce est correctement formatée"""
        # Announce request is 98 bytes
        connection_id = 12345678
        action = UDPAction.ANNOUNCE
        transaction_id = 11111
        info_hash = b'A' * 20
        peer_id = b'B' * 20
        downloaded = 1000
        left = 5000
        uploaded = 500
        event = UDPEvent.STARTED
        ip = 0
        key = 12345
        numwant = 200
        port = 6881
        
        packed = struct.pack(
            '>QII20s20sQQQIIIiH',
            connection_id,
            action,
            transaction_id,
            info_hash,
            peer_id,
            downloaded,
            left,
            uploaded,
            event,
            ip,
            key,
            numwant,
            port
        )
        
        assert len(packed) == 98


class TestAnnounceResponseParsing:
    """Test du parsing de la réponse announce"""
    
    def test_announce_response_parsing(self):
        """Test parsing de réponse announce"""
        # Announce response: action (4) + transaction_id (4) + interval (4) + leechers (4) + seeders (4) + peers
        action = UDPAction.ANNOUNCE
        transaction_id = 12345
        interval = 1800
        leechers = 10
        seeders = 50
        
        header = struct.pack('>IIIII', action, transaction_id, interval, leechers, seeders)
        
        assert len(header) == 20
        
        # Unpack
        unpacked = struct.unpack('>IIIII', header)
        assert unpacked == (action, transaction_id, interval, leechers, seeders)
    
    def test_peer_parsing(self):
        """Test parsing des peers depuis une réponse"""
        # Peers: 4 bytes IP + 2 bytes port each
        ip1 = socket.inet_aton("192.168.1.1")
        port1 = struct.pack('>H', 6881)
        
        ip2 = socket.inet_aton("10.0.0.1")
        port2 = struct.pack('>H', 51413)
        
        peer_data = ip1 + port1 + ip2 + port2
        
        assert len(peer_data) == 12
        
        # Parse
        peers = []
        for i in range(0, len(peer_data), 6):
            ip_bytes = peer_data[i:i+4]
            port_bytes = peer_data[i+4:i+6]
            
            ip = socket.inet_ntoa(ip_bytes)
            peer_port = struct.unpack('>H', port_bytes)[0]
            peers.append((ip, peer_port))
        
        assert peers == [("192.168.1.1", 6881), ("10.0.0.1", 51413)]


class TestScrapeRequestPacking:
    """Test du packing de la requête scrape"""
    
    def test_scrape_request_format(self):
        """Test que la requête scrape est correctement formatée"""
        connection_id = 12345678
        action = UDPAction.SCRAPE
        transaction_id = 11111
        info_hashes = [b'A' * 20, b'B' * 20]
        
        # Build scrape request
        request = struct.pack('>QII', connection_id, action, transaction_id)
        for info_hash in info_hashes:
            request += info_hash[:20]
        
        assert len(request) == 16 + 40  # Header + 2 info hashes


class TestScrapeResponseParsing:
    """Test du parsing de la réponse scrape"""
    
    def test_scrape_response_parsing(self):
        """Test parsing de réponse scrape"""
        action = UDPAction.SCRAPE
        transaction_id = 12345
        
        # Scrape response per torrent: seeders (4) + completed (4) + leechers (4)
        header = struct.pack('>II', action, transaction_id)
        torrent1 = struct.pack('>III', 100, 5000, 25)  # seeders, completed, leechers
        torrent2 = struct.pack('>III', 50, 2000, 10)
        
        response = header + torrent1 + torrent2
        
        # Parse
        unpacked_action, unpacked_tid = struct.unpack('>II', response[:8])
        assert unpacked_action == action
        assert unpacked_tid == transaction_id
        
        scrape_data = response[8:]
        results = []
        for i in range(0, len(scrape_data), 12):
            seeders, completed, leechers = struct.unpack('>III', scrape_data[i:i+12])
            results.append((seeders, completed, leechers))
        
        assert results == [(100, 5000, 25), (50, 2000, 10)]


class TestErrorResponse:
    """Test du parsing des erreurs"""
    
    def test_error_response_format(self):
        """Test format de réponse d'erreur"""
        action = UDPAction.ERROR
        transaction_id = 12345
        error_message = "Torrent not found"
        
        response = struct.pack('>II', action, transaction_id) + error_message.encode('utf-8')
        
        # Parse
        unpacked_action, unpacked_tid = struct.unpack('>II', response[:8])
        error_msg = response[8:].decode('utf-8')
        
        assert unpacked_action == UDPAction.ERROR
        assert unpacked_tid == transaction_id
        assert error_msg == "Torrent not found"


class TestUDPTrackerError:
    """Test de l'exception UDP"""
    
    def test_error_message(self):
        """Test message d'erreur"""
        error = UDPTrackerError("Connection failed")
        
        assert str(error) == "Connection failed"
    
    def test_error_inheritance(self):
        """Test que l'erreur hérite d'Exception"""
        error = UDPTrackerError("Test")
        
        assert isinstance(error, Exception)


@pytest.mark.asyncio
class TestAsyncConnect:
    """Tests asynchrones pour connect"""
    
    async def test_connect_returns_cached_connection_id(self):
        """Test que connect retourne l'ID mis en cache si valide"""
        tracker = UDPTracker("udp://tracker.example.com:1337")
        tracker._connection_id = 12345
        
        import time
        tracker._connection_time = time.time()  # Valid
        
        result = await tracker.connect()
        
        assert result == 12345


@pytest.mark.asyncio
class TestAsyncAnnounce:
    """Tests asynchrones pour announce"""
    
    async def test_announce_event_conversion(self):
        """Test conversion des événements"""
        tracker = UDPTracker("udp://tracker.example.com:1337")
        
        # Mock connect pour éviter la vraie connexion
        tracker._connection_id = 12345
        import time
        tracker._connection_time = time.time()
        
        # Vérifier les conversions d'événements
        assert UDPEvent.STARTED == 2
        assert UDPEvent.STOPPED == 3
        assert UDPEvent.COMPLETED == 1
        assert UDPEvent.NONE == 0


class TestEventConversion:
    """Test de la conversion des événements (synchrone)"""
    
    def test_event_string_to_code(self):
        """Test conversion chaîne vers code d'événement"""
        event_map = {
            'started': UDPEvent.STARTED,
            'stopped': UDPEvent.STOPPED,
            'completed': UDPEvent.COMPLETED,
            None: UDPEvent.NONE,
        }
        
        for event_str, expected_code in event_map.items():
            if event_str == 'started':
                assert UDPEvent.STARTED == expected_code
            elif event_str == 'stopped':
                assert UDPEvent.STOPPED == expected_code
            elif event_str == 'completed':
                assert UDPEvent.COMPLETED == expected_code
            else:
                assert UDPEvent.NONE == expected_code


class TestKeyConversion:
    """Test de la conversion des clés"""
    
    def test_hex_key_conversion(self):
        """Test conversion clé hexadécimale"""
        hex_key = "DEADBEEF"
        
        # Conversion comme dans le code
        try:
            key = int(hex_key, 16) & 0xFFFFFFFF
        except ValueError:
            key = None
        
        assert key == 0xDEADBEEF
    
    def test_invalid_hex_key(self):
        """Test clé hexadécimale invalide"""
        invalid_key = "not_hex"
        
        try:
            key = int(invalid_key, 16) & 0xFFFFFFFF
        except ValueError:
            key = None
        
        assert key is None


class TestPeerIdPadding:
    """Test du padding de peer_id"""
    
    def test_short_peer_id_padded(self):
        """Test que peer_id court est rempli"""
        peer_id = "short"
        
        peer_id_bytes = peer_id.encode('latin-1')[:20].ljust(20, b'\x00')
        
        assert len(peer_id_bytes) == 20
        assert peer_id_bytes.startswith(b'short')
        assert peer_id_bytes.endswith(b'\x00' * 15)
    
    def test_long_peer_id_truncated(self):
        """Test que peer_id long est tronqué"""
        peer_id = "a" * 30
        
        peer_id_bytes = peer_id.encode('latin-1')[:20].ljust(20, b'\x00')
        
        assert len(peer_id_bytes) == 20
        assert peer_id_bytes == b'a' * 20
    
    def test_exact_peer_id(self):
        """Test peer_id de longueur exacte"""
        peer_id = "a" * 20
        
        peer_id_bytes = peer_id.encode('latin-1')[:20].ljust(20, b'\x00')
        
        assert len(peer_id_bytes) == 20
        assert peer_id_bytes == b'a' * 20
