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

# Fonction de confirmation simplifiée et sécurisée
demander_confirmation() {
    local prompt="$1"
    local default="${2:-non}"
    local response
    
    while true; do
        printf "\n%s (oui/non) [default: %s]: " "$prompt" "$default"
        
        # Lecture simple sans options
        read -r response
        
        # Si vide, utiliser la valeur par défaut
        if [[ -z "$response" ]]; then
            response="$default"
        fi
        
        # Normaliser
        response=$(printf "%s" "$response" | tr '[:upper:]' '[:lower:]' | tr -d ' ')
        
        case "$response" in
            oui|yes)
                printf "→ OUI\n"
                return 0
                ;;
            non|no)
                printf "→ NON\n"
                return 1
                ;;
            *)
                printf "Erreur: Tapez 'oui' ou 'non'\n"
                ;;
        esac
    done
}

# Fonction pour générer le fichier .env s'il n'existe pas
generate_env_if_missing() {
    if [[ ! -f ".env" ]]; then
        log_info "Génération du fichier .env..."
        
        # Générer un token secret aléatoire
        secret_token=$(openssl rand -hex 16 2>/dev/null || head /dev/urandom | tr -dc A-Za-z0-9 | head -c 32)
        
        # Générer un path prefix aléatoire
        path_prefix=$(openssl rand -hex 8 2>/dev/null || head /dev/urandom | tr -dc A-Za-z0-9 | head -c 16)
        
        cat > .env << EOF
# REQUIRED - Security
SECRET_TOKEN=${secret_token}
UI_PATH_PREFIX=${path_prefix}

# Optional - Server Configuration
PORT=8080

# Optional - BitTorrent Configuration
MIN_UPLOAD_RATE=30
MAX_UPLOAD_RATE=160
SIMULTANEOUS_SEED=20
KEEP_TORRENT_WITH_ZERO_LEECHERS=true
UPLOAD_RATIO_TARGET=-1.0
DEFAULT_CLIENT=qbittorrent-4.6.0.client

# Optional - Proxy Configuration
# HTTP_PROXY_HOST=10.10.10.10
# HTTP_PROXY_PORT=8888
EOF
        
        log_success "Fichier .env généré avec des valeurs aléatoires sécurisées"
        echo -e "${YELLOW}  → SECRET_TOKEN: ${secret_token}${NC}"
        echo -e "${YELLOW}  → UI_PATH_PREFIX: ${path_prefix}${NC}"
        echo -e "${YELLOW}  → Accès WebUI: http://localhost:8080/${path_prefix}/ui/${NC}"
    else
        log_info "Fichier .env existant utilisé"
    fi
}
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
    
    # Générer .env si nécessaire
    generate_env_if_missing
    
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
    
    # Sauvegarder le répertoire courant
    local current_dir=$(pwd)
    
    cd backend || {
        log_error "Impossible d'accéder au dossier backend"
        return 1
    }
    
    # Vérifier si python3-venv est installé, sinon utiliser pip directement
    if ! python3 -c "import venv" 2>/dev/null; then
        log_warn "python3-venv non installé, utilisation de pip global"
        use_global_python=true
    else
        use_global_python=false
    fi
    
    if [[ "$use_global_python" == false ]]; then
        # Créer un environnement virtuel si nécessaire
        if [[ ! -d "venv" ]]; then
            log_info "Création de l'environnement virtuel Python..."
            if ! python3 -m venv venv; then
                log_warn "Échec de la création de l'environnement virtuel, utilisation de pip global"
                use_global_python=true
            fi
        elif [[ ! -f "venv/bin/activate" ]]; then
            log_warn "Environnement virtuel corrompu, recréation..."
            rm -rf venv
            if ! python3 -m venv venv; then
                log_warn "Échec de la recréation de l'environnement virtuel, utilisation de pip global"
                use_global_python=true
            fi
        fi
        
        # Activer l'environnement virtuel si disponible
        if [[ "$use_global_python" == false && -f "venv/bin/activate" ]]; then
            source venv/bin/activate
            log_info "Environnement virtuel activé"
        else
            use_global_python=true
        fi
    fi
    
    if [[ "$use_global_python" == true ]]; then
        log_info "Utilisation de Python global (pas d'environnement virtuel)"
    fi
    
    # Installer les dépendances
    log_info "Installation des dépendances..."
    if ! pip3 install --user --upgrade pip > /dev/null 2>&1; then
        log_warn "Échec de la mise à jour de pip"
    fi
    
    if ! pip3 install --user -r requirements.txt > /dev/null 2>&1; then
        log_error "Échec de l'installation des dépendances"
        if [[ "$use_global_python" == false ]]; then
            deactivate 2>/dev/null || true
        fi
        cd "$current_dir"
        return 1
    fi
    
    if ! pip3 install --user pytest pytest-cov flake8 black isort > /dev/null 2>&1; then
        log_warn "Échec de l'installation des outils de test (continuons quand même)"
    fi
    
    # Linting
    log_info "Vérification du code (flake8)..."
    if command -v flake8 >/dev/null 2>&1; then
        flake8 app/ --max-line-length=88 --extend-ignore=E203,W503 || log_warn "Problèmes de linting trouvés"
    else
        log_warn "flake8 non disponible, vérification ignorée"
    fi
    
    # Tests
    log_info "Exécution des tests..."
    if command -v pytest >/dev/null 2>&1; then
        if [[ -d "tests" ]]; then
            python3 -m pytest tests/ -v --tb=short || log_warn "Certains tests ont échoué"
        else
            log_warn "Dossier tests/ non trouvé, tests ignorés"
        fi
    else
        log_warn "pytest non disponible, tests ignorés"
    fi
    
    # Désactiver l'environnement virtuel et revenir au répertoire original
    if [[ "$use_global_python" == false ]]; then
        deactivate 2>/dev/null || true
    fi
    cd "$current_dir"
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
    
    # Sauvegarder le répertoire courant
    local current_dir=$(pwd)
    
    cd frontend || {
        log_error "Impossible d'accéder au dossier frontend"
        return 1
    }
    
    # Installer les dépendances
    log_info "Installation des dépendances npm..."
    if ! npm install > /dev/null 2>&1; then
        log_error "Échec de l'installation des dépendances npm"
        cd "$current_dir"
        return 1
    fi
    
    # Tests
    log_info "Exécution des tests frontend..."
    if npm run test -- --watchAll=false 2>/dev/null || npm test -- --watchAll=false 2>/dev/null; then
        log_success "Tests frontend réussis"
    else
        log_warn "Tests frontend échoués ou non configurés"
    fi
    
    cd "$current_dir"
    log_success "Tests frontend terminés"
}

