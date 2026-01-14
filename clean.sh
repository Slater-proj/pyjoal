#!/bin/bash
# Clean script for JOAL Modern project

echo "🧹 Nettoyage du projet JOAL Modern..."

# Remove Python cache
echo "  → Suppression des caches Python..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null

# Remove Node modules and build
echo "  → Suppression des builds Node.js..."
rm -rf frontend/node_modules
rm -rf frontend/dist

# Remove test torrents
echo "  → Suppression des torrents de test..."
find torrents -type f -name "*.torrent" -delete 2>/dev/null

# Remove generated client files (keep base versions)
echo "  → Suppression des clients générés..."
find clients -type f -name "*-5.*.client" -delete 2>/dev/null
find clients -type f -name "*-2.2.*.client" -delete 2>/dev/null
find clients -type f -name "*-4.0.6.client" -delete 2>/dev/null

# Remove logs
echo "  → Suppression des logs..."
find . -type f -name "*.log" -delete 2>/dev/null
rm -rf logs/

# Remove pytest cache
echo "  → Suppression des caches de test..."
rm -rf .pytest_cache
rm -rf backend/.pytest_cache
rm -f .coverage
rm -rf htmlcov/

echo ""
echo "✅ Projet nettoyé avec succès!"
echo ""
echo "📦 Pour réinstaller les dépendances :"
echo "   Backend:  cd backend && pip install -r requirements.txt"
echo "   Frontend: cd frontend && npm install"
