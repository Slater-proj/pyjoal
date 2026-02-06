# Changelog - PyJOAL

## [1.11.2] - 2026-02-06

### Added
- **Configurable Peer Speed Tiers**: Upload speed now scales based on total peer count
  - Tier 1 (0-20 peers): 15% of speed range (configurable)
  - Tier 2 (20-100 peers): 60% of speed range (configurable)
  - Tier 3 (100+ peers): 100% of speed range (configurable)
  - All thresholds and percentages configurable in Settings page
- **Peer Speed Tiers Settings Section**: New section in Settings page with inline help

### Changed
- **Torrent Metadata Layout**: Creator, tracker, and date displayed inline instead of stacked
- **Speed Calculation**: Replaced broken swarm_factor formula with configurable tier-based system

### Fixed
- Torrents with few peers no longer report near-zero upload speed


## [1.11.2] - 2026-02-06

### Added
- **Configurable Peer Speed Tiers**: Upload speed now scales based on total peer count
  - Tier 1 (0-20 peers): 15% of speed range (configurable)
  - Tier 2 (20-100 peers): 60% of speed range (configurable)
  - Tier 3 (100+ peers): 100% of speed range (configurable)
  - All thresholds and percentages configurable in Settings page
- **Peer Speed Tiers Settings Section**: New "Peer-Based Speed Tiers" section in Settings page with inline help and live examples

### Changed
- **Torrent Metadata Layout**: Created by, tracker, and added date now displayed inline (single line) instead of stacked vertically — improved readability and reduced row height
- **Speed Calculation**: Replaced broken swarm_factor formula (leecher_ratio² × min(leechers,10)/3) with configurable tier-based percentage system — ensures all torrents share at minimum configured rate

### Fixed
- Torrents with few peers no longer report near-zero upload speed (was caused by aggressive swarm_factor formula)


## [1.11.0] - 2026-02-06

### Added
- **Created by field** - Display torrent creator from .torrent metadata in UI table
- **Added date column** - Torrent addition date with relative formatting and tooltip
- **Stats persistence** - Uploaded bytes, seeding time, and added date survive container restarts (JSON at CONFIG_DIR/torrent_stats.json)
- **Notification system** - Gotify and generic webhook support with per-event filtering, rate limiting, and test button
- **Notification settings UI** - Full configuration panel in Settings page (backends, events, test)
- **Favicon/app icon** - Custom hexagonal logo for browser tabs and bookmarks
- **API endpoint** - GET/PUT /api/notifications/config + POST /api/notifications/test

### Changed
- **Stealth: peer-based upload rate** - Zero leechers = zero upload (critical anti-detection), swarm-weighted speed distribution
- **Mobile responsive** - Horizontal scroll for torrent table on small screens
- **Auto-archive with reason tracking** - Notification includes full bilan (ratio, uploaded, seeding time)

### Fixed
- Test datetime naive/aware mismatch in test_pause_ends_when_time_expires

## [1.11.0] - 2026-02-06

### Added
- **Created by field** - Display torrent creator from .torrent metadata in UI table
- **Added date column** - Torrent addition date with relative formatting and tooltip
- **Stats persistence** - Uploaded bytes, seeding time, and added date survive container restarts (JSON at CONFIG_DIR/torrent_stats.json)
- **Notification system** - Gotify and generic webhook support with per-event filtering, rate limiting, and test button
- **Notification settings UI** - Full configuration panel in Settings page (backends, events, test)
- **Favicon/app icon** - Custom hexagonal logo for browser tabs and bookmarks
- **API endpoint** - GET/PUT /api/notifications/config + POST /api/notifications/test

### Changed
- **Stealth: peer-based upload rate** - Zero leechers = zero upload (critical anti-detection), swarm-weighted speed distribution using JOAL-inspired leecher_ratio² formula
- **Mobile responsive** - Horizontal scroll for torrent table on small screens
- **Auto-archive with reason tracking** - Notification includes full bilan (ratio, uploaded, seeding time)

### Fixed
- Test datetime naive/aware mismatch in test_pause_ends_when_time_expires

