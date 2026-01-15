#!/bin/bash

# local-dev.sh - Local Development Script for PyJOAL
# Interactive menu interface for build, test, and local deployment

set -e

# Colors for messages
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to display header
show_header() {
    clear
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    PyJOAL - Dev Tools                        ║"
    echo "║              Local Development Script                        ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
}

# Message display functions
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

# Enhanced confirmation function with flexible input
ask_confirmation() {
    local prompt="$1"
    local default="${2:-no}"
    local response
    
    while true; do
        if [[ "$default" == "yes" ]]; then
            printf "${YELLOW}%s (Yes/no): ${NC}" "$prompt"
        else
            printf "${YELLOW}%s (yes/No): ${NC}" "$prompt"
        fi
        
        # Safe reading without special options
        IFS= read -r response
        
        # If empty, use default
        if [[ -z "$response" ]]; then
            response="$default"
        fi
        
        # Normalize response
        response=$(printf "%s" "$response" | tr '[:upper:]' '[:lower:]')
        
        case "$response" in
            yes|oui)
                return 0
                ;;
            no|non)
                return 1
                ;;
            *)
                printf "${RED}Please answer 'yes' or 'no'${NC}\n"
                ;;
        esac
    done
}

# Function to generate .env file if missing
generate_env_if_missing() {
    if [[ ! -f ".env" ]]; then
        log_info "Generating .env file..."
        
        # Generate random secure token
        secret_token=$(openssl rand -hex 16 2>/dev/null || head /dev/urandom | tr -dc A-Za-z0-9 | head -c 32)
        
        # Generate random path prefix
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
        
        log_success ".env file generated with secure random values"
        echo -e "${YELLOW}  → SECRET_TOKEN: ${secret_token}${NC}"
        echo -e "${YELLOW}  → UI_PATH_PREFIX: ${path_prefix}${NC}"
        echo -e "${YELLOW}  → WebUI Access: http://localhost:8080/${path_prefix}/ui/${NC}"
    else
        log_info "Using existing .env file"
    fi
}

# Function to check prerequisites
check_prerequisites() {
    log_step "Checking prerequisites..."
    
    MISSING_DEPS=false
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        MISSING_DEPS=true
    fi
    
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not available"
        MISSING_DEPS=true
    fi
    
    if ! command -v python3 &> /dev/null; then
        log_warn "Python3 is not installed (optional for some functions)"
    fi
    
    if ! command -v node &> /dev/null; then
        log_warn "Node.js is not installed (optional for frontend tests)"
    fi
    
    if [[ $MISSING_DEPS == true ]]; then
        log_error "Critical dependencies are missing. Please install them."
        exit 1
    fi
    
    log_success "Prerequisites verified"
}

# Function to clean Docker environment
clean_environment() {
    log_step "Cleaning Docker environment..."
    
    # Stop all PyJOAL containers
    docker ps -q --filter "name=pyjoal" | xargs -r docker stop
    docker ps -aq --filter "name=pyjoal" | xargs -r docker rm
    
    # Remove local PyJOAL images
    docker images | grep pyjoal | awk '{print $3}' | sort -u | xargs -r docker rmi -f
    
    # Clean orphaned volumes and networks
    docker system prune -f
    docker volume prune -f
    
    log_success "Environment cleaned"
}

# Function to build the application
build_app() {
    log_step "Building PyJOAL application..."
    
    # Generate .env if needed
    generate_env_if_missing
    
    echo "Docker build in progress..."
    if docker compose build --no-cache; then
        log_success "Docker build successful"
    else
        log_error "Docker build failed"
        return 1
    fi
}

