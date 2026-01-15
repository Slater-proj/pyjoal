# PyJOAL - BitTorrent Ratio Client

Une réécriture moderne et maintenable de JOAL (Jack Of All Leechers) - Un client qui émule différents clients BitTorrent pour maintenir un ratio de seed.

## 🚀 Fonctionnalités

- ✅ Émulation de multiples clients BitTorrent (qBittorrent, Deluge, Transmission, µTorrent, etc.)
- ✅ Interface Web moderne et responsive
- ✅ WebSocket pour les mises à jour en temps réel
- ✅ Gestion de torrents par drag & drop
- ✅ Configuration du ratio d'upload
- ✅ Support proxy HTTP/HTTPS
- ✅ Multi-torrents simultanés
- ✅ API REST complète
- ✅ Architecture propre et extensible

## 🏗️ Architecture

### Backend
- **FastAPI** (Python 3.11+) - Framework web async moderne
- **WebSockets** - Communication temps réel
- **asyncio** - Gestion asynchrone des annonces tracker
- **Pydantic** - Validation des données

### Frontend
- **React 18** - UI moderne et réactive
- **Vite** - Build ultra-rapide
- **TailwindCSS** - Styling moderne
- **WebSocket** - Updates en temps réel

### Déploiement
- **Docker** - Multi-stage build optimisé
- **Docker Compose** - Orchestration simple

## 📦 Installation Rapide

### Avec Docker (Recommandé)

```bash
docker run -d \
  -p 8080:8080 \
  -v ./config:/app/config \
  -v ./torrents:/app/torrents \
  -v ./clients:/app/clients \
  -e SECRET_TOKEN="votre_token_secret" \
  -e UI_PATH_PREFIX="chemin_secret" \
  --name pyjoal \
  pyjoal:latest
```

> 💡 **Les clients BitTorrent sont automatiquement mis à jour au démarrage du conteneur !**  
> Les dernières versions de qBittorrent, Deluge et Transmission sont téléchargées depuis GitHub.

### Avec Docker Compose

```yaml
version: '3.8'
services:
  joal:
    image: pyjoal:latest
    container_name: pyjoal
    ports:
      - "8080:8080"
    volumes:
      - ./config:/app/config
      - ./torrents:/app/torrents
      - ./clients:/app/clients
    environment:
      - SECRET_TOKEN=votre_token_secret_complexe
      - UI_PATH_PREFIX=chemin_obfuscation_secret
      - MIN_UPLOAD_RATE=30
      - MAX_UPLOAD_RATE=160
      - SIMULTANEOUS_SEED=20
    restart: unless-stopped
```

### Installation Manuelle

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## ⚙️ Configuration

### Fichier config/config.json

```json
{
  "minUploadRate": 30,
  "maxUploadRate": 160,
  "simultaneousSeed": 20,
  "client": "qbittorrent-4.6.0.client",
  "keepTorrentWithZeroLeechers": true,
  "uploadRatioTarget": -1.0
}
```

### Variables d'Environnement

| Variable | Description | Défaut | Requis |
|----------|-------------|--------|--------|
| `SECRET_TOKEN` | Token d'authentification | - | ✅ |
| `UI_PATH_PREFIX` | Chemin obfusqué pour l'UI | - | ✅ |
| `MIN_UPLOAD_RATE` | Upload min (kB/s) | 30 | ❌ |
| `MAX_UPLOAD_RATE` | Upload max (kB/s) | 160 | ❌ |
| `SIMULTANEOUS_SEED` | Torrents simultanés | 20 | ❌ |
| `HTTP_PROXY_HOST` | Proxy host | - | ❌ |
| `HTTP_PROXY_PORT` | Proxy port | - | ❌ |

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
# Windows
update_clients.bat

# Linux/Mac
./update_clients.sh

# Python directement
python update_clients.py
```

Le script récupère automatiquement les dernières versions depuis GitHub pour :
- **qBittorrent** (dernière stable : 5.1.4)
- **Deluge** (dernière stable : 2.2.1)
- **Transmission** (dernière stable : 4.0.6)

📖 Plus d'infos : [CLIENT_UPDATER.md](CLIENT_UPDATER.md)

**Automatisation GitHub Actions :** Un workflow hebdomadaire vérifie les nouvelles versions et crée automatiquement une Pull Request.

## 🐳 Build Docker

```bash
docker build -t pyjoal:latest .
```

## 🧪 Tests

```bash
# Backend
cd backend
pytest tests/ -v --cov=app

# Frontend
cd frontend
npm test
```

## 📊 Différences avec JOAL Original

| Aspect | JOAL Original | PyJOAL |
|--------|---------------|-------------|
| Langage | Java + Spring | Python + FastAPI |
| Frontend | JavaScript vanilla | React 18 + Vite |
| Build | Maven | pip + npm |
| Image Docker | ~300MB | ~150MB (multi-stage) |
| Hot Reload | ❌ | ✅ |
| API Docs | ❌ | ✅ (Swagger/OpenAPI) |
| Tests | Limités | Complets (pytest + jest) |
| Type Safety | Partiel | Complet (Pydantic + TS) |

## 🛠️ Développement

### Structure du Projet

```
pyjoal/
├── backend/
│   ├── app/
│   │   ├── api/          # Endpoints REST
│   │   ├── core/         # Logique BitTorrent
│   │   ├── models/       # Modèles Pydantic
│   │   ├── services/     # Services métier
│   │   ├── utils/        # Utilitaires
│   │   └── main.py       # Point d'entrée
│   ├── tests/            # Tests unitaires
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/   # Composants React
│   │   ├── services/     # API client
│   │   ├── hooks/        # Hooks personnalisés
│   │   └── App.tsx
│   └── package.json
├── config/               # Configuration
├── clients/              # Fichiers .client
├── torrents/             # Fichiers .torrent
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🤝 Contribution

Les contributions sont bienvenues ! Pour contribuer:

1. Fork le projet
2. Créez une branche (`git checkout -b feature/amélioration`)
3. Committez vos changements (`git commit -am 'Ajout fonctionnalité'`)
4. Pushez vers la branche (`git push origin feature/amélioration`)
5. Ouvrez une Pull Request

## 📝 License

Apache 2.0 - Voir le fichier LICENSE

## ⚠️ Disclaimer

PyJOAL n'est pas conçu pour aider ou encourager le téléchargement de matériel illégal. Vous devez respecter les lois applicables dans votre pays. L'auteur ne peut être tenu responsable des activités illégales réalisées avec cet outil.

## 🙏 Remerciements

- Projet original: [anthonyraymond/joal](https://github.com/anthonyraymond/joal)
- Inspiré par les travaux de la communauté BitTorrent

## 📮 Contact

Pour les questions ou suggestions, ouvrez une issue sur GitHub.
