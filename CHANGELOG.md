# Changelog - PyJOAL

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

## [Unreleased]

### Added
- 🔄 **Real-time WebSocket updates** for torrent status, peers, and upload speeds
- 🚫 **Clean error handling** - failed torrents no longer pollute the main table
- 🔔 **Toast notifications** for torrent load errors instead of table pollution
- 📚 **Enhanced history tracking** with detailed error logging (`torrent_load_failed` events)
- ⚡ **Live torrent monitoring** with 5-second update intervals during seeding
- 🎯 **Smart torrent updates** - individual torrent status broadcasting via WebSocket
- 🔄 **Automatic BitTorrent client updates** on Docker container startup
- 📥 Client update script (`update_clients.py`) that fetches latest versions from GitHub
- 🤖 GitHub Actions workflow for weekly client version checks
- 🔔 Toast notifications for torrent upload success/failure
- ⏱️ Seeding duration limit feature (in hours)
- 📦 Torrent archiving instead of deletion when limits are reached
- 🧪 Test script for validating torrent files (`test_torrent.py`)
- 📚 Comprehensive documentation for client updater

### Fixed

- ✅ **Real-time UI synchronization** - torrent status updates now visible in table during seeding
- 🧹 **Clean table interface** - failed torrents no longer appear in main torrent table
- 🔄 **WebSocket message handling** - frontend now processes `torrents_update` messages
- 📡 **Enhanced monitoring loop** - broadcasts individual torrent details every 5 seconds
- 🗑️ **Torrent deletion behavior** - removing torrents no longer affects other torrent statuses
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

## [1.3.1] - 2026-01-16

### Changed
- Version bump to 1.3.1



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

## [Unreleased]

### Added
- 🔄 **Real-time WebSocket updates** for torrent status, peers, and upload speeds
- 🚫 **Clean error handling** - failed torrents no longer pollute the main table
- 🔔 **Toast notifications** for torrent load errors instead of table pollution
- 📚 **Enhanced history tracking** with detailed error logging (`torrent_load_failed` events)
- ⚡ **Live torrent monitoring** with 5-second update intervals during seeding
- 🎯 **Smart torrent updates** - individual torrent status broadcasting via WebSocket
- 🔄 **Automatic BitTorrent client updates** on Docker container startup
- 📥 Client update script (`update_clients.py`) that fetches latest versions from GitHub
- 🤖 GitHub Actions workflow for weekly client version checks
- 🔔 Toast notifications for torrent upload success/failure
- ⏱️ Seeding duration limit feature (in hours)
- 📦 Torrent archiving instead of deletion when limits are reached
- 🧪 Test script for validating torrent files (`test_torrent.py`)
- 📚 Comprehensive documentation for client updater

### Fixed

- ✅ **Real-time UI synchronization** - torrent status updates now visible in table during seeding
- 🧹 **Clean table interface** - failed torrents no longer appear in main torrent table
- 🔄 **WebSocket message handling** - frontend now processes `torrents_update` messages
- 📡 **Enhanced monitoring loop** - broadcasts individual torrent details every 5 seconds
- 🗑️ **Torrent deletion behavior** - removing torrents no longer affects other torrent statuses
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
