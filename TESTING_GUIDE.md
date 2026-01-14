# 🧪 Tests de Validation - Mise à Jour des Clients

## ✅ Ce qui a été corrigé

1. **Détection automatique Docker** - Le backend détecte s'il tourne dans Docker et évite la double exécution
2. **Update systématique dans Docker** - `docker-entrypoint.sh` exécute toujours `update_clients.py`
3. **Validation et logs** - Affichage clair du nombre de clients détectés au démarrage
4. **Fallback intelligent** - Si un client configuré n'existe pas, bascule automatiquement sur le premier disponible

## 🔍 Marche à Suivre pour Tester

### Étape 1: Nettoyer l'environnement

```bash
# Arrêter et supprimer tout
docker-compose down -v

# Supprimer l'image existante
docker rmi joal-modern-joal-modern 2>/dev/null || true

# Vérifier les fichiers locaux
ls -la clients/
# Doit montrer 6 fichiers .client
```

### Étape 2: Rebuild complet

```bash
# Build sans cache
docker-compose build --no-cache

# Vérifier que le build a réussi
docker images | grep joal-modern
```

### Étape 3: Démarrer avec logs

```bash
# Démarrer en mode détaché
docker-compose up -d

# Suivre les logs en temps réel
docker-compose logs -f joal-modern
```

### Étape 4: Vérifier les logs de démarrage

**Logs attendus:**

```
🚀 Starting JOAL Modern...

🔄 Updating BitTorrent client definitions...
📥 Checking qBittorrent...
   Latest version: 5.1.4
✅ Generated: qbittorrent-5.1.4.client

📥 Checking Deluge...
   Latest version: 2.2.1
   ✓ Already exists

📥 Checking Transmission...
   Latest version: 4.0.6
   ✓ Already exists

============================================================
✨ New versions generated:
   • qBittorrent: 5.1.4

💡 Old versions were kept. Delete them manually if needed.
============================================================

✅ Found 6 client definition(s)
   • deluge-2.1.1.client
   • deluge-2.2.1.client
   • qbittorrent-4.6.0.client
   • qbittorrent-5.1.4.client
   • transmission-4.0.5.client
   • transmission-4.0.6.client

🎬 Starting FastAPI application...
INFO:     Started server process [1]
INFO:     Waiting for application startup.
🐳 Running in Docker, client update handled by entrypoint
📱 Client chargé: qBittorrent 4.6.0
✅ JOAL Modern started on port 8080
🌐 UI available at: /joal/ui/
```

**Points clés à vérifier:**
- ✅ "Found 6 client definition(s)" apparaît
- ✅ Liste des 6 clients affichée
- ✅ "Running in Docker, client update handled by entrypoint" apparaît
- ✅ "Client chargé: ..." affiche un client valide

### Étape 5: Vérifier le volume monté

```bash
# Lister les fichiers dans le volume
ls -lh clients/

# Devrait montrer 6 fichiers
deluge-2.1.1.client
deluge-2.2.1.client
qbittorrent-4.6.0.client
qbittorrent-5.1.4.client
transmission-4.0.5.client
transmission-4.0.6.client
```

### Étape 6: Tester l'API

```bash
# Test de santé
curl http://localhost:8080/health

# Liste des clients disponibles
curl http://localhost:8080/api/clients | python -m json.tool

# Output attendu:
# {
#   "clients": [
#     "deluge-2.1.1.client",
#     "deluge-2.2.1.client",
#     "qbittorrent-4.6.0.client",
#     "qbittorrent-5.1.4.client",
#     "transmission-4.0.5.client",
#     "transmission-4.0.6.client"
#   ]
# }
```

### Étape 7: Tester l'IHM

1. Ouvrir: `http://localhost:8080/joal/ui/`
   - ⚠️ Remplacer `joal` par votre `UI_PATH_PREFIX` dans `.env`

