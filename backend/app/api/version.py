"""
Version API endpoint
"""
from fastapi import APIRouter, Depends
from pathlib import Path

from app.core.auth import verify_token

router = APIRouter(prefix="/api/version", tags=["version"], dependencies=[Depends(verify_token)])


def get_version():
    """Get application version from VERSION file"""
    try:
        # In container, VERSION is at /app/VERSION
        version_file = Path("/app/VERSION")
        if version_file.exists():
            return version_file.read_text().strip()
        
        # Fallback: try relative path from this file
        version_file = Path(__file__).parent.parent.parent.parent / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
        else:
            # Try to get version from git tag as last resort
            try:
                import subprocess
                result = subprocess.run(['git', 'describe', '--tags', '--exact-match', 'HEAD'], 
                                     capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent.parent)
                if result.returncode == 0:
                    return result.stdout.strip().lstrip('v')
            except Exception:
                pass
            return "dev"  # development fallback
    except Exception:
        return "dev"  # development fallback


@router.get("")
async def get_app_version():
    """Get current application version"""
    return {
        "version": get_version(),
        "name": "PyJOAL",
        "description": "Python BitTorrent Ratio Client"
    }