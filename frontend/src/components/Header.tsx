import { Activity } from 'lucide-react'
import { useStore } from '../store/useStore'
import { useState, useEffect } from 'react'

interface HeaderProps {
  appVersion: string
}

export default function Header({ appVersion }: HeaderProps) {
  const { connected } = useStore()
  const [healthStatus, setHealthStatus] = useState('⚡')
  const [healthDetails, setHealthDetails] = useState<any>(null)
  const [versionInfo, setVersionInfo] = useState<any>(null)
  const [showHealthTooltip, setShowHealthTooltip] = useState(false)
  const [showLiveTooltip, setShowLiveTooltip] = useState(false)

  // Simple health check
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch('/api/system/health/status')
        if (response.ok) {
          const data = await response.json()
          setHealthStatus(data.icon || '🟢')
        } else {
          setHealthStatus('🔴')
        }
        
        // Fetch detailed health info for tooltip
        const detailResponse = await fetch('/api/system/health/detailed')
        if (detailResponse.ok) {
          const detailData = await detailResponse.json()
          setHealthDetails(detailData)
        }
        
        // Check version info (cached daily)
        try {
          const versionResponse = await fetch('/api/system/version/check')
          if (versionResponse.ok) {
            const versionData = await versionResponse.json()
            setVersionInfo(versionData)
          }
        } catch (versionError) {
          console.log('Version check failed:', versionError)
        }
      } catch (error) {
        setHealthStatus('🔴')
        setHealthDetails({
          overall_status: 'error',
          checks: {
            memory: { status: 'error', message: 'Connection failed' }
          }
        })
      }
    }
    
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <header className="bg-slate-800 border-b border-slate-700 shadow-lg">
      <div className="w-full px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-3xl font-bold text-blue-400">PyJOAL</h1>
            <span className="text-slate-500 text-sm bg-slate-700 px-2 py-0.5 rounded">v{appVersion}</span>
            
            {/* Live Status with Tooltip */}
            <div 
              className="relative"
              onMouseEnter={() => setShowLiveTooltip(true)}
              onMouseLeave={() => setShowLiveTooltip(false)}
            >
              <div className={`flex items-center space-x-2 text-sm cursor-help ${connected ? 'text-green-400' : 'text-slate-500'}`}>
                <Activity className={`w-4 h-4 ${connected ? 'animate-pulse' : ''}`} />
                <span>{connected ? 'Live' : 'Offline'}</span>
              </div>
              
              {/* Live Tooltip */}
              {showLiveTooltip && (
                <div className="absolute top-full left-0 mt-2 w-72 bg-slate-800 border border-slate-600 rounded-lg shadow-xl p-4 z-50">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between border-b border-slate-600 pb-2">
                      <h3 className="text-sm font-medium text-slate-300">WebSocket Connection</h3>
                      <span className={`text-lg ${connected ? 'text-green-400' : 'text-slate-500'}`}>
                        {connected ? '🟢' : '🔴'}
                      </span>
                    </div>
                    <div className="text-xs space-y-2">
                      <div>
                        <span className="text-slate-400">Status: </span>
                        <span className={connected ? 'text-green-400' : 'text-red-400'}>
                          {connected ? 'Connected' : 'Disconnected'}
                        </span>
                      </div>
                      <div className="text-slate-300">
                        <p>• Auto-updating logs</p>
                        <p>• Real-time statistics</p>
                        <p>• Instant notifications</p>
                        {!connected && <p className="text-red-400 mt-1">⚠️ No automatic updates</p>}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-4">
            {/* Health Badge with Tooltip */}
            <div 
              className="relative"
              onMouseEnter={() => setShowHealthTooltip(true)}
              onMouseLeave={() => setShowHealthTooltip(false)}
            >
              <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-700/50 rounded-lg text-sm border border-slate-600 cursor-help">
                <span className="text-lg">{healthStatus}</span>
                <span className="text-slate-300 text-xs">Health</span>
              </div>
              
              {/* Health Tooltip - System metrics only, no torrent info */}
              {showHealthTooltip && healthDetails && (
                <div className="absolute top-full right-0 mt-2 w-80 bg-slate-800 border border-slate-600 rounded-lg shadow-xl p-4 z-50">
                  <div className="space-y-3">
                    {/* Header */}
                    <div className="flex items-center justify-between border-b border-slate-600 pb-2">
                      <h3 className="text-sm font-medium text-slate-300">System Health</h3>
                      <span className="text-lg">{healthStatus}</span>
                    </div>
                    
                    {/* System metrics only - no dashboard duplicates */}
                    <div className="space-y-2 text-xs">
                      {healthDetails.checks?.memory && (
                        <div className="flex justify-between">
                          <span className="text-slate-400">💾 RAM Used:</span>
                          <span className="text-slate-300">{healthDetails.checks.memory.value || 'N/A'}</span>
                        </div>
                      )}
                      {healthDetails.checks?.cpu && (
                        <div className="flex justify-between">
                          <span className="text-slate-400">🔥 CPU Usage:</span>
                          <span className="text-slate-300">{healthDetails.checks.cpu.value || 'N/A'}</span>
                        </div>
                      )}
                      {healthDetails.checks?.uptime && (
                        <div className="flex justify-between">
                          <span className="text-slate-400">⏱️ System Uptime:</span>
                          <span className="text-slate-300">{healthDetails.checks.uptime.value || 'N/A'}</span>
                        </div>
                      )}
                      <div className="flex justify-between">
                        <span className="text-slate-400">🔄 Last Check:</span>
                        <span className="text-slate-300">
                          {healthDetails.timestamp ? new Date(healthDetails.timestamp).toLocaleTimeString() : 'N/A'}
                        </span>
                      </div>
                    </div>
                    
                    {/* Overall Status */}
                    <div className="pt-2 border-t border-slate-600">
                      <div className="text-xs">
                        <span className="text-slate-400">Overall Status: </span>
                        <span className={`font-medium ${
                          healthDetails.overall_status === 'healthy' ? 'text-green-400' :
                          healthDetails.overall_status === 'warning' ? 'text-yellow-400' : 'text-red-400'
                        }`}>
                          {healthDetails.overall_status === 'healthy' && 'System OK'}
                          {healthDetails.overall_status === 'warning' && 'Monitoring'}
                          {healthDetails.overall_status === 'error' && 'Issues Detected'}
                        </span>
                      </div>
                    </div>
                    
                    {/* Explicit Issues List */}
                    {healthDetails.issues && healthDetails.issues.length > 0 && (
                      <div className="pt-2 border-t border-slate-600">
                        <p className="text-xs text-red-400 font-medium mb-1">⚠️ Issues detected:</p>
                        <ul className="text-xs space-y-1">
                          {healthDetails.issues.map((issue: string, index: number) => (
                            <li key={index} className="text-slate-300 pl-2">• {issue}</li>
                          ))}
                        </ul>
                        <p className="text-xs text-slate-400 mt-2 italic">
                          💡 These errors may be temporary (trackers unavailable) or require action (check .torrent files)
                        </p>
                      </div>
                    )}
                    
                    {/* Performance suggestions only */}
                    {healthDetails.suggestions && healthDetails.suggestions.length > 0 && (
                      <div className="pt-2 border-t border-slate-600">
                        <p className="text-xs text-slate-400 mb-1">⚡ Optimizations:</p>
                        <ul className="text-xs text-slate-300 space-y-1">
                          {healthDetails.suggestions.slice(0, 2).map((suggestion: string, index: number) => (
                            <li key={index} className="list-disc list-inside">• {suggestion}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {/* Version update check */}
                    {versionInfo && (
                      <div className="pt-2 border-t border-slate-600">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-slate-400">📦 Version:</span>
                          <span className="text-slate-300">{versionInfo.current_version}</span>
                        </div>
                        {versionInfo.update_available ? (
                          <div className="mt-1">
                            <div className="flex items-center gap-1 text-xs text-yellow-400">
                              <span>🔔</span>
                              <span>Update available: {versionInfo.latest_version}</span>
                            </div>
                            {versionInfo.release_url && (
                              <a 
                                href={versionInfo.release_url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="text-xs text-blue-400 hover:text-blue-300 underline mt-1 block"
                              >
                                View release notes →
                              </a>
                            )}
                          </div>
                        ) : versionInfo.is_dev_version || (versionInfo.latest_version === 'unknown' && versionInfo.error) ? (
                          <div className="text-xs text-purple-400 mt-1">🚀 Development version</div>
                        ) : (
                          <div className="text-xs text-green-400 mt-1">✓ Up to date</div>
                        )}
                        {versionInfo.error && !versionInfo.is_dev_version && !(versionInfo.latest_version === 'unknown' && versionInfo.error) && (
                          <div className="text-xs text-slate-400 mt-1">
                            ⚠️ Check failed
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
