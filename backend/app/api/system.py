"""
System Health API
Simple health monitoring endpoints for PyJOAL
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import logging

from app.core.auth import verify_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/system", tags=["system"], dependencies=[Depends(verify_token)])


@router.get("/health/detailed")
async def get_detailed_health() -> Dict[str, Any]:
    """Get comprehensive system health information"""
    try:
        from app.services.simple_health import health_checker
        
        health_status = health_checker.get_health_status()
        
        return {
            'overall_status': health_status['status'],
            'timestamp': health_status['timestamp'],
            'uptime_seconds': health_status['uptime_seconds'],
            'checks': health_status['checks'],
            'issues': health_status['issues'],
            'suggestions': health_status['suggestions'],
            'summary': {
                'memory': health_status['checks']['memory']['value'],
                'tracker_status': health_status['checks']['tracker_health']['message'], 
                'torrent_status': health_status['checks']['torrent_health']['message']
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get detailed health: {e}")
        raise HTTPException(status_code=500, detail="Health check system unavailable")


@router.get("/health/status")
async def get_simple_health_status() -> Dict[str, str]:
    """Get simple health status for UI indicators"""
    try:
        from app.services.simple_health import health_checker
        
        health_status = health_checker.get_health_status()
        
        # Simple status mapping for UI
        status_icon = {
            'healthy': '🟢',
            'warning': '🟡', 
            'error': '🔴'
        }.get(health_status['status'], '⚪')
        
        primary_issue = health_status['issues'][0] if health_status['issues'] else "Système fonctionnel"
        
        return {
            'status': health_status['status'],
            'icon': status_icon,
            'message': primary_issue,
            'uptime': health_status['checks']['uptime']['value']
        }
        
    except Exception as e:
        logger.error(f"Failed to get simple health status: {e}")
        return {
            'status': 'error',
            'icon': '🔴',
            'message': 'Vérification système indisponible',
            'uptime': 'Unknown'
        }


@router.get("/version/check")
async def check_version_updates() -> Dict[str, Any]:
    """Check for PyJOAL version updates from GitHub"""
    try:
        from app.services.version_checker import version_checker
        
        version_info = await version_checker.get_version_info()
        
        return {
            'current_version': version_info['current_version'],
            'latest_version': version_info['latest_version'],
            'update_available': version_info['update_available'],
            'release_url': version_info.get('release_url', ''),
            'release_notes': version_info.get('release_notes', ''),
            'published_at': version_info.get('published_at', ''),
            'last_check': version_info['last_check'],
            'error': version_info.get('error', None)
        }
        
    except Exception as e:
        logger.error(f"Failed to check version updates: {e}")
        return {
            'current_version': '1.5.0',
            'latest_version': 'unknown',
            'update_available': False,
            'release_url': '',
            'release_notes': '',
            'published_at': '',
            'last_check': 'never',
            'error': 'Version check service unavailable'
        }