"""
JOAL Modern - Main Application Entry Point
FastAPI application with WebSocket support for BitTorrent ratio client
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path

from app.core.config import settings
from app.api import config, torrents, client, history
from app.services.websocket_manager import websocket_manager
from app.services.seeder_service import seeder_service
from app.services.history_service import history_service, EventType


async def update_clients_on_startup():
    """Run update_clients.py script to fetch latest client versions"""
    import sys
    import subprocess
    import os
    from pathlib import Path
    
    # Skip if running in Docker (handled by docker-entrypoint.sh)
    if os.getenv("DOCKER_CONTAINER") or os.path.exists("/.dockerenv"):
        print("🐳 Running in Docker, client update handled by entrypoint")
        return
    
    # Find update_clients.py in project root
    project_root = Path(__file__).parent.parent.parent
    update_script = project_root / "update_clients.py"
    
    if not update_script.exists():
        print("⚠️  update_clients.py not found, skipping client update")
        return
    
    try:
        print("🔄 Updating BitTorrent clients...")
        result = subprocess.run(
            [sys.executable, str(update_script)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Clients updated successfully")
        else:
            print(f"⚠️  Client update completed with warnings")
            if result.stdout:
                print(result.stdout)
    except subprocess.TimeoutExpired:
        print("⚠️  Client update timed out, using existing clients")
    except Exception as e:
        print(f"⚠️  Could not update clients: {e}")
        print("   Using existing client files")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("🚀 Starting JOAL Modern...")
    
    # Update clients from GitHub
    await update_clients_on_startup()
    
    # Initialize seeder service
    await seeder_service.initialize()
    
    print(f"✅ JOAL Modern started on port {settings.PORT}")
    print(f"🌐 UI available at: /{settings.UI_PATH_PREFIX}/ui/")
    print(f"📚 API docs at: /docs")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down JOAL Modern...")
    await seeder_service.stop()
    print("✅ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="JOAL Modern API",
    description="BitTorrent Ratio Client - Modern reimplementation",
    version="3.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(config.router, prefix="/api", tags=["Configuration"])
app.include_router(torrents.router, prefix="/api", tags=["Torrents"])
app.include_router(client.router, prefix="/api", tags=["Client Control"])
app.include_router(history.router, prefix="/api", tags=["History"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "3.0.0",
        "seeding": seeder_service.is_running
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            # Echo back for ping/pong
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket)


# Serve static files for frontend (in production)
# In Docker: /app/frontend/dist, in dev: ../frontend/dist
frontend_build_path = Path("/app/frontend/dist") if Path("/app/frontend/dist").exists() else Path(__file__).parent.parent.parent / "frontend" / "dist"

print(f"🔍 Looking for frontend at: {frontend_build_path}")
print(f"📁 Frontend exists: {frontend_build_path.exists()}")

if frontend_build_path.exists():
    print(f"✅ Mounting frontend from: {frontend_build_path}")
    
    # Mount all assets at root level (for relative imports in index.html)
    if (frontend_build_path / "assets").exists():
        app.mount(
            "/assets",
            StaticFiles(directory=frontend_build_path / "assets"),
            name="static"
        )
    
    @app.get(f"/{settings.UI_PATH_PREFIX}/ui/{{full_path:path}}")
    async def serve_frontend(full_path: str):
        """Serve frontend application"""
        # If it's an empty path or root, serve index.html
        if not full_path or full_path == "/":
            return FileResponse(frontend_build_path / "index.html")
        
        # Check if file exists
        file_path = frontend_build_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        
        # For SPA routing, return index.html
        return FileResponse(frontend_build_path / "index.html")
else:
    print(f"⚠️  Frontend not found at {frontend_build_path}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )
