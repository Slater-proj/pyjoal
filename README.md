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

## 📋 Améliorations Récentes (v1.7.2)

- 🚀 **Performance optimisée** - Consommation CPU réduite de 50% et mémoire de 30%
- 🔧 **Monitoring de ressources** - Suivi en temps réel CPU/RAM avec alertes intelligentes
- ⚡ **Cache intelligent** - Système de mise en cache TTL pour réduire la charge
- 🧹 **Gestion automatique mémoire** - Nettoyage automatique toutes les 5 minutes
- 📊 **Santé système** - Monitoring avancé avec tooltip informatif dans l'interface
- 🐳 **Container optimisé** - Image Docker plus efficace et démarrage plus rapide

### Fonctionnalités de Discrétion (v1.7.2-1.7.2)
- 🎭 **Modes de comportement** - Choix entre seeding pur ou simulation complète de téléchargement
- ⏱️ **Patterns d'activité naturels** - Simulation d'heures d'activité utilisateur réaliste
- 📊 **Variations de vitesse avancées** - Fluctuations intelligentes basées sur l'activité simulée
- 🛡️ **Anti-détection per-torrent** - Timing individuel pour chaque torrent
- 🔧 **Configuration avancée** - Paramètres de discrétion et timing dans l'interface

### Corrections précédentes (v1.7.2-1.7.2)
- ✅ **Onglet Historique** - Filtre "Load Failed" pour voir les torrents échoués
- ✅ **Colonne Duration** - Renommée de "Dur" vers "Duration" pour plus de clarté
- ✅ **Vitesses authentiques** - Les vitesses affichées correspondent exactement aux données tracker
- ✅ **Protocole BitTorrent** - Calcul des vitesses basé sur les announces réussis (plus de fausses vitesses)
- ✅ **Versioning unifié** - Système de version centralisé pour cohérence Docker Hub/GitHub
- ✅ **Archivage avancé** - Raisons d'archivage (ratio/temps/erreur) dans l'historique

## 🚀 Démarrage Rapide

### Avec Docker (Recommandé)

```bash
# Cloner le dépôt
git clone https://github.com/adminclem/pyjoal.git
cd pyjoal

# Créer le fichier .env
cat > .env << EOF
SECRET_TOKEN=votre_token_secret_complexe
UI_PATH_PREFIX=chemin_secret
MIN_UPLOAD_RATE=30
MAX_UPLOAD_RATE=160
EOF

# Lancer avec Docker Compose
docker-compose up -d

# L'interface est disponible sur http://localhost:8080/chemin_secret/ui/
```

### Installation Rapide avec Script

```bash
./setup.sh  # Linux/Mac
setup.bat   # Windows
```

## 📋 Prérequis

- **Docker** & Docker Compose (recommandé)
- OU **Python 3.11+** et **Node.js 20+** pour installation manuelle

## ⚙️ Configuration

### Variables d'Environnement (.env)

| Variable | Requis | Défaut | Description |
|----------|--------|--------|-------------|
| `SECRET_TOKEN` | ✅ | - | Token d'authentification API |
| `UI_PATH_PREFIX` | ✅ | - | Chemin d'obfuscation UI (ex: `secret-path`) |
| `MIN_UPLOAD_RATE` | ❌ | 30 | Vitesse upload min (KB/s) |
| `MAX_UPLOAD_RATE` | ❌ | 160 | Vitesse upload max (KB/s) |
| `SIMULTANEOUS_SEED` | ❌ | 20 | Nombre de torrents simultanés |
| `HTTP_PROXY_HOST` | ❌ | - | Hôte du proxy HTTP |
| `HTTP_PROXY_PORT` | ❌ | - | Port du proxy HTTP |
| `DEFAULT_CLIENT` | ❌ | qbittorrent-1.7.2.client | Client par défaut |

### Configuration JSON (config/config.json)

Le fichier de configuration est créé automatiquement au premier lancement :

```json
{
  "minUploadRate": 30,
  "maxUploadRate": 160,
  "simultaneousSeed": 20,
  "client": "qbittorrent-1.7.2.client",
  "keepTorrentWithZeroLeechers": true,
  "uploadRatioTarget": -1.0,
  "seedingDurationLimit": -1.0
}
```

