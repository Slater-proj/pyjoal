#!/bin/bash
# Diagnostic script for PyJOAL client issues

echo "╔════════════════════════════════════════════════════════════╗"
echo "║       PyJOAL - Client Diagnostics                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if Docker is running
if docker ps &>/dev/null; then
    DOCKER_RUNNING=true
    echo "✅ Docker is running"
else
    DOCKER_RUNNING=false
    echo "⚠️  Docker is not running or not accessible"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  1. Local Files Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -d "clients" ]; then
    CLIENT_COUNT=$(ls -1 clients/*.client 2>/dev/null | wc -l)
    echo "📂 clients/ directory: ✅ EXISTS"
    echo "📊 Client files count: $CLIENT_COUNT"
    
    if [ "$CLIENT_COUNT" -gt 0 ]; then
        echo ""
        echo "Client files:"
        ls -lh clients/*.client | awk '{print "   • " $9 " (" $5 ")"}'
    else
        echo "❌ No .client files found in clients/"
    fi
else
    echo "❌ clients/ directory not found"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  2. Docker Container Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$DOCKER_RUNNING" = true ]; then
    if docker ps --filter "name=pyjoal" --format "{{.Names}}" | grep -q "pyjoal"; then
        echo "✅ Container 'pyjoal' is running"
        
        echo ""
        echo "Container client files:"
        docker exec pyjoal ls -lh /app/clients/*.client 2>/dev/null | awk '{print "   • " $9 " (" $5 ")"}'
        
        echo ""
        echo "Recent container logs:"
        docker logs pyjoal --tail 30 2>&1 | grep -E "(client|Client|📱|✅|❌|⚠️)" | tail -10
    else
        echo "⚠️  Container 'pyjoal' is not running"
        echo "   Run: docker-compose up -d"
    fi
else
    echo "⚠️  Cannot check container (Docker not accessible)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  3. API Health Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if command -v curl &>/dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health 2>/dev/null)
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ API is accessible at http://localhost:8080"
        
        echo ""
        echo "Available clients from API:"
        curl -s http://localhost:8080/api/clients 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "   Failed to parse JSON"
    else
        echo "❌ API is not accessible (HTTP $HTTP_CODE)"
        echo "   Expected: http://localhost:8080"
    fi
else
    echo "⚠️  curl not installed, skipping API check"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  4. Recommendations"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$CLIENT_COUNT" -lt 3 ]; then
    echo "⚠️  Less than 3 base clients detected"
    echo "   Action: git checkout clients/*.client"
fi

if [ "$CLIENT_COUNT" -lt 6 ]; then
    echo "⚠️  New client versions may not be generated"
    echo "   Action: python update_clients.py"
fi

if [ "$DOCKER_RUNNING" = true ] && ! docker ps --filter "name=pyjoal" --format "{{.Names}}" | grep -q "pyjoal"; then
    echo "⚠️  Container not running"
    echo "   Action: docker-compose up -d"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Quick Fix Commands"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Update clients locally:"
echo "  $ python update_clients.py"
echo ""
echo "Rebuild Docker (full):"
echo "  $ docker-compose down"
echo "  $ docker-compose build --no-cache"
echo "  $ docker-compose up -d"
echo ""
echo "Force update in running container:"
echo "  $ docker exec pyjoal python /app/update_clients.py"
echo "  $ docker-compose restart"
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                  Diagnostic Complete                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
