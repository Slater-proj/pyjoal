#!/bin/bash

echo "🔨 Building JOAL Modern Docker Image..."

docker build --no-cache -t joal-modern:latest .

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo ""
    echo "To run the container:"
    echo "docker-compose up -d"
    echo ""
    echo "Or manually:"
    echo "docker run -d -p 8080:8080 -v ./config:/app/config -v ./torrents:/app/torrents -v ./clients:/app/clients -e SECRET_TOKEN=your_token -e UI_PATH_PREFIX=your_path joal-modern:latest"
else
    echo "❌ Build failed!"
    exit 1
fi
