#!/bin/bash
# Version Update Script - PyJOAL
# Usage: ./update_version.sh <new_version>
# Example: ./update_version.sh X.Y.Z

if [ -z "$1" ]; then
    echo "❌ Usage: $0 <version>"
    echo "   Example: $0 X.Y.Z"
    exit 1
fi

NEW_VERSION="$1"

# Validate version format (x.y.z)
if [[ ! "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "❌ Invalid version format. Use X.Y.Z format"
    exit 1
fi

echo "🚀 Updating PyJOAL to version $NEW_VERSION"

# 1. Update main VERSION file
echo "$NEW_VERSION" > VERSION
echo "✅ Updated VERSION file"

# 2. Update package.json
sed -i "s/\"version\": \".*\"/\"version\": \"$NEW_VERSION\"/" frontend/package.json
echo "✅ Updated frontend/package.json"

# 3. Update documentation examples (replace old version examples with new ones)
echo "📝 Updating documentation examples..."
find . -name "*.md" -not -path "./CHANGELOG.md" -exec sed -i "s/[0-9]\+\.[0-9]\+\.[0-9]\+/$NEW_VERSION/g" {} \;
echo "✅ Updated documentation examples"

# 4. Update CHANGELOG.md
CHANGELOG_ENTRY="## [$NEW_VERSION] - $(date +%Y-%m-%d)

### Changed
- Version bump to $NEW_VERSION

"

# Insert at the top of changelog after header (more robust sed)
if grep -q "^# Changelog - PyJOAL" CHANGELOG.md; then
    # Create temp file with new content
    {
        sed -n '1,/^# Changelog - PyJOAL/p' CHANGELOG.md
        echo ""
        echo "$CHANGELOG_ENTRY"
        sed -n '/^# Changelog - PyJOAL/,$p' CHANGELOG.md | tail -n +2
    } > CHANGELOG.tmp && mv CHANGELOG.tmp CHANGELOG.md
    echo "✅ Updated CHANGELOG.md"
else
    echo "⚠️  Could not update CHANGELOG.md automatically"
fi

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