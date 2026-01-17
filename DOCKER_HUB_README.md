# PyJOAL - BitTorrent Ratio Client 🚀

**PyJOAL** est un client BitTorrent intelligent qui émule différents clients pour maintenir un ratio de seed sans consommer de bande passante réelle.

## ✨ Fonctionnalités

- 🎭 **Émulation multi-clients** - qBittorrent, Deluge, Transmission
- 🎨 **Interface Web moderne** - React 18 + TailwindCSS responsive
- ⚡ **Temps réel** - WebSocket pour mises à jour instantanées
- 📤 **Drag & Drop** - Glissez vos fichiers .torrent
- 🎯 **Configuration flexible** - Ratio, durée, proxy
- 🔄 **Auto-update clients** - Mise à jour automatique des clients
- 🛡️ **Anti-détection** - Patterns d'activité naturels
- 🐳 **Docker Ready** - Image optimisée (~150MB)
- 🔐 **Sécurisé** - Token API + path obfuscation

## 🚀 Utilisation Docker

### Docker Compose (Recommandé)

```yaml
version: '3.8'
services:
  pyjoal:
    image: adminclem/pyjoal:latest
    ports:
      - "8080:8080"
    environment:
      - SECRET_TOKEN=votre_token_secret_complexe
      - UI_PATH_PREFIX=chemin_secret
      - MIN_UPLOAD_RATE=30
      - MAX_UPLOAD_RATE=160
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
  -e SECRET_TOKEN=votre_token_secret \
  -e UI_PATH_PREFIX=admin \
  -e MIN_UPLOAD_RATE=30 \
  -e MAX_UPLOAD_RATE=160 \
  -v $(pwd)/torrents:/app/torrents \
  -v $(pwd)/config:/app/config \
  --restart unless-stopped \
  adminclem/pyjoal:latest
```

## 📁 Structure des Volumes

| Volume | Description |
|--------|-------------|
| `/app/torrents` | Fichiers .torrent à seeder |
| `/app/config` | Configuration (config.json) |
| `/app/clients` | Définitions clients BitTorrent |

## 🔧 Variables d'Environnement

### Requises

| Variable | Description |
|----------|-------------|
| `SECRET_TOKEN` | Token d'authentification API |
| `UI_PATH_PREFIX` | Préfixe secret pour l'interface |

### Optionnelles

| Variable | Défaut | Description |
|----------|--------|-------------|
| `PORT` | 8080 | Port du serveur |
| `MIN_UPLOAD_RATE` | 30 | Vitesse upload min (KB/s) |
| `MAX_UPLOAD_RATE` | 160 | Vitesse upload max (KB/s) |
| `SIMULTANEOUS_SEED` | 20 | Torrents simultanés |
| `HTTP_PROXY_HOST` | - | Hôte proxy |
| `HTTP_PROXY_PORT` | - | Port proxy |

## 🎯 Accès à l'Interface

Une fois démarré, l'interface est accessible sur :

```
http://localhost:8080/{UI_PATH_PREFIX}/ui/
```

## 📊 Fonctionnalités Principales

- **Dashboard** - Vue d'ensemble avec statistiques temps réel
- **Torrents** - Gestion des torrents avec drag & drop
- **Historique** - Historique complet des annonces
- **Configuration** - Paramètres clients, vitesses, proxy
- **Logs** - Console de logs en temps réel

## 🛡️ Anti-détection

PyJOAL intègre des mécanismes avancés :

- Désynchronisation temporelle par torrent
- Variations de vitesse réalistes
- Patterns d'activité naturels
- Jitter configurable sur les annonces

## 🔗 Liens

- **GitHub** : https://github.com/adminclem/pyjoal
- **Documentation** : https://github.com/adminclem/pyjoal/blob/master/README.md
- **Issues** : https://github.com/adminclem/pyjoal/issues

## 📄 Licence

Apache License 2.0 - voir [LICENSE](https://github.com/adminclem/pyjoal/blob/master/LICENSE)

---

**Made with ❤️ by PyJOAL Contributors**
