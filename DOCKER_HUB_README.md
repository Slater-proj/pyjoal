# PyJOAL - BitTorrent Ratio Client 🚀

**PyJOAL** est une réécriture Python moderne de [JOAL](https://github.com/anthonyraymond/joal) (Jack Of All Leechers) - Un client qui émule différents clients BitTorrent pour maintenir un ratio de seed sans consommer de bande passante réelle.

## ✨ Fonctionnalités

- 🎭 **Émulation multi-clients** - qBittorrent, Deluge, Transmission, µTorrent
- 🎨 **Interface Web moderne** - React 18 + TailwindCSS avec design responsive  
- ⚡ **Temps réel** - WebSocket pour mises à jour instantanées
- 📤 **Drag & Drop** - Glissez vos fichiers .torrent directement
- 🎯 **Configuration flexible** - Ratio upload, limite de temps, proxy
- 🔄 **Auto-update clients** - Téléchargement automatique des dernières versions
- 📊 **Tableau de bord** - Stats détaillées et historique des annonces
- 🐳 **Docker Ready** - Image optimisée multi-stage
- 🔐 **Sécurisé** - Token API et path obfuscation

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
  -v $(pwd)/clients:/app/clients \
  --restart unless-stopped \
  adminclem/pyjoal:latest
```

## 📁 Structure des volumes

- `/app/torrents` - Dossier pour vos fichiers .torrent
- `/app/clients` - Clients BitTorrent (.client files) 

## 🔧 Variables d'environnement

| Variable | Description | Défaut | Requis |
|----------|-------------|--------|--------|
| `SECRET_TOKEN` | Token d'authentification API | - | ✅ |
| `UI_PATH_PREFIX` | Préfixe secret pour l'interface | `ui` | ❌ |
| `MIN_UPLOAD_RATE` | Vitesse upload min (KB/s) | `30` | ❌ |
| `MAX_UPLOAD_RATE` | Vitesse upload max (KB/s) | `160` | ❌ |
| `PROXY_HOST` | Hôte proxy | - | ❌ |
| `PROXY_PORT` | Port proxy | - | ❌ |
| `ANNOUNCE_INTERVAL` | Intervalle annonces (min) | `15` | ❌ |

## 🎯 Accès à l'interface

Une fois démarré, l'interface est accessible sur :
`http://localhost:8080/{UI_PATH_PREFIX}/ui/`

## 📊 Fonctionnalités principales

- **Dashboard** - Vue d'ensemble avec statistiques temps réel
- **Torrents** - Gestion des torrents actifs avec drag & drop
- **Historique** - Historique complet des annonces avec filtrage
- **Configuration** - Paramètres clients, vitesses, proxy
- **Logs** - Console de logs en temps réel

## 🔗 Liens utiles

- **GitHub** : https://github.com/adminclem/pyjoal
- **Documentation** : https://github.com/adminclem/pyjoal/blob/master/README.md
- **Issues** : https://github.com/adminclem/pyjoal/issues

## 📄 Licence

MIT License - voir [LICENSE](https://github.com/adminclem/pyjoal/blob/master/LICENSE)
