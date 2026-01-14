#!/bin/bash
# Update BitTorrent client definitions with latest versions

cd "$(dirname "$0")"

echo "🔄 Updating BitTorrent clients to latest versions..."
echo ""

python3 update_clients.py

echo ""
echo "✅ Done! Check the clients/ folder for new .client files"
