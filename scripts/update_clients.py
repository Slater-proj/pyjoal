#!/usr/bin/env python3
"""
Script to automatically fetch latest BitTorrent client versions
and generate .client files
"""
import json
import re
import requests
from pathlib import Path
from typing import Dict, Optional

# GitHub repositories for each client
CLIENTS = {
    "qbittorrent": {
        "name": "qBittorrent",
        "repo": "qbittorrent/qBittorrent",
        "peer_id_format": lambda v: f"-qB{v.replace('.', '')[:4].ljust(4, '0')}-",
        "user_agent_format": lambda v: f"qBittorrent/{v}",
        "numwant": 200,
        "headers": {"Accept-Encoding": "gzip"}
    },
    "deluge": {
        "name": "Deluge",
        "repo": "deluge-torrent/deluge",
        "peer_id_format": lambda v: f"-DE{v.replace('.', '')[:3].ljust(3, '0')}s-",
        "user_agent_format": lambda v: f"Deluge {v}",
        "numwant": 200,
        "headers": {"Accept-Encoding": "gzip, deflate"}
    },
    "transmission": {
        "name": "Transmission",
        "repo": "transmission/transmission",
        "peer_id_format": lambda v: f"-TR{v.replace('.', '')[:3].ljust(3, '0')}Z-",
        "user_agent_format": lambda v: f"Transmission/{v}",
        "numwant": 80,
        "headers": {"Accept-Encoding": "gzip"}
    }
}

def get_latest_release(repo: str) -> Optional[str]:
    """Get latest release version from GitHub"""
    try:
        # Try latest release first
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 404:
            # No releases, try tags instead
            url = f"https://api.github.com/repos/{repo}/tags"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            tags = response.json()
            
            if not tags:
                return None
                
            # Get first tag (most recent)
            version = tags[0].get('name', '').lstrip('v')
        else:
            response.raise_for_status()
            data = response.json()
            version = data.get('tag_name', '').lstrip('v')
        
        # Clean up version string (e.g., "release-4.0.5" -> "4.0.5")
        version = re.sub(r'^release[-_]', '', version)
        version = re.sub(r'^v\.', '', version)  # Remove 'v.' prefix
        version = re.sub(r'^deluge-', '', version)  # Remove 'deluge-' prefix
        version = re.sub(r'\.dev\d+$', '', version)  # Remove .dev suffix
        
        # Validate version format (x.y.z or x.y)
        if not re.match(r'^\d+\.\d+', version):
            print(f"   ⚠️  Invalid version format: {version}")
            return None
            
        return version
    except Exception as e:
        print(f"❌ Failed to fetch {repo}: {e}")
        return None

