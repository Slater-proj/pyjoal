# Changelog - PyJOAL

## [1.3.1] - 2026-01-16

### Added
- 🔄 **Unified Version Management** - Single VERSION file as source of truth across entire project
- 🐳 **Multi-Registry Docker Support** - GitHub Container Registry + Docker Hub publishing
- 🤖 **Enhanced CI/CD Pipeline** - Version-aware automated releases
- 📋 **Integration Verification Tools** - Scripts for validating version consistency
- 📚 **Comprehensive Documentation** - Docker registry setup guides and version management

### Fixed
- ✅ **Version Consistency** - Fixed inconsistent versioning across application, Docker, and releases
- 🔧 **CI Workflow** - Updated to use VERSION file instead of auto-incrementing
- 🏷️ **Docker Tags** - Proper version tags for both registries
- 📝 **API Version Endpoint** - Dynamic version reading from VERSION file

### Changed
- 🔄 **Release Process** - Simplified with `update_version.sh` script for unified updates
- 🐳 **Docker Build** - VERSION file copied to containers for runtime version access
- 📋 **Release Notes** - Automated GitHub releases with proper version information

### Technical
- VERSION file integration in backend/app/main.py
- GitHub Actions workflow adapted for VERSION-based releases  
- Multi-platform Docker builds (amd64, arm64)
- Automated CHANGELOG management

## [1.2.1] - 2026-01-15

### Fixed
- **History tab**: Added "Load Failed" filter to display torrent loading failures
- **Duration column**: Changed unclear "Dur" to "Duration" in torrents table  
- **Upload speeds**: Implemented authentic speed calculation based on real tracker announces
- **Speed authenticity**: Displayed speeds now match exactly what trackers receive (no fake values)

### Technical Improvements  
- Upload speed calculation based on successful announce intervals
- Enhanced tracker protocol compliance  
- Real-time WebSocket updates for authentic speed reporting

## Version History

### v1.0.0 - Initial Release
- ✅ Full BitTorrent ratio client implementation
- ✅ FastAPI backend with WebSocket support
- ✅ React frontend with real-time updates
- ✅ Docker support with multi-stage build
- ✅ Multiple client emulation support
- ✅ Proxy configuration
- ✅ Web UI with drag & drop

## [1.3.2] - 2026-01-16

### Changed
- Version bump to 1.3.2



## [1.3.1] - 2026-01-16

### Added
- 🔄 **Unified Version Management** - Single VERSION file as source of truth across entire project
- 🐳 **Multi-Registry Docker Support** - GitHub Container Registry + Docker Hub publishing
- 🤖 **Enhanced CI/CD Pipeline** - Version-aware automated releases
- 📋 **Integration Verification Tools** - Scripts for validating version consistency
- 📚 **Comprehensive Documentation** - Docker registry setup guides and version management

### Fixed
- ✅ **Version Consistency** - Fixed inconsistent versioning across application, Docker, and releases
- 🔧 **CI Workflow** - Updated to use VERSION file instead of auto-incrementing
- 🏷️ **Docker Tags** - Proper version tags for both registries
- 📝 **API Version Endpoint** - Dynamic version reading from VERSION file

### Changed
- 🔄 **Release Process** - Simplified with `update_version.sh` script for unified updates
- 🐳 **Docker Build** - VERSION file copied to containers for runtime version access
- 📋 **Release Notes** - Automated GitHub releases with proper version information

### Technical
- VERSION file integration in backend/app/main.py
- GitHub Actions workflow adapted for VERSION-based releases  
- Multi-platform Docker builds (amd64, arm64)
- Automated CHANGELOG management

## [1.2.1] - 2026-01-15

### Fixed
- **History tab**: Added "Load Failed" filter to display torrent loading failures
- **Duration column**: Changed unclear "Dur" to "Duration" in torrents table  
- **Upload speeds**: Implemented authentic speed calculation based on real tracker announces
- **Speed authenticity**: Displayed speeds now match exactly what trackers receive (no fake values)

### Technical Improvements  
- Upload speed calculation based on successful announce intervals
- Enhanced tracker protocol compliance  
- Real-time WebSocket updates for authentic speed reporting

## Version History

### v1.0.0 - Initial Release
- ✅ Full BitTorrent ratio client implementation
- ✅ FastAPI backend with WebSocket support
- ✅ React frontend with real-time updates
- ✅ Docker support with multi-stage build
- ✅ Multiple client emulation support
- ✅ Proxy configuration
- ✅ Web UI with drag & drop
