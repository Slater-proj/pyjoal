# CI/CD Pipeline Unifié

## 🎯 Un seul workflow pour tout gérer

**Fichier :** [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

### 📋 Logique d'exécution intelligente

Le workflow s'adapte automatiquement selon la branche :

**📝 Sur les branches feature/develop :**
```yaml
✅ test-backend     # Validation Python basique
✅ test-frontend    # Build React/TypeScript  
❌ build-docker    # Skipped (condition: if master)
❌ push-dockerhub   # Skipped (condition: if master)
❌ auto-release    # Skipped (condition: if master)
```

**🚀 Sur la branche master :**
```yaml
✅ test-backend     # Validation Python
✅ test-frontend    # Build React/TypeScript
✅ build-docker     # Build image Docker 
✅ push-dockerhub   # Push DockerHub + versioning
✅ auto-release     # GitHub Release automatique
```

## 🔄 Workflow Feature → Master

### 1️⃣ Développement Feature
```bash
# Nouvelle branche
git checkout -b feature/ma-fonctionnalite
git push origin feature/ma-fonctionnalite
```

**CI déclenche :** Tests uniquement (rapide ⚡)

### 2️⃣ Pull Request
```bash
# PR vers master
gh pr create --title "feat: nouvelle fonctionnalité"
```

**CI déclenche :** Re-validation + tests

### 3️⃣ Merge dans Master  
```bash
# Une fois merge approuvé
git checkout master && git pull
```

**CI déclenche :** Pipeline COMPLET 🚀
- Tests ✅
- Build Docker 🐳  
- Push Docker Hub 📦
- Release GitHub 🎉
- Auto-versioning (v1.0.0 → v1.0.1)

## 📊 Avantages du workflow unifié

| Critère | Avant (2 fichiers) | Après (1 fichier) |
|---------|-------------------|-------------------|
| **Maintenance** | 2 workflows à sync | 1 seul fichier |
| **Lisibilité** | Logic éparpillée | Logic centralisée |
| **Performance** | Tests dupliqués | Tests optimisés |
| **Debugging** | 2 endroits à check | 1 seul endroit |
| **Conditions** | Complexe | Simple et claire |

## ⚙️ Configuration

### GitHub Secrets
```bash
DOCKERHUB_USERNAME=slaterproj
DOCKERHUB_TOKEN=dckr_pat_xxxxx
```

### Conditions clés
```yaml
# Uniquement sur master ET push (pas PR)
if: github.ref == 'refs/heads/master' && github.event_name == 'push'
```

## 🛠️ Commandes CI/CD

```bash
# Status des workflows
gh run list --limit 5

# Logs d'un workflow spécifique
gh run view --log

# Re-déclencher en cas d'échec
gh run rerun [RUN_ID]

# Vérifier les secrets
gh secret list
```

## 🚨 Résolution des problèmes

### Pipeline qui ne se déclenche pas sur master
```bash
# Vérifier les conditions
git log --oneline -5  # Vérifier dernier commit
gh run list           # Vérifier si workflow lancé
```

### Double exécution de pipeline
```bash
# Vérifier les triggers dans ci.yml
# Doit avoir SEULEMENT :
on:
  push:
    branches: ['**']
# PAS de "tags:" trigger
```

### Échec versioning
```bash
# Vérifier les tags existants
git tag --sort=-version:refname | head -5

# Nettoyer si nécessaire
git tag -d v1.0.0  # local
git push --delete origin v1.0.0  # remote
```