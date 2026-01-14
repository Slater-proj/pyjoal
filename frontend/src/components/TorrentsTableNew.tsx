import { Trash2 } from 'lucide-react'
import { useStore } from '../store/useStore'

export default function TorrentsTable() {
  const { torrents, stats, removeTorrent } = useStore()
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

  const handleRemove = async (e: React.MouseEvent, infoHash: string) => {
    e.stopPropagation()
    if (confirm('Are you sure you want to remove this torrent?')) {
      try {
        await removeTorrent(infoHash)
      } catch (error) {
        console.error('Failed to remove torrent:', error)
      }
    }
  }

  // When not running, show message
  if (!isRunning) {
    return (
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-12 text-center">
        <div className="text-slate-400 text-lg mb-2">⏸️ Client is paused</div>
        <p className="text-slate-500">Click <strong>START</strong> to begin seeding torrents</p>
      </div>
    )
  }

  // When no torrents
  if (torrents.length === 0) {
    return (
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-12 text-center">
        <div className="text-6xl mb-4">📂</div>
        <div className="text-slate-300 text-lg mb-2">No torrents yet</div>
        <p className="text-slate-500">
          Use the <strong className="text-blue-400">ADD TORRENTS</strong> button or drop files on this page
        </p>
      </div>
    )
  }

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-slate-700/50 border-b border-slate-600">
        <h2 className="text-lg font-semibold text-white">
          Seeding Torrents ({torrents.length})
        </h2>
      </div>
      
      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-slate-750">
            <tr className="text-left text-xs text-slate-400 uppercase tracking-wider">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium text-right">Size</th>
              <th className="px-4 py-3 font-medium text-right">Speed</th>
              <th className="px-4 py-3 font-medium text-right">Uploaded</th>
              <th className="px-4 py-3 font-medium text-center">Peers</th>
              <th className="px-4 py-3 font-medium text-right">Ratio</th>
              <th className="px-4 py-3 font-medium w-12"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {torrents.map((torrent) => (
              <tr 
                key={torrent.id}
                className="hover:bg-slate-700/30 transition-colors"
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <span 
                      className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                        torrent.state === 'seeding' 
                          ? 'bg-green-500 shadow-sm shadow-green-500/50' 
                          : 'bg-slate-500'
                      }`}
                    />
                    <span className="text-white font-medium truncate max-w-[250px] lg:max-w-[400px]" title={torrent.name}>
                      {torrent.name}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 text-right text-slate-300 text-sm whitespace-nowrap">
                  {formatBytes(torrent.size)}
                </td>
                <td className="px-4 py-3 text-right text-green-400 text-sm whitespace-nowrap font-medium">
                  ↑ {formatSpeed(torrent.uploadSpeed)}
                </td>
                <td className="px-4 py-3 text-right text-slate-300 text-sm whitespace-nowrap">
                  {formatBytes(torrent.uploaded)}
                </td>
                <td className="px-4 py-3 text-center text-sm whitespace-nowrap">
                  <span className="text-green-400" title="Seeders">{torrent.seeders}</span>
                  <span className="text-slate-600 mx-1">/</span>
                  <span className="text-blue-400" title="Leechers">{torrent.leechers}</span>
                </td>
                <td className="px-4 py-3 text-right text-sm whitespace-nowrap">
                  <span className={`font-medium ${torrent.ratio >= 1 ? 'text-green-400' : 'text-slate-300'}`}>
                    {torrent.ratio.toFixed(2)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={(e) => handleRemove(e, torrent.id)}
                    className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                    title="Remove torrent"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
