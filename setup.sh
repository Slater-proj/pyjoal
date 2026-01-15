#!/bin/bash

# setup.sh - Configuration et installation locale pour pyjoal
# Utile pour les tests locaux et le développement

set -e

echo "🚀 Configuration de l'environnement pyjoal..."

# Couleurs pour les messages
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Fonction d'affichage des messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérification que nous sommes dans le bon répertoire
if [[ ! -f "docker-compose.yml" ]]; then
    log_error "Fichier docker-compose.yml non trouvé. Exécutez ce script depuis la racine du projet."
    exit 1
fi

# Fonction pour vérifier les prérequis
check_prerequisites() {
    log_info "Vérification des prérequis..."
    
    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker n'est pas installé. Installez Docker et réessayez."
        exit 1
    fi
    
    # Vérifier Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose n'est pas disponible. Vérifiez votre installation Docker."
        exit 1
    fi
    
    # Vérifier Python (pour les tests backend)
    if ! command -v python3 &> /dev/null; then
        log_warn "Python3 n'est pas installé. Certains tests locaux ne pourront pas s'exécuter."
    fi
    
    # Vérifier Node.js (pour les tests frontend)
    if ! command -v node &> /dev/null; then
        log_warn "Node.js n'est pas installé. Certains tests frontend ne pourront pas s'exécuter."
    fi
    
    log_info "✅ Prérequis vérifiés"
}

# Fonction pour nettoyer l'environnement
clean_environment() {
    log_info "Nettoyage de l'environnement..."
    
    # Arrêter et supprimer les conteneurs existants
    docker compose down --remove-orphans 2>/dev/null || true
    
    # Supprimer les images locales obsolètes
    docker images | grep pyjoal | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null || true
    
    # Nettoyer les volumes orphelins
    docker volume prune -f 2>/dev/null || true
    
    log_info "✅ Environnement nettoyé"
}

# Fonction pour installer les dépendances backend
setup_backend() {
    if [[ -d "backend" ]] && command -v python3 &> /dev/null; then
        log_info "Installation des dépendances backend..."
        
        cd backend
        
        # Créer un environnement virtuel si il n'existe pas
        if [[ ! -d "venv" ]]; then
            python3 -m venv venv
            log_info "Environnement virtuel créé"
        fi
        
        # Activer l'environnement virtuel et installer les dépendances
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        pip install flake8 black isort bandit safety pytest pytest-cov
        
        cd ..
        log_info "✅ Dépendances backend installées"
    else
        log_warn "Dossier backend non trouvé ou Python3 non disponible"
    fi
}

# Fonction pour installer les dépendances frontend
setup_frontend() {
    if [[ -d "frontend" ]] && command -v node &> /dev/null; then
        log_info "Installation des dépendances frontend..."
        
        cd frontend
        npm install
        cd ..
        
        log_info "✅ Dépendances frontend installées"
    else
        log_warn "Dossier frontend non trouvé ou Node.js non disponible"
    fi
}

# Fonction pour mettre à jour les clients BitTorrent
update_clients() {
    log_info "Mise à jour des clients BitTorrent..."
    
    if [[ -f "scripts/update_clients.py" ]]; then
        if command -v python3 &> /dev/null; then
            python3 scripts/update_clients.py
            log_info "✅ Clients BitTorrent mis à jour"
        else
            log_warn "Python3 non disponible, mise à jour des clients ignorée"
        fi
    else
        log_warn "Script update_clients.py non trouvé"
    fi
}

# Fonction pour construire l'environnement Docker
build_docker() {
    log_info "Construction de l'image Docker..."
    
    # Construction avec cache
    docker compose build
    
    log_info "✅ Image Docker construite"
}

