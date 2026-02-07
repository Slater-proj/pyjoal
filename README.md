# PyJOAL - BitTorrent Ratio Client 🚀

[![CI/CD Pipeline](https://github.com/Slater-proj/pyjoal/actions/workflows/ci.yml/badge.svg)](https://github.com/Slater-proj/pyjoal/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/Slater-proj/pyjoal/branch/master/graph/badge.svg)](https://codecov.io/gh/Slater-proj/pyjoal)
[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![Docker Pulls](https://img.shields.io/docker/pulls/pyjoal/pyjoal.svg)](https://hub.docker.com/r/slaterdev/pyjoal)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

**PyJOAL** is a smart BitTorrent client that emulates various clients to maintain seed ratio without consuming real bandwidth. Written entirely in Python with a modern React web interface.

## ✨ Features

### 🎭 Advanced Emulation

- **Multi-client** - qBittorrent, Deluge, Transmission with automatic updates
- **Anti-detection** - Natural activity patterns and desynchronized timing
- **Realistic variations** - Speed fluctuations simulating a real client

### 🎨 Modern Interface

- **React 18 + TailwindCSS** - Responsive and elegant design
- **Real-time** - WebSocket for instant updates
- **Drag & Drop** - Drop your .torrent files directly
- **Complete dashboard** - Stats, history, real-time logs

### 🔧 Flexible Configuration

- **Upload ratio** - Configurable target with automatic archiving
- **Time limit** - Maximum seed duration per torrent
- **Proxy support** - Built-in HTTP proxy
- **Advanced stealth** - Jitter, intervals, configurable variations
- **📨 Notifications** - Gotify + webhook with per-event filtering
- **💾 Stats persistence** - Upload stats survive container restarts
### 🐳 Production Ready

- **Optimized Docker** - Multi-stage image (~150MB)
- **Security** - API token + path obfuscation
- **Auto-update** - BitTorrent clients updated automatically

## 🚀 Quick Start

### With Docker Compose (Recommended)

```bash
git clone https://github.com/Slater-proj/pyjoal.git
cd pyjoal
cp .env.example .env
# Edit .env with your values
docker-compose up -d
# Interface at http://localhost:8080/{UI_PATH_PREFIX}/ui/
```

### Docker Run

```bash
docker run -d --name pyjoal -p 8080:8080 \
  -e SECRET_TOKEN=your_token \
  -e UI_PATH_PREFIX=secret_path \
  -v $(pwd)/torrents:/app/torrents \
  -v $(pwd)/config:/app/config \
  adminclem/pyjoal:latest
```

## ⚙️ Configuration

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `SECRET_TOKEN` | API authentication token (required) |
| `UI_PATH_PREFIX` | Secret path for the interface (required) |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8080 | Server port |
| `MIN_UPLOAD_RATE` | 30 | Min upload speed (KB/s) |
| `MAX_UPLOAD_RATE` | 160 | Max upload speed (KB/s) |
| `SIMULTANEOUS_SEED` | 20 | Max simultaneous torrents |
| `TZ` | Europe/Paris | Timezone for logs |

### JSON Configuration (config/config.json)

Created automatically on first launch, editable via the interface:

```json
{
  "minUploadRate": 30,
  "maxUploadRate": 160,
  "simultaneousSeed": 20,
  "client": "qbittorrent-5.1.4.client",
  "keepTorrentWithZeroLeechers": true,
  "uploadRatioTarget": -1.0,
  "seedingDurationLimit": -1.0
}
```

> All additional fields (peer speed tiers, discretion timing, announce intervals, etc.) are auto-populated with defaults and configurable from the Settings UI.

## 🎭 Stealth & Anti-detection

- **Temporal desynchronization** - Each torrent has its own cycle with random jitter
- **Speed variations** - Natural fluctuations simulating a real client
- **Anti-fingerprinting** - Removal of detectable synchronous patterns
- **Realistic behavior** - State changes in hours, not minutes

## 🔒 Security

1. **Path obfuscation** - URL hidden via `UI_PATH_PREFIX`
2. **API Token** - Authentication required on all requests
3. **Referrer Policy** - Protection against URL leaks

## 📡 REST API

Interactive Swagger documentation: `http://localhost:8080/docs`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/PUT | `/api/config` | Configuration |
| GET/POST/DELETE | `/api/torrents` | Torrent management |
| POST | `/api/start` | Start seeding |
| POST | `/api/stop` | Stop seeding |
| GET | `/api/stats` | Statistics |
| WS | `/ws` | Real-time WebSocket |
| GET/PUT | `/api/notifications/config` | Notification settings |
| POST | `/api/notifications/test` | Test notification |

## 🏗️ Architecture

- **Backend**: FastAPI (Python 3.12+) • WebSocket • asyncio • Pydantic
- **Frontend**: React 18 • Vite • TailwindCSS • Zustand
- **Container**: Docker multi-stage • Alpine Linux

## 📝 License

Apache License 2.0 - See [LICENSE](LICENSE)

## ⚠️ Disclaimer

PyJOAL is designed for **educational and legitimate use only**.

Using it to maintain ratio on copyrighted content may be **illegal** in some countries. You are solely responsible for the use of this software.

---

**Made with ❤️ by PyJOAL Contributors**
