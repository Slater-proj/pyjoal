# Changelog - PyJOAL

## [1.12.2] - 2025-02-07

### Fixed — Critical
- **Mass torrent archiving at startup**: Monitor loop called `check_ratio_targets()` every 3s before first announce completed, causing all torrents with `seeders=0, leechers=0` and seeding time > 5 min to be archived. Fixed by: (1) Only checking zero peers after first announce (`last_announce is not None`), (2) Reduced check frequency from every 3s to every 60s (every 20 iterations)
- **Torrents never starting after archiving**: After torrents were archived and new ones added, they weren't started because the monitor loop didn't ensure simultaneous seed limit. Added `_ensure_simultaneous_seed_limit()` called every 60s to start inactive torrents up to the limit

### Fixed — High
- **Favicon and logo broken**: Root `/` returned 404 instead of redirecting to `/ui/`, and `/favicon.svg` wasn't served. Added root → UI redirect and `/favicon.svg` endpoint
- **Infinite "Loading torrents..." message**: Frontend never received WebSocket `loading_status: "ready"` or `"error"` events to clear the banner. Frontend now clears on both states and shows error toast if needed

### Fixed — Medium
- **Monitor loop excessive load**: Removed unnecessary `await self.load_torrents()` call from monitor loop (ran every 3s). File watcher handles new torrents automatically
- **Startup notification spam**: Removed toast broadcasts from `check_ratio_targets()` and torrent load failures during the initial startup phase to avoid flooding the UI

## [1.12.1] - 2025-02-07

### Fixed — Critical
- **Route shadowing**: `/api/torrents/failed` was unreachable because FastAPI matched "failed" as `{info_hash}` — moved it before the path-parameter route
- **Double upload counting**: Monitor loop (`update_stats_for_display`) and announce loop (`update_stats_with_stealth`) both incremented `self.uploaded` — display path now only updates `upload_speed`
- **Wrong announce path on start/stop**: Initial "completed" and "stopped" events used legacy `_send_announce()` (single HTTP tracker) instead of `_send_announce_stealth()` (multi-tracker + UDP)

### Fixed — High
- **Global PRNG corruption**: `random.seed()` / `random.seed(value)` in `StealthService._generate_session_profile()` polluted global state — replaced with local `random.Random(seed)` instance
- **Dict mutation during iteration**: Monitor loop iterated `self.announcers.values()` while add/remove torrent tasks could mutate it — now iterates a `list()` copy
- **WebSocket unauthenticated**: `/ws` endpoint had no token verification — now requires `?token=` query parameter matching `SECRET_TOKEN`
- **Non-deterministic download phase**: `is_in_downloading_phase()` re-rolled `random.randint(5,30)` on every call — delay is now cached per instance

### Fixed — Medium
- **`datetime.utcnow()` deprecated**: All 16 occurrences replaced with `datetime.now(timezone.utc)` in `stats_simulator.py`
- **Peak hours midnight wrap**: `range(18, 25)` didn't handle wrap-around (e.g. 20→2) — rewritten with proper modular comparison

### Changed — Frontend
- **WebSocket auth**: Frontend now sends `?token=` on WebSocket connect
- **Toast handler**: Added `case "toast"` to WebSocket message handler for server-sent notifications
- **Removed dead code**: `startAutoRefresh`/`stopAutoRefresh` (unused), `startTorrent`/`stopTorrent` API methods (no backend endpoints)
- **Logo added**: PyJOAL logo displayed next to the title in the header, linked to dashboard

## [1.11.6] - 2026-02-06

### Fixed
- **Torrents not uploading with 0 leechers**: Replaced hard `speed=0` when leechers=0 with minimal background speed (~1 KB/s). Tracker peer lists are stale (15-30 min updates) and brief peer connections between announces are normal — a real client doesn't drop to 0
- **Peer Speed Tiers table hidden despite being active**: The tier configuration table was invisible when `peerSpeedTiersEnabled` was `undefined` (old config), even though the checkbox showed as checked. Now both use `?? true` consistently
- **`get_realistic_upload_speed_based_on_swarm` ignoring dynamic config**: Now uses runtime config for min/max upload rate instead of static defaults

### Changed
- **Tier 1 default**: 15% → 40% (was too aggressive for small private tracker swarms ≤20 peers)
- **Tier 2 default**: 35% → 55% (same reason, ≤50 peers)

## [1.11.5] - 2026-02-06

### Added
- **5 Configurable Peer Speed Tiers**: Expanded from 3 to 5 tiers with adjustable max peers and speed percentages, plus effective range preview in settings
- **Peer Speed Tiers Toggle**: Option to completely enable/disable peer-based speed scaling
- **Loading Banner**: Blue spinner banner during torrent loading at startup, with WebSocket-driven status updates
- **Ratio Tooltip**: Hover on ratio cells to see color meaning (green = target reached, yellow = in progress, gray = starting)

### Changed
- **Faster Startup**: Torrent loading and auto-start now run as background tasks after HTTP server is ready
- **Log Reduction**: Moved frequent per-upload, per-torrent stats, and per-announce logs from INFO to DEBUG level
- **Config Sync Fix**: Behavior timing settings (pause duration, reduced speed, etc.) now properly propagate from config to torrent simulators
- **Gotify Test**: Test notification button now sends current (unsaved) form values instead of requiring save first

### Fixed
- Missing 
enderPage() call in App.tsx after loading banner addition
- Unused Response import in main.py

## [1.11.4] - 2026-02-06

### Fixed
- **Upload speed with 0 leechers**: Torrents now upload based on total peer count (seeders + leechers), not leechers only. Only truly empty swarms (0 total peers) result in 0 speed.
- **Favicon not displaying**: Added proper routes for serving favicon.svg, favicon.ico, and apple-touch-icon.png from frontend build

### Changed
- Speed tier calculation now uses total peers (seeders + leechers) instead of requiring leechers > 0

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