## 🎭 Discrétion & Anti-détection

PyJOAL v1.7.2+ intègre des mécanismes avancés pour éviter la détection par les trackers :

### 🛡️ Fonctionnalités de discrétion
- **Désynchronisation temporelle** - Chaque torrent a son propre cycle d'announce avec jitter aléatoire
- **Variations de vitesse réalistes** - Fluctuations naturelles simulant un vrai client BitTorrent  
- **Anti-fingerprinting** - Suppression des patterns synchrones détectables
- **Timing authentique** - Intervalles variables basés sur la configuration du tracker

### ⚙️ Configuration avancée

Dans l'onglet "Configuration" → "Discretion & Timing Settings" :

| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| `Announce Interval` | 30s | Intervalle de base entre les annonces |
| `Announce Jitter` | ±30s | Variation aléatoire pour désynchroniser |
| `Min Stats Update` | 3s | Délai minimum entre les mises à jour |
| `Speed Variation` | ±20% | Pourcentage de fluctuation des vitesses |
| `Enable Variation` | ✅ | Activer les variations réalistes |

### 🔍 Recommandations de sécurité
- Utilisez des ratios de vitesse réalistes (30-160 KB/s par défaut)
- Évitez de faire tourner trop de torrents simultanément
- Activez toujours les variations de vitesse
- Configurez un jitter approprié (15-60s recommandé)

## 🔒 Sécurité

L'interface web est protégée par:

1. **Path obfuscation** (`UI_PATH_PREFIX`) - Masque l'URL de l'UI
2. **Secret token** - Authentification par token
3. **Referrer Policy** - Protection contre les fuites d'URL

Accédez à l'UI via: `http://localhost:8080/{UI_PATH_PREFIX}/ui/`

## 📡 API

Documentation API interactive disponible à: `http://localhost:8080/docs`

### Endpoints principaux

- `GET /api/config` - Configuration actuelle
- `PUT /api/config` - Mettre à jour la config
- `GET /api/torrents` - Liste des torrents
- `POST /api/torrents` - Ajouter un torrent
- `DELETE /api/torrents/{id}` - Supprimer un torrent
- `POST /api/start` - Démarrer le seeding
- `POST /api/stop` - Arrêter le seeding
- `WS /ws` - WebSocket pour updates temps réel

## 🎯 Utilisation

