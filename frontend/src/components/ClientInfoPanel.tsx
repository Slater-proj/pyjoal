import { Play, Pause, Activity } from 'lucide-react'
import { useStore } from '../store/useStore'

export default function ClientInfoPanel() {
  const { stats, config, startSeeding, stopSeeding } = useStore()
  const isRunning = stats?.isRunning || false

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const formatSpeed = (bytesPerSec: number) => {
    return formatBytes(bytesPerSec) + '/s'
  }

  const handleToggle = async () => {
    try {
      if (isRunning) {
        await stopSeeding()
      } else {
        await startSeeding()
      }
    } catch (error) {
      console.error('Failed to toggle seeding:', error)
    }
  }

  // Extraire le nom du client depuis le fichier
  const clientName = config?.client?.replace('.client', '').replace(/-/g, ' ') || 'Unknown Client'

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-5 shadow-lg">
      {/* Status Badge */}
      <div className="flex items-center justify-center gap-2 mb-4">
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${
          isRunning ? 'bg-green-500/20 text-green-400' : 'bg-slate-700 text-slate-400'
        }`}>
          {isRunning ? (
            <>
              <Activity className="w-4 h-4 animate-pulse" />
              <span className="text-sm font-medium">Seeding Active</span>
            </>
          ) : (
            <>
              <Pause className="w-4 h-4" />
              <span className="text-sm font-medium">Paused</span>
            </>
          )}
        </div>
      </div>

      {/* Start/Stop Button */}
      <button
        onClick={handleToggle}
        className={`
          w-full flex items-center justify-center gap-3 py-4 px-4 rounded-lg font-bold text-base
          transition-all duration-200 shadow-md
          ${isRunning 
            ? 'bg-red-600 hover:bg-red-700 text-white' 
            : 'bg-green-600 hover:bg-green-700 text-white'}
        `}
      >
        {isRunning ? (
          <>
            <Pause className="w-5 h-5" />
            <span>STOP SEEDING</span>
          </>
        ) : (
          <>
            <Play className="w-5 h-5" />
            <span>START SEEDING</span>
          </>
        )}
      </button>

      {/* Divider */}
      <div className="border-t border-slate-600 my-5"></div>

      {/* Client Info */}
      <div className="bg-slate-700/30 rounded-lg p-3 mb-4">
        <p className="text-slate-500 text-xs uppercase tracking-wide mb-2 text-center">Emulating Client</p>
        <p className="text-blue-400 font-bold text-base text-center">
          {clientName}
        </p>
      </div>

      {/* Stats Table */}
      <div className="bg-slate-900/50 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <tbody>
            <tr className="border-b border-slate-700">
              <td className="py-2.5 px-3 text-slate-400">Upload Speed</td>
              <td className="py-2.5 px-3 text-right font-semibold text-green-400">
                {formatSpeed(stats?.uploadSpeed || 0)}
              </td>
            </tr>
            <tr className="border-b border-slate-700">
              <td className="py-2.5 px-3 text-slate-400">Total Torrents</td>
              <td className="py-2.5 px-3 text-right font-semibold text-white">
                {stats?.totalTorrents || 0}
              </td>
            </tr>
            <tr>
              <td className="py-2.5 px-3 text-slate-400">Active Torrents</td>
              <td className="py-2.5 px-3 text-right font-semibold text-white">
                {stats?.activeTorrents || 0}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Total Uploaded */}
      <div className="border-t border-slate-600 mt-5 pt-4">
        <div className="text-center">
          <p className="text-slate-500 text-xs uppercase tracking-wide mb-1">Total Uploaded</p>
          <p className="text-2xl font-bold text-green-400">
            {formatBytes(stats?.totalUploaded || 0)}
          </p>
        </div>
      </div>
    </div>
  )
}
