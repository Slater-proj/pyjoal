# Guide de Démarrage Rapide - JOAL Modern

## 🚀 Installation et Démarrage

### Option 1: Docker (Recommandé)

1. **Clonez le projet**
```bash
git clone <votre-repo>
cd joal-modern
```

2. **Configurez les variables d'environnement**
```bash
cp .env.example .env
```

Éditez `.env` et configurez **obligatoirement**:
- `SECRET_TOKEN`: Un token secret complexe
- `UI_PATH_PREFIX`: Un chemin d'obfuscation (ex: `mySecret123Path`)

3. **Lancez avec Docker Compose**
```bash
docker-compose up -d
```

> 💡 **Au premier démarrage**, le conteneur télécharge automatiquement les dernières versions des clients BitTorrent (qBittorrent, Deluge, Transmission) depuis GitHub.

4. **Accédez à l'interface**
Ouvrez votre navigateur: `http://localhost:8080/{UI_PATH_PREFIX}/ui/`

### Option 2: Installation Manuelle

#### Backend (Python)

```bash
cd backend

# Créer un environnement virtuel
python -m venv venv

# Activer l'environnement
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp ../.env.example ../.env
# Éditez .env avec vos valeurs

# Lancer le serveur
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

#### Frontend (React)

Dans un nouveau terminal:

```bash
cd frontend

# Installer les dépendances
npm install

# Lancer le serveur de développement
npm run dev
```

Le frontend sera disponible sur `http://localhost:3000` et proxy les requêtes API vers le backend sur le port 8080.

## 📦 Build Production

### Build Docker Image

```bash
docker build -t joal-modern:latest .
```

### Build Frontend Seul

```bash
cd frontend
npm run build
```

Les fichiers seront dans `frontend/dist/` et seront servis par le backend en production.

## 🧪 Tests

### Backend Tests

```bash
cd backend
pytest tests/ -v --cov=app
```

### Frontend Tests

```bash
cd frontend
npm test
```

## 📝 Configuration Initiale

1. **Ajoutez des fichiers clients** dans le dossier `clients/`
   - Des exemples sont déjà fournis (qBittorrent, Deluge, Transmission)

2. **Configurez** votre `config/config.json`
   - Ou utilisez l'interface web pour modifier la configuration

3. **Ajoutez des torrents** via:
   - Drag & drop dans l'interface web
   - Copie manuelle dans le dossier `torrents/`

## 🔧 Dépannage

### Le serveur ne démarre pas

- Vérifiez que `SECRET_TOKEN` et `UI_PATH_PREFIX` sont configurés dans `.env`
- Vérifiez les logs: `docker-compose logs -f joal-modern`

### L'interface web ne s'affiche pas

- Vérifiez que vous utilisez le bon path: `http://localhost:8080/{UI_PATH_PREFIX}/ui/`
- Vérifiez que le frontend a bien été build (si en production)

### Les torrents ne s'annoncent pas

- Vérifiez que les fichiers `.client` existent dans `clients/`
- Vérifiez les logs pour les erreurs d'announce
- Assurez-vous que les trackers sont accessibles

### Erreurs de proxy

Si vous utilisez un proxy:
```bash
# Dans docker-compose.yml ou .env
HTTP_PROXY_HOST=10.10.10.10
HTTP_PROXY_PORT=8888
```

## 🔒 Sécurité

- Toujours utiliser un `SECRET_TOKEN` complexe en production
- Toujours utiliser un `UI_PATH_PREFIX` difficile à deviner
- Ne jamais exposer le port directement sur Internet sans reverse proxy
- Utilisez HTTPS en production (avec nginx/traefik)

## 📚 Ressources

- Documentation API: `http://localhost:8080/docs`
- Swagger UI interactif: `http://localhost:8080/docs`
- Health check: `http://localhost:8080/health`
