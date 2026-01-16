#!/bin/bash

# Test API Configuration avec nouvelles validations

echo "🧪 Testing Configuration API with new validation..."

# Token from logs  
TOKEN="17bc9cc3781c8116f3bdc6a6aee8a48c"
API_URL="http://localhost:8080/api/config"

echo ""
echo "1️⃣ Testing valid config with 16000 KB/s (should work now):"
RESPONSE1=$(curl -s -X PUT "$API_URL" \
  -H "Content-Type: application/json" \
  -H "X-API-Token: $TOKEN" \
  -d '{"minUploadRate": 30, "maxUploadRate": 16000, "uploadRatioTarget": -1, "seedingDurationLimit": -1, "simultaneousSeed": 20, "client": "deluge-2.2.1.client", "keepTorrentWithZeroLeechers": true}')
echo "Response: $RESPONSE1"

echo ""
echo "2️⃣ Testing invalid config (min > max, should show user-friendly error):"
RESPONSE2=$(curl -s -X PUT "$API_URL" \
  -H "Content-Type: application/json" \
  -H "X-API-Token: $TOKEN" \
  -d '{"minUploadRate": 200, "maxUploadRate": 100, "uploadRatioTarget": -1, "seedingDurationLimit": -1, "simultaneousSeed": 20, "client": "deluge-2.2.1.client", "keepTorrentWithZeroLeechers": true}')
echo "Response: $RESPONSE2"

echo ""
echo "3️⃣ Testing very high value (should show limit error):"
RESPONSE3=$(curl -s -X PUT "$API_URL" \
  -H "Content-Type: application/json" \
  -H "X-API-Token: $TOKEN" \
  -d '{"minUploadRate": 30, "maxUploadRate": 200000, "uploadRatioTarget": -1, "seedingDurationLimit": -1, "simultaneousSeed": 20, "client": "deluge-2.2.1.client", "keepTorrentWithZeroLeechers": true}')
echo "Response: $RESPONSE3"

echo ""
echo "4️⃣ Testing negative values (should show validation error):"
RESPONSE4=$(curl -s -X PUT "$API_URL" \
  -H "Content-Type: application/json" \
  -H "X-API-Token: $TOKEN" \
  -d '{"minUploadRate": -10, "maxUploadRate": 160, "uploadRatioTarget": -1, "seedingDurationLimit": -1, "simultaneousSeed": 20, "client": "deluge-2.2.1.client", "keepTorrentWithZeroLeechers": true}')
echo "Response: $RESPONSE4"

echo ""
echo "✅ Configuration validation tests completed!"