# 🔧 Guide de Développement - PyJOAL

## 🏗️ Architecture du Projet

```
pyjoal/
├── backend/              # API FastAPI
│   ├── app/
│   │   ├── api/         # Endpoints REST
│   │   ├── core/        # Logique BitTorrent
│   │   ├── models/      # Schémas Pydantic
│   │   └── services/    # Services métier
│   └── requirements.txt
├── frontend/            # Application React
│   ├── src/
│   │   ├── components/  # Composants UI
│   │   ├── services/    # API client
│   │   └── store/       # État Zustand
│   └── package.json
├── clients/             # Définitions clients BitTorrent
├── update_clients.py    # Script de mise à jour auto
└── docker-compose.yml   # Orchestration
```

## 🚀 Configuration de l'Environnement de Dev

### Prérequis
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose (optionnel)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Lancer le serveur de dev :**
```bash
uvicorn app.main:app --reload --port 8080
```

**Tester :**
```bash
pytest
```

### Frontend

```bash
cd frontend
npm install
```

**Lancer le serveur de dev :**
```bash
npm run dev  # http://localhost:3000
```

**Build de production :**
```bash
npm run build
```

**Tester les types :**
```bash
npx tsc --noEmit
```

## 📝 Workflow de Développement

### 1. Créer une Branche

```bash
git checkout -b feature/ma-fonctionnalite
```

### 2. Développer

- Utilisez **hot reload** pour le backend et frontend
- Testez votre code au fur et à mesure
- Suivez les conventions de code (PEP 8 pour Python, ESLint pour TypeScript)

### 3. Tester

**Backend :**
```bash
cd backend
pytest tests/
```

**Frontend :**
```bash
cd frontend
npm run test  # À implémenter
```

**Test de validation torrent :**
```bash
python test_torrent.py torrents/example.torrent
```

### 4. Build Docker

```bash
docker-compose build
docker-compose up
```

### 5. Commit

```bash
git add .
git commit -m "feat: ajout de ma fonctionnalité"
git push origin feature/ma-fonctionnalite
```

## 🧪 Tests

### Tests Backend

```python
# backend/tests/test_torrent_parser.py
def test_valid_torrent():
    torrent = Torrent(Path("tests/fixtures/valid.torrent"))
    assert torrent.name is not None
    assert torrent.size > 0
```

### Tests Frontend (À implémenter)

```typescript
// frontend/src/components/__tests__/Dashboard.test.tsx
describe('Dashboard', () => {
  it('renders without crashing', () => {
    render(<Dashboard />)
  })
})
```

## 🐛 Debugging

### Backend

**Logs détaillés :**
```bash
export DEBUG=true
uvicorn app.main:app --reload --log-level debug
```

**VSCode launch.json :**
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--reload"],
      "cwd": "${workspaceFolder}/backend"
    }
  ]
}
```

### Frontend

**React DevTools** + **Redux DevTools** recommandés

## 🔄 Mise à Jour des Clients BitTorrent

**Manuellement :**
```bash
python update_clients.py
```

**Dans le conteneur :**
```bash
docker exec pyjoal python /app/update_clients.py
```

**Ajouter un nouveau client :**

Éditez `update_clients.py` :
```python
CLIENTS = {
    "nouveau_client": {
        "name": "NouveauClient",
        "repo": "owner/repo",
        "peer_id_format": lambda v: f"-NC{v[:3]}-",
        "user_agent_format": lambda v: f"NouveauClient/{v}",
        "numwant": 200,
        "headers": {"Accept-Encoding": "gzip"}
    }
}
```

## 📦 Release Process

### 1. Mettre à Jour CHANGELOG.md

```markdown
## [1.1.0] - 2026-01-15

### Added
- Nouvelle fonctionnalité X
```

### 2. Tag Version

```bash
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0
```

### 3. Build & Push Docker Image

```bash
docker build -t pyjoal:1.1.0 .
docker tag pyjoal:1.1.0 pyjoal:latest
docker push pyjoal:1.1.0
docker push pyjoal:latest
```

## 🎨 Conventions de Code

### Python (Backend)

- **Style :** PEP 8
- **Type hints :** Obligatoires
- **Docstrings :** Google style

```python
def parse_torrent(path: Path) -> Dict[str, Any]:
    """Parse a torrent file.
    
    Args:
        path: Path to the .torrent file
        
    Returns:
        Dict containing torrent metadata
        
    Raises:
        ValueError: If file is invalid
    """
    pass
```

### TypeScript (Frontend)

- **Style :** ESLint + Prettier
- **Composants :** Functional components avec hooks
- **Types :** Strict mode activé

```typescript
interface TorrentProps {
  id: string
  name: string
  onRemove: (id: string) => void
}

export default function Torrent({ id, name, onRemove }: TorrentProps) {
  // ...
}
```

### Commits

Format : `type(scope): message`

Types :
- `feat`: Nouvelle fonctionnalité
- `fix`: Correction de bug
- `docs`: Documentation
- `style`: Formatage
- `refactor`: Refactoring
- `test`: Tests
- `chore`: Maintenance

Exemples :
```
feat(api): add torrent duration limit endpoint
fix(ui): prevent invalid torrents from being saved
docs(readme): update installation instructions
```

## 🔐 Sécurité

### Validation des Entrées

**Toujours valider côté backend :**
```python
@router.post("/torrents")
async def add_torrent(file: UploadFile):
    if not file.filename.endswith('.torrent'):
        raise HTTPException(400, "Invalid file type")
    
    # Parse BEFORE saving
    try:
        torrent = Torrent(temp_path)
    except Exception:
        temp_path.unlink()
        raise HTTPException(400, "Invalid torrent")
```

### Authentification

- Token secret dans `.env`
- Path obfuscation pour l'UI
- Rate limiting (à implémenter)

## 📚 Ressources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [React Docs](https://react.dev/)
- [BitTorrent Protocol](https://www.bittorrent.org/beps/bep_0003.html)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

## 🤝 Contribuer

1. Fork le projet
2. Créez votre branche feature
3. Committez vos changements
4. Pushez vers votre fork
5. Ouvrez une Pull Request

**Merci de contribuer à PyJOAL ! 🎉**