# Fonction pour démarrer l'application
start_app() {
    log_step "Démarrage de l'application PyJOAL..."
    
    # Générer .env si nécessaire
    generate_env_if_missing
    
    # Démarrer avec docker-compose
    docker compose up -d
    
    # Attendre le démarrage
    log_info "Attente du démarrage (15 secondes)..."
    sleep 15
    
    # Lire les valeurs du .env pour afficher l'URL
    if [[ -f ".env" ]]; then
        port=$(grep '^PORT=' .env 2>/dev/null | cut -d'=' -f2 | tr -d '"' || echo "8080")
        ui_prefix=$(grep '^UI_PATH_PREFIX=' .env 2>/dev/null | cut -d'=' -f2 | tr -d '"' || echo "")
        
        if [[ -n "$ui_prefix" ]]; then
            webui_url="http://localhost:${port}/${ui_prefix}/ui/"
        else
            webui_url="http://localhost:${port}/"
        fi
    else
        webui_url="http://localhost:8080/"
    fi
    
    # Vérifier que l'application répond
    if curl -s -f "$webui_url" > /dev/null 2>&1 || curl -s -f "http://localhost:${port:-8080}" > /dev/null 2>&1; then
        log_success "Application démarrée avec succès!"
        echo ""
        echo -e "${GREEN}🌐 Application accessible sur: $webui_url${NC}"
        echo -e "${BLUE}📊 Logs en temps réel: docker compose logs -f${NC}"
    else
        log_warn "L'application ne répond pas encore"
        echo ""
        echo -e "${YELLOW}🌐 URL prévue: $webui_url${NC}"
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

# Fonction de nettoyage Git avancé
clean_git_repo() {
    log_step "Nettoyage avancé du dépôt Git..."
    
    # Désactiver le pager Git pour éviter l'ouverture d'un éditeur
    export GIT_PAGER=cat
    export PAGER=cat
    
    echo ""
    echo -e "${CYAN}=== OPTIONS DE NETTOYAGE ===${NC}"
    
    # Option 1: Supprimer les fichiers non suivis
    echo ""
    echo -e "${YELLOW}Fichiers non suivis qui seraient supprimés :${NC}"
    local git_clean_output
    git_clean_output=$(git clean -xdn 2>/dev/null)
    if echo "$git_clean_output" | grep -q "Would remove"; then
        echo "$git_clean_output"
        echo ""
        if demander_confirmation "Supprimer ces fichiers non suivis ?"; then
            clean_untracked="oui"
        else
            clean_untracked="NON"
        fi
    else
        echo "Aucun fichier non suivi à supprimer"
        clean_untracked="NON"
    fi
    
    # Option 2: Reset --hard
    echo ""
    echo -e "${YELLOW}Fichiers modifiés qui seraient remis à l'état de la branche :${NC}"
    local git_diff_output
    git_diff_output=$(git diff --name-only HEAD 2>/dev/null)
    if [[ -n "$git_diff_output" ]]; then
        echo "$git_diff_output"
        echo ""
        echo -e "${RED}⚠️  ATTENTION: git reset --hard va PERDRE toutes vos modifications non committées !${NC}"
        if demander_confirmation "Remettre tous les fichiers à l'état de la branche Git ?"; then
            reset_hard="oui"
        else
            reset_hard="NON"
        fi
    else
        echo "Aucun fichier modifié"
        reset_hard="NON"
    fi
    
    # Vérifier les fichiers de configuration importants
    config_files=(".env" "docker-compose.override.yml" "config.json")
    important_files_found=()
    
    for file in "${config_files[@]}"; do
        if [[ -f "$file" ]] && ! git ls-files --error-unmatch "$file" >/dev/null 2>&1; then
            important_files_found+=("$file")
        fi
    done
    
    # Avertir pour les fichiers de configuration importants
    if [[ ${#important_files_found[@]} -gt 0 && "$clean_untracked" == "oui" ]]; then
        echo ""
        echo -e "${RED}⚠️  ATTENTION: Ces fichiers de configuration seraient supprimés :${NC}"
        for file in "${important_files_found[@]}"; do
            echo -e "${RED}   - $file${NC}"
        done
        echo -e "${YELLOW}   Pensez à sauvegarder vos configurations !${NC}"
        echo ""
        if ! demander_confirmation "Continuer malgré ces fichiers importants ?"; then
            clean_untracked="NON"
        fi
    fi
    
    # Résumé des actions
    echo ""
    echo -e "${CYAN}=== RÉSUMÉ DES ACTIONS ===${NC}"
    echo -e "Supprimer fichiers non suivis: ${clean_untracked}"
    echo -e "Reset --hard: ${reset_hard}"
    
    if [[ "$clean_untracked" == "NON" && "$reset_hard" == "NON" ]]; then
        log_warn "Aucune action de nettoyage sélectionnée"
        return 1
    fi
    
    echo ""
    if demander_confirmation "Confirmer ces actions ?"; then
        log_info "Nettoyage en cours..."
        
        if [[ "$reset_hard" == "oui" ]]; then
            log_info "Reset --hard en cours..."
            git reset --hard HEAD
            log_success "Reset --hard terminé"
        fi
        
        if [[ "$clean_untracked" == "oui" ]]; then
            log_info "Suppression des fichiers non suivis..."
            git clean -xdf
            log_success "Fichiers non suivis supprimés"
        fi
        
        log_success "Nettoyage Git terminé"
    else
        log_warn "Nettoyage annulé"
        unset GIT_PAGER PAGER
        return 1
    fi
    
    # Remettre l'environnement Git normal
    unset GIT_PAGER PAGER
}

# Fonction d'installation complète avec tests
full_setup_with_tests() {
    log_step "Setup complet avec tests..."
    
    update_clients
    build_app
    test_backend
    start_app
    
    log_success "Setup complet avec tests terminé!"
}

# Fonction de déploiement complet (clean + build + start)
full_deploy() {
    log_step "Déploiement complet (clean + build + start)..."
    
    # Nettoyage Git
    if ! clean_git_repo; then
        log_warn "Déploiement annulé à cause du nettoyage"
        return 1
    fi
    
    # Build
    build_app
    
    # Lancement
    start_app
    
    log_success "Déploiement complet terminé!"
}

# Mise à jour de version interactive
update_version_interactive() {
    log_info "📦 Assistant de mise à jour de version"
    echo ""
    
    # Afficher la version actuelle
    if [[ -f "VERSION" ]]; then
        CURRENT_VERSION=$(cat VERSION)
        echo -e "Version actuelle: ${CYAN}${CURRENT_VERSION}${NC}"
    else
        CURRENT_VERSION="0.0.0"
        echo -e "Pas de fichier VERSION trouvé. Création d'un nouveau."
    fi
    
    # Parser la version actuelle
    IFS='.' read -r major minor patch <<< "$CURRENT_VERSION"
    
    # Suggérer les prochaines versions
    NEXT_PATCH="$major.$minor.$((patch + 1))"
    NEXT_MINOR="$major.$((minor + 1)).0"
    NEXT_MAJOR="$((major + 1)).0.0"
    
    echo ""
    echo "Versions suggérées:"
    echo "  1) Patch: ${NEXT_PATCH} (corrections de bugs)"
    echo "  2) Minor: ${NEXT_MINOR} (nouvelles fonctionnalités)"
    echo "  3) Major: ${NEXT_MAJOR} (changements majeurs)"
    echo "  4) Version personnalisée"
    echo "  0) Annuler"
    echo ""
    echo -n -e "${YELLOW}Votre choix [0-4]: ${NC}"
    read -r version_choice
    
    case $version_choice in
        1) NEW_VERSION="$NEXT_PATCH" ;;
        2) NEW_VERSION="$NEXT_MINOR" ;;
        3) NEW_VERSION="$NEXT_MAJOR" ;;
        4)
            echo -n -e "${YELLOW}Entrez la version personnalisée (X.Y.Z): ${NC}"
            read -r NEW_VERSION
            ;;
        0|*)
            log_info "Mise à jour de version annulée"
            return 0
            ;;
    esac
    
    # Valider le format de version
    if [[ ! "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        log_error "Format de version invalide. Utilisez le format X.Y.Z"
        return 1
    fi
    
    echo ""
    if demander_confirmation "Mettre à jour la version de ${CURRENT_VERSION} vers ${NEW_VERSION}?" "oui"; then
        log_step "Mise à jour vers la version $NEW_VERSION..."
        
        # 1. Mettre à jour le fichier VERSION principal
        echo "$NEW_VERSION" > VERSION
        log_info "Fichier VERSION mis à jour"
        
        # 2. Mettre à jour package.json
        if [[ -f "frontend/package.json" ]]; then
            sed -i "s/\"version\": \".*\"/\"version\": \"$NEW_VERSION\"/" frontend/package.json
            log_info "frontend/package.json mis à jour"
        fi
        
        # 3. Mettre à jour BUILD_VERSION.txt pour le frontend
        if [[ -d "frontend" ]]; then
            echo "$NEW_VERSION" > frontend/BUILD_VERSION.txt
            log_info "frontend/BUILD_VERSION.txt mis à jour"
        fi
        
        # 4. Ajouter une entrée au changelog (si existe)
        if [[ -f "CHANGELOG.md" ]]; then
            CHANGELOG_ENTRY="## [$NEW_VERSION] - $(date +%Y-%m-%d)

### Changed
- Version bump to $NEW_VERSION

"
            # Insérer après l'en-tête
            if grep -q "^# Changelog" CHANGELOG.md; then
                {
                    head -n 1 CHANGELOG.md
                    echo ""
                    echo "$CHANGELOG_ENTRY"
                    tail -n +2 CHANGELOG.md
                } > CHANGELOG.tmp && mv CHANGELOG.tmp CHANGELOG.md
                log_info "CHANGELOG.md mis à jour"
            fi
        fi
        
        # 5. Opérations Git (optionnel)
        echo ""
        if demander_confirmation "Créer un commit Git et un tag pour cette version?" "oui"; then
            git add VERSION frontend/package.json frontend/BUILD_VERSION.txt CHANGELOG.md 2>/dev/null || true
            git commit -m "chore: bump version to v$NEW_VERSION

- Updated VERSION file to $NEW_VERSION
- Synced frontend/package.json version
- Added changelog entry"
            log_info "Commit Git créé"
            
            if demander_confirmation "Créer le tag Git v$NEW_VERSION?" "oui"; then
                git tag "v$NEW_VERSION"
                log_info "Tag v$NEW_VERSION créé"
                
                if demander_confirmation "Pousser le commit et le tag vers origin?" "non"; then
                    git push origin main || git push origin master
                    git push origin "v$NEW_VERSION"
                    log_info "Poussé vers origin"
                fi
            fi
        fi
        
        log_success "Version mise à jour vers $NEW_VERSION!"
        echo ""
        echo "Prochaines étapes:"
        echo "  1. 🐳 Rebuild l'image Docker: Option 2 du menu"
        echo "  2. 🚀 Déployer: docker push your-registry/pyjoal:$NEW_VERSION"
        echo "  3. 🏷️  Créer une release GitHub depuis le tag v$NEW_VERSION"
    else
        log_info "Mise à jour de version annulée"
    fi
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
    echo "11) 🧪 Setup complet avec tests (clients + build + test + start)"
    echo "12) 🚀 Déploiement rapide (clean Git + build + start)"
    echo "13) 📦 Mise à jour de version"
    echo "0)  ❌ Quitter"
    echo ""
    echo -n -e "${YELLOW}Votre choix [0-13]: ${NC}"
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
                full_setup_with_tests
                echo ""
                echo -e "${GREEN}Appuyez sur Entrée pour continuer...${NC}"
                read -r
                ;;
            12)
                echo ""
                full_deploy
                echo ""
                echo -e "${GREEN}Appuyez sur Entrée pour continuer...${NC}"
                read -r
                ;;
            13)
                echo ""
                update_version_interactive
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
                log_error "Option invalide. Veuillez choisir entre 0 et 13."
                sleep 2
                ;;
        esac
    done
}

# Point d'entrée
main "$@"