# Function to run backend tests
test_backend() {
    log_step "Running Python backend tests..."
    
    if [[ ! -d "backend" ]]; then
        log_error "Backend directory not found"
        return 1
    fi
    
    # Save current directory
    local current_dir=$(pwd)
    
    cd backend || {
        log_error "Cannot access backend directory"
        return 1
    }
    
    # Check if python3-venv is installed, otherwise use global pip
    if ! python3 -c "import venv" 2>/dev/null; then
        log_warn "python3-venv not installed, using global Python"
        use_global_python=true
    else
        use_global_python=false
    fi
    
    if [[ "$use_global_python" == false ]]; then
        # Create virtual environment if needed
        if [[ ! -d "venv" ]]; then
            log_info "Creating Python virtual environment..."
            if ! python3 -m venv venv; then
                log_warn "Failed to create virtual environment, using global Python"
                use_global_python=true
            fi
        elif [[ ! -f "venv/bin/activate" ]]; then
            log_warn "Virtual environment corrupted, recreating..."
            rm -rf venv
            if ! python3 -m venv venv; then
                log_warn "Failed to recreate virtual environment, using global Python"
                use_global_python=true
            fi
        fi
        
        # Activate virtual environment if available
        if [[ "$use_global_python" == false && -f "venv/bin/activate" ]]; then
            source venv/bin/activate
            log_info "Virtual environment activated"
        else
            use_global_python=true
        fi
    fi
    
    if [[ "$use_global_python" == true ]]; then
        log_info "Using global Python (no virtual environment)"
    fi
    
    # Install dependencies
    log_info "Installing dependencies..."
    if ! pip3 install --user --upgrade pip > /dev/null 2>&1; then
        log_warn "Failed to upgrade pip"
    fi
    
    if ! pip3 install --user -r requirements.txt > /dev/null 2>&1; then
        log_error "Failed to install dependencies"
        if [[ "$use_global_python" == false ]]; then
            deactivate 2>/dev/null || true
        fi
        cd "$current_dir"
        return 1
    fi
    
    if ! pip3 install --user pytest pytest-cov flake8 black isort > /dev/null 2>&1; then
        log_warn "Failed to install test tools (continuing anyway)"
    fi
    
    # Linting
    log_info "Code verification (flake8)..."
    if command -v flake8 >/dev/null 2>&1; then
        flake8 app/ --max-line-length=88 --extend-ignore=E203,W503 || log_warn "Linting issues found"
    else
        log_warn "flake8 not available, verification skipped"
    fi
    
    # Tests
    log_info "Running tests..."
    if command -v pytest >/dev/null 2>&1; then
        if [[ -d "tests" ]]; then
            python3 -m pytest tests/ -v --tb=short || log_warn "Some tests failed"
        else
            log_warn "tests/ directory not found, tests skipped"
        fi
    else
        log_warn "pytest not available, tests skipped"
    fi
    
    # Deactivate virtual environment and return to original directory
    if [[ "$use_global_python" == false ]]; then
        deactivate 2>/dev/null || true
    fi
    cd "$current_dir"
    log_success "Backend tests completed"
}

# Function to run frontend tests
test_frontend() {
    log_step "Running frontend tests..."
    
    if [[ ! -d "frontend" ]]; then
        log_error "Frontend directory not found"
        return 1
    fi
    
    if ! command -v node &> /dev/null; then
        log_warn "Node.js not installed, frontend tests skipped"
        return 0
    fi
    
    # Save current directory
    local current_dir=$(pwd)
    
    cd frontend || {
        log_error "Cannot access frontend directory"
        return 1
    }
    
    # Install dependencies
    log_info "Installing npm dependencies..."
    if ! npm install > /dev/null 2>&1; then
        log_error "Failed to install npm dependencies"
        cd "$current_dir"
        return 1
    fi
    
    # Tests
    log_info "Running frontend tests..."
    if npm run test -- --watchAll=false 2>/dev/null || npm test -- --watchAll=false 2>/dev/null; then
        log_success "Frontend tests successful"
    else
        log_warn "Frontend tests failed or not configured"
    fi
    
    cd "$current_dir"
    log_success "Frontend tests completed"
}

# Function to start the application
start_app() {
    log_step "Starting PyJOAL application..."
    
    # Generate .env if needed
    generate_env_if_missing
    
    # Start with docker-compose
    docker compose up -d
    
    # Wait for startup
    log_info "Waiting for startup (15 seconds)..."
    sleep 15
    
    # Read values from .env to display URL
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
    
    # Check if application responds
    if curl -s -f "$webui_url" > /dev/null 2>&1 || curl -s -f "http://localhost:${port:-8080}" > /dev/null 2>&1; then
        log_success "Application started successfully!"
        echo ""
        echo -e "${GREEN}🌐 Application accessible at: $webui_url${NC}"
        echo -e "${BLUE}📊 Real-time logs: docker compose logs -f${NC}"
    else
        log_warn "Application not responding yet"
        echo ""
        echo -e "${YELLOW}🌐 Expected URL: $webui_url${NC}"
        echo "Check logs with: docker compose logs"
    fi
}

