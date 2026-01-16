# PyJOAL Docker Hub & Registry Setup

## 🐳 Docker Hub Configuration

### 1. Create Docker Hub Repository
1. Go to [Docker Hub](https://hub.docker.com/)
2. Create repository: `username/pyjoal`
3. Set as public repository

### 2. Configure GitHub Secrets
In your GitHub repository, go to Settings → Secrets and variables → Actions:

```
DOCKERHUB_USERNAME=your-dockerhub-username
DOCKERHUB_TOKEN=your-dockerhub-access-token
```

To get access token:
1. Docker Hub → Account Settings → Security → New Access Token
2. Copy the token value

### 3. Test Local Docker Build
```bash
# Build with version tags
docker build -t pyjoal:1.3.4 -t pyjoal:latest .

# Tag for registries
docker tag pyjoal:1.3.4 username/pyjoal:1.3.4
docker tag pyjoal:latest username/pyjoal:latest
docker tag pyjoal:1.3.4 ghcr.io/username/pyjoal:1.3.4
docker tag pyjoal:latest ghcr.io/username/pyjoal:latest

# Push to registries
docker push username/pyjoal:1.3.4
docker push username/pyjoal:latest
docker push ghcr.io/username/pyjoal:1.3.4
docker push ghcr.io/username/pyjoal:latest
```

## 🚀 Automated Release Process

### Complete Release Workflow
```bash
# 1. Update version (updates VERSION, package.json, CHANGELOG)
./update_version.sh 1.3.4

# 2. Push changes
git push origin master

# 3. Create and push tag (triggers GitHub Actions)
git tag v1.3.4
git push origin v1.3.4
```

### What GitHub Actions Does Automatically
✅ Validates VERSION file matches git tag
✅ Builds multi-platform Docker images (amd64, arm64)
✅ Pushes to GitHub Container Registry (ghcr.io)
✅ Pushes to Docker Hub
✅ Creates GitHub release with auto-generated notes
✅ Updates both `latest` and version-specific tags

## 📍 Registry URLs

### GitHub Container Registry
- `ghcr.io/username/pyjoal:1.3.4`
- `ghcr.io/username/pyjoal:latest`

### Docker Hub
- `username/pyjoal:1.3.4`
- `username/pyjoal:latest`

## 🔍 Version Verification

### Check Application Version
```bash
# Via API
curl http://localhost:8080/api/version

# Via logs
docker logs container-name | grep "PyJOAL v"

# Via VERSION file
docker exec container-name cat /app/VERSION
```

### Verify All Locations
```bash
# Check VERSION file
cat VERSION

# Check package.json
grep version frontend/package.json

# Check running container
curl -s http://localhost:8080/api/version | jq .version

# Check Docker images
docker images pyjoal
docker images ghcr.io/username/pyjoal
```

## 🔧 Manual Docker Commands

### Build and Test Locally
```bash
# Build with current version
VERSION=$(cat VERSION)
docker build -t pyjoal:$VERSION -t pyjoal:latest .

# Test container
docker run --rm -p 8080:8080 pyjoal:$VERSION

# Check version in logs
docker logs container-name | grep "PyJOAL v"
```

### Manual Registry Push
```bash
VERSION=$(cat VERSION)

# Login to registries
docker login ghcr.io
docker login docker.io

# Tag and push
docker tag pyjoal:$VERSION ghcr.io/username/pyjoal:$VERSION
docker tag pyjoal:latest ghcr.io/username/pyjoal:latest
docker tag pyjoal:$VERSION username/pyjoal:$VERSION
docker tag pyjoal:latest username/pyjoal:latest

docker push ghcr.io/username/pyjoal:$VERSION
docker push ghcr.io/username/pyjoal:latest
docker push username/pyjoal:$VERSION
docker push username/pyjoal:latest
```

## 📋 Troubleshooting

### Version Mismatch
If VERSION file doesn't match tag:
```bash
# Fix and re-tag
echo "1.3.4" > VERSION
git add VERSION
git commit -m "fix: sync VERSION file"
git tag -d v1.3.4  # delete old tag
git tag v1.3.4     # create new tag
git push --delete origin v1.3.4  # delete remote tag
git push origin v1.3.4           # push new tag
```

### Docker Build Fails
```bash
# Check Dockerfile copies VERSION
grep "COPY VERSION" Dockerfile

# Ensure VERSION file exists
ls -la VERSION

# Test build locally
docker build -t test-build .
docker run --rm test-build cat /app/VERSION
```

### Registry Push Fails
```bash
# Check authentication
docker login ghcr.io
docker login docker.io

# Check image exists locally
docker images | grep pyjoal

# Check secrets in GitHub
# Go to Settings → Secrets → Actions
# Verify DOCKERHUB_USERNAME and DOCKERHUB_TOKEN
```