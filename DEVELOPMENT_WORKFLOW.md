# Guide de Gestion des Branches et CI/CD

## 📋 Workflow de Développement

### 🔒 Protection de la Branche `master`
- Seul le **propriétaire** peut merger directement sur `master`
- Toutes les fonctionnalités doivent passer par des **Pull Requests**
- Les tests doivent **passer** avant de pouvoir merger

### 🌿 Gestion des Branches

#### 1. Créer une branche pour nouvelle fonctionnalité
```bash
# Créer et basculer sur une nouvelle branche
git checkout master
git pull origin master
git checkout -b feature/nom-de-la-fonctionnalite

# Exemples de noms de branches
git checkout -b feature/add-torrent-scheduling
git checkout -b bugfix/fix-memory-leak
git checkout -b feature/improve-ui-responsiveness
```

#### 2. Développement et tests automatiques
```bash
# Faire vos modifications
git add .
git commit -m "feat: add torrent scheduling functionality"

# Pousser la branche - déclenche les tests automatiquement
git push origin feature/nom-de-la-fonctionnalite
```

**🤖 À chaque `git push` sur n'importe quelle branche :**
- ✅ Tests backend (Python 3.11, 3.12)
- ✅ Tests frontend (Node.js 18, 20) 
- ✅ Validation TypeScript
- ✅ Lint et vérification syntaxe
- ✅ Tests de sécurité

#### 3. Créer une Pull Request
```bash
# Aller sur GitHub et créer une PR depuis votre branche vers master
# Ou utiliser la CLI GitHub :
gh pr create --title "Add torrent scheduling" --body "Description des changements"
```

#### 4. Review et Merge
- Les tests doivent être **✅ verts** pour pouvoir merger
- Une fois mergé sur `master` → **Déploiement automatique !**

### 🚀 Déploiement Automatique sur `master`

**Quand un merge arrive sur `master` :**
1. ✅ **Tests complets** (backend + frontend)
2. 🐳 **Build Docker** multi-architecture
3. 📦 **Push vers Docker Hub**
4. 🏷️ **Création automatique de tag version** (v1.0.1, v1.0.2, etc.)
5. 🎉 **Release GitHub** avec notes automatiques

### 📊 Monitoring des Workflows

#### **🌿 Branches feature uniquement**
- **Workflow** : `Tests & Validation` 
- **Déclenché** : Sur `git push` (toutes branches sauf master)
- **Objectif** : Valider que le code peut être mergé vers master
- **Jobs** : test-backend + test-frontend + lint + security

#### **🚀 Branche master uniquement**
- **Workflow** : `Release & Deploy`
- **Déclenché** : Sur `git push` vers master uniquement
- **Objectif** : Pipeline complet de production
- **Jobs** : test-backend + test-frontend + build-docker + push-dockerhub + auto-release

**💡 Logique simplifiée :**
- Branches feature → Tests seulement
- Master → Tests + Build + Release + Deploy automatique

### 🛠️ Configuration Protection Branche

**Pour configurer la protection de `master` :**

1. **Aller sur GitHub** : `Settings` → `Branches`
2. **Ajouter règle** pour `master` :
   - ✅ Require a pull request before merging
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - ✅ Include administrators (sauf vous)

### 📝 Convention de Commits

```bash
# Types de commits recommandés
feat: nouvelle fonctionnalité
fix: correction de bug
docs: documentation
style: formatage
refactor: refactoring
test: ajout de tests
chore: maintenance

# Exemples
git commit -m "feat: add real-time torrent progress tracking"
git commit -m "fix: resolve memory leak in seeder service"
git commit -m "docs: update API documentation"
```

### 🎯 Workflow Complet Exemple

```bash
# 1. Créer branche
git checkout master
git pull origin master  
git checkout -b feature/improve-torrent-management

# 2. Développer
# ... faire vos modifications ...
git add .
git commit -m "feat: improve torrent management interface"

# 3. Pousser (déclenche tests automatiques)
git push origin feature/improve-torrent-management

# 4. Créer PR sur GitHub
gh pr create --title "Improve torrent management" --body "Enhanced UI with better controls"

# 5. Attendre validation des tests
# 6. Merger la PR (vous ou propriétaire)
# 7. Automatically: Release + Deploy! 🎉
```

Cette architecture garantit :
- 🔒 **Sécurité** : Pas de push direct sur master
- 🧪 **Qualité** : Tests obligatoires avant merge  
- 🚀 **Automatisation** : Release et déploiement sans intervention
- 📈 **Traçabilité** : Historique complet des versions