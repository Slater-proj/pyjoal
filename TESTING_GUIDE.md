# PyJOAL Test Suite

Ce projet contient une suite de tests complète pour PyJOAL, couvrant à la fois le backend Python et le frontend React.

## 🧪 Tests Backend (Python)

### Structure des Tests

```
backend/tests/
├── __init__.py
├── test_auth.py          # Tests d'authentification
├── test_config.py        # Tests de configuration  
├── test_seeder_service.py # Tests du service de seeding
├── test_torrent_parser.py # Tests du parser de torrents
├── test_history_service.py # Tests du service d'historique
└── test_api.py           # Tests des endpoints API
```

### Lancer les Tests Backend

```bash
cd backend

# Tests avec couverture
python -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term

# Tests spécifiques
python -m pytest tests/test_auth.py -v

# Tests en mode watch
python -m pytest tests/ -v --cov=app -f
```

### Couverture de Code

- **Authentification** : Validation des tokens, headers, erreurs 401
- **API Endpoints** : Tous les endpoints avec/sans auth
- **Services** : SeederService, HistoryService, ConfigService
- **Utilitaires** : Parser de torrents, formatters

## 🧪 Tests Frontend (React)

### Structure des Tests

```
frontend/src/__tests__/
├── App.test.tsx          # Tests du composant principal
├── api.test.ts          # Tests du service API
└── format.test.ts       # Tests des utilitaires de formatage
```

### Lancer les Tests Frontend

```bash
cd frontend

# Installer les dépendances de test
npm install

# Tests une fois
npm run test

# Tests en mode watch
npm run test:watch

# Tests avec couverture
npm run test:coverage
```

### Outils de Test

- **Vitest** : Runner de tests rapide
- **Testing Library** : Tests de composants React
- **JSdom** : Environnement de navigateur simulé

## 🚀 CI/CD GitHub Actions

Le workflow `.github/workflows/ci.yml` lance automatiquement :

### 📋 Jobs de Test

1. **test-backend** (Python 3.11, 3.12)
   - Installation des dépendances
   - Tests avec pytest et couverture
   - Upload vers Codecov

2. **test-frontend** (Node 18, 20)
   - Installation npm
   - Tests Vitest avec couverture
   - Upload vers Codecov

3. **lint** (Code Quality)
   - Black, Flake8, MyPy pour Python
   - ESLint, TypeScript pour React

4. **security** (Sécurité)
   - Scan Trivy pour vulnérabilités
   - Upload vers GitHub Security

5. **build-docker** (Production)
   - Build multi-architecture (AMD64, ARM64)
   - Push vers Docker Hub (si branche main)

### ⚙️ Configuration Requise

Dans GitHub Settings > Secrets, ajouter :

```
DOCKERHUB_USERNAME  # Votre username Docker Hub
DOCKERHUB_TOKEN     # Token Docker Hub (pas le mot de passe)
```

### 🔄 Déclencheurs

- **Push** : branches `main`, `master`, `develop`
- **Pull Request** : vers `main`, `master`, `develop`

## 📊 Métriques de Qualité

### Couverture de Code Cible

- **Backend** : > 80%
- **Frontend** : > 70%

### Standards de Code

- **Python** : Black formatting, Flake8 linting
- **TypeScript** : ESLint, strict TypeScript

## 🐛 Debugging des Tests

### Tests Backend qui échouent

```bash
# Mode verbose avec détails
python -m pytest tests/test_api.py::test_get_torrents_authorized -vv -s

# Avec pdb pour débogage
python -m pytest tests/ --pdb

# Variables d'environnement de test
export SECRET_TOKEN=test-token
export UI_PATH_PREFIX=test
python -m pytest tests/ -v
```

### Tests Frontend qui échouent

```bash
# Mode debug avec logs
npm run test -- --reporter=verbose

# Test spécifique
npm run test -- src/__tests__/api.test.ts

# Mode UI (si disponible)
npm run test -- --ui
```

## 📝 Écrire de Nouveaux Tests

### Backend (pytest)

```python
@pytest.mark.asyncio
async def test_my_feature():
    # Test async
    result = await my_async_function()
    assert result.success

def test_my_sync_feature():
    # Test sync
    assert my_function() == expected_value
```

### Frontend (Vitest)

```typescript
import { describe, it, expect, vi } from 'vitest'

describe('MyComponent', () => {
  it('should render correctly', () => {
    // Test de rendu
    render(<MyComponent />)
    expect(screen.getByText('Expected')).toBeInTheDocument()
  })
})
```

## 🎯 Bonnes Pratiques

1. **Tests isolés** : Chaque test doit être indépendant
2. **Mocks appropriés** : Mocker les dépendances externes
3. **Assertions claires** : Messages d'erreur descriptifs
4. **Couverture réaliste** : Tester les cas d'edge et erreurs
5. **Tests rapides** : Optimiser pour des runs fréquents

## 📚 Ressources

- [Pytest Documentation](https://docs.pytest.org/)
- [Vitest Guide](https://vitest.dev/guide/)
- [Testing Library](https://testing-library.com/)
- [GitHub Actions](https://docs.github.com/en/actions)