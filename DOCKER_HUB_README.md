# PyJOAL - BitTorrent Ratio Manager 🚀

**PyJOAL** is a modern Python rewrite of [JOAL](https://github.com/anthonyraymond/joal) - A BitTorrent client emulator designed to maintain your seeding ratio without consuming real bandwidth.

Perfect for maintaining ratios on private trackers by simulating realistic seeding activity.

---

## 🌟 Features

- 🎭 **Multi-client emulation** - qBittorrent, Deluge, Transmission, µTorrent
- 🎨 **Modern Web UI** - Responsive React interface with dark theme
- ⚡ **Real-time updates** - WebSocket for instant statistics
- 📤 **Drag & Drop** - Drop your .torrent files directly
- 🎯 **Flexible configuration** - Upload ratio targets, time limits, proxy support
- 🔄 **Auto-update clients** - Latest client definitions downloaded on startup
- 📊 **Dashboard** - Detailed stats and announce history
- 🔐 **Secure** - API token and path obfuscation

---

## 🚀 Quick Start

### Docker Run (Simple)

```bash
docker run -d \
  --name pyjoal \
  -p 8080:8080 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/torrents:/app/torrents \
  -v $(pwd)/clients:/app/clients \
  -e SECRET_TOKEN=your_secret_token_here \
  -e UI_PATH_PREFIX=secret-path \
  -e MIN_UPLOAD_RATE=30 \
  -e MAX_UPLOAD_RATE=160 \
  --restart unless-stopped \
  youruser/pyjoal:latest
```

Access the interface at: `http://localhost:8080/secret-path/ui/`

### Docker Compose (Recommended)

Create a `docker-compose.yml`:

```yaml
services:
  pyjoal:
    image: youruser/pyjoal:latest
    container_name: pyjoal
    restart: unless-stopped
    
    ports:
      - "8080:8080"
    
    volumes:
      - ./config:/app/config      # Configuration
      - ./torrents:/app/torrents  # Your .torrent files
      - ./clients:/app/clients    # Client definitions (auto-updated)
    
    environment:
      # 🔐 Security (REQUIRED)
      - SECRET_TOKEN=your_secret_token_here
      - UI_PATH_PREFIX=secret-path
      
      # ⚙️ BitTorrent Configuration
      - MIN_UPLOAD_RATE=30          # KB/s
      - MAX_UPLOAD_RATE=160         # KB/s
      - SIMULTANEOUS_SEED=20        # Max concurrent torrents
      
      # 🎯 Optional: Ratio & Time Limits
      - UPLOAD_RATIO_TARGET=-1.0    # -1 = unlimited
      - SEEDING_DURATION_LIMIT=-1.0 # -1 = unlimited (hours)
      
      # 🌐 Optional: Proxy
      # - HTTP_PROXY_HOST=proxy.example.com
      # - HTTP_PROXY_PORT=8080
```

Then run:

```bash
docker-compose up -d
```

---

## 📁 Volume Mapping

| Path | Description | Required |
|------|-------------|----------|
| `/app/config` | Configuration files (`config.json`) | ✅ |
| `/app/torrents` | Your `.torrent` files (drag & drop here or via UI) | ✅ |
| `/app/clients` | Client definitions (auto-updated on startup) | ⚠️ Recommended |

**Note**: The `archived` subfolder in `/app/torrents` stores deleted torrents.

---

## ⚙️ Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_TOKEN` | API authentication token | `my-super-secret-token-123` |
| `UI_PATH_PREFIX` | URL path for UI obfuscation | `secret-path` |

### BitTorrent Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_UPLOAD_RATE` | `30` | Minimum upload speed (KB/s) |
| `MAX_UPLOAD_RATE` | `160` | Maximum upload speed (KB/s) |
| `SIMULTANEOUS_SEED` | `20` | Max concurrent torrents |
| `KEEP_TORRENT_WITH_ZERO_LEECHERS` | `true` | Keep seeding when no leechers |
| `UPLOAD_RATIO_TARGET` | `-1.0` | Upload ratio goal (`-1` = unlimited) |
| `SEEDING_DURATION_LIMIT` | `-1.0` | Max seed time in hours (`-1` = unlimited) |
| `DEFAULT_CLIENT` | `qbittorrent-1.3.3.client` | Default client emulation |

### Proxy (Optional)

| Variable | Description |
|----------|-------------|
| `HTTP_PROXY_HOST` | Proxy hostname/IP |
| `HTTP_PROXY_PORT` | Proxy port |

### Server

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | Internal server port |
| `DEBUG` | `false` | Enable debug logging |

---

## 🎯 Usage

1. **Start the container**:
   ```bash
   docker-compose up -d
   ```

2. **Access the UI**:
   - Navigate to `http://localhost:8080/secret-path/ui/`
   - Replace `secret-path` with your `UI_PATH_PREFIX`

3. **Add torrents**:
   - Click the upload button or drag & drop `.torrent` files
   - Place files directly in the `./torrents/` volume

4. **Configure**:
   - Click the ⚙️ Settings icon to adjust:
     - Upload speed ranges
     - Client emulation
     - Ratio targets
     - Seeding duration limits

5. **Monitor**:
   - View real-time upload statistics
   - Check seeding progress and ratios
   - View announce history in the Logs panel

---

## 🔒 Security Best Practices

1. **Use a strong SECRET_TOKEN**:
   ```bash
   openssl rand -hex 32
   ```

2. **Use a non-obvious UI_PATH_PREFIX**:
   - ❌ Bad: `ui`, `admin`, `joal`
   - ✅ Good: `my-secret-path-12345`

3. **Don't expose to public internet without a reverse proxy**:
   - Use nginx/Caddy with HTTPS
   - Add authentication layer

4. **Keep client definitions updated**:
   - Clients auto-update on container restart
   - Or manually run: `docker exec pyjoal python scripts/update_clients.py`

---

## 📊 Dashboard Features

- **Real-time stats**: Current upload speed, ratio, seeding time
- **Torrent table**: Name, status, uploaded, downloaded, ratio, duration
- **Resizable columns**: Double-click headers to auto-fit
- **Drag columns**: Reorder by dragging headers
- **Action buttons**: Start/stop individual torrents, delete
- **Log console**: View announce history and events
- **Responsive**: Optimized for 1080p+ displays

---

## 🐛 Troubleshooting

### Container won't start
```bash
# Check logs
docker logs pyjoal

# Common issues:
# - Missing SECRET_TOKEN or UI_PATH_PREFIX
# - Port 8080 already in use
# - Volume permission issues
```

### Can't access UI
- Check your `UI_PATH_PREFIX` - it's case-sensitive
- Verify port mapping: `docker ps | grep pyjoal`
- Try: `http://localhost:8080/health` (should return 200)

### Torrents not announcing
- Verify tracker is reachable: check logs
- Try different client emulation in settings
- Check proxy settings if using one
- Ensure `.torrent` files are valid

### Update clients manually
```bash
docker exec pyjoal python scripts/update_clients.py
```

---

## 🔄 Updates

Pull the latest image:

```bash
docker-compose pull
docker-compose up -d
```

Or for `docker run`:

```bash
docker pull youruser/pyjoal:latest
docker stop pyjoal && docker rm pyjoal
# Then re-run your docker run command
```

---

## 📝 Configuration File

On first start, a `config/config.json` is created with your environment variables. You can edit it manually:

```json
{
  "minUploadRate": 30,
  "maxUploadRate": 160,
  "simultaneousSeed": 20,
  "client": "qbittorrent-1.3.3.client",
  "keepTorrentWithZeroLeechers": true,
  "uploadRatioTarget": -1.0,
  "seedingDurationLimit": -1.0
}
```

Changes via UI override the file automatically.

---

## 🛠️ Advanced: Reverse Proxy

### Nginx Example

```nginx
server {
    listen 443 ssl http2;
    server_name pyjoal.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Caddy Example

```caddyfile
pyjoal.yourdomain.com {
    reverse_proxy localhost:8080
}
```

---

## 📖 Client Emulation

PyJOAL can emulate various BitTorrent clients:

- **qBittorrent** 1.3.3, 1.3.3, 1.3.3
- **Deluge** 1.3.3
- **Transmission** 1.3.3
- **µTorrent** and more...

Client definitions are automatically updated from the official repository on container start.

---

## ⚠️ Disclaimer

This tool is for educational purposes and maintaining legitimate ratios on private trackers where you have actual files. 

**Do not use this to:**
- Cheat on trackers
- Claim credit for files you don't have
- Violate tracker rules

Always follow your tracker's terms of service.

---

## 🤝 Contributing

Found a bug? Have a feature request?

- **GitHub**: [yourrepo/pyjoal](https://github.com/yourrepo/pyjoal)
- **Issues**: Report bugs and request features
- **Pull Requests**: Contributions welcome!

---

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the LICENSE file for details.

---

## 🙏 Credits

- Original [JOAL](https://github.com/anthonyraymond/joal) by Anthony Raymond
- PyJOAL - Modern Python rewrite with React UI

---

**⭐ If you find this useful, please star the repo!**