# Fonction pour lancer les tests
run_tests() {
    log_info "Exécution des tests..."
    
    # Tests backend
    if [[ -d "backend" ]] && command -v python3 &> /dev/null; then
        log_info "Tests backend..."
        cd backend
        if [[ -d "venv" ]]; then
            source venv/bin/activate
            python -m pytest tests/ -v || log_warn "Certains tests backend ont échoué"
        fi
        cd ..
    fi
    
    # Tests frontend
    if [[ -d "frontend" ]] && command -v node &> /dev/null; then
        log_info "Tests frontend..."
        cd frontend
        npm test -- --watchAll=false || log_warn "Certains tests frontend ont échoué"
        cd ..
    fi
    
    log_info "✅ Tests terminés"
}

# Fonction pour démarrer l'application
start_app() {
    log_info "Démarrage de l'application..."
    
    docker compose up -d
    
    # Attendre que l'application soit prête
    log_info "Attente du démarrage de l'application..."
    sleep 10
    
    # Vérifier que l'application répond
    if curl -s http://localhost:8080 > /dev/null; then
        log_info "✅ Application démarrée et accessible sur http://localhost:8080"
    else
        log_warn "L'application semble avoir des problèmes de démarrage"
        log_info "Vérifiez les logs avec: docker compose logs"
    fi
}

# Fonction d'affichage de l'aide
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -c, --clean     Nettoyer l'environnement avant l'installation"
    echo "  -b, --backend   Installer seulement les dépendances backend"
    echo "  -f, --frontend  Installer seulement les dépendances frontend"
    echo "  -u, --update    Mettre à jour les clients BitTorrent"
    echo "  -t, --test      Exécuter les tests"
    echo "  -d, --docker    Construire l'image Docker"
    echo "  -s, --start     Démarrer l'application"
    echo "  -h, --help      Afficher cette aide"
    echo ""
    echo "Exemples:"
    echo "  $0                    # Installation complète"
    echo "  $0 --clean --docker --start  # Nettoyage, construction et démarrage"
    echo "  $0 --test            # Exécuter seulement les tests"
}

# Analyse des arguments
CLEAN=false
BACKEND_ONLY=false
FRONTEND_ONLY=false
UPDATE_CLIENTS=false
TEST_ONLY=false
DOCKER_ONLY=false
START_ONLY=false
FULL_SETUP=true

while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--clean)
            CLEAN=true
            FULL_SETUP=false
            shift
            ;;
        -b|--backend)
            BACKEND_ONLY=true
            FULL_SETUP=false
            shift
            ;;
        -f|--frontend)
            FRONTEND_ONLY=true
            FULL_SETUP=false
            shift
            ;;
        -u|--update)
            UPDATE_CLIENTS=true
            FULL_SETUP=false
            shift
            ;;
        -t|--test)
            TEST_ONLY=true
            FULL_SETUP=false
            shift
            ;;
        -d|--docker)
            DOCKER_ONLY=true
            FULL_SETUP=false
            shift
            ;;
        -s|--start)
            START_ONLY=true
            FULL_SETUP=false
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Option inconnue: $1"
            show_help
            exit 1
            ;;
    esac
done

# Exécution principale
main() {
    log_info "🚀 Démarrage du script de configuration pyjoal"
    
    check_prerequisites
    
    if [[ $CLEAN == true ]]; then
        clean_environment
    fi
    
    if [[ $BACKEND_ONLY == true ]]; then
        setup_backend
    elif [[ $FRONTEND_ONLY == true ]]; then
        setup_frontend
    elif [[ $UPDATE_CLIENTS == true ]]; then
        update_clients
    elif [[ $TEST_ONLY == true ]]; then
        run_tests
    elif [[ $DOCKER_ONLY == true ]]; then
        build_docker
    elif [[ $START_ONLY == true ]]; then
        start_app
    elif [[ $FULL_SETUP == true ]]; then
        # Installation complète
        update_clients
        setup_backend
        setup_frontend
        build_docker
        run_tests
        start_app
    fi
    
    log_info "🎉 Configuration terminée avec succès!"
    echo ""
    log_info "Commandes utiles:"
    echo "  docker compose logs        # Voir les logs"
    echo "  docker compose down        # Arrêter l'application"
    echo "  docker compose restart     # Redémarrer l'application"
    echo "  ./setup.sh --clean --start # Redémarrage propre"
}

# Point d'entrée
main "$@"

