# BitTorrent Client Definitions

Ce dossier contient les fichiers `.client` qui définissent comment PyJOAL émule différents clients BitTorrent.

## 🎯 Clients Pré-installés

Ces clients sont fournis par défaut avec PyJOAL :

- **deluge-2.1.1.client** - Deluge 2.1.1
- **qbittorrent-4.6.0.client** - qBittorrent 4.6.0  
- **transmission-4.0.5.client** - Transmission 4.0.5

## 🔄 Mise à Jour Automatique

### Avec Docker
Les clients sont **automatiquement mis à jour** au démarrage du conteneur vers les dernières versions stables.

### Mise à jour manuelle

```bash
python scripts/update_clients.py
```

Le script télécharge automatiquement :
- **qBittorrent** - Dernière version stable depuis GitHub
- **Deluge** - Dernière version stable depuis GitHub  
- **Transmission** - Dernière version stable depuis GitHub

## 📋 Format de Fichier .client

Exemple `qbittorrent-4.6.0.client` :

```json
{
  "name": "qBittorrent",
  "version": "4.6.0",
  "peerIdPattern": {
    "prefix": "-qB4600-",
    "minLength": 20,
    "maxLength": 20
  },
  "userAgent": "qBittorrent/4.6.0",
  "numwant": 200,
  "requestHeaders": {
    "Accept-Encoding": "gzip",
    "Connection": "close"
  }
}
```

## ➕ Ajouter un Nouveau Client

Pour ajouter le support d'un nouveau client BitTorrent :

1. Créer un fichier `.client` avec le format ci-dessus
2. Définir le `peerIdPattern` selon les spécifications du client
3. Configurer les `requestHeaders` appropriés
4. Placer le fichier dans ce dossier `clients/`
5. Redémarrer PyJOAL

**Sources pour les spécifications des clients :**
- [BEP-0020](http://www.bittorrent.org/beps/bep_0020.html) - Peer ID conventions
- Repositories GitHub des clients officiels
- Analyse du trafic réseau des clients réels
