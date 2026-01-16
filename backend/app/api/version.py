"""
Version API endpoint
"""
from fastapi import APIRouter
from pathlib import Path

router = APIRouter(prefix="/api/version", tags=["version"])

def get_version():
    """Get application version from VERSION file"""
    try:
        version_file = Path(__file__).parent.parent.parent.parent / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
        else:
            return "1.2.2"  # fallback
    except:
        return "1.2.2"  # fallback

@router.get("")
async def get_app_version():
    """Get current application version"""
    return {
        "version": get_version(),
        "name": "PyJOAL",
        "description": "Python BitTorrent Ratio Client"
    }