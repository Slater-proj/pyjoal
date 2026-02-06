#!/bin/bash
# Version Update Script - PyJOAL
# Usage: ./update_version.sh <new_version>
# Example: ./update_version.sh 1.10.0
#
# This script safely updates the version in:
#   - VERSION (source of truth)
#   - frontend/package.json
#
# It does NOT auto-modify markdown files or CHANGELOG to avoid corruption.
# Update CHANGELOG.md manually before running this script.

set -euo pipefail

if [ -z "${1:-}" ]; then
    echo "❌ Usage: $0 <version>"
    echo "   Example: $0 1.10.0"
    exit 1
fi

NEW_VERSION="$1"

# Validate version format (x.y.z)
if [[ ! "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "❌ Invalid version format. Use X.Y.Z (e.g. 1.10.0)"
    exit 1
fi

# Read current version
CURRENT_VERSION=$(cat VERSION 2>/dev/null | tr -d '\n' || echo "unknown")
echo "📋 Current version: $CURRENT_VERSION"
echo "🚀 Updating PyJOAL to version $NEW_VERSION"
echo ""

# 1. Update VERSION file (source of truth)
echo "$NEW_VERSION" > VERSION
echo "✅ VERSION file: $CURRENT_VERSION → $NEW_VERSION"

# 2. Update frontend/package.json
if [ -f frontend/package.json ]; then
    sed -i "s/\"version\": \".*\"/\"version\": \"$NEW_VERSION\"/" frontend/package.json
    echo "✅ frontend/package.json updated"
else
    echo "⚠️  frontend/package.json not found, skipping"
fi

# 3. Verify consistency
echo ""
echo "🔍 Version consistency check:"
echo "   VERSION file:    $(cat VERSION | tr -d '\n')"
if [ -f frontend/package.json ]; then
    PKG_VER=$(grep '"version"' frontend/package.json | head -1 | sed 's/.*"version": "\(.*\)".*/\1/')
    echo "   package.json:    $PKG_VER"
fi

echo ""
echo "🎉 Version updated to $NEW_VERSION!"
echo ""
echo "📝 Reminder: Update CHANGELOG.md if not already done."
echo ""
echo "Next steps:"
echo "  1. Review changes:  git diff"
echo "  2. Commit:          git add -A && git commit -m 'chore: bump version to v$NEW_VERSION'"
echo "  3. Tag & push:      git tag v$NEW_VERSION && git push origin master --tags"
echo ""
echo "CI will automatically build Docker image and create GitHub release on push."