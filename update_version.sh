#!/bin/bash
# Version Update Script - PyJOAL
# Usage: ./update_version.sh <new_version>
# Example: ./update_version.sh 1.3.0

if [ -z "$1" ]; then
    echo "❌ Usage: $0 <version>"
    echo "   Example: $0 1.3.0"
    exit 1
fi

NEW_VERSION="$1"

# Validate version format (x.y.z)
if [[ ! "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "❌ Invalid version format. Use x.y.z (e.g., 1.3.0)"
    exit 1
fi

echo "🚀 Updating PyJOAL to version $NEW_VERSION"

# 1. Update main VERSION file
echo "$NEW_VERSION" > VERSION
echo "✅ Updated VERSION file"

# 2. Update package.json
sed -i "s/\"version\": \".*\"/\"version\": \"$NEW_VERSION\"/" frontend/package.json
echo "✅ Updated frontend/package.json"

# 3. Update CHANGELOG.md
CHANGELOG_ENTRY="## [$NEW_VERSION] - $(date +%Y-%m-%d)

### Changed
- Version bump to $NEW_VERSION

"

# Insert at the top of changelog after header
sed -i "/^# Changelog - PyJOAL/a\\
\\
$CHANGELOG_ENTRY" CHANGELOG.md
echo "✅ Updated CHANGELOG.md"

# 4. Git commit
git add VERSION frontend/package.json CHANGELOG.md
git commit -m "chore: bump version to v$NEW_VERSION

- Updated VERSION file to $NEW_VERSION
- Synced frontend/package.json version
- Added changelog entry"

echo "✅ Git commit created"

echo ""
echo "🎉 Version updated to $NEW_VERSION!"
echo ""
echo "Next steps:"
echo "1. 🐳 Build and push Docker image:"
echo "   docker build -t pyjoal:$NEW_VERSION -t pyjoal:latest ."
echo "   docker tag pyjoal:$NEW_VERSION your-registry/pyjoal:$NEW_VERSION"
echo "   docker tag pyjoal:latest your-registry/pyjoal:latest"
echo "   docker push your-registry/pyjoal:$NEW_VERSION"
echo "   docker push your-registry/pyjoal:latest"
echo ""
echo "2. 🏷️  Create GitHub release:"
echo "   git tag v$NEW_VERSION"
echo "   git push origin v$NEW_VERSION"
echo "   # Create release on GitHub with tag v$NEW_VERSION"