# Function to stop the application
stop_app() {
    log_step "Stopping PyJOAL application..."
    
    docker compose down
    
    log_success "Application stopped"
}

# Function to show logs
show_logs() {
    log_step "Displaying logs..."
    
    echo "Press Ctrl+C to exit log monitoring"
    sleep 2
    docker compose logs -f
}

# Function to show status
show_status() {
    log_step "Application status..."
    
    echo ""
    echo -e "${CYAN}=== CONTAINERS ===${NC}"
    docker compose ps
    
    echo ""
    echo -e "${CYAN}=== IMAGES ===${NC}"
    docker images | grep -E "(pyjoal|REPOSITORY)" || echo "No PyJOAL images found"
    
    echo ""
    echo -e "${CYAN}=== VOLUMES ===${NC}"
    docker volume ls | grep pyjoal || echo "No PyJOAL volumes found"
    
    echo ""
    if curl -s -f http://localhost:8080 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Application accessible at http://localhost:8080${NC}"
    else
        echo -e "${RED}❌ Application not accessible${NC}"
    fi
}

# Function to update BitTorrent clients
update_clients() {
    log_step "Updating BitTorrent clients..."
    
    if [[ -f "scripts/update_clients.py" ]]; then
        if command -v python3 &> /dev/null; then
            python3 scripts/update_clients.py
            log_success "BitTorrent clients updated"
        else
            log_warn "Python3 not available, update skipped"
        fi
    else
        log_warn "Update script not found"
    fi
}

