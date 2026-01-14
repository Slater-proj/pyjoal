#!/bin/bash
# Test script to simulate Docker client update behavior

echo "🧪 Testing Docker client update flow..."
echo ""

# Simulate docker-entrypoint.sh behavior
echo "1️⃣ Running update_clients.py..."
python update_clients.py

echo ""
echo "2️⃣ Checking generated clients..."
CLIENT_COUNT=$(ls -1 clients/*.client 2>/dev/null | wc -l)

if [ "$CLIENT_COUNT" -eq 0 ]; then
    echo "❌ ERROR: No .client files found!"
    exit 1
fi

echo "✅ Found $CLIENT_COUNT client definition(s):"
ls -1 clients/*.client | sed 's|^clients/|   • |'

echo ""
echo "3️⃣ Verifying clients are accessible..."
for client in clients/*.client; do
    if [ -r "$client" ]; then
        name=$(basename "$client")
        size=$(stat -f%z "$client" 2>/dev/null || stat -c%s "$client" 2>/dev/null)
        echo "   ✓ $name ($size bytes)"
    else
        echo "   ✗ $name (not readable)"
    fi
done

echo ""
echo "✅ Test completed successfully!"
