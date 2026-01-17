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
            'cpu': self._check_cpu(),
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
        """Check memory usage of PyJOAL process"""
        try:
            # Get current process memory (not system memory)
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss // (1024 * 1024)  # RSS = Resident Set Size
            
            # Show memory usage without confusing percentage
            # Just display the actual usage with clear status thresholds
            
            if memory_mb > 300:  # 300MB is critical for PyJOAL
                return {
                    'status': 'error',
                    'value': f"{memory_mb}MB",
                    'message': f"Mémoire PyJOAL critique: {memory_mb}MB"
                }
            elif memory_mb > 200:  # 200MB is warning
                return {
                    'status': 'warning', 
                    'value': f"{memory_mb}MB",
                    'message': f"Mémoire élevée: {memory_mb}MB"
                }
            else:
                return {
                    'status': 'healthy',
                    'value': f"{memory_mb}MB",
                    'message': "Mémoire OK"
                }
                
        except Exception as e:
            logger.warning(f"Failed to check memory: {e}")
            return {
                'status': 'error',
                'value': 'Unknown',
                'message': 'Impossible de vérifier la mémoire'
            }

    def _check_cpu(self) -> Dict:
        """Check CPU usage of PyJOAL process"""
        try:
            process = psutil.Process()
            
            # Use a longer interval for more accurate CPU measurement
            # This approach is better for containers
            cpu_percent = process.cpu_percent(interval=1.0)
            
            # If still 0, try alternative approach
            if cpu_percent == 0.0:
                # Try system CPU as fallback
                import time
                cpu1 = process.cpu_times()
                time.sleep(0.5)
                cpu2 = process.cpu_times()
                
                # Calculate CPU percentage manually
                cpu_delta = (cpu2.user + cpu2.system) - (cpu1.user + cpu1.system)
                cpu_percent = (cpu_delta / 0.5) * 100
            
            if cpu_percent > 80:
                return {
                    'status': 'error',
                    'value': f"{cpu_percent:.1f}%",
                    'message': f"CPU critique: {cpu_percent:.1f}%"
                }
            elif cpu_percent > 50:
                return {
                    'status': 'warning',
                    'value': f"{cpu_percent:.1f}%", 
                    'message': f"CPU élevé: {cpu_percent:.1f}%"
                }
            else:
                return {
                    'status': 'healthy',
                    'value': f"{cpu_percent:.1f}%",
                    'message': "CPU OK"
                }
                
        except Exception as e:
            logger.warning(f"Failed to check CPU: {e}")
            return {
                'status': 'error',
                'value': 'Unknown',
                'message': 'Impossible de vérifier le CPU'
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