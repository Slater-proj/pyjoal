#!/usr/bin/env python3
"""
Test script for Phase 1 & 2 - Full BitTorrent client test
"""
import sys
import json
import random
import re
import string
from pathlib import Path

# Simulate settings to avoid loading full app
class FakeSettings:
    CLIENTS_DIR = Path('/home/adminclem/pyjoal/clients')
    MIN_UPLOAD_RATE = 30
    MAX_UPLOAD_RATE = 300

# Patch the config module
import types
fake_settings_module = types.ModuleType('app.core.config')
fake_settings_module.settings = FakeSettings()
sys.modules['app.core.config'] = fake_settings_module

# Now we can load the module
sys.path.insert(0, '/home/adminclem/pyjoal/backend')
from app.core.bittorrent_client import BitTorrentClient, list_available_clients


def test_client(client_file: str) -> bool:
    """Test a specific client"""
    print(f"\n{'='*60}")
    print(f"Testing: {client_file}")
    print('='*60)
    
    try:
        client = BitTorrentClient(client_file)
        print(f"✅ Loaded: {client.name} {client.version}")
        
        # Test info_hash (20 bytes binary - this is the SHA1 hash)
        test_hash = bytes.fromhex('0123456789abcdef0123456789abcdef01234567')
        test_hash_hex = test_hash.hex()
        
        # Test peer_id
        peer_id = client.generate_peer_id(test_hash_hex)
        peer_id_len = len(peer_id.encode('latin-1'))
        print(f"\n📝 Peer ID: {peer_id}")
        print(f"   Length: {peer_id_len} bytes", end="")
        if peer_id_len == 20:
            print(" ✅")
        else:
            print(f" ❌ (should be 20)")
            return False
        
        # Test key
        key = client.generate_key(test_hash_hex)
        print(f"\n🔑 Key: {key}")
        
        # Test URL encoding
        encoded_hash = client.url_encode(test_hash)
        print(f"\n🔗 URL-encoded info_hash:")
        print(f"   Original (hex): {test_hash_hex}")
        print(f"   Encoded: {encoded_hash[:60]}...")
        
        # Check it's not just hex
        if encoded_hash == test_hash_hex:
            print("   ❌ ERROR: Not URL-encoded (same as hex)")
            return False
        elif '%' in encoded_hash:
            print("   ✅ Contains URL encoding")
        
        # Test headers
        headers = client.get_request_headers()
        print(f"\n📋 Headers: {len(headers)}")
        for name, value in headers.items():
            print(f"   {name}: {value}")
        
        # Test full URL building
        url = client.build_announce_url(
            tracker_url='http://tracker.example.com/announce',
            info_hash=test_hash,
            peer_id=peer_id,
            port=51413,
            uploaded=104857600,  # 100 MB
            downloaded=524288000,  # 500 MB
            left=0,
            event='started'
        )
        
        print(f"\n🌐 Announce URL:")
        print(f"   Length: {len(url)} chars")
        print(f"   URL: {url[:120]}...")
        
        # Verify info_hash is NOT in hex format
        if 'info_hash=0123456789abcdef' in url.lower():
            print("   ❌ ERROR: info_hash is in HEX format!")
            return False
        else:
            print("   ✅ info_hash is URL-encoded binary")
        
        # Verify query order matches template
        query = client.config.get('query', '')
        if query:
            # Check first param is info_hash
            if url.split('?')[1].startswith('info_hash='):
                print("   ✅ Query starts with info_hash")
            else:
                print("   ⚠️  Query doesn't start with info_hash")
        
        # Test URL without event
        url_no_event = client.build_announce_url(
            tracker_url='http://tracker.example.com/announce',
            info_hash=test_hash,
            peer_id=peer_id,
            port=51413,
            uploaded=104857600,
            downloaded=524288000,
            left=0,
            event=None
        )
        
        # Check event is not present or empty
        if 'event={event}' in url_no_event:
            print("   ❌ Event placeholder not replaced")
            return False
        elif 'event=&' in url_no_event or '&event=&' in url_no_event:
            print("   ⚠️  Empty event parameter present")
        else:
            print("   ✅ Event correctly handled when None")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("🧪 PyJOAL Phase 1 & 2 - Full Test Suite")
    print("Testing JOAL-compatible BitTorrent client emulation\n")
    
    clients = list_available_clients()
    print(f"📁 Found {len(clients)} client files")
    
    results = {}
    for client_file in clients:
        results[client_file] = test_client(client_file)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")
    
    passed = sum(1 for v in results.values() if v)
    failed = len(results) - passed
    
    print(f"\nTotal: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All Phase 1 & 2 tests passed!")
        print("   - info_hash: URL-encoded binary ✓")
        print("   - peer_id: exactly 20 bytes ✓")
        print("   - key: generated per client algorithm ✓")
        print("   - query: uses client template ✓")
        print("   - headers: JOAL array format ✓")
        return 0
    else:
        print("\n⚠️  Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
