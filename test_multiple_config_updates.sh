#!/bin/bash

# Test Multiple Configuration Updates
# This script tests if configuration can be updated multiple times without issues

echo "🔧 Testing Multiple Configuration Updates..."

# Start the application
echo "🚀 Starting application..."
docker compose up -d > /dev/null 2>&1

# Wait for startup
echo "⏳ Waiting for application startup..."
sleep 10

# Test configuration multiple times
echo "📋 Testing configuration updates..."

# Function to test config update
test_config_update() {
    local test_num=$1
    local min_rate=$2
    local max_rate=$3
    local ratio=$4
    
    echo "   Test $test_num: min=$min_rate, max=$max_rate, ratio=$ratio"
    
    CONFIG_JSON="{\"minUploadRate\": $min_rate, \"maxUploadRate\": $max_rate, \"uploadRatioTarget\": $ratio, \"seedingDurationLimit\": -1, \"simultaneousSeed\": 20, \"client\": \"qbittorrent-4.6.0.client\", \"keepTorrentWithZeroLeechers\": true}"
    
    RESPONSE=$(curl -s -X PUT "http://localhost:8080/api/config" \
      -H "Content-Type: application/json" \
      -H "X-API-Token: test123" \
      -d "$CONFIG_JSON" 2>&1)
    
    if echo "$RESPONSE" | grep -q "successfully\|message" && ! echo "$RESPONSE" | grep -q "error\|failed\|Failed"; then
        echo "   ✅ Update $test_num successful"
        
        # Verify the config was saved
        SAVED_CONFIG=$(curl -s "http://localhost:8080/api/config" -H "X-API-Token: test123" 2>&1)
        if echo "$SAVED_CONFIG" | grep -q "\"minUploadRate\": $min_rate"; then
            echo "   ✅ Config persisted correctly"
            return 0
        else
            echo "   ❌ Config not persisted: $SAVED_CONFIG"
            return 1
        fi
    else
        echo "   ❌ Update $test_num failed: $RESPONSE"
        return 1
    fi
}

# Test multiple configuration updates
test_config_update 1 30 160 -1.0 || exit 1
sleep 2
test_config_update 2 50 200 2.0 || exit 1  
sleep 2
test_config_update 3 40 180 -1.0 || exit 1
sleep 2
test_config_update 4 60 250 1.5 || exit 1
sleep 2
test_config_update 5 35 150 -1.0 || exit 1

echo ""
echo "🔍 Checking application logs for errors..."
docker logs pyjoal --since 2m | tail -20

echo ""
echo "✅ Multiple configuration update test completed!"
echo "🧹 Cleaning up..."
docker compose down > /dev/null 2>&1