def generate_client_file(client_key: str, version: str, output_dir: Path):
    """Generate a .client file for the given client and version"""
    client_config = CLIENTS[client_key]
    
    # Generate JOAL-compatible client configuration
    if client_key == "qbittorrent":
        # qBittorrent format
        version_code = version.replace('.', '')[:4].ljust(4, '0')
        client_data = {
            "name": client_config["name"],
            "version": version,
            "keyGenerator": {
                "algorithm": {
                    "type": "HASH_NO_LEADING_ZERO",
                    "length": 8
                },
                "refreshOn": "TORRENT_PERSISTENT",
                "keyCase": "upper"
            },
            "peerIdGenerator": {
                "algorithm": {
                    "type": "REGEX",
                    "pattern": f"-qB{version_code}-[A-Za-z0-9_~\\(\\)\\!\\.\\*-]{{12}}"
                },
                "refreshOn": "NEVER",
                "shouldUrlEncode": False
            },
            "urlEncoder": {
                "encodingExclusionPattern": "[A-Za-z0-9_~\\(\\)\\!\\.\\*-]",
                "encodedHexCase": "lower"
            },
            "query": "info_hash={infohash}&peer_id={peerid}&port={port}&uploaded={uploaded}&downloaded={downloaded}&left={left}&corrupt=0&key={key}&event={event}&numwant={numwant}&compact=1&no_peer_id=1&supportcrypto=1&redundant=0",
            "numwant": 200,
            "numwantOnStop": 0,
            "requestHeaders": [
                {"name": "User-Agent", "value": f"qBittorrent/{version}"},
                {"name": "Accept-Encoding", "value": "gzip"},
                {"name": "Connection", "value": "close"}
            ]
        }
    elif client_key == "deluge":
        # Deluge format
        version_code = version.replace('.', '')[:3].ljust(3, '0')
        client_data = {
            "name": client_config["name"],
            "version": version,
            "keyGenerator": {
                "algorithm": {
                    "type": "HASH",
                    "length": 8
                },
                "refreshOn": "TORRENT_PERSISTENT",
                "keyCase": "upper"
            },
            "peerIdGenerator": {
                "algorithm": {
                    "type": "REGEX",
                    "pattern": f"-DE{version_code}s-[A-Za-z0-9]{{12}}"
                },
                "refreshOn": "NEVER",
                "shouldUrlEncode": False
            },
            "urlEncoder": {
                "encodingExclusionPattern": "[A-Za-z0-9_~\\(\\)\\!\\.\\*-]",
                "encodedHexCase": "lower"
            },
            "query": "info_hash={infohash}&peer_id={peerid}&port={port}&uploaded={uploaded}&downloaded={downloaded}&left={left}&key={key}&event={event}&numwant={numwant}&compact=1&no_peer_id=1&supportcrypto=1",
            "numwant": 200,
            "numwantOnStop": 0,
            "requestHeaders": [
                {"name": "User-Agent", "value": f"Deluge {version}"},
                {"name": "Accept-Encoding", "value": "gzip, deflate"},
                {"name": "Connection", "value": "close"}
            ]
        }
    elif client_key == "transmission":
        # Transmission format
        version_code = version.replace('.', '')[:3].ljust(3, '0')
        client_data = {
            "name": client_config["name"],
            "version": version,
            "keyGenerator": {
                "algorithm": {
                    "type": "HASH",
                    "length": 8
                },
                "refreshOn": "NEVER",
                "keyCase": "lower"
            },
            "peerIdGenerator": {
                "algorithm": {
                    "type": "REGEX",
                    "pattern": f"-TR{version_code}Z-[A-Za-z0-9]{{12}}"
                },
                "refreshOn": "NEVER",
                "shouldUrlEncode": False
            },
            "urlEncoder": {
                "encodingExclusionPattern": "[A-Za-z0-9_~\\(\\)\\!\\.\\*-]",
                "encodedHexCase": "upper"
            },
            "query": "info_hash={infohash}&peer_id={peerid}&port={port}&uploaded={uploaded}&downloaded={downloaded}&left={left}&key={key}&event={event}&numwant={numwant}&compact=1&supportcrypto=1",
            "numwant": 80,
            "numwantOnStop": 0,
            "requestHeaders": [
                {"name": "User-Agent", "value": f"Transmission/{version}"},
                {"name": "Accept-Encoding", "value": "gzip"},
                {"name": "Connection", "value": "close"}
            ]
        }
    else:
        raise ValueError(f"Unknown client: {client_key}")
    
    # Create filename
    filename = f"{client_key}-{version}.client"
    filepath = output_dir / filename
    
    # Write to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(client_data, f, indent=4)
        f.write('\n')
    
    print(f"✅ Generated: {filename}")
    return filepath

def main():
    """Main function"""
    print("🔄 Fetching latest BitTorrent client versions...\n")
    
    # Check if running in Docker (looking for mounted volume)
    docker_clients_dir = Path("/app/clients")
    if docker_clients_dir.exists():
        clients_dir = docker_clients_dir
        print(f"📁 Using Docker volume: {clients_dir}")
    else:
        # Get script directory for local execution
        script_dir = Path(__file__).parent
        clients_dir = script_dir.parent / "clients"
        print(f"📁 Using local directory: {clients_dir}")
    
    clients_dir.mkdir(exist_ok=True)
    
    # Get existing client files
    existing_files = {f.stem: f for f in clients_dir.glob("*.client")}
    
    # Track new versions
    new_versions = {}
    
    # Fetch and generate for each client
    for client_key, client_config in CLIENTS.items():
        print(f"📥 Checking {client_config['name']}...")
        
        version = get_latest_release(client_config["repo"])
        if not version:
            print(f"⚠️  Skipping {client_config['name']} (failed to fetch)\n")
            continue
        
        print(f"   Latest version: {version}")
        
        # Check if this version already exists
        expected_name = f"{client_key}-{version}"
        if expected_name in existing_files:
            print(f"   ✓ Already exists\n")
            continue
        
        # Generate new client file
        filepath = generate_client_file(client_key, version, clients_dir)
        new_versions[client_key] = version
        print()
    
    # Summary
    print("\n" + "="*60)
    if new_versions:
        print("✨ New versions generated:")
        for client, version in new_versions.items():
            print(f"   • {CLIENTS[client]['name']}: {version}")
        print("\n💡 Old versions were kept. Delete them manually if needed.")
    else:
        print("✓ All clients are up to date!")
    print("="*60)

if __name__ == "__main__":
    main()