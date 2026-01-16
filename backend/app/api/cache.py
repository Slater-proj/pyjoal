"""
Cache API Endpoints
Provides cache statistics and management endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from app.core.cache_manager import cache_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/cache", tags=["cache"])


@router.get("/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """Get comprehensive cache statistics"""
    try:
        stats = cache_manager.get_global_stats()
        
        # Add summary metrics
        total_hits = sum(cache['hits'] for cache in stats.values() if isinstance(cache, dict) and 'hits' in cache)
        total_misses = sum(cache['misses'] for cache in stats.values() if isinstance(cache, dict) and 'misses' in cache)
        overall_hit_rate = (total_hits / (total_hits + total_misses) * 100) if (total_hits + total_misses) > 0 else 0
        
        summary = {
            'total_hits': total_hits,
            'total_misses': total_misses,
            'overall_hit_rate': round(overall_hit_rate, 2),
            'total_caches': len([k for k, v in stats.items() if isinstance(v, dict) and 'size' in v]),
            'last_cleanup': stats.get('last_cleanup', 'Never')
        }
        
        return {
            'summary': summary,
            'details': stats,
            'performance_impact': _calculate_performance_impact(stats)
        }
        
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_all_caches() -> Dict[str, str]:
    """Clear all caches (admin operation)"""
    try:
        cache_manager.clear_all()
        logger.info("🧹 All caches cleared via API")
        
        return {
            'status': 'success',
            'message': 'All caches cleared successfully'
        }
        
    except Exception as e:
        logger.error(f"Failed to clear caches: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_expired() -> Dict[str, Any]:
    """Force cleanup of expired cache entries"""
    try:
        cache_manager._run_cleanup()
        stats = cache_manager.get_global_stats()
        
        return {
            'status': 'success',
            'message': 'Cache cleanup completed',
            'current_stats': stats['summary'] if 'summary' in stats else {}
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup caches: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _calculate_performance_impact(stats: Dict) -> Dict[str, Any]:
    """Calculate estimated performance impact of caching"""
    cache_details = {k: v for k, v in stats.items() if isinstance(v, dict) and 'hits' in v}
    
    if not cache_details:
        return {'estimated_io_savings': 0, 'estimated_time_savings_ms': 0}
    
    total_hits = sum(cache['hits'] for cache in cache_details.values())
    
    # Rough estimates based on operation types
    io_savings_estimate = total_hits * 0.8  # Assume 80% of hits avoid I/O
    time_savings_ms = total_hits * 2.5      # Assume ~2.5ms saved per cache hit
    
    return {
        'estimated_io_operations_saved': int(io_savings_estimate),
        'estimated_time_savings_ms': int(time_savings_ms),
        'efficiency_rating': min(100, int(io_savings_estimate / 10))  # Rating out of 100
    }