#!/bin/bash
set -e
cd /home/clem/pyjoal

VERSION="1.10.2"

# Fix package.json version
sed -i 's/"version": "1.11.0"/"version": "1.10.2"/' frontend/package.json
echo "package.json: $(grep '"version"' frontend/package.json)"

# Fix torrent_manager.py - add peer tier config
python3 << 'PYEOF'
content = open('backend/app/services/torrent_manager.py').read()
old = '                "speed_variation_percent": config.get("speedVariationPercent", settings.SPEED_VARIATION_PERCENT),\n            },'
new = '''                "speed_variation_percent": config.get("speedVariationPercent", settings.SPEED_VARIATION_PERCENT),
                # Peer speed tiers
                "peer_tier1_max_peers": config.get("peerTier1MaxPeers", settings.PEER_TIER1_MAX_PEERS),
                "peer_tier1_speed_percent": config.get("peerTier1SpeedPercent", settings.PEER_TIER1_SPEED_PERCENT),
                "peer_tier2_max_peers": config.get("peerTier2MaxPeers", settings.PEER_TIER2_MAX_PEERS),
                "peer_tier2_speed_percent": config.get("peerTier2SpeedPercent", settings.PEER_TIER2_SPEED_PERCENT),
                "peer_tier3_speed_percent": config.get("peerTier3SpeedPercent", settings.PEER_TIER3_SPEED_PERCENT),
            },'''
if old in content:
    content = content.replace(old, new)
    with open('backend/app/services/torrent_manager.py', 'w') as f:
        f.write(content)
    print("torrent_manager.py: FIXED")
else:
    # Check if already patched
    if "peer_tier1_max_peers" in content:
        print("torrent_manager.py: already patched")
    else:
        print("torrent_manager.py: ERROR - pattern not found")
        # Show context
        import re
        m = re.search(r'speed_variation.*\n.*\},', content)
        if m:
            print(f"Found: {m.group()[:100]}")
PYEOF

# Verify
echo ""
echo "--- Verify ---"
echo "torrent_manager peer_tier count: $(grep -c peer_tier backend/app/services/torrent_manager.py)"
echo "package.json version: $(grep '"version"' frontend/package.json)"

# Clean up
rm -f _commit.sh _apply_backend.sh _fix_ci.sh _release.sh _release2.sh

# Commit fix
git add -A
git diff --cached --stat
git commit -m "fix: correct package.json version and torrent_manager peer tiers" 2>&1
git push origin master 2>&1

echo "=== Fix pushed ==="
