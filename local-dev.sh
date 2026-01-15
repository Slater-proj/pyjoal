#!/bin/bash

# local-dev.sh - Script de développement local pour PyJOAL
# Interface de menu interactive pour build, test et déploiement local

set -e

# Couleurs pour les messages
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Fonction d'affichage du header
show_header() {
    clear
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    PyJOAL - Dev Tools                        ║"
    echo "║              Script de développement local                   ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
}

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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Fonction pour vérifier les prérequis
check_prerequisites() {
    log_step "Vérification des prérequis..."
    
    MISSING_DEPS=false
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker n'est pas installé"
        MISSING_DEPS=true
    fi
    
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose n'est pas disponible"
        MISSING_DEPS=true
    fi
    
    if ! command -v python3 &> /dev/null; then
        log_warn "Python3 n'est pas installé (optionnel pour certaines fonctions)"
    fi
    
    if ! command -v node &> /dev/null; then
        log_warn "Node.js n'est pas installé (optionnel pour les tests frontend)"
    fi
    
    if [[ $MISSING_DEPS == true ]]; then
        log_error "Des dépendances critiques manquent. Veuillez les installer."
        exit 1
    fi
    
    log_success "Prérequis vérifiés"
}

# Fonction pour nettoyer l'environnement
clean_environment() {
    log_step "Nettoyage de l'environnement Docker..."
    
    # Arrêter tous les conteneurs PyJOAL
    docker ps -q --filter "name=pyjoal" | xargs -r docker stop
    docker ps -aq --filter "name=pyjoal" | xargs -r docker rm
    
    # Supprimer les images PyJOAL locales
    docker images | grep pyjoal | awk '{print $3}' | sort -u | xargs -r docker rmi -f
    
    # Nettoyer les volumes et réseaux orphelins
    docker system prune -f
    docker volume prune -f
    
    log_success "Environnement nettoyé"
}

# Fonction pour construire l'application
build_app() {
    log_step "Construction de l'application PyJOAL..."
    
    echo "Construction Docker en cours..."
    if docker compose build --no-cache; then
        log_success "Build Docker réussi"
    else
        log_error "Échec du build Docker"
        return 1
    fi
}

# Fonction pour lancer les tests backend
test_backend() {
    log_step "Tests backend Python..."
    
    if [[ ! -d "backend" ]]; then
        log_error "Dossier backend non trouvé"
        return 1
    fi
    
    cd backend
    
    # Créer un environnement virtuel si nécessaire
    if [[ ! -d "venv" ]]; then
        log_info "Création de l'environnement virtuel Python..."
        python3 -m venv venv
    fi
    
    # Activer l'environnement virtuel
    source venv/bin/activate
    
    # Installer les dépendances
    log_info "Installation des dépendances..."
    pip install --upgrade pip > /dev/null
    pip install -r requirements.txt > /dev/null
    pip install pytest pytest-cov flake8 black isort > /dev/null
    
    # Linting
    log_info "Vérification du code (flake8)..."
    flake8 app/ --max-line-length=88 --extend-ignore=E203,W503 || log_warn "Problèmes de linting trouvés"
    
    # Tests
    log_info "Exécution des tests..."
    python -m pytest tests/ -v --tb=short
    
    cd ..
    log_success "Tests backend terminés"
}

# Fonction pour lancer les tests frontend
test_frontend() {
    log_step "Tests frontend..."
    
    if [[ ! -d "frontend" ]]; then
        log_error "Dossier frontend non trouvé"
        return 1
    fi
    
    if ! command -v node &> /dev/null; then
        log_warn "Node.js non installé, tests frontend ignorés"
        return 0
    fi
    
    cd frontend
    
    # Installer les dépendances
    log_info "Installation des dépendances npm..."
    npm install > /dev/null
    
    # Tests
    log_info "Exécution des tests frontend..."
    npm test -- --watchAll=false
    
    cd ..
    log_success "Tests frontend terminés"
}

# Fonction pour démarrer l'application
start_app() {
    log_step "Démarrage de l'application PyJOAL..."
    
    # Démarrer avec docker-compose
    docker compose up -d
    
    # Attendre le démarrage
    log_info "Attente du démarrage (15 secondes)..."
    sleep 15
    
    # Vérifier que l'application répond
    if curl -s -f http://localhost:8080 > /dev/null 2>&1; then
        log_success "Application démarrée avec succès!"
        echo ""
        echo -e "${GREEN}🌐 Application accessible sur: http://localhost:8080${NC}"
        echo -e "${BLUE}📊 Logs en temps réel: docker compose logs -f${NC}"
    else
        log_warn "L'application ne répond pas sur le port 8080"
        echo ""
        echo "Vérifiez les logs avec: docker compose logs"
    fi
}

# Fonction pour arrêter l'application
stop_app() {
    log_step "Arrêt de l'application PyJOAL..."
    
    docker compose down
    
    log_success "Application arrêtée"
}

