"""
Simple Health Monitor - Lightweight system health checks
Provides essential health information without complexity
"""
import psutil
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SimpleHealthCheck:
    """Lightweight health monitoring with essential checks only"""
    
    def __init__(self):
        self.start_time = time.time()
        self._last_check = 0
        self._cached_status = None
        
    def get_health_status(self, force_check: bool = False) -> Dict:
        """Get current health status with smart caching"""
        current_time = time.time()
        
        # Cache for 10 seconds to avoid excessive checks
        if not force_check and self._cached_status and (current_time - self._last_check) < 10:
            return self._cached_status
        
        status = self._perform_health_checks()
        self._cached_status = status
        self._last_check = current_time
        
        return status
    
    def _perform_health_checks(self) -> Dict:
        """Perform lightweight health checks"""
        checks = {
            'memory': self._check_memory(),
            'tracker_health': self._check_tracker_health(), 
            'torrent_health': self._check_torrent_health(),
            'uptime': self._get_uptime()
        }
        
        # Determine overall status
        overall_status = 'healthy'
        issues = []
        
        for check_name, check_result in checks.items():
            if check_result['status'] == 'warning':
                overall_status = 'warning'
                issues.append(check_result['message'])
            elif check_result['status'] == 'error':
                overall_status = 'error'
                issues.append(check_result['message'])
        
        return {
            'status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'uptime_seconds': int(time.time() - self.start_time),
            'checks': checks,
            'issues': issues,
            'suggestions': self._get_suggestions(checks)
        }
    
    def _check_memory(self) -> Dict:
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            memory_mb = memory.used // (1024 * 1024)
            memory_percent = memory.percent
            
            if memory_percent > 90:
                return {
                    'status': 'error',
                    'value': f"{memory_mb}MB ({memory_percent:.1f}%)",
                    'message': f"Mémoire critique: {memory_percent:.1f}%"
                }
            elif memory_percent > 75:
                return {
                    'status': 'warning', 
                    'value': f"{memory_mb}MB ({memory_percent:.1f}%)",
                    'message': f"Mémoire élevée: {memory_percent:.1f}%"
                }
            else:
                return {
                    'status': 'healthy',
                    'value': f"{memory_mb}MB ({memory_percent:.1f}%)",
                    'message': "Mémoire OK"
                }
                
        except Exception as e:
            logger.warning(f"Failed to check memory: {e}")
            return {
                'status': 'error',
                'value': 'Unknown',
                'message': 'Impossible de vérifier la mémoire'
            }
    
    def _check_tracker_health(self) -> Dict:
        """Check tracker health from seeder service"""
        try:
            from app.services.seeder_service import seeder_service
            
            error_count = 0
            total_announcers = len(seeder_service.announcers)
            
            if total_announcers == 0:
                return {
                    'status': 'healthy',
                    'value': 'No torrents',
                    'message': 'Aucun torrent actif'
                }
            
            # Count announcers with recent errors
            for announcer in seeder_service.announcers.values():
                if announcer.last_error and announcer.last_error_time:
                    # Error in last 5 minutes is concerning
                    error_age = (datetime.utcnow() - announcer.last_error_time).total_seconds()
                    if error_age < 300:  # 5 minutes
                        error_count += 1
            
            error_rate = (error_count / total_announcers) * 100 if total_announcers > 0 else 0
            
            if error_rate > 50:
                return {
                    'status': 'error',
                    'value': f"{error_count}/{total_announcers} errors",
                    'message': f"{error_count} trackers en erreur"
                }
            elif error_rate > 20:
                return {
                    'status': 'warning',
                    'value': f"{error_count}/{total_announcers} errors", 
                    'message': f"{error_count} tracker(s) instable(s)"
                }
            else:
                return {
                    'status': 'healthy',
                    'value': f"{total_announcers} torrents",
                    'message': 'Trackers fonctionnels'
                }
                
        except Exception as e:
            logger.warning(f"Failed to check tracker health: {e}")
            return {
                'status': 'warning',
                'value': 'Unknown',
                'message': 'Vérification tracker échouée'
            }
    
    def _check_torrent_health(self) -> Dict:
        """Check torrent loading health"""
        try:
            from app.services.seeder_service import seeder_service
            
            failed_count = len(seeder_service.failed_torrents)
            active_count = sum(1 for a in seeder_service.announcers.values() if a.is_running)
            total_count = len(seeder_service.announcers)
            
            if failed_count > 5:
                return {
                    'status': 'error',
                    'value': f"{failed_count} failed",
                    'message': f"{failed_count} torrents échoués"
                }
            elif failed_count > 0:
                return {
                    'status': 'warning',
                    'value': f"{failed_count} failed", 
                    'message': f"{failed_count} torrent(s) échoué(s)"
                }
            elif total_count == 0:
                return {
                    'status': 'healthy',
                    'value': 'No torrents',
                    'message': 'Aucun torrent'
                }
            else:
                return {
                    'status': 'healthy',
                    'value': f"{active_count}/{total_count} active",
                    'message': f"{active_count} torrents actifs"
                }
                
        except Exception as e:
            logger.warning(f"Failed to check torrent health: {e}")
            return {
                'status': 'warning',
                'value': 'Unknown',
                'message': 'Vérification torrents échouée'
            }
    
    def _get_uptime(self) -> Dict:
        """Get service uptime"""
        uptime_seconds = int(time.time() - self.start_time)
        
        if uptime_seconds < 60:
            uptime_str = f"{uptime_seconds}s"
        elif uptime_seconds < 3600:
            uptime_str = f"{uptime_seconds // 60}min"
        else:
            hours = uptime_seconds // 3600
            minutes = (uptime_seconds % 3600) // 60
            uptime_str = f"{hours}h{minutes}m"
        
        return {
            'status': 'healthy',
            'value': uptime_str,
            'message': f'Actif depuis {uptime_str}'
        }
    
    def _get_suggestions(self, checks: Dict) -> List[str]:
        """Get actionable suggestions based on health status"""
        suggestions = []
        
        memory_check = checks.get('memory', {})
        if memory_check.get('status') in ['warning', 'error']:
            suggestions.append("💡 Redémarrez PyJOAL pour libérer la mémoire")
        
        tracker_check = checks.get('tracker_health', {})
        if tracker_check.get('status') == 'error':
            suggestions.append("🔄 Vérifiez votre connexion internet") 
            suggestions.append("⚙️  Essayez de redémarrer les torrents en erreur")
        
        torrent_check = checks.get('torrent_health', {})
        if torrent_check.get('status') in ['warning', 'error']:
            suggestions.append("📋 Consultez l'historique pour les détails des erreurs")
            suggestions.append("📁 Vérifiez que les fichiers .torrent sont valides")
        
        return suggestions


# Global health checker instance
health_checker = SimpleHealthCheck()