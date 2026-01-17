import { Trash2, ChevronLeft, ChevronRight, RotateCcw } from 'lucide-react'
import { useStore } from '../store/useStore'
import { useEffect, useState, useCallback, useRef } from 'react'

// Default column widths in pixels
const DEFAULT_COLUMN_WIDTHS = {
  name: 420,
  size: 90,
  speed: 100,
  uploaded: 90,
  peers: 100,
  ratio: 110,
  duration: 110,
  actions: 50
}

// Min widths for auto-size calculation
const MIN_COLUMN_WIDTHS = {
  name: 150,
  size: 70,
  speed: 80,
  uploaded: 70,
  peers: 70,
  ratio: 80,
  duration: 80,
  actions: 40
}

export default function TorrentsTable() {
  const { torrents, stats, removeTorrent, config, startAutoRefresh, stopAutoRefresh, reloadTorrents } = useStore()
  const isRunning = stats?.isRunning || false
  const [currentPage, setCurrentPage] = useState(1)
  const [isReloading, setIsReloading] = useState(false)
  const torrentsPerPage = 20
  
  // Column resize state
  const [columnWidths, setColumnWidths] = useState(DEFAULT_COLUMN_WIDTHS)
  const [resizing, setResizing] = useState<string | null>(null)
  const tableRef = useRef<HTMLTableElement>(null)
  
  // Use refs to avoid stale closures in event listeners
  const resizeRef = useRef<{
    column: string | null
    startX: number
    startWidth: number
  }>({ column: null, startX: 0, startWidth: 0 })

  // Get target values from config
  const ratioTarget = config?.uploadRatioTarget ?? -1
  const durationTarget = config?.seedingDurationLimit ?? -1 // in hours

  // Handle column resize start
  const handleMouseDown = useCallback((column: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    
    resizeRef.current = {
      column,
      startX: e.clientX,
      startWidth: columnWidths[column as keyof typeof columnWidths]
    }
    setResizing(column)
  }, [columnWidths])

  // Handle double-click to auto-size column (like Excel)
  const handleDoubleClick = useCallback((column: string) => {
    if (!tableRef.current) return
    
    // Find the column index
    const columnIndex = Object.keys(DEFAULT_COLUMN_WIDTHS).indexOf(column)
    if (columnIndex === -1) return
    
    // Get header text width
    const headerCells = tableRef.current.querySelectorAll('thead th')
    const headerCell = headerCells[columnIndex] as HTMLElement
    
    // Measure using a hidden clone with no width constraints
    const measureDiv = document.createElement('div')
    measureDiv.style.cssText = 'position:absolute;visibility:hidden;white-space:nowrap;font:14px system-ui,-apple-system,sans-serif;'
    document.body.appendChild(measureDiv)
    
    // Measure header
    const headerText = headerCell?.querySelector('span')?.textContent || headerCell?.textContent || ''
    measureDiv.textContent = headerText
    let maxWidth = measureDiv.offsetWidth + 24 // Header padding
    
    // Measure all rows in this column
    const rows = tableRef.current.querySelectorAll('tbody tr')
    rows.forEach(row => {
      const cell = row.children[columnIndex] as HTMLElement
      if (cell) {
        // For name column, get just the title text (not the size/client info)
        if (column === 'name') {
          const titleDiv = cell.querySelector('.font-semibold')
          measureDiv.textContent = titleDiv?.textContent || cell.textContent || ''
        } else {
          measureDiv.textContent = cell.textContent || ''
        }
        const width = measureDiv.offsetWidth + 24 // Cell padding
        maxWidth = Math.max(maxWidth, width)
      }
    })
    
    document.body.removeChild(measureDiv)
    
    // Add some extra padding for the name column (has icon)
    if (column === 'name') {
      maxWidth += 32 // For the status dot
    }
    
    // Apply min/max constraints
    const minWidth = MIN_COLUMN_WIDTHS[column as keyof typeof MIN_COLUMN_WIDTHS] || 50
    maxWidth = Math.max(minWidth, maxWidth)
    
    // Max limit to prevent crazy widths
    const maxLimit = column === 'name' ? 600 : 250
    maxWidth = Math.min(maxWidth, maxLimit)
    
    setColumnWidths(prev => ({
      ...prev,
      [column]: maxWidth
    }))
  }, [])

  // Global mouse move and up handlers
  useEffect(() => {
    if (!resizing) return

    const handleMouseMove = (e: MouseEvent) => {
      const { startX, startWidth } = resizeRef.current
      const diff = e.clientX - startX
      const newWidth = Math.max(40, startWidth + diff) // Minimum 40px
      
      setColumnWidths(prev => ({
        ...prev,
        [resizing]: newWidth
      }))
    }

    const handleMouseUp = () => {
      resizeRef.current.column = null
      setResizing(null)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [resizing])

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

  const formatSeedingTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    if (days > 0) return `${days}d ${hours % 24}h`
    if (hours > 0) return `${hours}h ${minutes % 60}m`
    if (minutes > 0) return `${minutes}m`
    return `${seconds}s`
  }

  const formatDurationTarget = (hours: number) => {
    if (hours < 0) return '∞'
    if (hours >= 24) return `${Math.floor(hours / 24)}d`
    return `${hours}h`
  }

  const handleReload = async () => {
    if (isReloading) return
    
    setIsReloading(true)
    try {
      await reloadTorrents()
    } catch (error) {
      console.error('Failed to reload torrents:', error)
    } finally {
      setIsReloading(false)
    }
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

  // Auto-refresh pour réactivité temps réel
  useEffect(() => {
    startAutoRefresh()
    return () => stopAutoRefresh()
  }, [])

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
      <div className="px-6 py-4 bg-gradient-to-r from-slate-700 to-slate-600 border-b-2 border-slate-500 flex items-center justify-between">
        <h2 className="text-xl font-bold text-white flex items-center gap-3">
          <span className={`w-3 h-3 rounded-full ${isRunning ? 'bg-green-400 animate-pulse' : 'bg-gray-400'}`}></span>
          {isRunning ? 'Seeding' : 'Paused'} • {torrents.length} Torrent{torrents.length !== 1 ? 's' : ''}
          {totalPages > 1 && <span className="text-slate-300 text-base font-normal">• Page {currentPage}/{totalPages}</span>}
        </h2>
        <button
          onClick={handleReload}
          disabled={isReloading}
          className="flex items-center gap-2 px-3 py-1.5 bg-slate-600 hover:bg-slate-500 disabled:bg-slate-700 
                     text-white text-sm rounded-md transition-all duration-200 disabled:cursor-not-allowed"
          title="Reload torrents from directory"
        >
          <RotateCcw className={`w-4 h-4 ${isReloading ? 'animate-spin' : ''}`} />
          {isReloading ? 'Reloading...' : 'Reload'}
        </button>
      </div>
      
      {/* Table with visible borders - full width */}
      <div className="overflow-hidden">
        <table ref={tableRef} className="w-full border-collapse table-fixed">
          <thead>
            <tr className="bg-slate-700/70 text-left text-sm text-slate-200 font-semibold">
              <th className="px-4 py-3 border-r border-slate-600 relative overflow-hidden" style={{ width: columnWidths.name }}>
                <span className="truncate block">Name</span>
                <div 
                  className="absolute right-0 top-0 bottom-0 w-2 cursor-col-resize hover:bg-blue-500/50 transition-colors"
                  onMouseDown={(e) => handleMouseDown('name', e)}
                  onDoubleClick={() => handleDoubleClick('name')}
                  title="Double-click to auto-fit"
                />
              </th>
              <th className="px-4 py-3 border-r border-slate-600 text-right relative overflow-hidden" style={{ width: columnWidths.size }}>
                <span className="truncate block">Size</span>
                <div 
                  className="absolute right-0 top-0 bottom-0 w-2 cursor-col-resize hover:bg-blue-500/50 transition-colors"
                  onMouseDown={(e) => handleMouseDown('size', e)}
                  onDoubleClick={() => handleDoubleClick('size')}
                  title="Double-click to auto-fit"
                />
              </th>
              <th className="px-4 py-3 border-r border-slate-600 text-right relative overflow-hidden" style={{ width: columnWidths.speed }}>
                <span className="truncate block">Speed ↑</span>
                <div 
                  className="absolute right-0 top-0 bottom-0 w-2 cursor-col-resize hover:bg-blue-500/50 transition-colors"
                  onMouseDown={(e) => handleMouseDown('speed', e)}
                  onDoubleClick={() => handleDoubleClick('speed')}
                  title="Double-click to auto-fit"
                />
              </th>
              <th className="px-4 py-3 border-r border-slate-600 text-right relative overflow-hidden" style={{ width: columnWidths.uploaded }}>
                <span className="truncate block">Uploaded</span>
                <div 
                  className="absolute right-0 top-0 bottom-0 w-2 cursor-col-resize hover:bg-blue-500/50 transition-colors"
                  onMouseDown={(e) => handleMouseDown('uploaded', e)}
                  onDoubleClick={() => handleDoubleClick('uploaded')}
                  title="Double-click to auto-fit"
                />
              </th>
              <th className="px-4 py-3 border-r border-slate-600 text-center relative overflow-hidden" style={{ width: columnWidths.peers }}>
                <span className="truncate block">Peers</span>
                <div 
                  className="absolute right-0 top-0 bottom-0 w-2 cursor-col-resize hover:bg-blue-500/50 transition-colors"
                  onMouseDown={(e) => handleMouseDown('peers', e)}
                  onDoubleClick={() => handleDoubleClick('peers')}
                  title="Double-click to auto-fit"
                />
              </th>
              <th className="px-4 py-3 border-r border-slate-600 text-center relative overflow-hidden" style={{ width: columnWidths.ratio }}>
                <span className="truncate block">Ratio {ratioTarget > 0 ? <span className="text-slate-400 font-normal">/{ratioTarget}</span> : <span className="text-slate-400 font-normal">/∞</span>}</span>
                <div 
                  className="absolute right-0 top-0 bottom-0 w-2 cursor-col-resize hover:bg-blue-500/50 transition-colors"
                  onMouseDown={(e) => handleMouseDown('ratio', e)}
                  onDoubleClick={() => handleDoubleClick('ratio')}
                  title="Double-click to auto-fit"
                />
              </th>
              <th className="px-4 py-3 border-r border-slate-600 text-center relative overflow-hidden" style={{ width: columnWidths.duration }}>
                <span className="truncate block">Duration {durationTarget > 0 ? <span className="text-slate-400 font-normal">/{formatDurationTarget(durationTarget)}</span> : <span className="text-slate-400 font-normal">/∞</span>}</span>
                <div 
                  className="absolute right-0 top-0 bottom-0 w-2 cursor-col-resize hover:bg-blue-500/50 transition-colors"
                  onMouseDown={(e) => handleMouseDown('duration', e)}
                  onDoubleClick={() => handleDoubleClick('duration')}
                  title="Double-click to auto-fit"
                />
              </th>
              <th className="px-4 py-3 text-center overflow-hidden" style={{ width: columnWidths.actions }}>
                <span className="truncate block">Del</span>
              </th>
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
                  <td className="px-4 py-3 border-r border-slate-700 overflow-hidden" style={{ width: columnWidths.name }}>
                    <div className="flex items-center gap-2 overflow-hidden">
                      <div className="flex flex-col items-center gap-0.5 flex-shrink-0">
                        <span 
                          className={`w-2.5 h-2.5 rounded-full flex-shrink-0 transition-all cursor-help ${
                            torrent.status?.status === 'pause_fake'
                              ? 'bg-yellow-400 animate-pulse'
                              : torrent.status?.status === 'seeding_active'
                              ? 'bg-green-400 animate-pulse'
                              : torrent.status?.status === 'seeding_low'
                              ? 'bg-blue-400'
                              : isActive
                              ? torrent.uploadSpeed > 0
                                ? 'bg-green-400 animate-pulse'
                                : 'bg-yellow-400'
                              : 'bg-slate-500'
                          }`}
                          title={(() => {
                            const status = torrent.status;
                            if (!status) {
                              return isActive ? 'Partage en cours' : 'En pause';
                            }
                            const parts = [
                              `État: ${status.status_text}`,
                              `Vitesse actuelle: ${status.speed_formatted}`,
                              `Heures d'activité: ${status.peak_hours}`,
                              status.time_until_change_formatted ? 
                                `Prochain changement: ${status.time_until_change_formatted}` : ''
                            ].filter(Boolean);
                            return parts.join(' • ');
                          })()}
                        />
                      </div>
                      <div className="min-w-0 flex-1 overflow-hidden">
                        <div className="font-semibold text-white truncate text-sm leading-tight" title={torrent.name}>
                          {torrent.name}
                        </div>
                        <div className="text-xs text-slate-400 mt-1 truncate">
                          📡 {torrent.tracker ? new URL(torrent.tracker).hostname : 'Unknown'}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right text-slate-300 border-r border-slate-700 font-mono text-sm overflow-hidden">
                    <span className="truncate block">{formatBytes(torrent.size)}</span>
                  </td>
                  <td className="px-4 py-3 text-right border-r border-slate-700 text-sm overflow-hidden">
                    {isActive ? (
                      <span className={`font-mono font-bold truncate block ${torrent.uploadSpeed > 0 ? 'text-green-400' : 'text-yellow-400'}`}>
                        ↑{formatSpeed(torrent.uploadSpeed)}
                      </span>
                    ) : (
                      <span className="text-slate-600 font-mono">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right text-slate-300 font-mono border-r border-slate-700 text-sm overflow-hidden">
                    <span className="truncate block">{formatBytes(torrent.uploaded)}</span>
                  </td>
                  <td className="px-4 py-3 text-center border-r border-slate-700 text-sm overflow-hidden">
                    {isActive ? (
                      <div className="flex items-center justify-center gap-1">
                        <span className="bg-green-500/20 text-green-300 px-1 py-0.5 rounded text-xs font-bold" title="Seeders">
                          {torrent.seeders}S
                        </span>
                        <span className="bg-blue-500/20 text-blue-300 px-1 py-0.5 rounded text-xs font-bold" title="Leechers">
                          {torrent.leechers}L
                        </span>
                      </div>
                    ) : (
                      <span className="text-slate-600">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center border-r border-slate-700 text-sm overflow-hidden">
                    <div className="flex items-center justify-center gap-1 overflow-hidden">
                      <span className={`font-mono font-bold px-1 py-0.5 rounded text-xs truncate ${
                        ratioTarget > 0 && torrent.ratio >= ratioTarget
                          ? 'bg-green-500/30 text-green-300'
                          : torrent.ratio >= 1 
                            ? 'bg-green-500/20 text-green-300' 
                            : torrent.ratio >= 0.5 
                              ? 'bg-yellow-500/20 text-yellow-300'
                              : 'bg-slate-600/50 text-slate-300'
                      }`}>
                        {torrent.ratio.toFixed(2)}
                      </span>
                      <span className="text-slate-500 flex-shrink-0">/</span>
                      <span className="text-slate-400 text-xs flex-shrink-0">{ratioTarget > 0 ? ratioTarget : '∞'}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center text-slate-300 font-mono border-r border-slate-700 text-sm overflow-hidden">
                    <div className="flex items-center justify-center gap-1 overflow-hidden">
                      <span className={`px-1 py-0.5 rounded text-xs truncate ${
                        durationTarget > 0 && (torrent.seedingTime / 3600) >= durationTarget
                          ? 'bg-green-500/30 text-green-300'
                          : 'bg-slate-700/50 text-slate-300'
                      }`}>
                        {formatSeedingTime(torrent.seedingTime)}
                      </span>
                      <span className="text-slate-500 flex-shrink-0">/</span>
                      <span className="text-slate-400 text-xs flex-shrink-0">{formatDurationTarget(durationTarget)}</span>
                    </div>
                  </td>
                  <td className="px-2 py-3 text-center overflow-hidden">
                    <button
                      onClick={(e) => handleRemove(e, torrent.id)}
                      className="p-1.5 rounded text-red-400 hover:bg-red-500/20 transition-all"
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
