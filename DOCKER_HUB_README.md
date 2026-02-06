# PyJOAL - BitTorrent Ratio Client 🚀

**PyJOAL** is a smart BitTorrent client that emulates various clients to maintain seed ratio without consuming real bandwidth.

## ✨ Features

- 🎭 **Multi-client emulation** - qBittorrent, Deluge, Transmission
- 🎨 **Modern Web interface** - React 18 + TailwindCSS responsive
- ⚡ **Real-time** - WebSocket for instant updates
- 📤 **Drag & Drop** - Drop your .torrent files
- 🎯 **Flexible config** - Ratio, duration, proxy
- 🔄 **Auto-update clients** - Automatic client updates
- 🛡️ **Anti-detection** - Natural activity patterns
- 🐳 **Docker Ready** - Optimized image (~150MB)
- 📨 **Notifications** - Gotify + webhook alerts
- 💾 **Stats persistence** - Survives container restarts
- 🔐 **Secure** - API token + path obfuscation

## 🚀 Docker Usage

### Docker Compose (Recommended)

```yaml
services:
  pyjoal:
    image: adminclem/pyjoal:latest
    ports:
      - "8080:8080"
    environment:
      - SECRET_TOKEN=your_complex_secret_token
      - UI_PATH_PREFIX=secret_path
      - MIN_UPLOAD_RATE=30
      - MAX_UPLOAD_RATE=160
      - TZ=Europe/Paris
    volumes:
      - ./torrents:/app/torrents
      - ./config:/app/config
      - ./clients:/app/clients
    restart: unless-stopped
```

### Docker Run

```bash
docker run -d \
  --name pyjoal \
  -p 8080:8080 \
  -e SECRET_TOKEN=your_secret_token \
  -e UI_PATH_PREFIX=admin \
  -e MIN_UPLOAD_RATE=30 \
  -e MAX_UPLOAD_RATE=160 \
  -v $(pwd)/torrents:/app/torrents \
  -v $(pwd)/config:/app/config \
  --restart unless-stopped \
  adminclem/pyjoal:latest
```

## 📁 Volume Structure

| Volume | Description |
|--------|-------------|
| `/app/torrents` | .torrent files to seed |
| `/app/config` | Configuration (config.json) |
| `/app/clients` | BitTorrent client definitions |

## 🔧 Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `SECRET_TOKEN` | API authentication token |
| `UI_PATH_PREFIX` | Secret prefix for interface |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8080 | Server port |
| `MIN_UPLOAD_RATE` | 30 | Min upload speed (KB/s) |
| `MAX_UPLOAD_RATE` | 160 | Max upload speed (KB/s) |
| `SIMULTANEOUS_SEED` | 20 | Simultaneous torrents |
| `TZ` | Europe/Paris | Timezone for logs |

## 🎯 Interface Access

Once started, the interface is available at:

```
http://localhost:8080/{UI_PATH_PREFIX}/ui/
```

## 📊 Main Features

- **Dashboard** - Overview with real-time statistics
- **Torrents** - Torrent management with drag & drop
- **History** - Complete announce history
- **Settings** - Client, speed, proxy configuration
- **Logs** - Real-time log console
- **Notifications** - Gotify/webhook alerts configuration

## 🛡️ Anti-detection

PyJOAL integrates advanced mechanisms:

- Temporal desynchronization per torrent
- Realistic speed variations
- Natural activity patterns
- Configurable announce jitter

## 🔗 Links

- **GitHub**: https://github.com/Slater-proj/pyjoal
- **Documentation**: https://github.com/Slater-proj/pyjoal/blob/master/README.md
- **Issues**: https://github.com/Slater-proj/pyjoal/issues

## 📄 License

Apache License 2.0 - see [LICENSE](https://github.com/Slater-proj/pyjoal/blob/master/LICENSE)

---

**Made with ❤️ by PyJOAL Contributors**
