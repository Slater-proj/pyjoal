# PyJOAL - BitTorrent Ratio Client 🚀

**PyJOAL** est un client BitTorrent intelligent qui émule différents clients pour maintenir un ratio de seed sans consommer de bande passante réelle. Écrit entièrement en Python avec une interface web moderne React.

## ✨ Fonctionnalités

### 🎭 Émulation Avancée
- **Multi-clients** - qBittorrent, Deluge, Transmission avec mise à jour automatique
- **Anti-détection** - Patterns d'activité naturels et timing désynchronisé
- **Variations réalistes** - Fluctuations de vitesse simulant un vrai client

### 🎨 Interface Moderne
- **React 18 + TailwindCSS** - Design responsive et élégant
- **Temps réel** - WebSocket pour mises à jour instantanées
- **Drag & Drop** - Glissez vos fichiers .torrent directement
- **Dashboard complet** - Stats, historique, logs en temps réel

### 🔧 Configuration Flexible
- **Ratio upload** - Cible configurable avec archivage automatique
- **Limite de temps** - Durée de seed maximale par torrent
- **Proxy support** - HTTP proxy intégré
- **Discrétion avancée** - Jitter, intervalles, variations configurables

### 🐳 Production Ready
- **Docker optimisé** - Image multi-stage (~150MB)
- **Sécurité** - Token API + path obfuscation
- **Auto-update** - Clients BitTorrent mis à jour automatiquement

## 🚀 Démarrage Rapide

### Avec Docker Compose (Recommandé)

```bash
# Cloner le dépôt
git clone https://github.com/Slater-proj/pyjoal.git
cd pyjoal

# Créer le fichier .env
cp .env.example .env
# Éditez .env avec vos valeurs

# Lancer
docker-compose up -d

# L'interface est disponible sur http://localhost:8080/{UI_PATH_PREFIX}/ui/
```

### Docker Run

```bash
docker run -d \
  --name pyjoal \
  -p 8080:8080 \
  -e SECRET_TOKEN=votre_token_secret_complexe \
  -e UI_PATH_PREFIX=chemin_secret \
  -v $(pwd)/torrents:/app/torrents \
  -v $(pwd)/config:/app/config \
  --restart unless-stopped \
  adminclem/pyjoal:latest
```

## ⚙️ Configuration

### Variables d'Environnement Requises

| Variable | Description |
|----------|-------------|
| `SECRET_TOKEN` | Token d'authentification API (obligatoire) |
| `UI_PATH_PREFIX` | Chemin secret pour l'interface (obligatoire) |

### Variables Optionnelles

| Variable | Défaut | Description |
|----------|--------|-------------|
| `PORT` | 8080 | Port du serveur |
| `MIN_UPLOAD_RATE` | 30 | Vitesse upload min (KB/s) |
| `MAX_UPLOAD_RATE` | 160 | Vitesse upload max (KB/s) |
| `SIMULTANEOUS_SEED` | 20 | Torrents simultanés max |
| `HTTP_PROXY_HOST` | - | Hôte du proxy HTTP |
| `HTTP_PROXY_PORT` | - | Port du proxy HTTP |

### Fichier .env

```bash
# Requis
SECRET_TOKEN=votre_token_secret_tres_complexe
UI_PATH_PREFIX=chemin_secret_unique

# Optionnel
PORT=8080
MIN_UPLOAD_RATE=30
MAX_UPLOAD_RATE=160
SIMULTANEOUS_SEED=20
```

### Configuration JSON (config/config.json)

Créé automatiquement au premier lancement, modifiable via l'interface :

```json
{
  "minUploadRate": 30,
  "maxUploadRate": 160,
  "simultaneousSeed": 20,
  "client": "qbittorrent-1.8.2.client",
  "keepTorrentWithZeroLeechers": true,
  "uploadRatioTarget": -1.0,
  "seedingDurationLimit": -1.0,
  "announceInterval": 15,
  "announceJitter": 15,
  "enableSpeedVariation": true,
  "speedVariationPercent": 15
}
```

