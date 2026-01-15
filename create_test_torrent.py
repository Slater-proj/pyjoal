#!/usr/bin/env python3
"""
Create a simple test torrent file for testing PyJOAL
"""

import bencodepy
import hashlib
import os

def create_test_torrent():
    # Create a simple torrent structure
    torrent_data = {
        b'announce': b'http://tracker.example.com:8080/announce',
        b'info': {
            b'name': b'test-file.txt',
            b'piece length': 32768,  # 32KB pieces
            b'length': 1024*1024,    # 1MB file
            b'pieces': b'0' * 20,    # Fake pieces hash
        }
    }
    
    # Encode to bencode
    encoded = bencodepy.encode(torrent_data)
    
    # Save to file
    with open('torrents/test-upload-speed.torrent', 'wb') as f:
        f.write(encoded)
    
    print("✅ Created test-upload-speed.torrent")

if __name__ == '__main__':
    create_test_torrent()