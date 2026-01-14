#!/usr/bin/env python3
"""
Script de test pour valider la logique de validation des clients au démarrage
"""
import json
from pathlib import Path

# Simuler la configuration
CLIENTS_DIR = Path("clients")
CONFIG_FILE = Path("config/config.json")

def list_available_clients():
    """Liste tous les clients disponibles (triés)"""
    if not CLIENTS_DIR.exists():
        return []
    
    clients = sorted([f.name for f in CLIENTS_DIR.glob("*.client")])
    return clients

def validate_client_on_startup():
    """Valider le client au démarrage avec fallback"""
    print("🔍 Test de validation du client au démarrage\n")
    
    # Lister les clients disponibles
    available_clients = list_available_clients()
    print(f"✅ Clients disponibles ({len(available_clients)}):")
    for client in available_clients:
        print(f"   • {client}")
    print()
    
    if not available_clients:
        print("❌ ERREUR: Aucun client disponible!")
        print("   L'application devrait lever une RuntimeError")
        return False
    
    # Charger la config
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        configured_client = config.get("client", "qbittorrent-4.6.0.client")
        print(f"📄 Client configuré: {configured_client}")
    else:
        configured_client = "qbittorrent-4.6.0.client"
        print(f"⚠️  Pas de config.json, client par défaut: {configured_client}")
    
    # Validation
    if configured_client in available_clients:
        print(f"✅ Client configuré existe, pas de changement nécessaire")
        final_client = configured_client
    else:
        fallback_client = available_clients[0]
        print(f"⚠️  Client configuré '{configured_client}' introuvable")
        print(f"🔄 Fallback sur: {fallback_client}")
        final_client = fallback_client
        
        # Mettre à jour config.json
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            config["client"] = final_client
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"💾 config.json mis à jour avec: {final_client}")
    
    print(f"\n🎯 Client final: {final_client}")
    return True

if __name__ == "__main__":
    try:
        validate_client_on_startup()
    except Exception as e:
        print(f"❌ Erreur: {e}")
