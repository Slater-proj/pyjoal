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
    
    # Generate client data
    client_data = {
        "name": client_config["name"],
        "version": version,
        "peerIdPattern": {
            "prefix": client_config["peer_id_format"](version)
        },
        "userAgent": client_config["user_agent_format"](version),
        "numwant": client_config["numwant"],
        "requestHeaders": client_config["headers"]
    }
    
    # Create filename
    filename = f"{client_key}-{version}.client"
    filepath = output_dir / filename
    
    # Write to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(client_data, f, indent=2)
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