## 🎭 Discrétion & Anti-détection

PyJOAL intègre des mécanismes avancés pour éviter la détection :

### Fonctionnalités
- **Désynchronisation temporelle** - Chaque torrent a son propre cycle avec jitter aléatoire
- **Variations de vitesse** - Fluctuations naturelles simulant un vrai client
- **Patterns d'activité** - Simulation d'heures d'activité utilisateur
- **Anti-fingerprinting** - Suppression des patterns synchrones détectables

### Paramètres de Discrétion

| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| Announce Interval | 15s | Intervalle de base entre annonces |
| Announce Jitter | ±15s | Variation aléatoire |
| Speed Variation | ±15% | Fluctuation des vitesses |
| Min Stats Update | 2s | Délai minimum entre MAJ |

### Recommandations
- Utilisez des vitesses réalistes (30-160 KB/s)
- Activez toujours les variations de vitesse
- Configurez un jitter approprié (15-30s)
- Limitez le nombre de torrents simultanés

## 🔒 Sécurité

L'interface est protégée par :

1. **Path obfuscation** - URL masquée via `UI_PATH_PREFIX`
2. **Token API** - Authentification requise sur toutes les requêtes
3. **Referrer Policy** - Protection contre les fuites d'URL

**Accès UI :** `http://localhost:8080/{UI_PATH_PREFIX}/ui/`

## 📡 API REST

Documentation Swagger interactive : `http://localhost:8080/docs`

### Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET/PUT | `/api/config` | Configuration |
| GET/POST/DELETE | `/api/torrents` | Gestion torrents |
| POST | `/api/start` | Démarrer seeding |
| POST | `/api/stop` | Arrêter seeding |
| GET | `/api/stats` | Statistiques |
| GET | `/api/history` | Historique |
| WS | `/ws` | WebSocket temps réel |

## 🎯 Utilisation

1. **Lancez** le container Docker
2. **Accédez** à l'interface : `http://localhost:8080/{UI_PATH_PREFIX}/ui/`
3. **Glissez** vos fichiers `.torrent` dans l'interface
4. **Configurez** vos paramètres (optionnel)
5. **Cliquez** sur "START SEEDING"
6. **Suivez** vos stats en temps réel

## 🔄 Mise à jour des Clients

Les définitions de clients BitTorrent sont **mises à jour automatiquement** au démarrage.

**Clients supportés :**
- qBittorrent (dernière stable)
- Deluge (dernière stable)  
- Transmission (dernière stable)

**Mise à jour manuelle :**
```bash
python scripts/update_clients.py
```

## 📁 Structure des Volumes

| Volume | Description |
|--------|-------------|
| `/app/torrents` | Fichiers .torrent à seeder |
| `/app/config` | Configuration (config.json) |
| `/app/clients` | Définitions clients (.client) |

## 🏗️ Architecture

- **Backend** : FastAPI (Python 3.11+) • WebSocket • asyncio • Pydantic
- **Frontend** : React 18 • Vite • TailwindCSS • Zustand
- **Container** : Docker multi-stage • Alpine Linux

## 🐳 Build Local

```bash
# Build l'image
docker build -t pyjoal:local .

# Ou avec docker-compose
docker-compose build
```

## 🤝 Contribution

1. Fork le projet
2. Créez une branche (`git checkout -b feature/nom`)
3. Committez (`git commit -m 'Ajout fonctionnalité'`)
4. Push (`git push origin feature/nom`)
5. Ouvrez une Pull Request

## 📝 Licence

Apache License 2.0 - Voir [LICENSE](LICENSE)

## ⚠️ Avertissement

PyJOAL est conçu pour un usage **éducatif et légitime uniquement**.

L'utilisation pour maintenir un ratio sur du contenu protégé par des droits d'auteur peut être **illégale** dans certains pays. Vous êtes seul responsable de l'utilisation de ce logiciel.

---

**Made with ❤️ by PyJOAL Contributors**

Pour les questions ou suggestions, ouvrez une issue sur GitHub.
