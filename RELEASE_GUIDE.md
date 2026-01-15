# Guide pour publier une release GitHub

## Étapes pour créer une nouvelle release

1. **Assurez-vous que tout fonctionne**
   ```bash
   # Testez localement que votre build fonctionne
   cd frontend && npm run build
   cd ../backend && python -c "import app.main"
   ```

2. **Créez un tag de version**
   ```bash
   # Format: v[MAJOR].[MINOR].[PATCH] (exemple: v1.0.0, v1.2.3)
   git tag -a v1.0.0 -m "Version 1.0.0 - Initial release"
   git push origin v1.0.0
   ```

3. **Le pipeline se déclenche automatiquement**
   - GitHub Actions détecte le tag `v*`
   - Exécute tous les tests (backend + frontend)
   - Build et push l'image Docker vers Docker Hub
   - Crée automatiquement une release GitHub avec:
     - Notes de release automatiques
     - Instructions Docker
     - Liste des fonctionnalités

## Format des versions

- **v1.0.0** : Release majeure (nouvelles fonctionnalités importantes)
- **v1.1.0** : Release mineure (nouvelles fonctionnalités, non-breaking)
- **v1.0.1** : Patch (corrections de bugs, sécurité)

## Exemples de tags

```bash
# Première release stable
git tag -a v1.0.0 -m "🎉 Initial stable release"

# Nouvelle fonctionnalité
git tag -a v1.1.0 -m "✨ Add torrent scheduling feature"

# Correction de bug
git tag -a v1.0.1 -m "🐛 Fix torrent deletion bug"

# Push du tag
git push origin v1.0.0
```

## Ce qui se passe automatiquement

1. ✅ **Tests** : Backend (Python 3.11, 3.12) + Frontend (Node 18, 20)
2. ✅ **Lint** : Vérification syntaxe Python + TypeScript  
3. ✅ **Sécurité** : Scan basique de sécurité
4. 🐳 **Docker Build** : Image multi-architecture (AMD64/ARM64)
5. 📦 **Docker Push** : Publication sur Docker Hub
6. 🎉 **Release GitHub** : Création automatique avec notes

## Configuration requise

Pour que cela fonctionne, vous devez configurer ces secrets GitHub :
- `DOCKERHUB_USERNAME` : Votre nom d'utilisateur Docker Hub
- `DOCKERHUB_TOKEN` : Token d'accès Docker Hub

## Accès aux releases

- **GitHub Releases** : https://github.com/Slater-proj/pyjoal/releases
- **Docker Hub** : https://hub.docker.com/r/[YOUR_USERNAME]/pyjoal