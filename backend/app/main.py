"""
PyJOAL - Main Application Entry Point
FastAPI application with WebSocket support for BitTorrent ratio client
Python reimplementation of JOAL (https://github.com/anthonyraymond/joal)
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import os
import sys
import logging
import html
import subprocess
from pathlib import Path

from app.core.config import settings
from app.api import config, torrents, client, history, logs, errors
from app.services.websocket_manager import websocket_manager
from app.services.seeder_service import seeder_service
from app.services.history_service import history_service, EventType
from app.services.log_stream_service import log_handler

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        log_handler  # Add our custom handler for log streaming
    ]
)

# Set third-party loggers to WARNING to reduce noise
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def update_clients_on_startup():
    """Run update_clients.py script to fetch latest client versions"""
    import subprocess
    
    # Skip if running in Docker (handled by docker-entrypoint.sh)
    if os.getenv("DOCKER_CONTAINER") or os.path.exists("/.dockerenv"):
        logger.info("🐳 Running in Docker, client update handled by entrypoint")
        return
    
    # Find update_clients.py in project root
    project_root = Path(__file__).parent.parent.parent
    update_script = project_root / "update_clients.py"
    
    if not update_script.exists():
        logger.warning("⚠️  update_clients.py not found, skipping client update")
        return
    
    try:
        logger.info("🔄 Updating BitTorrent clients...")
        result = subprocess.run(
            [sys.executable, str(update_script)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logger.info("✅ Clients updated successfully")
        else:
            logger.warning("⚠️  Client update completed with warnings")
            if result.stdout:
                logger.debug(result.stdout)
    except subprocess.TimeoutExpired:
        logger.warning("⚠️  Client update timed out, using existing clients")
    except Exception as e:
        logger.warning(f"⚠️  Could not update clients: {e}")
        logger.info("   Using existing client files")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("=" * 80)
    logger.info("🚀 Starting PyJOAL - Python BitTorrent Ratio Client")
    logger.info("   Based on JOAL by Anthony Raymon")
    logger.info("=" * 80)
    
    # Update clients from GitHub
    await update_clients_on_startup()
    
    # Initialize seeder service
    await seeder_service.initialize()
    
    # Start log broadcasting for WebSocket
    await websocket_manager.start_log_broadcasting()
    
    # Auto-start seeding if torrents are available
    if seeder_service.has_torrents():
        logger.info("🚀 Auto-starting seeder service (torrents found)")
        try:
            await seeder_service.start()
            logger.info("✅ Seeder service started automatically")
        except Exception as e:
            logger.warning(f"⚠️  Failed to auto-start seeder service: {e}")
    else:
        logger.info("💤 No torrents found, seeder service remains stopped")
    
    logger.info("=" * 80)
    logger.info(f"✅ PyJOAL v1.2.1 started successfully on port {settings.PORT}")
    logger.info(f"🌐 UI available at: http://localhost:{settings.PORT}/{settings.UI_PATH_PREFIX}/ui/")
    logger.info(f"📚 API docs at: http://localhost:{settings.PORT}/docs")
    logger.info(f"🔐 Secret token: {settings.SECRET_TOKEN}")
    logger.info("=" * 80)
    
    yield
    
    # Shutdown
    logger.info("=" * 80)
    logger.info("🛑 Shutting down PyJOAL...")
    await websocket_manager.stop_log_broadcasting()
    await seeder_service.stop()
    logger.info("✅ Shutdown complete")
    logger.info("=" * 80)


# Create FastAPI app
app = FastAPI(
    title="PyJOAL API",
    description="BitTorrent Ratio Client - Python reimplementation of JOAL",
    version="1.0.0",
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
app.include_router(logs.router, prefix="/api", tags=["Logs"])
app.include_router(errors.router, prefix="/api", tags=["Error Information"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": "PyJOAL",
        "version": "1.0.0",
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

logger.debug(f"🔍 Looking for frontend at: {frontend_build_path}")
logger.debug(f"📁 Frontend exists: {frontend_build_path.exists()}")

if frontend_build_path.exists():
    logger.info(f"✅ Mounting frontend from: {frontend_build_path}")
    
    # Mount all assets at root level (for relative imports in index.html)
    if (frontend_build_path / "assets").exists():
        app.mount(
            "/assets",
            StaticFiles(directory=frontend_build_path / "assets"),
            name="static"
        )
    
    @app.get(f"/{settings.UI_PATH_PREFIX}/ui/{{full_path:path}}")
    async def serve_frontend(full_path: str):
        """Serve frontend application with token injection"""
        # If it's an empty path or root, serve index.html with token injection
        if not full_path or full_path == "/":
            index_path = frontend_build_path / "index.html"
            with open(index_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Inject token into HTML (before closing </head>)
            token_script = f'<script>window.__PYJOAL_TOKEN__ = "{html.escape(settings.SECRET_TOKEN)}";</script>'
            html_content = html_content.replace('</head>', f'{token_script}</head>')
            
            return HTMLResponse(content=html_content)
        
        # Check if file exists
        file_path = frontend_build_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        
        # For SPA routing, return index.html with token injection
        index_path = frontend_build_path / "index.html"
        with open(index_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        token_script = f'<script>window.__PYJOAL_TOKEN__ = "{html.escape(settings.SECRET_TOKEN)}";</script>'
        html_content = html_content.replace('</head>', f'{token_script}</head>')
        
        return HTMLResponse(content=html_content)
else:
    logger.warning(f"⚠️  Frontend not found at {frontend_build_path}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )
