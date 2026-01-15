# Changelog - PyJOAL

## [Unreleased]

### Added
- 🔄 **Automatic BitTorrent client updates** on Docker container startup
- 📥 Client update script (`update_clients.py`) that fetches latest versions from GitHub
- 🤖 GitHub Actions workflow for weekly client version checks
- 🔔 Toast notifications for torrent upload success/failure
- ⏱️ Seeding duration limit feature (in hours)
- 📦 Torrent archiving instead of deletion when limits are reached
- 🧪 Test script for validating torrent files (`test_torrent.py`)
- 📚 Comprehensive documentation for client updater

### Fixed
- ✅ **Torrent validation now happens BEFORE saving to disk**
  - Invalid torrent files are no longer saved to the torrents folder
  - Proper error messages shown in UI via toast notifications
  - Temporary file approach prevents corruption
- 🔄 Torrents are now loaded at startup regardless of seeding state
- 🎨 UI improvements: clearer buttons, better spacing, responsive navigation
- 🔧 Client info panel now uses proper table layout

### Changed
- 🐳 Docker entrypoint script now updates clients before starting app
- 📁 Clients folder includes default .client files as fallback
- 🎨 Removed "Modern" from UI title
- 🎯 "ADD TORRENTS" button always enabled (can add torrents while paused)

### Security
- 🔒 Enhanced torrent file validation prevents invalid files from being stored

---

## Version History

### v1.0.0 - Initial Release
- ✅ Full BitTorrent ratio client implementation
- ✅ FastAPI backend with WebSocket support
- ✅ React frontend with real-time updates
- ✅ Docker support with multi-stage build
- ✅ Multiple client emulation support
- ✅ Proxy configuration
- ✅ Web UI with drag & drop
