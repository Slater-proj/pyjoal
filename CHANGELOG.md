# Changelog - PyJOAL

## [1.11.3] - 2026-02-06

### Changed
- **Unified CI/CD Pipeline**: Single pipeline on master push (tests → build → Docker Hub → GitHub Release)
- **Repository cleanup**: Removed obsolete test scripts and temporary files
- **Removed tag-based release workflow**: Everything handled by master push pipeline

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
- `totalUploaded` ResponseValidationError (float → int cast)
- Torrents with few peers no longer report near-zero upload speed

## [1.11.0] - 2026-02-06

### Added
- **Created by field** - Display torrent creator from .torrent metadata in UI table
- **Added date column** - Torrent addition date with relative formatting and tooltip
- **Stats persistence** - Uploaded bytes, seeding time, and added date survive container restarts
- **Notification system** - Gotify and generic webhook support with per-event filtering, rate limiting, and test button
- **Notification settings UI** - Full configuration panel in Settings page
- **Favicon/app icon** - Custom hexagonal logo for browser tabs and bookmarks
- **API endpoints** - GET/PUT /api/notifications/config + POST /api/notifications/test

### Changed
- **Stealth: peer-based upload rate** - Zero leechers = zero upload, swarm-weighted speed distribution
- **Mobile responsive** - Horizontal scroll for torrent table on small screens
- **Auto-archive with reason tracking** - Notification includes full stats (ratio, uploaded, seeding time)

### Fixed
- Test datetime naive/aware mismatch in test_pause_ends_when_time_expires

## [1.10.0] - 2026-01-25

### Added
- Initial public release
- BitTorrent client emulation (qBittorrent, Deluge, Transmission)
- Modern React 18 web interface with TailwindCSS
- Real-time WebSocket updates
- Drag & Drop torrent upload
- Configurable upload ratio target and time limits
- HTTP proxy support
- Docker multi-stage build
- Anti-detection features (natural activity patterns, desynchronized timing)
