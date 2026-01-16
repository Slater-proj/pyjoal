import { useState, useEffect } from 'react'
import { AlertCircle, CheckCircle, Clock } from 'lucide-react'

interface HealthStatus {
  status: 'healthy' | 'warning' | 'error'
  icon: string
  message: string
  uptime: string
}

export default function HealthBadge() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [showDetails, setShowDetails] = useState(false)

  useEffect(() => {
    // Initial fetch
    fetchHealth()
    
    // Update every 30 seconds
    const interval = setInterval(fetchHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchHealth = async () => {
    try {
      const response = await fetch('/api/system/health/status')
      if (response.ok) {
        const healthData = await response.json()
        setHealth(healthData)
      }
    } catch (error) {
      console.warn('Health check failed:', error)
      setHealth({
        status: 'error',
        icon: '🔴',
        message: 'Vérification indisponible',
        uptime: 'Unknown'
      })
    }
  }

  if (!health) {
    return (
      <div className="flex items-center gap-2 text-slate-400 text-sm">
        <div className="w-2 h-2 bg-slate-400 rounded-full animate-pulse"></div>
        <span>Checking...</span>
      </div>
    )
  }

  const getStatusColor = () => {
    switch (health.status) {
      case 'healthy': return 'text-green-400'
      case 'warning': return 'text-yellow-400'
      case 'error': return 'text-red-400'
      default: return 'text-slate-400'
    }
  }

  const getStatusIcon = () => {
    switch (health.status) {
      case 'healthy': return <CheckCircle className="w-4 h-4" />
      case 'warning': return <AlertCircle className="w-4 h-4" />
      case 'error': return <AlertCircle className="w-4 h-4" />
      default: return <Clock className="w-4 h-4" />
    }
  }

  return (
    <div className="relative">
      {/* Health Badge */}
      <button
        onClick={() => setShowDetails(!showDetails)}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${getStatusColor()} hover:bg-slate-700/50`}
        title={health.message}
      >
        {getStatusIcon()}
        <span className="hidden sm:inline">{health.uptime}</span>
        <span className="text-xs">{health.icon}</span>
      </button>

      {/* Details Dropdown */}
      {showDetails && (
        <div className="absolute top-full right-0 mt-1 w-72 bg-slate-800 border border-slate-600 rounded-lg shadow-lg p-4 z-50">
          <div className="space-y-3">
            {/* Header */}
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-slate-300">État du système</h3>
              <span className={`text-lg ${getStatusColor()}`}>{health.icon}</span>
            </div>

            {/* Status */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-slate-400 text-xs">Statut:</span>
                <span className={`text-sm font-medium ${getStatusColor()}`}>
                  {health.status === 'healthy' && 'Système OK'}
                  {health.status === 'warning' && 'Attention'}
                  {health.status === 'error' && 'Problème détecté'}
                </span>
              </div>
              
              <div className="flex items-center gap-2">
                <span className="text-slate-400 text-xs">Activité:</span>
                <span className="text-sm text-slate-300">{health.uptime}</span>
              </div>
            </div>

            {/* Message */}
            {health.message !== 'Système fonctionnel' && (
              <div className="bg-slate-700/50 rounded p-2">
                <p className="text-xs text-slate-300">{health.message}</p>
              </div>
            )}

            {/* Quick Actions */}
            {health.status !== 'healthy' && (
              <div className="pt-2 border-t border-slate-600">
                <p className="text-xs text-slate-400 mb-2">Actions suggérées:</p>
                <div className="space-y-1 text-xs">
                  {health.status === 'warning' && (
                    <p className="text-yellow-400">• Surveillez les torrents actifs</p>
                  )}
                  {health.status === 'error' && (
                    <>
                      <p className="text-red-400">• Vérifiez les logs pour plus de détails</p>
                      <p className="text-red-400">• Redémarrez PyJOAL si nécessaire</p>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Overlay to close dropdown */}
      {showDetails && (
        <div 
          className="fixed inset-0 z-40"
          onClick={() => setShowDetails(false)}
        />
      )}
    </div>
  )
}