# Changelog - PyJOAL

## [1.4.0] - 2026-01-16

### 🎨 Major UI/UX Improvements & History Optimization

#### 📊 Enhanced History System
- **Unified Archive Categories** - Simplified from 3 separate types (ratio/time/error) to 1 unified "Auto Archived" category
- **Detailed Reason Display** - Clear badge system with color coding:
  - 🟣 Purple badges for ratio targets achieved
  - 🔵 Indigo badges for duration limits reached
  - 🔴 Red badges for errors and zero peer situations
- **Enhanced Information** - Detailed tooltips showing exact values (e.g., "Ratio: 2.5 (Target: 2.0)")
- **Better Event Tracking** - Comprehensive event logging with structured data for analysis

#### 🎯 Responsive Design & Layout
- **Unified Panel Widths** - Harmonized History and Settings panels to same max width (6xl)
- **Improved Mobile Experience** - Responsive grids that adapt to screen size:
  - Mobile: Single column layout
  - Tablet: Two column layout  
  - Desktop: Three column layout for discretion settings
- **Enhanced History Panel** - Increased height by 100px for better visibility without scrollbars
- **Smart Filter Layout** - Flex-wrap filters instead of horizontal scroll for better mobile UX

#### 🔧 Input Field Improvements
- **Complete Value Deletion** - Fixed UX bug where last digit couldn't be deleted in discretion fields
- **Better Validation** - OnBlur validation with proper empty string handling
- **Placeholder Values** - Clear default values shown for better user guidance
- **Enhanced Form UX** - Smoother interaction with proper focus and blur handling

#### 📝 Optimized Logging System
- **Real-time Log Streaming** - Live WebSocket log broadcasting to frontend console
- **Structured Log Levels** - Color-coded log levels (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- **Smart Log Retention** - Keep last 500 logs in UI, 1000 in backend queue
- **Comprehensive Tracking** - All major operations logged with appropriate detail level
- **Performance Optimized** - Batched log transmission and efficient memory management

## [1.3.8] - 2026-01-16

### ✨ Major Feature: Advanced Discretion & Anti-Detection System

#### 🛡️ Anti-Fingerprinting
- **Desynchronized Announces** - Each torrent now has individual announce timing with random jitter
- **Realistic Speed Variations** - Configurable speed fluctuations (±20% default) to mimic real clients
- **Anti-Pattern Detection** - Eliminated synchronized speed updates that trackers can detect
- **Authentic Timing** - Variable intervals based on real torrent client behavior patterns

#### ⚙️ New Configuration Options
- **Announce Interval** - Base time between announces (15-300s, default: 30s)
- **Announce Jitter** - Random variation to avoid synchronization (0-180s, default: ±30s)
- **Min Stats Update Interval** - Minimum time between speed updates (1-30s, default: 3s)
- **Speed Variation Toggle** - Enable/disable realistic speed fluctuations
- **Speed Variation Percentage** - Control fluctuation intensity (0-50%, default: 20%)

#### 🎭 UI Enhancements
- **Discretion Settings Panel** - New dedicated section in Configuration tab
- **Real-time Parameter Validation** - Bounds checking with helpful tooltips
- **Security Recommendations** - Built-in guidance for optimal stealth settings

#### 🧪 Enhanced Testing
- **Comprehensive Test Suite** - New tests for discretion features and timing validation
- **Configuration Schema Tests** - Validation of all new discretion parameters
- **Timing Logic Tests** - Verification of anti-synchronization mechanisms

#### 📚 Documentation Updates
- **Discretion Guide** - Detailed explanation of anti-detection features
- **Security Best Practices** - Recommendations for tracker evasion
- **Configuration Reference** - Complete parameter documentation with examples

### 🔧 Technical Improvements
- **TrackerAnnouncer Refactoring** - Support for per-instance discretion configuration
- **Settings Enhancement** - New discretion-related global settings with proper validation
- **Timing Precision** - Improved time-based calculations for more realistic behavior
- **Code Quality** - Enhanced error handling and logging for discretion features

### 🐛 Bug Fixes
- **Synchronized Speed Updates** - Fixed major fingerprinting vulnerability where all torrents updated simultaneously
- **Configuration Duplication** - Resolved code duplication in default config generation
- **Syntax Errors** - Fixed indentation and structure issues in seeder service

## [1.3.5] - 2026-01-16

### Fixed
- 🔧 **Configuration Sync Bug** - Config changes now properly update across all UI components after save
- 🔢 **Negative Values Input** - Fixed ratio (-1) and seeding duration (-1) fields to accept negative values
- 💾 **Config Persistence** - Configuration updates now refetch from server ensuring UI stays in sync
- 📝 **Input Validation** - Improved handling of empty and partially typed numeric values
- 🎯 **Missing Field** - Added seeding duration limit field to ConfigPanel for consistency

### Enhanced
- 🎉 **User Feedback** - Replaced alert() with elegant toast notifications for config operations
- 🔄 **Loading States** - Added saving indicators and disabled states for better UX
- ⚡ **Real-time Updates** - Configuration changes are immediately reflected in dashboard and info panels

### Technical Improvements
- Store.updateConfig now refetches from server after successful update
- Enhanced input handlers for numeric fields with negative value support
- Consistent error handling with toast notifications across all config forms
- Added missing seedingDurationLimit field to ConfigPanel component

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

## [1.3.3] - 2026-01-16

### Changed
- Version bump to 1.3.3



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

## [1.3.4] - 2026-01-16

### Changed
- Version bump to 1.3.4



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

## [1.3.3] - 2026-01-16

### Changed
- Version bump to 1.3.3



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
