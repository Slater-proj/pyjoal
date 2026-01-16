# PyJOAL Version Management Policy

## 🎯 Overview
PyJOAL uses a **single source of truth** versioning system with **semantic versioning** (x.y.z).

## 📁 Version Sources

### 🎯 Single Source of Truth
- **`VERSION` file** - Contains only the version number (e.g., `1.2.2`)
- All other locations read from this file or are synced with it

### 🔄 Synced Locations
- `backend/app/main.py` - Reads VERSION file dynamically
- `frontend/package.json` - Synced via update script
- `CHANGELOG.md` - Updated via update script
- Docker tags - Created during build/release
- GitHub releases - Created via GitHub Actions

## 🚀 Release Process

### 1. Update Version
```bash
./update_version.sh 1.3.0
```

This script automatically:
- ✅ Updates `VERSION` file
- ✅ Updates `frontend/package.json`
- ✅ Adds entry to `CHANGELOG.md`
- ✅ Creates git commit

### 2. Create Release
```bash
git tag v1.3.0
git push origin v1.3.0
```

This triggers GitHub Actions that:
- ✅ Builds Docker images with version tags
- ✅ Pushes to GitHub Container Registry
- ✅ Creates GitHub release with auto-generated notes
- ✅ Updates `latest` tag

## 📋 Semantic Versioning

### Format: `MAJOR.MINOR.PATCH`

- **MAJOR** (x.0.0) - Breaking changes, incompatible API changes
- **MINOR** (0.x.0) - New features, backwards compatible
- **PATCH** (0.0.x) - Bug fixes, backwards compatible

### Examples
- `1.2.3` → `1.2.4` (Bug fix)
- `1.2.3` → `1.3.0` (New feature)
- `1.2.3` → `2.0.0` (Breaking change)

## 🐳 Docker Tags

### Automatic Tags
- `pyjoal:1.2.3` - Specific version
- `pyjoal:latest` - Always points to latest release

### Registry Strategy
```bash
# GitHub Container Registry
ghcr.io/username/pyjoal:1.2.3
ghcr.io/username/pyjoal:latest

# Docker Hub (if configured)
username/pyjoal:1.2.3
username/pyjoal:latest
```

## 🔍 Version Checking

### API Endpoint
```bash
curl http://localhost:8080/api/version
```
```json
{
  "version": "1.2.2",
  "name": "PyJOAL", 
  "description": "Python BitTorrent Ratio Client"
}
```

### Application Logs
```
✅ PyJOAL v1.2.2 started successfully on port 8080
```

## 🛠️ Development Workflow

### Bug Fix Release
```bash
./update_version.sh 1.2.3  # Patch increment
git push
git tag v1.2.3
git push origin v1.2.3
```

### Feature Release  
```bash
./update_version.sh 1.3.0  # Minor increment
git push
git tag v1.3.0
git push origin v1.3.0
```

### Breaking Change Release
```bash
./update_version.sh 2.0.0  # Major increment
git push
git tag v2.0.0
git push origin v2.0.0
```

## ✅ Verification Checklist

After each release, verify:
- [ ] `VERSION` file shows correct version
- [ ] API `/api/version` returns correct version
- [ ] Application logs show correct version
- [ ] `frontend/package.json` version matches
- [ ] Docker Hub has correct version tags
- [ ] GitHub release exists with correct version
- [ ] `latest` tag points to newest version

## 🔧 Troubleshooting

### Version Mismatch
If versions are out of sync:
```bash
# Re-run the update script
./update_version.sh <current_version>

# Force sync all locations
git add VERSION frontend/package.json CHANGELOG.md
git commit -m "fix: sync version across all files"
```

### Missing Docker Tags
```bash
# Manually build and push
docker build -t pyjoal:1.2.3 -t pyjoal:latest .
docker tag pyjoal:1.2.3 ghcr.io/username/pyjoal:1.2.3
docker tag pyjoal:latest ghcr.io/username/pyjoal:latest
docker push ghcr.io/username/pyjoal:1.2.3
docker push ghcr.io/username/pyjoal:latest
```