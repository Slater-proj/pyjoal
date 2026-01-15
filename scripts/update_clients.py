#!/usr/bin/env python3
"""
Client updater for PyJOAL.
Downloads the latest client definitions from the original java PyJOAL repository.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

# GitHub repository containing client definitions
REPO_URL = "https://api.github.com/repos/anthonyraymond/joal/contents/src/main/resources/client"
CLIENT_DIR = Path("./clients")

def download_file(url: str, dest_path: Path) -> bool:
    """Download a file from URL to destination path."""
    try:
        print(f"Downloading {dest_path.name}...")
        with urllib.request.urlopen(url) as response:
            content = response.read().decode('utf-8')
        
        with open(dest_path, 'w') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Error downloading {dest_path.name}: {e}")
        return False

def update_clients():
    """Update client definitions from GitHub repository."""
    try:
        # Ensure clients directory exists
        CLIENT_DIR.mkdir(exist_ok=True)
        
        print("Fetching client list from GitHub...")
        with urllib.request.urlopen(REPO_URL) as response:
            files_data = json.loads(response.read().decode('utf-8'))
        
        # Filter for .client files
        client_files = [f for f in files_data if f['name'].endswith('.client')]
        
        if not client_files:
            print("No client files found in repository")
            return False
        
        print(f"Found {len(client_files)} client files")
        
        success_count = 0
        for file_info in client_files:
            file_name = file_info['name']
            download_url = file_info['download_url']
            dest_path = CLIENT_DIR / file_name
            
            if download_file(download_url, dest_path):
                success_count += 1
        
        print(f"\nSuccessfully updated {success_count}/{len(client_files)} client files")
        return success_count > 0
        
    except Exception as e:
        print(f"Error updating clients: {e}")
        return False

if __name__ == "__main__":
    print("🔄 Updating PyJOAL client definitions...")
    
    if update_clients():
        print("✅ Client update completed successfully")
        sys.exit(0)
    else:
        print("⚠️  Client update failed, using existing files")
        sys.exit(0)  # Don't fail the container if update fails