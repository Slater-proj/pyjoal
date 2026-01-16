#!/bin/bash
# Version Consistency Check - Ensures no hardcoded versions exist

VERSION=$(cat VERSION | tr -d '\n')
echo "🔍 Checking version consistency for version: $VERSION"
echo "=================================================="

# Check if any hardcoded versions exist (except in CHANGELOG)
echo "🔍 Searching for hardcoded versions..."

HARDCODED_FOUND=false

# Check backend files for hardcoded versions (excluding comments and this check)
if grep -r "1\.[0-9]\+\.[0-9]\+" backend/app/ --exclude-dir=__pycache__ | grep -v "# fallback" | grep -v "development fallback" | grep -v "\.py:" | grep -v "get_version" > /dev/null; then
    echo "❌ Found potential hardcoded versions in backend:"
    grep -r "1\.[0-9]\+\.[0-9]\+" backend/app/ --exclude-dir=__pycache__ | grep -v "# fallback" | grep -v "development fallback"
    HARDCODED_FOUND=true
fi

# Check frontend files (excluding node_modules)
if grep -r "1\.[0-9]\+\.[0-9]\+" frontend/src/ 2>/dev/null | grep -v "node_modules" > /dev/null; then
    echo "❌ Found potential hardcoded versions in frontend:"
    grep -r "1\.[0-9]\+\.[0-9]\+" frontend/src/ | grep -v "node_modules"
    HARDCODED_FOUND=true
fi

# Check configuration files for hardcoded versions (excluding expected ones)
EXCLUDED_FILES="VERSION CHANGELOG.md package.json"
for file in *.md *.yml *.yaml *.json *.sh; do
    if [[ -f "$file" && "$file" != "package.json" && "$file" != "CHANGELOG.md" ]]; then
        if grep "1\.[0-9]\+\.[0-9]\+" "$file" > /dev/null 2>&1; then
            # Check if it's the actual version or a hardcoded one
            if ! grep "$VERSION" "$file" > /dev/null 2>&1; then
                echo "❌ Found outdated/hardcoded version in $file:"
                grep "1\.[0-9]\+\.[0-9]\+" "$file"
                HARDCODED_FOUND=true
            fi
        fi
    fi
done

if [ "$HARDCODED_FOUND" = false ]; then
    echo "✅ No hardcoded versions found!"
else
    echo ""
    echo "⚠️  Found hardcoded versions above. Use update_version.sh to fix."
fi

echo ""
echo "📋 Current version status:"
echo "========================="
echo "VERSION file: $VERSION"
echo "package.json: $(grep '"version"' frontend/package.json | cut -d'"' -f4)"

# Check if app reads version dynamically
if python3 -c "
import sys
sys.path.append('backend')
try:
    from app.main import get_version
    print('App dynamic version:', get_version())
except Exception as e:
    print('❌ Cannot read app version:', e)
" 2>/dev/null; then
    echo "✅ App reads version dynamically"
else
    echo "⚠️  App version reading needs checking"
fi

echo ""
echo "🎯 Remember: NEVER hardcode versions!"
echo "     Use: ./update_version.sh X.Y.Z"
echo "     All versions will be synced automatically."