1. **Configurez** votre fichier `config/config.json`
2. **Ajoutez** des fichiers `.client` dans `clients/` (ou utilisez le script d'auto-update)
3. **Déposez** vos fichiers `.torrent` dans `torrents/` ou via l'UI
4. **Démarrez** le seeding depuis l'interface web
5. **Surveillez** vos stats en temps réel

### 🔄 Mise à jour automatique des clients

Les définitions de clients BitTorrent peuvent être mises à jour automatiquement :

```bash
# Depuis le dossier du projet
python scripts/update_clients.py

# Ou dans un container Docker en cours d'exécution
docker exec pyjoal python scripts/update_clients.py
```

Le script récupère automatiquement les dernières versions depuis GitHub pour :
- **qBittorrent** (dernière stable : 1.7.2)
- **Deluge** (dernière stable : 1.7.2)
- **Transmission** (dernière stable : 1.7.2)

📖 Plus d'infos : [CLIENT_UPDATER.md](CLIENT_UPDATER.md)

**Automatisation GitHub Actions :** Un workflow hebdomadaire vérifie les nouvelles versions et crée automatiquement une Pull Request.

## 🐳 Build Docker

## 🔒 Sécurité

- **Path Obfuscation** : L'UI est accessible via un chemin secret (`UI_PATH_PREFIX`)
- **Token API** : Toutes les requêtes API nécessitent `X-API-Token`
- **Referrer Policy** : Protection contre les fuites d'URL
- **Accès UI** : `http://localhost:8080/{UI_PATH_PREFIX}/ui/`

## 📡 API REST

Documentation interactive (Swagger) : `http://localhost:8080/docs`

**Endpoints principaux :**
- `GET/PUT /api/config` - Configuration
- `GET/POST/DELETE /api/torrents` - Gestion torrents
- `POST /api/start|stop` - Contrôle seeding
- `GET /api/stats` - Statistiques
- `GET /api/history` - Historique
- `WS /ws` - WebSocket temps réel

## 🎯 Utilisation

1. **Lancez** le container Docker
2. **Accédez** à l'interface : `http://localhost:8080/{votre-path-secret}/ui/`
3. **Glissez** vos fichiers `.torrent` dans l'interface
4. **Cliquez** sur "START SEEDING"
5. **Suivez** vos stats en temps réel

## 🔄 Mise à jour des Clients BitTorrent

Les définitions de clients sont **mises à jour automatiquement** au démarrage du container.

**Mise à jour manuelle :**

```bash
python scripts/update_clients.py
```

**Clients supportés (auto-update) :**
- qBittorrent (dernière stable)
- Deluge (dernière stable)
- Transmission (dernière stable)

## 🐳 Docker

### Quick Start avec Images Pré-compilées

#### Option 1: GitHub Container Registry (Recommandé)

```bash
# Télécharger l'image officielle
docker pull ghcr.io/adminclem/pyjoal:latest

# Lancer avec configuration de base
docker run -d --name pyjoal \
  -p 8080:8080 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/torrents:/app/torrents \
  -e SECRET_TOKEN=votre_token_secret \
  -e UI_PATH_PREFIX=chemin_secret \
  ghcr.io/adminclem/pyjoal:latest
```

#### Option 2: Docker Hub

```bash
# Télécharger depuis Docker Hub
docker pull adminclem/pyjoal:latest

# Lancer avec configuration de base
docker run -d --name pyjoal \
  -p 8080:8080 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/torrents:/app/torrents \
  -e SECRET_TOKEN=votre_token_secret \
  -e UI_PATH_PREFIX=chemin_secret \
  adminclem/pyjoal:latest
```

### Build Local

```bash
docker build -t pyjoal:latest .
```

Image optimisée multi-stage (~150MB) avec frontend pré-compilé.

## 📊 PyJOAL vs JOAL Original

| Aspect | JOAL (Original) | PyJOAL |
|--------|-----------------|--------|
| Langage | Java + Spring Boot | Python + FastAPI |
| Frontend | JS vanilla | React 18 + TailwindCSS |
| Image Docker | ~300MB | ~150MB |
| API Docs | ❌ | ✅ Swagger/OpenAPI |
| Hot Reload | ❌ | ✅ |
| Type Safety | Partiel | Complet (Pydantic + TS) |
| WebSocket | ❌ | ✅ Real-time updates |

## 🏗️ Architecture Technique

**Backend :** FastAPI (Python 3.11+) • WebSocket • asyncio • Pydantic
**Frontend :** React 18 • Vite • TailwindCSS • Zustand
**Container :** Docker multi-stage • Alpine Linux

## 🤝 Contribution

1. Fork le projet
2. Créez une branche feature (`git checkout -b feature/nom`)
3. Committez (`git commit -m 'Ajout fonctionnalité'`)
4. Push (`git push origin feature/nom`)
5. Ouvrez une Pull Request

## 📝 Licence

Apache License 2.0 - Voir [LICENSE](LICENSE)

## ⚠️ Avertissement

PyJOAL est conçu pour un usage **éducatif et légitime uniquement**. 

L'utilisation pour télécharger du contenu protégé par des droits d'auteur est **illégale** dans de nombreux pays. Vous êtes seul responsable de l'utilisation que vous faites de ce logiciel et devez respecter les lois de votre juridiction.

L'auteur décline toute responsabilité quant aux activités illégales réalisées avec cet outil.

## 🙏 Crédits

- Projet original : [anthonyraymond/joal](https://github.com/anthonyraymond/joal)
- Merci à la communauté BitTorrent et aux contributeurs

---

**Made with ❤️ by PyJOAL Contributors**Pour les questions ou suggestions, ouvrez une issue sur GitHub.