# Fonction pour afficher les logs
show_logs() {
    log_step "Affichage des logs..."
    
    echo "Appuyez sur Ctrl+C pour quitter le suivi des logs"
    sleep 2
    docker compose logs -f
}

# Fonction pour afficher le statut
show_status() {
    log_step "Statut de l'application..."
    
    echo ""
    echo -e "${CYAN}=== CONTENEURS ===${NC}"
    docker compose ps
    
    echo ""
    echo -e "${CYAN}=== IMAGES ===${NC}"
    docker images | grep -E "(pyjoal|REPOSITORY)" || echo "Aucune image PyJOAL trouvée"
    
    echo ""
    echo -e "${CYAN}=== VOLUMES ===${NC}"
    docker volume ls | grep pyjoal || echo "Aucun volume PyJOAL trouvé"
    
    echo ""
    if curl -s -f http://localhost:8080 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Application accessible sur http://localhost:8080${NC}"
    else
        echo -e "${RED}❌ Application non accessible${NC}"
    fi
}

# Fonction pour mettre à jour les clients BitTorrent
update_clients() {
    log_step "Mise à jour des clients BitTorrent..."
    
    if [[ -f "scripts/update_clients.py" ]]; then
        if command -v python3 &> /dev/null; then
            python3 scripts/update_clients.py
            log_success "Clients BitTorrent mis à jour"
        else
            log_warn "Python3 non disponible, mise à jour ignorée"
        fi
    else
        log_warn "Script de mise à jour non trouvé"
    fi
}

# Fonction d'installation complète
full_setup() {
    log_step "Installation complète..."
    
    update_clients
    build_app
    test_backend
    start_app
    
    log_success "Installation complète terminée!"
}

# Menu principal
show_menu() {
    echo ""
    echo -e "${PURPLE}=== MENU PRINCIPAL ===${NC}"
    echo ""
    echo "1)  🔧 Build complet (clean + build + tests)"
    echo "2)  🐳 Build Docker seulement"
    echo "3)  🧪 Tests backend"
    echo "4)  🎨 Tests frontend"
    echo "5)  ▶️  Démarrer l'application"
    echo "6)  ⏹️  Arrêter l'application"
    echo "7)  📋 Afficher les logs"
    echo "8)  📊 Statut de l'application"
    echo "9)  🔄 Mettre à jour les clients BitTorrent"
    echo "10) 🧹 Nettoyer l'environnement"
    echo "11) 🚀 Installation complète (tout en un)"
    echo "0)  ❌ Quitter"
    echo ""
    echo -n -e "${YELLOW}Votre choix [0-11]: ${NC}"
}

# Fonction principale
main() {
    # Vérifier qu'on est dans le bon répertoire
    if [[ ! -f "docker-compose.yml" ]]; then
        log_error "Fichier docker-compose.yml non trouvé. Exécutez ce script depuis la racine du projet PyJOAL."
        exit 1
    fi
    
    check_prerequisites
    
    while true; do
        show_header
        show_menu
        read -r choice
        
        case $choice in
            1)
                echo ""
                log_info "Build complet sélectionné..."
                clean_environment
                build_app
                test_backend
                echo ""
                echo -e "${GREEN}Appuyez sur Entrée pour continuer...${NC}"
                read -r
                ;;
            2)
                echo ""
                build_app
                echo ""
                echo -e "${GREEN}Appuyez sur Entrée pour continuer...${NC}"
                read -r
                ;;
            3)
                echo ""
                test_backend
                echo ""
                echo -e "${GREEN}Appuyez sur Entrée pour continuer...${NC}"
                read -r
                ;;
            4)
                echo ""
                test_frontend
                echo ""
                echo -e "${GREEN}Appuyez sur Entrée pour continuer...${NC}"
                read -r
                ;;
            5)
                echo ""
                start_app
                echo ""
                echo -e "${GREEN}Appuyez sur Entrée pour continuer...${NC}"
                read -r
                ;;
            6)
                echo ""
                stop_app
                echo ""
                echo -e "${GREEN}Appuyez sur Entrée pour continuer...${NC}"
                read -r
                ;;
            7)
                echo ""
                show_logs
                ;;
            8)
                echo ""
                show_status
                echo ""
                echo -e "${GREEN}Appuyez sur Entrée pour continuer...${NC}"
                read -r
                ;;
            9)
                echo ""
                update_clients
                echo ""
                echo -e "${GREEN}Appuyez sur Entrée pour continuer...${NC}"
                read -r
                ;;
            10)
                echo ""
                clean_environment
                echo ""
                echo -e "${GREEN}Appuyez sur Entrée pour continuer...${NC}"
                read -r
                ;;
            11)
                echo ""
                full_setup
                echo ""
                echo -e "${GREEN}Appuyez sur Entrée pour continuer...${NC}"
                read -r
                ;;
            0)
                echo ""
                log_info "Au revoir! 👋"
                exit 0
                ;;
            *)
                echo ""
                log_error "Option invalide. Veuillez choisir entre 0 et 11."
                sleep 2
                ;;
        esac
    done
}

# Point d'entrée
main "$@"