"""
PyJOAL - Main Application Entry Point
FastAPI application with WebSocket support for BitTorrent ratio client
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
import asyncio
import os
import sys
import logging
import json
import hmac
from pathlib import Path

# Read version from VERSION file
def get_version():
    try:
        # In container, VERSION is at /app/VERSION
        version_file = Path("/app/VERSION")
        if version_file.exists():
            return version_file.read_text().strip()
        
        # Fallback: try relative path from this file
        version_file = Path(__file__).parent.parent.parent / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
        else:
            # Try to get version from git tag as last resort
            try:
                import subprocess
                result = subprocess.run(['git', 'describe', '--tags', '--exact-match', 'HEAD'], 
                                     capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)
                if result.returncode == 0:
                    return result.stdout.strip().lstrip('v')
            except Exception:
                pass
            return "dev"  # development fallback
    except Exception:
        return "dev"  # development fallback

APP_VERSION = get_version()

from app.core.config import settings
from app.api import config, torrents, client, history, logs, errors, version, cache, system, notifications
from app.services.websocket_manager import websocket_manager
from app.services.seeder_service import seeder_service
from app.services.log_stream_service import log_handler
import time

# Configure timezone-aware logging
class TimezoneFormatter(logging.Formatter):
    """Formatter that uses local timezone from TZ environment variable"""
    converter = time.localtime  # Use local time instead of UTC
    
    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            s = time.strftime('%Y-%m-%d %H:%M:%S', ct)
        return s

# Configure logging with timezone support
log_format = '%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s'
log_datefmt = '%Y-%m-%d %H:%M:%S'

# Create formatter and handlers
formatter = TimezoneFormatter(log_format, datefmt=log_datefmt)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    handlers=[
        console_handler,
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
    
    # Find update_clients.py in scripts folder
    project_root = Path(__file__).parent.parent.parent
    update_script = project_root / "scripts" / "update_clients.py"
    
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
    logger.info("=" * 80)
    
    # Update clients in background (non-blocking)
    asyncio.create_task(_background_client_update())
    
    # Initialize seeder service (core only: config + client loading, fast)
    await seeder_service.initialize()
    
    # Start log broadcasting for WebSocket
    await websocket_manager.start_log_broadcasting()
    
    # Defer torrent loading + auto-start to background (non-blocking)
    asyncio.create_task(_background_torrent_startup())
    
    logger.info("=" * 80)
    logger.info(f"✅ PyJOAL v{APP_VERSION} started successfully on port {settings.PORT}")
    logger.info(f"🌐 UI available at: http://localhost:{settings.PORT}/{settings.UI_PATH_PREFIX}/ui/")
    logger.info(f"📚 API docs at: http://localhost:{settings.PORT}/docs")
    token = settings.SECRET_TOKEN
    masked = f"{token[:4]}{'*' * max(0, len(token) - 6)}{token[-2:]}" if len(token) > 8 else "***"
    logger.info(f"🔐 Secret token: {masked} (masked, {len(token)} chars)")
    logger.info("=" * 80)
    
    yield
    
    # Shutdown
    logger.info("=" * 80)
    logger.info("🛑 Shutting down PyJOAL...")
    await websocket_manager.stop_log_broadcasting()
    await seeder_service.stop()
    # Persist history before exit
    from app.services.history_service import history_service
    history_service.save()
    logger.info("✅ Shutdown complete")
    logger.info("=" * 80)


async def _background_client_update():
    """Update clients from GitHub in background (non-blocking)."""
    try:
        await update_clients_on_startup()
    except Exception as e:
        logger.warning(f"Background client update failed: {e}")


async def _background_torrent_startup():
    """Load torrents and auto-start seeding in background.
    
    This runs after the HTTP server is already accepting connections,
    so the UI can load immediately while torrents are being loaded.
    """
    try:
        # Small delay to let the HTTP server finish startup
        await asyncio.sleep(0.5)
        
        # Notify UI that loading has started
        await websocket_manager.broadcast(
            {"type": "loading_status", "data": {"status": "loading_torrents", "message": "Loading torrents..."}}
        )
        
        await seeder_service.load_torrents()
        
        if seeder_service.has_torrents():
            logger.info("🚀 Auto-starting seeder service (torrents found)")
            try:
                await seeder_service.start()
                logger.info("✅ Seeder service started automatically")
            except Exception as e:
                logger.warning(f"⚠️  Failed to auto-start seeder service: {e}")
        else:
            logger.info("💤 No torrents found, seeder service remains stopped")
        
        # Notify UI that loading is complete
        await websocket_manager.broadcast({"type": "loading_status", "data": {"status": "ready", "message": "Ready"}})
        
    except Exception as e:
        logger.error(f"Background torrent startup failed: {e}", exc_info=True)
        await websocket_manager.broadcast({"type": "loading_status", "data": {"status": "error", "message": str(e)}})


# Create FastAPI app
app = FastAPI(
    title="PyJOAL API",
    description="BitTorrent Ratio Client - Multi-client emulation with modern web interface",
    version=APP_VERSION,
    lifespan=lifespan
)

# Add custom exception handler for validation errors
from pydantic import ValidationError

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Convert Pydantic validation errors to user-friendly messages"""
    error_msg = "Invalid configuration data"
    
    # Extract the first meaningful error message
    if exc.errors():
        error = exc.errors()[0]
        field = error.get('loc', [''])[-1] if error.get('loc') else ''
        error_type = error.get('type', '')
        msg = error.get('msg', '')
        
        if error_type == 'value_error' and 'ctx' in error and 'error' in error['ctx']:
            # Custom validator error - use the message directly
            error_msg = msg.replace('Value error, ', '')
        elif error_type == 'greater_than_equal':
            if 'minUploadRate' in field:
                error_msg = "Minimum upload rate cannot be negative"
            elif 'maxUploadRate' in field:
                error_msg = "Maximum upload rate cannot be negative"
            else:
                error_msg = f"The value of {field} cannot be negative"
        elif error_type == 'less_than_equal':
            if 'Upload' in field:
                error_msg = "Upload rate cannot exceed 100 MB/s (100000 KB/s)"
            else:
                error_msg = f"The value of {field} is too high"
        elif error_type == 'missing':
            error_msg = f"The field {field} is required"
        elif 'type' in error_type:
            error_msg = f"Invalid format for {field}"
        else:
            error_msg = msg
    
    logger.warning(f"⚠️ Validation error: {error_msg}")
    return JSONResponse(
        status_code=422,
        content={"detail": error_msg}
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
app.include_router(cache.router, tags=["Cache Management"])
app.include_router(system.router, tags=["System Health"])
app.include_router(version.router, tags=["Version"])
app.include_router(notifications.router, prefix="/api", tags=["Notifications"])


@app.get("/health")
async def health_check():
    """Enhanced health check endpoint with system monitoring"""
    try:
        from app.services.simple_health import health_checker
        
        # Get detailed health status
        health_status = health_checker.get_health_status()
        
        # Basic response for external monitoring
        basic_status = {
            "status": "healthy" if health_status['status'] in ['healthy', 'warning'] else "unhealthy",
            "app": "PyJOAL", 
            "version": APP_VERSION,
            "seeding": seeder_service.is_running,
            "uptime": health_status['uptime_seconds']
        }
        
        # Add detailed info for UI
        if health_status['status'] != 'healthy':
            basic_status.update({
                "health_status": health_status['status'],
                "issues": health_status['issues'][:3],  # Top 3 issues
                "suggestions": health_status['suggestions'][:2]  # Top 2 suggestions
            })
        
        return basic_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "app": "PyJOAL",
            "version": APP_VERSION, 
            "seeding": seeder_service.is_running,
            "error": "Health check system error"
        }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates (authenticated via query param)"""
    # Verify token from query parameter (?token=xxx)
    token = websocket.query_params.get("token", "")
    if not hmac.compare_digest(token, settings.SECRET_TOKEN):
        await websocket.close(code=4003, reason="Forbidden")
        return
    
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
frontend_build_path = (
    Path("/app/frontend/dist")
    if Path("/app/frontend/dist").exists()
    else Path(__file__).parent.parent.parent / "frontend" / "dist"
)

logger.debug(f"🔍 Looking for frontend at: {frontend_build_path}")
logger.debug(f"📁 Frontend exists: {frontend_build_path.exists()}")

if frontend_build_path.exists():
    logger.info(f"✅ Mounting frontend from: {frontend_build_path}")
    
    # Redirect root to UI
    @app.get("/")
    async def redirect_root():
        """Redirect root to UI"""
        prefix = f"/{settings.UI_PATH_PREFIX}" if settings.UI_PATH_PREFIX and settings.UI_PATH_PREFIX != "/" else ""
        return RedirectResponse(url=f"{prefix}/ui/")
    
    # Serve favicon
    @app.get("/favicon.svg")
    @app.get(f"/{settings.UI_PATH_PREFIX}/favicon.svg")
    async def serve_favicon():
        """Serve favicon"""
        favicon_path = frontend_build_path / "favicon.svg"
        if favicon_path.exists():
            return FileResponse(favicon_path, media_type="image/svg+xml")
        raise HTTPException(status_code=404, detail="Favicon not found")

    @app.get("/favicon.ico")
    @app.get(f"/{settings.UI_PATH_PREFIX}/favicon.ico")
    async def serve_favicon_ico():
        """Serve favicon ICO"""
        ico_path = frontend_build_path / "favicon.ico"
        if ico_path.exists():
            return FileResponse(ico_path, media_type="image/x-icon")
        raise HTTPException(status_code=404, detail="Favicon not found")

    @app.get("/apple-touch-icon.png")
    @app.get(f"/{settings.UI_PATH_PREFIX}/apple-touch-icon.png")
    async def serve_apple_touch_icon():
        """Serve Apple touch icon"""
        icon_path = frontend_build_path / "apple-touch-icon.png"
        if icon_path.exists():
            return FileResponse(icon_path, media_type="image/png")
        raise HTTPException(status_code=404, detail="Icon not found")
    
    # Mount all assets with prefix support
    if (frontend_build_path / "assets").exists():
        assets_path = f"/{settings.UI_PATH_PREFIX}/assets" if settings.UI_PATH_PREFIX else "/assets"
        app.mount(
            assets_path,
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
            
            # Inject token into HTML (before closing </head>) - use json.dumps for XSS-safe escaping
            token_script = f'<script>window.__PYJOAL_TOKEN__ = {json.dumps(settings.SECRET_TOKEN)};</script>'
            html_content = html_content.replace('</head>', f'{token_script}</head>')
            
            # Fix asset paths to include UI_PATH_PREFIX
            if settings.UI_PATH_PREFIX:
                html_content = html_content.replace('"/assets/', f'"/{settings.UI_PATH_PREFIX}/assets/')
                html_content = html_content.replace("'/assets/", f"'/{settings.UI_PATH_PREFIX}/assets/")
            
            return HTMLResponse(content=html_content)
        
        # Check if file exists
        file_path = frontend_build_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        
        # For SPA routing, return index.html with token injection
        index_path = frontend_build_path / "index.html"
        with open(index_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        token_script = f'<script>window.__PYJOAL_TOKEN__ = {json.dumps(settings.SECRET_TOKEN)};</script>'
        html_content = html_content.replace('</head>', f'{token_script}</head>')
        
        # Fix asset paths to include UI_PATH_PREFIX
        if settings.UI_PATH_PREFIX:
            html_content = html_content.replace('"/assets/', f'"/{settings.UI_PATH_PREFIX}/assets/')
            html_content = html_content.replace("'/assets/", f"'/{settings.UI_PATH_PREFIX}/assets/")

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