# Advanced Git cleanup function
clean_git_repo() {
    log_step "Advanced Git repository cleanup..."
    
    # Disable Git pager to avoid opening editor
    export GIT_PAGER=cat
    export PAGER=cat
    
    echo ""
    echo -e "${CYAN}=== CLEANUP OPTIONS ===${NC}"
    
    # Option 1: Remove untracked files
    echo ""
    echo -e "${YELLOW}Untracked files that would be removed:${NC}"
    local git_clean_output
    git_clean_output=$(git clean -xdn 2>/dev/null)
    if echo "$git_clean_output" | grep -q "Would remove"; then
        echo "$git_clean_output"
        echo ""
        if ask_confirmation "Remove these untracked files?"; then
            clean_untracked="yes"
        else
            clean_untracked="no"
        fi
    else
        echo "No untracked files to remove"
        clean_untracked="no"
    fi
    
    # Option 2: Reset --hard
    echo ""
    echo -e "${YELLOW}Modified files that would be reset to branch state:${NC}"
    local git_diff_output
    git_diff_output=$(git diff --name-only HEAD 2>/dev/null)
    if [[ -n "$git_diff_output" ]]; then
        echo "$git_diff_output"
        echo ""
        echo -e "${RED}⚠️  WARNING: git reset --hard will LOSE all uncommitted changes!${NC}"
        if ask_confirmation "Reset all files to Git branch state?"; then
            reset_hard="yes"
        else
            reset_hard="no"
        fi
    else
        echo "No modified files"
        reset_hard="no"
    fi
    
    # Check for important configuration files
    config_files=(".env" "docker-compose.override.yml" "config.json")
    important_files_found=()
    
    for file in "${config_files[@]}"; do
        if [[ -f "$file" ]] && ! git ls-files --error-unmatch "$file" >/dev/null 2>&1; then
            important_files_found+=("$file")
        fi
    done
    
    # Warn about important configuration files
    if [[ ${#important_files_found[@]} -gt 0 && "$clean_untracked" == "yes" ]]; then
        echo ""
        echo -e "${RED}⚠️  WARNING: These important configuration files would be removed:${NC}"
        for file in "${important_files_found[@]}"; do
            echo -e "${RED}   - $file${NC}"
        done
        echo -e "${YELLOW}   Consider backing up your configurations!${NC}"
        echo ""
        if ask_confirmation "Continue despite these important files?"; then
            # Keep clean_untracked="yes"
            :
        else
            clean_untracked="no"
        fi
    fi
    
    # Action summary
    echo ""
    echo -e "${CYAN}=== ACTION SUMMARY ===${NC}"
    echo -e "Remove untracked files: ${clean_untracked}"
    echo -e "Reset --hard: ${reset_hard}"
    
    if [[ "$clean_untracked" == "no" && "$reset_hard" == "no" ]]; then
        log_warn "No cleanup actions selected"
        return 1
    fi
    
    echo ""
    if ask_confirmation "Confirm these actions?"; then
        log_info "Cleanup in progress..."
        
        if [[ "$reset_hard" == "yes" ]]; then
            log_info "Performing reset --hard..."
            git reset --hard HEAD
            log_success "Reset --hard completed"
        fi
        
        if [[ "$clean_untracked" == "yes" ]]; then
            log_info "Removing untracked files..."
            git clean -xdf
            log_success "Untracked files removed"
        fi
        
        log_success "Git cleanup completed"
    else
        log_warn "Cleanup cancelled"
        unset GIT_PAGER PAGER
        return 1
    fi
    
    # Reset Git environment to normal
    unset GIT_PAGER PAGER
}

# Full setup with tests function
full_setup_with_tests() {
    log_step "Complete setup with tests..."
    
    update_clients
    build_app
    test_backend
    start_app
    
    log_success "Complete setup with tests finished!"
}

# Full deployment function (clean + build + start)
full_deploy() {
    log_step "Complete deployment (clean + build + start)..."
    
    # Git cleanup
    if ! clean_git_repo; then
        log_warn "Deployment cancelled due to cleanup cancellation"
        return 1
    fi
    
    # Build
    build_app
    
    # Start
    start_app
    
    log_success "Complete deployment finished!"
}

# Main menu
show_menu() {
    echo ""
    echo -e "${PURPLE}=== MAIN MENU ===${NC}"
    echo ""
    echo "1)  🔧 Complete build (clean + build + tests)"
    echo "2)  🐳 Docker build only"
    echo "3)  🧪 Backend tests"
    echo "4)  🎨 Frontend tests"
    echo "5)  ▶️  Start application"
    echo "6)  ⏹️  Stop application"
    echo "7)  📋 Show logs"
    echo "8)  📊 Application status"
    echo "9)  🔄 Update BitTorrent clients"
    echo "10) 🧹 Clean environment"
    echo "11) 🧪 Complete setup with tests (clients + build + test + start)"
    echo "12) 🚀 Quick deployment (clean Git + build + start)"
    echo "0)  ❌ Exit"
    echo ""
    echo -n -e "${YELLOW}Your choice [0-12]: ${NC}"
}

# Main function
main() {
    # Check if we're in the right directory
    if [[ ! -f "docker-compose.yml" ]]; then
        log_error "docker-compose.yml file not found. Run this script from PyJOAL project root."
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
                log_info "Complete build selected..."
                clean_environment
                build_app
                test_backend
                echo ""
                echo -e "${GREEN}Press Enter to continue...${NC}"
                read -r
                ;;
            2)
                echo ""
                build_app
                echo ""
                echo -e "${GREEN}Press Enter to continue...${NC}"
                read -r
                ;;
            3)
                echo ""
                test_backend
                echo ""
                echo -e "${GREEN}Press Enter to continue...${NC}"
                read -r
                ;;
            4)
                echo ""
                test_frontend
                echo ""
                echo -e "${GREEN}Press Enter to continue...${NC}"
                read -r
                ;;
            5)
                echo ""
                start_app
                echo ""
                echo -e "${GREEN}Press Enter to continue...${NC}"
                read -r
                ;;
            6)
                echo ""
                stop_app
                echo ""
                echo -e "${GREEN}Press Enter to continue...${NC}"
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
                echo -e "${GREEN}Press Enter to continue...${NC}"
                read -r
                ;;
            9)
                echo ""
                update_clients
                echo ""
                echo -e "${GREEN}Press Enter to continue...${NC}"
                read -r
                ;;
            10)
                echo ""
                clean_environment
                echo ""
                echo -e "${GREEN}Press Enter to continue...${NC}"
                read -r
                ;;
            11)
                echo ""
                full_setup_with_tests
                echo ""
                echo -e "${GREEN}Press Enter to continue...${NC}"
                read -r
                ;;
            12)
                echo ""
                full_deploy
                echo ""
                echo -e "${GREEN}Press Enter to continue...${NC}"
                read -r
                ;;
            0)
                echo ""
                log_info "Goodbye! 👋"
                exit 0
                ;;
            *)
                echo ""
                log_error "Invalid option. Please choose between 0 and 12."
                sleep 2
                ;;
        esac
    done
}

# Entry point
main "$@"