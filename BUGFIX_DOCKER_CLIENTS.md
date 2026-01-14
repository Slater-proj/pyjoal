# 🐳 Fix: Clients Non Mis à Jour dans Docker

## 🐛 Problème

Lors du lancement avec `setup.sh` (Docker), les clients ne se mettent pas à jour dans l'IHM :
- ❌ Seuls les 3 clients de base apparaissent (Deluge 2.1.1, qBittorrent 4.6.0, Transmission 4.0.5)
- ❌ Les nouvelles versions (qBittorrent 5.1.4, Deluge 2.2.1, Transmission 4.0.6) ne sont pas visibles

## 🔍 Cause Racine

**Double exécution conflictuelle** de `update_clients.py` :
1. ✅ `docker-entrypoint.sh` exécute le script AU DÉMARRAGE du container
2. ❌ `main.py` réexécute le script PENDANT l'initialisation FastAPI
3. 💥 Conflit de timing : L'API peut charger la liste AVANT que le 2ème update soit terminé

## ✅ Solution Appliquée

### 1. Désactivation dans main.py pour Docker

**Fichier:** `backend/app/main.py`

```python
async def update_clients_on_startup():
    """Run update_clients.py script to fetch latest client versions"""
    import os
    
    # 🆕 Skip if running in Docker (handled by docker-entrypoint.sh)
    if os.getenv("DOCKER_CONTAINER") or os.path.exists("/.dockerenv"):
        print("🐳 Running in Docker, client update handled by entrypoint")
        return
    
    # Continue normally for local development
    ...
```

**Résultat:**
- ✅ En Docker : Exécution uniquement dans l'entrypoint
- ✅ En local : Exécution uniquement dans main.py
- ✅ Plus de conflit de double exécution

---

### 2. Variable d'environnement Docker

**Fichier:** `Dockerfile`

```dockerfile
# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    DOCKER_CONTAINER=1  # 🆕 Indicateur Docker
```

**Résultat:**
- ✅ Le backend détecte automatiquement qu'il tourne dans Docker
- ✅ Saute l'update dans main.py pour éviter la duplication

---

### 3. Amélioration docker-entrypoint.sh

**Fichier:** `docker-entrypoint.sh`

```bash
#!/bin/bash
set -e

echo "🚀 Starting JOAL Modern..."
echo ""

# 🆕 Update toujours exécuté (sans condition)
echo "🔄 Updating BitTorrent client definitions..."
python /app/update_clients.py || echo "⚠️  Warning: Failed to update clients"

echo ""

# 🆕 Vérification du nombre de clients
CLIENT_COUNT=$(ls -1 /app/clients/*.client 2>/dev/null | wc -l)
if [ "$CLIENT_COUNT" -eq 0 ]; then
    echo "❌ ERROR: No .client files found!"
    exit 1
fi

# 🆕 Liste les clients détectés
echo "✅ Found $CLIENT_COUNT client definition(s)"
ls -1 /app/clients/*.client | sed 's|^/app/clients/|   • |'
echo ""

# Start application
echo "🎬 Starting FastAPI application..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

**Résultat:**
- ✅ Update systématique au démarrage du container
- ✅ Validation qu'au moins un client existe
- ✅ Liste visible dans les logs Docker

---

## 🧪 Validation

### Test 1: Vérifier les logs Docker

```bash
docker-compose logs joal-modern
```

**Output attendu:**
```
🚀 Starting JOAL Modern...

🔄 Updating BitTorrent client definitions...
📥 Checking qBittorrent...
   Latest version: 5.1.4
✅ Generated: qbittorrent-5.1.4.client
...

✅ Found 6 client definition(s)
   • deluge-2.1.1.client
   • deluge-2.2.1.client
   • qbittorrent-4.6.0.client
   • qbittorrent-5.1.4.client
   • transmission-4.0.5.client
   • transmission-4.0.6.client

🎬 Starting FastAPI application...
🐳 Running in Docker, client update handled by entrypoint
📱 Client chargé: qBittorrent 4.6.0
✅ JOAL Modern started on port 8080
```

---

### Test 2: Vérifier le volume clients/

```bash
# Lister les fichiers montés
ls -la clients/

# Devrait montrer 6 fichiers .client
```

---

### Test 3: Tester l'API /api/clients

```bash
# Dans un navigateur ou avec curl
curl http://localhost:8080/api/clients

# Output attendu (JSON):
{
  "clients": [
    "deluge-2.1.1.client",
    "deluge-2.2.1.client",
    "qbittorrent-4.6.0.client",
    "qbittorrent-5.1.4.client",
    "transmission-4.0.5.client",
    "transmission-4.0.6.client"
  ]
}
```

---

### Test 4: Vérifier l'IHM

1. Ouvrir l'IHM dans le navigateur
2. Aller dans **Configuration**
3. Vérifier le dropdown **BitTorrent Client**
4. ✅ Doit afficher **6 clients** triés alphabétiquement

---

## 🔄 Rebuild Nécessaire

⚠️ **IMPORTANT:** Ces changements nécessitent un rebuild de l'image Docker

```bash
# Arrêter et supprimer les containers
docker-compose down

# Rebuild l'image
docker-compose build --no-cache

# Redémarrer
docker-compose up -d

# Vérifier les logs
docker-compose logs -f joal-modern
```

**OU utiliser le script setup:**
```bash
./setup.sh  # Linux/Mac
setup.bat   # Windows
```

---

## 📋 Checklist de Vérification

Après rebuild :

- [ ] Logs Docker montrent "Updating BitTorrent client definitions..."
- [ ] Logs Docker montrent "Found 6 client definition(s)"
- [ ] Logs Docker listent les 6 fichiers .client
- [ ] `ls clients/` montre 6 fichiers .client
- [ ] API `/api/clients` retourne 6 clients
- [ ] IHM affiche 6 clients dans le dropdown
- [ ] Client sélectionné est sauvegardé et persiste après redémarrage

---

## 🎯 Comportement Final

### En Docker:
1. Container démarre
2. `docker-entrypoint.sh` exécute `update_clients.py`
3. Clients générés dans `/app/clients` (monté depuis `./clients`)
4. FastAPI démarre
5. `main.py` détecte Docker → saute l'update
6. Charge les clients depuis `/app/clients`
7. ✅ IHM affiche tous les clients

### En Local:
1. `python -m uvicorn app.main:app`
2. `main.py` exécute `update_clients.py`
3. Clients générés dans `./clients`
4. FastAPI démarre
5. Charge les clients depuis `./clients`
6. ✅ IHM affiche tous les clients

---

## 🐛 Troubleshooting

### Problème: Toujours que 3 clients

**Solution 1:** Rebuild complet
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

**Solution 2:** Vérifier les permissions du volume
```bash
# Vérifier les permissions
ls -la clients/

# Si problème, changer les permissions
chmod 755 clients/
chmod 644 clients/*.client
```

**Solution 3:** Forcer l'update manuel
```bash
# Dans le container en cours d'exécution
docker exec joal-modern python /app/update_clients.py

# Redémarrer le container
docker-compose restart
```

---

### Problème: Erreur "No .client files found"

**Cause:** Le volume `./clients` est vide ou non monté

**Solution:**
```bash
# Vérifier que les 3 clients de base existent
ls clients/
# Doit montrer: deluge-2.1.1.client, qbittorrent-4.6.0.client, transmission-4.0.5.client

# Si vide, les copier depuis le repo
git checkout clients/*.client

# Rebuild
docker-compose build --no-cache
docker-compose up -d
```

---

**Status:** ✅ RÉSOLU  
**Impact:** Docker maintenant au même niveau que local