2. Cliquer sur **Configuration** (panneau s'ouvre)

3. Vérifier le dropdown **"BitTorrent Client"**
   - ✅ Doit afficher **6 options**
   - ✅ Triées alphabétiquement
   - ✅ Déluge 2.1.1 et 2.2.1
   - ✅ qBittorrent 4.6.0 et 5.1.4
   - ✅ Transmission 4.0.5 et 4.0.6

4. Sélectionner **qbittorrent-5.1.4.client**

5. Cliquer **Save Configuration**

6. Redémarrer le container:
   ```bash
   docker-compose restart
   ```

7. Vérifier les logs après redémarrage:
   ```bash
   docker-compose logs joal-modern | grep "Client chargé"
   # Doit afficher: 📱 Client chargé: qBittorrent 5.1.4
   ```

## 🔧 Tests Supplémentaires

### Test du Fallback Automatique

**Objectif:** Vérifier que si un client configuré n'existe pas, le système bascule automatiquement

```bash
# 1. Modifier config.json pour pointer vers un client inexistant
docker exec joal-modern sh -c "echo '{
  \"minUploadRate\": 30,
  \"maxUploadRate\": 160,
  \"simultaneousSeed\": 20,
  \"client\": \"qbittorrent-99.0.0.client\",
  \"keepTorrentWithZeroLeechers\": false,
  \"uploadRatioTarget\": -1.0,
  \"seedingDurationLimit\": -1.0
}' > /app/config/config.json"

# 2. Redémarrer
docker-compose restart

# 3. Vérifier les logs
docker-compose logs joal-modern | tail -20

# Output attendu:
# ⚠️  Client configuré 'qbittorrent-99.0.0.client' introuvable
# 🔄 Utilisation du client par défaut: deluge-2.1.1.client
# 📱 Client chargé: Deluge 2.1.1
```

### Test de Mise à Jour Manuelle

**Objectif:** Forcer une mise à jour dans le container en cours d'exécution

```bash
# 1. Supprimer tous les clients générés (garder juste les 3 de base)
docker exec joal-modern sh -c "rm -f /app/clients/*-5.*.client /app/clients/*-2.2.*.client /app/clients/*-4.0.6.client"

# 2. Vérifier
docker exec joal-modern ls /app/clients
# Doit montrer seulement 3 fichiers

# 3. Forcer l'update
docker exec joal-modern python /app/update_clients.py

# 4. Vérifier
docker exec joal-modern ls /app/clients
# Doit montrer 6 fichiers

# 5. Redémarrer pour recharger
docker-compose restart
```

## 📊 Script de Diagnostic

Utilisez le script fourni pour un diagnostic complet:

```bash
./diagnose.sh
```

Cela affichera:
- ✅ État des fichiers locaux
- ✅ État du container Docker
- ✅ Logs récents du container
- ✅ Status de l'API
- ✅ Recommendations automatiques

## ❌ Problèmes Courants et Solutions

### Problème 1: Toujours seulement 3 clients dans l'IHM

**Cause:** L'image Docker n'a pas été rebuild

**Solution:**
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

### Problème 2: Erreur "No .client files found"

**Cause:** Le volume `./clients` est vide

**Solution:**
```bash
# Restaurer les 3 clients de base
git checkout clients/*.client

# Rebuild
docker-compose build --no-cache
docker-compose up -d
```

---

### Problème 3: API retourne 6 clients mais IHM en affiche 3

**Cause:** Cache navigateur

**Solution:**
```bash
# Ouvrir les DevTools (F12)
# Aller dans l'onglet Network
# Cocher "Disable cache"
# Rafraîchir la page (Ctrl+Shift+R)

# OU vider le cache:
# Chrome: Ctrl+Shift+Del
# Firefox: Ctrl+Shift+Del
```

---

### Problème 4: "Client configuré introuvable" au démarrage

**Cause:** `config.json` pointe vers un client supprimé

**Solution:** C'est normal ! Le système bascule automatiquement
```bash
# Vérifier les logs
docker-compose logs joal-modern | grep "Client"

# Output attendu:
# ⚠️  Client configuré 'xxx' introuvable
# 🔄 Utilisation du client par défaut: deluge-2.1.1.client
# 📱 Client chargé: Deluge 2.1.1
```

## ✅ Checklist Finale

Après avoir suivi tous les tests :

- [ ] Logs Docker montrent "Found 6 client definition(s)"
- [ ] `ls clients/` affiche 6 fichiers .client
- [ ] API `/api/clients` retourne 6 clients
- [ ] IHM affiche 6 clients dans le dropdown
- [ ] Changement de client persiste après redémarrage
- [ ] Fallback automatique fonctionne avec client invalide
- [ ] Update manuelle fonctionne (`docker exec ... python /app/update_clients.py`)

---

**Status:** ✅ Tests de validation complets  
**Documentation:** Voir [BUGFIX_DOCKER_CLIENTS.md](BUGFIX_DOCKER_CLIENTS.md)
