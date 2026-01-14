# BitTorrent Client Definitions

Ce dossier contient les fichiers `.client` qui définissent comment JOAL émule différents clients BitTorrent.

## Clients de Base (versionnés dans Git)

Ces 3 clients sont fournis par défaut :

- **deluge-2.1.1.client** - Deluge 2.1.1
- **qbittorrent-4.6.0.client** - qBittorrent 4.6.0  
- **transmission-4.0.5.client** - Transmission 4.0.5

## Mise à Jour Automatique

### Docker
Les clients sont automatiquement mis à jour au démarrage du conteneur.

### Manuel
```bash
# Télécharger les dernières versions
python update_clients.py

# Ou via les scripts
./update_clients.sh    # Linux/Mac
update_clients.bat     # Windows
```

## Format des Fichiers .client

```json
{
  "name": "qBittorrent",
  "version": "4.6.0",
  "peerIdPattern": {
    "prefix": "-qB4600-"
  },
  "userAgent": "qBittorrent/4.6.0",
  "numwant": 200,
  "requestHeaders": {
    "Accept-Encoding": "gzip"
  }
}
```

## Ajout d'un Nouveau Client

Voir [CLIENT_UPDATER.md](../CLIENT_UPDATER.md) pour ajouter le support d'autres clients.
