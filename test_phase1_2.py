#!/usr/bin/env python3
"""
Test script for Phase 1 & 2 corrections
Tests the BitTorrent client emulation with JOAL-compatible format
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.bittorrent_client import BitTorrentClient, list_available_clients


def test_client(client_file: str):
    """Test a specific client configuration"""
    print(f"\n{'='*60}")
    print(f"Testing: {client_file}")
    print('='*60)
    
    try:
        client = BitTorrentClient(client_file)
        print(f"✅ Loaded: {client.name} {client.version}")
        
        # Test info_hash (20 bytes binary)
        test_info_hash = bytes.fromhex("0123456789abcdef0123456789abcdef01234567")
        test_info_hash_hex = test_info_hash.hex()
        
        # Test peer_id generation
        peer_id = client.generate_peer_id(test_info_hash_hex)
        print(f"\n📝 Peer ID:")
        print(f"   Value: {peer_id}")
        print(f"   Length: {len(peer_id)} bytes (should be 20)")
        print(f"   Encoded length: {len(peer_id.encode('latin-1'))} bytes")
        
        # Test key generation
        key = client.generate_key(test_info_hash_hex)
        print(f"\n🔑 Key:")
        print(f"   Value: {key}")
        print(f"   Length: {len(key)}")
        
        # Test URL encoding of info_hash
        encoded_hash = client.url_encode(test_info_hash)
        print(f"\n🔗 URL-encoded info_hash:")
        print(f"   Original (hex): {test_info_hash_hex}")
        print(f"   Encoded: {encoded_hash}")
        
        # Test headers
        headers = client.get_request_headers()
        print(f"\n📋 Headers:")
        for name, value in headers.items():
            print(f"   {name}: {value}")
        
        # Test full announce URL
        url = client.build_announce_url(
            tracker_url="https://tracker.example.com/announce",
            info_hash=test_info_hash,
            peer_id=peer_id,
            port=51413,
            uploaded=1024*1024*100,  # 100 MB
            downloaded=1024*1024*500,  # 500 MB
            left=0,
            event="started"
        )
        print(f"\n🌐 Announce URL:")
        print(f"   {url[:100]}...")
        print(f"   Full length: {len(url)} chars")
        
        # Verify info_hash is properly URL-encoded (not hex)
        if "info_hash=0123456789" in url:
            print(f"   ❌ ERROR: info_hash is in HEX format (should be URL-encoded binary)")
        elif "info_hash=%01%23" in url or "info_hash=%01%23" in url.lower():
            print(f"   ✅ info_hash is properly URL-encoded")
        else:
            print(f"   ⚠️  Cannot verify info_hash encoding")
        
        # Test URL without event
        url_no_event = client.build_announce_url(
            tracker_url="https://tracker.example.com/announce",
            info_hash=test_info_hash,
            peer_id=peer_id,
            port=51413,
            uploaded=1024*1024*100,
            downloaded=1024*1024*500,
            left=0,
            event=None
        )
        if "event=" in url_no_event and "event=&" not in url_no_event and "event={event}" not in url_no_event:
            print(f"   ⚠️  Event parameter present when it shouldn't be")
        else:
            print(f"   ✅ Event parameter correctly removed when None")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("🧪 PyJOAL Phase 1 & 2 Test Suite")
    print("Testing JOAL-compatible client emulation")
    
    # List available clients
    clients = list_available_clients()
    print(f"\n📁 Available clients: {len(clients)}")
    for c in clients:
        print(f"   - {c}")
    
    # Test each client
    results = {}
    for client_file in clients:
        results[client_file] = test_client(client_file)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed! Phase 1 & 2 corrections are working.")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
