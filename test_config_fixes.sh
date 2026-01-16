#!/bin/bash

# Test Configuration Bug Fixes
# Tests the configuration save and negative value input functionality

echo "🔧 Testing Configuration Fixes..."

# Test 1: Build with new configuration changes
echo "📦 Building application with configuration fixes..."
if docker compose build --no-cache > /dev/null 2>&1; then
    echo "✅ Build successful - no TypeScript/React errors"
else
    echo "❌ Build failed"
    exit 1
fi

# Test 2: Start application
echo "🚀 Starting application..."
if docker compose up -d > /dev/null 2>&1; then
    echo "✅ Application started successfully"
else
    echo "❌ Failed to start application"
    exit 1
fi

# Wait for app to be ready
echo "⏳ Waiting for application to be ready..."
sleep 10

# Test 3: Check if API is responding
if curl -s "http://localhost:8080/api/config" -H "X-API-Token: test123" > /dev/null; then
    echo "✅ API is responding"
else
    echo "❌ API not responding"
    docker compose down > /dev/null 2>&1
    exit 1
fi

# Test 4: Test config update endpoint
echo "🔧 Testing configuration update..."
CONFIG_JSON='{"minUploadRate": 50, "maxUploadRate": 200, "uploadRatioTarget": -1, "seedingDurationLimit": -1, "simultaneousSeed": 25, "client": "qbittorrent-4.6.0.client", "keepTorrentWithZeroLeechers": true}'

RESPONSE=$(curl -s -X PUT "http://localhost:8080/api/config" \
  -H "Content-Type: application/json" \
  -H "X-API-Token: test123" \
  -d "$CONFIG_JSON")

if echo "$RESPONSE" | grep -q "successfully"; then
    echo "✅ Configuration update API working"
else
    echo "❌ Configuration update failed"
    echo "Response: $RESPONSE"
    docker compose down > /dev/null 2>&1
    exit 1
fi

# Test 5: Verify config was saved correctly
echo "📋 Verifying configuration persistence..."
SAVED_CONFIG=$(curl -s "http://localhost:8080/api/config" -H "X-API-Token: test123")

if echo "$SAVED_CONFIG" | grep -q '"minUploadRate": 50' && \
   echo "$SAVED_CONFIG" | grep -q '"maxUploadRate": 200' && \
   echo "$SAVED_CONFIG" | grep -q '"uploadRatioTarget": -1' && \
   echo "$SAVED_CONFIG" | grep -q '"seedingDurationLimit": -1'; then
    echo "✅ Configuration persisted correctly with negative values"
else
    echo "❌ Configuration not saved correctly"
    echo "Saved config: $SAVED_CONFIG"
    docker compose down > /dev/null 2>&1
    exit 1
fi

# Clean up
echo "🧹 Cleaning up..."
docker compose down > /dev/null 2>&1

echo "✅ All configuration tests passed!"
echo ""
echo "🎯 Fixes Validated:"
echo "   • Configuration updates are properly persisted"
echo "   • Negative values (-1) are correctly handled"
echo "   • API endpoints working with new store.updateConfig logic"
echo "   • Docker build successful with all frontend changes"