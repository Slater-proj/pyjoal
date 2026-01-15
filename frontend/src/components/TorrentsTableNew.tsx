import { Trash2, ChevronLeft, ChevronRight } from 'lucide-react'
import { useStore } from '../store/useStore'
import { useEffect, useState } from 'react'

export default function TorrentsTable() {
  const { torrents, stats, removeTorrent } = useStore()
  const isRunning = stats?.isRunning || false
  const [currentTime, setCurrentTime] = useState(Date.now())
  const [currentPage, setCurrentPage] = useState(1)
  const torrentsPerPage = 20

  // Update current time every second for duration calculation
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(Date.now())
    }, 1000)
    return () => clearInterval(interval)
  }, [])

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

  const formatDuration = (addedAt: string) => {
    const added = new Date(addedAt).getTime()
    const diff = currentTime - added
    const seconds = Math.floor(diff / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    if (days > 0) return `${days}d ${hours % 24}h`
    if (hours > 0) return `${hours}h ${minutes % 60}m`
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`
    return `${seconds}s`
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

  // Pagination logic
  const totalPages = Math.ceil(torrents.length / torrentsPerPage)
  const startIndex = (currentPage - 1) * torrentsPerPage
  const endIndex = startIndex + torrentsPerPage
  const currentTorrents = torrents.slice(startIndex, endIndex)

  // Reset to page 1 if current page is out of bounds
  useEffect(() => {
    if (currentPage > totalPages && totalPages > 0) {
      setCurrentPage(1)
    }
  }, [torrents.length, totalPages, currentPage])

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
    <div className="bg-slate-800 rounded-lg border-2 border-slate-600 overflow-hidden shadow-lg">
      {/* Header */}
      <div className="px-6 py-4 bg-gradient-to-r from-slate-700 to-slate-600 border-b-2 border-slate-500">
        <h2 className="text-xl font-bold text-white flex items-center gap-3">
          <span className={`w-3 h-3 rounded-full ${isRunning ? 'bg-green-400 animate-pulse' : 'bg-gray-400'}`}></span>
          {isRunning ? 'Seeding' : 'Paused'} • {torrents.length} Torrent{torrents.length !== 1 ? 's' : ''}
          {totalPages > 1 && <span className="text-slate-300 text-base font-normal">• Page {currentPage}/{totalPages}</span>}
        </h2>
      </div>
      
      {/* Table with visible borders */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-slate-700/70 text-left text-sm text-slate-200 font-semibold">
              <th className="px-4 py-4 border-r border-slate-600">Name</th>
              <th className="px-4 py-4 border-r border-slate-600 text-right">Size</th>
              <th className="px-4 py-4 border-r border-slate-600 text-right">Speed ↑</th>
              <th className="px-4 py-4 border-r border-slate-600 text-right">Uploaded</th>
              <th className="px-4 py-4 border-r border-slate-600 text-center">Peers (S/L)</th>
              <th className="px-4 py-4 border-r border-slate-600 text-right">Ratio</th>
              <th className="px-4 py-4 border-r border-slate-600 text-right">Duration</th>
              <th className="px-4 py-4 w-12 text-center">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700">
            {currentTorrents.map((torrent, index) => {
              const isActive = torrent.state === 'seeding'
              const isEven = index % 2 === 0
              return (
                <tr 
                  key={torrent.id}
                  className={`border-b border-slate-700 hover:bg-slate-600/50 transition-colors ${
                    isEven ? 'bg-slate-800/50' : 'bg-slate-750/30'
                  }`}
                >
                  <td className="px-4 py-4 border-r border-slate-700">
                    <div className="flex items-center gap-3">
                      <div className="flex flex-col items-center gap-1">
                        <span 
                          className={`w-3 h-3 rounded-full flex-shrink-0 ${
                            isActive
                              ? torrent.uploadSpeed > 0
                                ? 'bg-green-400 animate-pulse'
                                : 'bg-yellow-400'
                              : 'bg-slate-500'
                          }`}
                          title={isActive ? 'Seeding' : 'Stopped'}
                        />
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          isActive ? 'bg-green-500/20 text-green-300' : 'bg-slate-600/50 text-slate-400'
                        }`}>
                          {isActive ? 'SEED' : 'STOP'}
                        </span>
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="font-semibold text-white truncate text-sm leading-tight" title={torrent.name}>
                          {torrent.name}
                        </div>
                        <div className="text-xs text-slate-400 mt-1">
                          📡 {torrent.tracker ? new URL(torrent.tracker).hostname : 'Unknown tracker'}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-right text-slate-300 border-r border-slate-700 font-mono text-sm whitespace-nowrap">
                    {formatBytes(torrent.size)}
                  </td>
                  <td className="px-4 py-4 text-right border-r border-slate-700 text-sm whitespace-nowrap">
                    {isActive ? (
                      <span className={`font-mono font-bold ${torrent.uploadSpeed > 0 ? 'text-green-400' : 'text-yellow-400'}`}>
                        ↑ {formatSpeed(torrent.uploadSpeed)}
                      </span>
                    ) : (
                      <span className="text-slate-600 font-mono">-</span>
                    )}
                  </td>
                  <td className="px-4 py-4 text-right text-slate-300 font-mono border-r border-slate-700 text-sm whitespace-nowrap">
                    {formatBytes(torrent.uploaded)}
                  </td>
                  <td className="px-4 py-4 text-center border-r border-slate-700 text-sm whitespace-nowrap">
                    {isActive ? (
                      <div className="flex items-center justify-center gap-2">
                        <span className="bg-green-500/20 text-green-300 px-2 py-1 rounded text-xs font-bold" title="Seeders">
                          {torrent.seeders}S
                        </span>
                        <span className="bg-blue-500/20 text-blue-300 px-2 py-1 rounded text-xs font-bold" title="Leechers">
                          {torrent.leechers}L
                        </span>
                      </div>
                    ) : (
                      <span className="text-slate-600">-</span>
                    )}
                  </td>
                  <td className="px-4 py-4 text-right border-r border-slate-700 text-sm whitespace-nowrap">
                    <span className={`font-mono font-bold px-2 py-1 rounded text-xs ${
                      torrent.ratio >= 1 
                        ? 'bg-green-500/20 text-green-300' 
                        : torrent.ratio >= 0.5 
                          ? 'bg-yellow-500/20 text-yellow-300'
                          : 'bg-red-500/20 text-red-300'
                    }`}>
                      {torrent.ratio.toFixed(3)}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-right text-slate-300 font-mono border-r border-slate-700 text-sm whitespace-nowrap">
                    <div className="bg-slate-700/50 px-2 py-1 rounded text-xs">
                      ⏱️ {formatDuration(torrent.addedAt)}
                    </div>
                  </td>
                  <td className="px-4 py-4 text-center">
                    <button
                      onClick={(e) => handleRemove(e, torrent.id)}
                      className="p-2 rounded-lg text-red-400 hover:bg-red-500/20 border border-red-500/30 hover:border-red-400 transition-all"
                      title="Remove torrent"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="px-4 py-3 border-t border-slate-700 flex items-center justify-between">
          <div className="text-sm text-slate-400">
            Showing {startIndex + 1} to {Math.min(endIndex, torrents.length)} of {torrents.length}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-4 py-2 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-blue-600 hover:bg-blue-500 text-white border-2 border-blue-500 hover:border-blue-400 font-semibold"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <span className="text-sm text-white bg-slate-600 px-4 py-2 rounded-lg font-bold border border-slate-500">
              {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-4 py-2 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-blue-600 hover:bg-blue-500 text-white border-2 border-blue-500 hover:border-blue-400 font-semibold"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