## [1.10.0] - 2026-02-06

### Added
- **Mypy/Pyright configuration** - `backend/pyproject.toml` with gradual type checking adoption
- **Frontend tests** - `format.test.ts`, `useStore.test.ts`, `DashboardPage.test.tsx`, `SettingsPage.test.tsx`
- **Backend tests** - `test_error_explanations.py`, `test_config_manager.py`, `test_log_stream_service.py`, `test_resource_optimizer.py`
- **310 backend tests** passing (up from 99 in v1.9.0)

### Changed
- **Refactored `seeder_service.py`** - Split 1031-line monolith into `config_manager.py` + `torrent_manager.py` + slim orchestrator
- **Refactored `tracker_announcer.py`** - Split 1481 lines into `stats_simulator.py` + `tracker_manager.py`
- **Fixed `datetime.utcnow()` deprecation** - All 55+ occurrences replaced with `datetime.now(timezone.utc)` across 13 files
- **Centralized test secrets** - `TEST_SECRET_TOKEN` constant in `conftest.py` replaces all hardcoded tokens
- **Replaced `print()` with logger** in `torrent_parser.py`
- **Aligned Python 3.12** across Dockerfile and CI workflows
- **Version management** - Rewrote `update_version.sh` for reliable version updates
- **Clean CHANGELOG** - Fixed bloated 75MB file caused by broken script

### Fixed
- Frontend version mismatch (was 1.9.4, aligned to VERSION file)
- Backend coverage: error_explanations 21%→100%, config_manager 54%→88%, log_stream_service 38%→79%, resource_optimizer 51%→78%

## [1.9.0] - 2026-01-19

### Test Suite Overhaul
- Fixed all 42 previously failing tests (99 total)
- Added `conftest.py` with proper environment variable setup
- Enhanced WebSocket Manager with `broadcast_log()` and `cleanup()` methods
- Enhanced CI/CD Pipeline with environment variables for test execution

## [1.7.7] - 2026-01-17

### Ultra-Reactive Speed Changes
- Speed changes every ~3 seconds per torrent
- Individual torrent speed control
- Fixed reload button functionality

## [1.7.6] - 2026-01-17

### Discretion & Anti-Detection
- Temporal desynchronization per torrent
- Configurable announce jitter and intervals
- Speed variation with natural fluctuations
- Discretion settings in web UI

## [1.7.5] - 2026-01-17

### UI/UX Improvements
- Resizable table columns with drag handles
- Pagination for torrent list
- History page with filtering
- Real-time log console via WebSocket

## [1.7.2] - 2026-01-17

### Architecture
- React 18 + TailwindCSS + Zustand frontend rewrite
- Bottom navigation with Dashboard / Settings / History
- Client info panel with live stats

## [1.7.1] - 2026-01-17

### Docker & CI
- Multi-stage Docker build (Node 20 alpine → Python 3.12-slim)
- GitHub Actions CI/CD: backend tests, frontend build, Docker build, security scan
- Automated Docker Hub push and GitHub Release on master

## [1.4.2] - 2026-01-16

### BitTorrent Protocol
- UDP tracker support (BEP 15)
- Magnet link parsing
- Enhanced client emulation (qBittorrent 5.1.4, Transmission 4.1.0, Deluge 2.2.1)
- Torrent file validation with bencode parsing

## [1.4.0] - 2026-01-16

### Core Features
- Stealth service with session profiles
- Resource optimizer for memory management
- Version checker with GitHub release monitoring
- Cache manager for stats aggregation

## [1.2.1] - 2026-01-15

### Fixed
- History tab: Added "Load Failed" filter
- Duration column label clarity
- Upload speeds based on real tracker announces

## [1.0.0] - 2026-01-14

### Initial Release
- Full BitTorrent ratio client implementation
- FastAPI backend with WebSocket support
- React frontend with real-time updates
- Docker support with multi-stage build
- Multiple client emulation (qBittorrent, Deluge, Transmission)
- Proxy configuration support
- Web UI with drag & drop torrent upload
