#!/bin/bash

echo "================================================"
echo "  PyJOAL - Setup & Installation Script"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    cp .env.example .env

    echo -e "${YELLOW}Please edit .env file and set:${NC}"
    echo "  - SECRET_TOKEN (required)"
    echo "  - UI_PATH_PREFIX (required)"
    echo ""
    read -p "Press Enter to open .env for editing..."
    ${EDITOR:-nano} .env
fi

# Check Docker installation
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed!${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Detect Docker Compose binary
DOCKER_COMPOSE=""
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo -e "${RED}❌ Docker Compose is not installed!${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✅ Docker and Docker Compose found (${DOCKER_COMPOSE})${NC}"
echo ""

# Ask what to do
echo "What would you like to do?"
echo "1) Build and start with Docker (recommended)"
echo "2) Development setup (Python + Node.js)"
echo "3) Just build Docker image"
echo "4) Exit"
echo ""
read -p "Choose option [1-4]: " choice

case $choice in
    1)
        echo ""
        echo -e "${GREEN}🔨 Building Docker image...${NC}"
        $DOCKER_COMPOSE build

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Build successful!${NC}"
            echo ""
            echo -e "${GREEN}🚀 Starting PyJOAL...${NC}"
            $DOCKER_COMPOSE up -d

            # Wait a bit for startup
            sleep 3

            # Get UI path from .env
            UI_PATH=$(grep UI_PATH_PREFIX .env | cut -d '=' -f2)
            PORT=$(grep PORT .env | cut -d '=' -f2)
            PORT=${PORT:-8080}

            echo ""
            echo -e "${GREEN}================================================${NC}"
            echo -e "${GREEN}  PyJOAL is now running! 🎉${NC}"
            echo -e "${GREEN}================================================${NC}"
            echo ""
            echo "Access the web UI at:"
            echo -e "${YELLOW}http://localhost:${PORT}/${UI_PATH}/ui/${NC}"
            echo ""
            echo "API Documentation:"
            echo -e "${YELLOW}http://localhost:${PORT}/docs${NC}"
            echo ""
            echo "To view logs:"
            echo "$DOCKER_COMPOSE logs -f pyjoal"
            echo ""
            echo "To stop:"
            echo "$DOCKER_COMPOSE down"
            echo ""
        else
            echo -e "${RED}❌ Build failed!${NC}"
            exit 1
        fi
        ;;

    2)
        echo ""
        echo -e "${YELLOW}Setting up development environment...${NC}"
        # ... reste identique ...
        ;;

    3)
        echo ""
        echo -e "${GREEN}🔨 Building Docker image only...${NC}"
        docker build -t pyjoal:latest .

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Build successful!${NC}"
        else
            echo -e "${RED}❌ Build failed!${NC}"
            exit 1
        fi
        ;;

    4)
        echo "Goodbye!"
        exit 0
        ;;

    *)
        echo -e "${RED}Invalid option!${NC}"
        exit 1
        ;;
esac

