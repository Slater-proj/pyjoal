#!/bin/bash
set -e

echo "🚀 Starting PyJOAL..."
echo ""

# Update BitTorrent client definitions
echo "🔄 Updating BitTorrent client definitions..."
python /app/scripts/update_clients.py || echo "⚠️  Warning: Failed to update clients, continuing with existing"

echo ""

# Verify clients directory
CLIENT_COUNT=$(ls -1 /app/clients/*.client 2>/dev/null | wc -l)
if [ "$CLIENT_COUNT" -eq 0 ]; then
    echo "❌ ERROR: No .client files found!"
    echo "   This should not happen. Please check volume mounting."
    exit 1
fi

echo "✅ Found $CLIENT_COUNT client definition(s)"
ls -1 /app/clients/*.client | sed 's|^/app/clients/|   • |'
echo ""

# Start the application
echo "🎬 Starting FastAPI application..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
