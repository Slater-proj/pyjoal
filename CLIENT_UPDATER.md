# 🔄 BitTorrent Client Auto-Updater

Automatically fetch and generate the latest BitTorrent client definitions.

## 📋 Description

This script checks GitHub repositories for the latest versions of popular BitTorrent clients and generates `.client` files that JOAL can use to emulate these clients.

### Supported Clients

- **qBittorrent** - Most popular client
- **Deluge** - Lightweight and efficient
- **Transmission** - Cross-platform client

## 🚀 Usage

### Automatic Update (Docker)

When starting the Docker container, client definitions are **automatically updated** to the latest versions:

```bash
docker-compose up -d
# or
docker run pyjoal:latest
```

The container will fetch the latest versions on startup and log:
```
🔄 Updating BitTorrent client definitions...
✅ Client definitions ready
```

### Manual Update in Running Container

To update clients in a running container:

```bash
docker exec pyjoal python /app/update_clients.py
```

### Manual Update (Local)

**Windows:**
```bash
update_clients.bat
```

**Linux/Mac:**
```bash
chmod +x update_clients.sh
./update_clients.sh
```

**Python directly:**
```bash
pip install requests
python update_clients.py
```

### Automated Updates (GitHub Actions)

The workflow `.github/workflows/update-clients.yml` runs automatically:
- **Every Monday at 9:00 AM UTC**
- Can be triggered manually from the GitHub Actions tab

When new versions are found, it creates a Pull Request for review.

## 📁 Generated Files

Files are created in the `clients/` directory with the format:
```
{client}-{version}.client
```

Example:
```
qbittorrent-5.1.4.client
deluge-2.2.1.client
transmission-4.0.6.client
```

### File Structure

```json
{
  "name": "qBittorrent",
  "version": "5.1.4",
  "peerIdPattern": {
    "prefix": "-qB5140-"
  },
  "userAgent": "qBittorrent/5.1.4",
  "numwant": 200,
  "requestHeaders": {
    "Accept-Encoding": "gzip"
  }
}
```

## 🔧 How It Works

1. **Fetches latest releases** from GitHub API
2. **Parses version numbers** (handles various formats)
3. **Generates peer ID** following BitTorrent conventions
4. **Creates .client file** with proper configuration
5. **Keeps old versions** for backward compatibility

### Peer ID Format

Each client has a specific peer ID pattern:

- **qBittorrent**: `-qB{version}-` → `-qB5140-` (v5.1.4)
- **Deluge**: `-DE{version}s-` → `-DE221s-` (v2.2.1)
- **Transmission**: `-TR{version}Z-` → `-TR406Z-` (v4.0.6)

## ⚙️ Configuration

To add a new client, edit `update_clients.py`:

```python
CLIENTS = {
    "newclient": {
        "name": "NewClient",
        "repo": "owner/repo",
        "peer_id_format": lambda v: f"-NC{v.replace('.', '')[:3]}-",
        "user_agent_format": lambda v: f"NewClient/{v}",
        "numwant": 200,
        "headers": {"Accept-Encoding": "gzip"}
    }
}
```

## 🔍 Troubleshooting

### Rate Limiting

GitHub API has rate limits (60 requests/hour unauthenticated). To increase this:

```python
headers = {
    "Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN')}"
}
response = requests.get(url, headers=headers, timeout=10)
```

### No Releases Found

Some repositories use tags instead of releases. The script handles both automatically.

### Version Parsing Issues

The script cleans common prefixes/suffixes:
- Removes `v`, `release-`, `deluge-` prefixes
- Removes `.dev0` development suffixes

## 📊 Example Output

```
🔄 Fetching latest BitTorrent client versions...

📥 Checking qBittorrent...
   Latest version: 5.1.4
✅ Generated: qbittorrent-5.1.4.client

📥 Checking Deluge...
   Latest version: 2.2.1
✅ Generated: deluge-2.2.1.client

📥 Checking Transmission...
   Latest version: 4.0.6
   ✓ Already exists

============================================================
✨ New versions generated:
   • qBittorrent: 5.1.4
   • Deluge: 2.2.1

💡 Old versions were kept. Delete them manually if needed.
============================================================
```

## 🗑️ Cleaning Old Versions

Old versions are kept for compatibility. To remove them:

```bash
# Keep only the latest version of each client
cd clients/
ls -t qbittorrent-*.client | tail -n +2 | xargs rm
ls -t deluge-*.client | tail -n +2 | xargs rm
ls -t transmission-*.client | tail -n +2 | xargs rm
```

## 🤝 Contributing

To add support for more clients:
1. Find the GitHub repository
2. Add configuration to `CLIENTS` dict
3. Test with `python update_clients.py`
4. Submit a PR

Popular clients to add:
- µTorrent (proprietary, no public API)
- Vuze/Azureus
- BiglyBT
- rTorrent
- libtorrent
