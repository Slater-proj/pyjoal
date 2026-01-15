# 📁 Structure du Projet

```
pyjoal/
├── 📄 Configuration & Documentation
│   ├── README.md              # Documentation principale
│   ├── QUICKSTART.md          # Guide de démarrage rapide
│   ├── CONTRIBUTING.md        # Guide du développeur
│   ├── CHANGELOG.md           # Historique des versions
│   ├── CLIENT_UPDATER.md      # Documentation mise à jour clients
│   ├── PROJECT_SUMMARY.md     # Résumé du projet
│   ├── LICENSE                # Licence du projet
│   ├── .gitignore            # Fichiers ignorés par Git
│   └── .dockerignore         # Fichiers ignorés par Docker
│
├── 🐳 Docker & Déploiement
│   ├── Dockerfile            # Image Docker multi-stage
│   ├── docker-compose.yml    # Orchestration Docker
│   ├── docker-entrypoint.sh  # Script de démarrage conteneur
│   ├── nginx-example.conf    # Configuration proxy inverse
│   ├── build.sh / build.bat  # Scripts de build
│   └── setup.sh / setup.bat  # Scripts de configuration
│
├── 🔄 Mise à Jour des Clients
│   ├── update_clients.py     # Script Python principal
│   ├── update_clients.sh     # Wrapper Linux/Mac
│   └── update_clients.bat    # Wrapper Windows
│
├── 🐍 Backend (FastAPI)
│   └── backend/
│       ├── requirements.txt   # Dépendances Python
│       ├── pytest.ini        # Configuration tests
│       ├── app/
│       │   ├── main.py       # Point d'entrée FastAPI
│       │   ├── api/          # Endpoints REST
│       │   │   ├── config.py
│       │   │   ├── torrents.py
│       │   │   ├── client.py
│       │   │   └── history.py
│       │   ├── core/         # Logique BitTorrent
│       │   │   ├── config.py
│       │   │   ├── bittorrent_client.py
│       │   │   ├── torrent_parser.py
│       │   │   └── tracker_announcer.py
│       │   ├── models/       # Schémas Pydantic
│       │   │   └── schemas.py
│       │   └── services/     # Services métier
│       │       ├── seeder_service.py
│       │       ├── history_service.py
│       │       └── websocket_manager.py
│       └── tests/            # Tests unitaires
│
├── ⚛️ Frontend (React + Vite)
│   └── frontend/
│       ├── package.json      # Dépendances Node.js
│       ├── vite.config.ts    # Configuration Vite
│       ├── tsconfig.json     # Configuration TypeScript
│       ├── tailwind.config.js # Configuration TailwindCSS
│       ├── index.html        # Page HTML principale
│       └── src/
│           ├── main.tsx      # Point d'entrée React
│           ├── App.tsx       # Composant racine
│           ├── index.css     # Styles globaux
│           ├── components/   # Composants React
│           │   ├── BottomNav.tsx
│           │   ├── ClientInfoPanel.tsx
│           │   ├── DashboardPage.tsx
│           │   ├── SettingsPage.tsx
│           │   ├── HistoryPage.tsx
│           │   ├── TorrentsTableNew.tsx
│           │   └── Toast.tsx
│           ├── services/     # API client
│           │   └── api.ts
│           └── store/        # État global (Zustand)
│               └── useStore.ts
│
├── 📦 Données Runtime (non versionnées)
│   ├── config/               # Configuration JSON
│   │   ├── .gitkeep
│   │   └── config.json       # Créé au premier démarrage
│   │
│   ├── torrents/             # Fichiers .torrent
│   │   └── .gitkeep
│   │
│   ├── clients/              # Définitions clients BitTorrent
│   │   ├── README.md
│   │   ├── .gitignore
│   │   ├── deluge-2.1.1.client       ✅ Versionné
│   │   ├── qbittorrent-4.6.0.client  ✅ Versionné
│   │   └── transmission-4.0.5.client ✅ Versionné
│   │
│   └── test-data/            # Tests locaux (ignoré par Git)
│       ├── README.md
│       ├── test_torrent.py
│       ├── test.torrent
│       └── invalid-test.torrent
│
└── 🤖 CI/CD
    └── .github/
        └── workflows/
            └── update-clients.yml  # Mise à jour hebdomadaire
```

## Fichiers Versionnés vs Ignorés

### ✅ Versionnés dans Git
- Code source (backend/ et frontend/)
- Documentation (*.md)
- Configuration Docker
- Scripts d'automatisation
- **3 clients de base** (deluge, qbittorrent, transmission)
- Fichiers .gitkeep

### ❌ Ignorés par Git
- `node_modules/`, `venv/`, `__pycache__/`
- `frontend/dist/` (généré au build)
- `config/config.json` (généré au runtime)
- `torrents/*.torrent` (données utilisateur)
- `test-data/` (développement local uniquement)
- Clients auto-générés (versions plus récentes)
- `.env` (secrets)

## Dossiers Montés en Docker

Volumes Docker définis dans `docker-compose.yml` :
- `./config:/app/config` - Configuration persistante
- `./torrents:/app/torrents` - Fichiers torrents
- `./clients:/app/clients` - Définitions clients (auto-mis à jour)

## Démarrage Rapide

```bash
# Clone
git clone <repo>
cd pyjoal

# Configuration
cp .env.example .env
nano .env  # Configurer SECRET_TOKEN et UI_PATH_PREFIX

# Lancement
docker-compose up -d

# Accès
http://localhost:8080/{UI_PATH_PREFIX}/ui/
```
