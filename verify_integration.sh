#!/bin/bash
# PyJOAL Integration Verification Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 PyJOAL Integration Verification${NC}"
echo "=================================="

# Check if VERSION file exists
if [ -f "VERSION" ]; then
    VERSION=$(cat VERSION | tr -d '\n')
    echo -e "${GREEN}✅ VERSION file found: $VERSION${NC}"
else
    echo -e "${RED}❌ VERSION file not found${NC}"
    exit 1
fi

# Check if main.py reads VERSION
if grep -q "get_version" backend/app/main.py; then
    echo -e "${GREEN}✅ main.py has version reading function${NC}"
else
    echo -e "${RED}❌ main.py doesn't read VERSION file${NC}"
fi

# Check if Dockerfile copies VERSION
if grep -q "COPY VERSION" Dockerfile; then
    echo -e "${GREEN}✅ Dockerfile copies VERSION file${NC}"
else
    echo -e "${RED}❌ Dockerfile doesn't copy VERSION file${NC}"
fi

# Check if package.json has correct version
if [ -f "frontend/package.json" ]; then
    PACKAGE_VERSION=$(grep '"version"' frontend/package.json | cut -d'"' -f4)
    if [ "$PACKAGE_VERSION" = "$VERSION" ]; then
        echo -e "${GREEN}✅ package.json version matches: $PACKAGE_VERSION${NC}"
    else
        echo -e "${YELLOW}⚠️  package.json version mismatch: $PACKAGE_VERSION vs $VERSION${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  package.json not found${NC}"
fi

# Check if GitHub Actions workflow exists
if [ -f ".github/workflows/release.yml" ]; then
    echo -e "${GREEN}✅ GitHub Actions workflow found${NC}"
    
    # Check if workflow validates VERSION
    if grep -q "Verify VERSION file matches tag" .github/workflows/release.yml; then
        echo -e "${GREEN}✅ Workflow validates VERSION file${NC}"
    else
        echo -e "${RED}❌ Workflow doesn't validate VERSION file${NC}"
    fi
    
    # Check if workflow builds for multiple registries
    if grep -q "DOCKERHUB_REGISTRY" .github/workflows/release.yml; then
        echo -e "${GREEN}✅ Workflow supports multiple registries${NC}"
    else
        echo -e "${YELLOW}⚠️  Workflow only supports single registry${NC}"
    fi
else
    echo -e "${RED}❌ GitHub Actions workflow not found${NC}"
fi

# Check if update script exists
if [ -f "update_version.sh" ]; then
    echo -e "${GREEN}✅ Version update script found${NC}"
    
    # Check if it's executable
    if [ -x "update_version.sh" ]; then
        echo -e "${GREEN}✅ Update script is executable${NC}"
    else
        echo -e "${YELLOW}⚠️  Update script not executable${NC}"
        echo "Run: chmod +x update_version.sh"
    fi
else
    echo -e "${RED}❌ Version update script not found${NC}"
fi

# Check current git status
echo ""
echo -e "${BLUE}📋 Git Status${NC}"
echo "=============="

if git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Git repository detected${NC}"
    
    # Check current version tag
    CURRENT_TAG=$(git describe --tags --exact-match HEAD 2>/dev/null || echo "no tag")
    if [ "$CURRENT_TAG" != "no tag" ]; then
        echo -e "${GREEN}✅ Current commit has tag: $CURRENT_TAG${NC}"
        
        # Check if tag matches VERSION
        TAG_VERSION=${CURRENT_TAG#v}
        if [ "$TAG_VERSION" = "$VERSION" ]; then
            echo -e "${GREEN}✅ Tag version matches VERSION file${NC}"
        else
            echo -e "${YELLOW}⚠️  Tag version ($TAG_VERSION) != VERSION file ($VERSION)${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Current commit has no tag${NC}"
    fi
    
    # Check if there are uncommitted changes
    if [ -z "$(git status --porcelain)" ]; then
        echo -e "${GREEN}✅ Working directory clean${NC}"
    else
        echo -e "${YELLOW}⚠️  Uncommitted changes detected${NC}"
    fi
else
    echo -e "${RED}❌ Not a git repository${NC}"
fi

# Test Docker build (optional)
echo ""
echo -e "${BLUE}🐳 Docker Build Test${NC}"
echo "==================="

read -p "Do you want to test Docker build? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Testing Docker build..."
    if docker build -t pyjoal:test-$VERSION .; then
        echo -e "${GREEN}✅ Docker build successful${NC}"
        
        # Test if VERSION is accessible in container
        if VERSION_IN_CONTAINER=$(docker run --rm pyjoal:test-$VERSION cat /app/VERSION 2>/dev/null); then
            if [ "$VERSION_IN_CONTAINER" = "$VERSION" ]; then
                echo -e "${GREEN}✅ VERSION file accessible in container: $VERSION_IN_CONTAINER${NC}"
            else
                echo -e "${RED}❌ VERSION mismatch in container: $VERSION_IN_CONTAINER vs $VERSION${NC}"
            fi
        else
            echo -e "${RED}❌ VERSION file not accessible in container${NC}"
        fi
        
        # Clean up test image
        docker rmi pyjoal:test-$VERSION > /dev/null 2>&1
    else
        echo -e "${RED}❌ Docker build failed${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Docker build test skipped${NC}"
fi

echo ""
echo -e "${BLUE}📋 Integration Summary${NC}"
echo "====================="
echo "Current version: $VERSION"
echo ""
echo -e "${BLUE}🚀 Next Steps:${NC}"
echo "1. Fix any issues shown above"
echo "2. Commit changes if needed: git add . && git commit -m 'fix: version integration'"
echo "3. Create release: ./update_version.sh X.Y.Z"
echo "4. Push changes: git push origin master"
echo "5. Push tag: git push origin vX.Y.Z"
echo ""
echo -e "${BLUE}🐳 After GitHub Actions completes:${NC}"
echo "- Images available at: ghcr.io/adminclem/pyjoal:$VERSION"
echo "- Docker Hub: adminclem/pyjoal:$VERSION"
echo "- GitHub Release created automatically"