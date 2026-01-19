import { useState, useEffect } from 'react'
import { Activity, AlertCircle, CheckCircle, X, Plus, Minus, Settings as SettingsIcon, Trash2, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react'
import axios from 'axios'

interface HistoryEntry {
  timestamp: string
  eventType: string
  message: string
  data: Record<string, any>
}

interface HistoryResponse {
  entries: HistoryEntry[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

const EVENT_ICONS: Record<string, any> = {
  system_start: CheckCircle,
  system_stop: X,
  torrent_added: Plus,
  torrent_removed: Minus,
  torrent_archived: Trash2,  // Unified archived category
  torrent_load_failed: AlertCircle,
  announce_success: Activity,
  announce_failed: AlertCircle,
  config_updated: SettingsIcon,
}

const EVENT_COLORS: Record<string, string> = {
  system_start: 'text-green-400 bg-green-500/10',
  system_stop: 'text-red-400 bg-red-500/10',
  torrent_added: 'text-blue-400 bg-blue-500/10',
  torrent_removed: 'text-orange-400 bg-orange-500/10',
  torrent_archived: 'text-purple-400 bg-purple-500/10',  // Default archived color
  torrent_load_failed: 'text-red-400 bg-red-500/10',
  announce_success: 'text-green-400 bg-green-500/10',
  announce_failed: 'text-red-400 bg-red-500/10',
  config_updated: 'text-purple-400 bg-purple-500/10',
}

// Function to get color based on archive reason
const getArchiveColor = (reason: string) => {
  switch (reason) {
    case 'ratio_target': return 'text-purple-400 bg-purple-500/10'
    case 'duration_limit': return 'text-indigo-400 bg-indigo-500/10'
    case 'zero_peers': return 'text-red-400 bg-red-500/10'
    case 'error': return 'text-red-400 bg-red-500/10'
    default: return 'text-purple-400 bg-purple-500/10'
  }
}

export default function HistoryPage() {
  const [entries, setEntries] = useState<HistoryEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState<string>('all')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const perPage = 50

  const fetchHistory = async () => {
    setLoading(true)
    try {
      const params: any = { page, per_page: perPage }
      if (filter !== 'all') {
        params.event_type = filter
      }
      const { data } = await axios.get<HistoryResponse>('/api/history', { params })
      setEntries(data.entries)
      setTotal(data.total)
      setTotalPages(data.total_pages)
    } catch (error) {
      console.error('Failed to fetch history:', error)
    } finally {
      setLoading(false)
    }
  }

  const clearHistory = async () => {
    if (!confirm('Are you sure you want to clear all history?')) return
    try {
      await axios.delete('/api/history')
      await fetchHistory()
    } catch (error) {
      console.error('Failed to clear history:', error)
    }
  }

  useEffect(() => {
    fetchHistory()
    const interval = setInterval(fetchHistory, 10000)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter, page])

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const filters = [
    { id: 'all', label: 'All Events' },
    { id: 'announce_success', label: 'Announce Success' },
    { id: 'announce_failed', label: 'Announce Failed' },
    { id: 'torrent_added', label: 'Torrents Added' },
    { id: 'torrent_removed', label: 'Manually Removed' },
    { id: 'torrent_archived', label: 'Auto Archived' },
    { id: 'torrent_load_failed', label: 'Load Failed' },
  ]

  return (
    <div className="w-full max-w-6xl mx-auto px-4">
      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white">Event History</h2>
            <p className="text-slate-400 text-sm mt-1">
              {total} events{totalPages > 1 && ` - Page ${page} of ${totalPages}`}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={fetchHistory}
              disabled={loading}
              className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={clearHistory}
              className="p-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors"
              title="Clear history"
            >
              <Trash2 className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="px-4 py-3 border-b border-slate-700 flex flex-wrap gap-2 sm:gap-3">
          {filters.map((f) => (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${filter === f.id
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Events List */}
        <div className="divide-y divide-slate-700 max-h-[calc(100vh-250px)] overflow-y-auto">
          {loading && entries.length === 0 ? (
            <div className="px-6 py-12 text-center text-slate-400">
              <RefreshCw className="w-8 h-8 mx-auto mb-3 animate-spin" />
              Loading history...
            </div>
          ) : entries.length === 0 ? (
            <div className="px-6 py-12 text-center text-slate-400">
              No events found
            </div>
          ) : (
            entries.map((entry, index) => {
              // Get icon and colors
              const Icon = EVENT_ICONS[entry.eventType] || Activity
              const defaultColors = EVENT_COLORS[entry.eventType] || 'text-slate-400 bg-slate-500/10'

              // Special handling for archived torrents with reason-specific colors
              const colors = entry.eventType === 'torrent_archived' && entry.data.reason
                ? getArchiveColor(entry.data.reason)
                : defaultColors

              const [textColor, bgColor] = colors.split(' ')

              // Format archive reason for display
              const formatArchiveReason = (reason: string) => {
                switch (reason) {
                  case 'ratio_target': return 'Ratio Target Reached'
                  case 'duration_limit': return 'Time Limit Reached'
                  case 'zero_peers': return 'No Active Peers'
                  case 'error': return 'Error Condition'
                  default: return 'Auto Archived'
                }
              }

              return (
                <div key={index} className="px-6 py-3 hover:bg-slate-700/30 transition-colors">
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-lg ${bgColor}`}>
                      <Icon className={`w-4 h-4 ${textColor}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-white text-sm">{entry.message}</p>

                      {/* Enhanced data display with archive reason */}
                      {entry.eventType === 'torrent_archived' && entry.data.reason && (
                        <div className="mt-2 space-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-slate-700 text-slate-300">
                              📋 {formatArchiveReason(entry.data.reason)}
                            </span>
                            {entry.data.ratio !== undefined && (
                              <span className="text-xs text-purple-300 bg-purple-500/20 px-2 py-0.5 rounded">
                                📊 Ratio: {typeof entry.data.ratio === 'number' ? entry.data.ratio.toFixed(2) : entry.data.ratio}
                                {entry.data.target && ` / ${entry.data.target}`}
                              </span>
                            )}
                            {entry.data.seeding_hours !== undefined && (
                              <span className="text-xs text-indigo-300 bg-indigo-500/20 px-2 py-0.5 rounded">
                                ⏱️ {typeof entry.data.seeding_hours === 'number' ? entry.data.seeding_hours.toFixed(1) : entry.data.seeding_hours}h
                                {entry.data.limit && ` / ${entry.data.limit}h`}
                              </span>
                            )}
                            {entry.data.seeders !== undefined && entry.data.leechers !== undefined && (
                              <span className="text-xs text-red-300 bg-red-500/20 px-2 py-0.5 rounded">
                                👥 {entry.data.seeders}S / {entry.data.leechers}L
                              </span>
                            )}
                          </div>
                          {entry.data.reason_detail && (
                            <p className="text-xs text-slate-400 italic pl-1">
                              💡 {entry.data.reason_detail}
                            </p>
                          )}
                          {entry.data.torrent_name && (
                            <p className="text-xs text-slate-500 truncate pl-1">
                              📁 {entry.data.torrent_name}
                            </p>
                          )}
                        </div>
                      )}

                      {/* Enhanced data display for load failures */}
                      {entry.eventType === 'torrent_load_failed' && (
                        <div className="mt-1">
                          <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-red-900 text-red-300">
                            ❌ {entry.data.error || 'Unknown error'}
                          </span>
                          {entry.data.filename && (
                            <span className="ml-2 text-xs text-slate-400">
                              📄 File: {entry.data.filename}
                            </span>
                          )}
                        </div>
                      )}

                      {/* Default data display for other events */}
                      {entry.eventType !== 'torrent_archived' && entry.eventType !== 'torrent_load_failed' && Object.keys(entry.data).length > 0 && (
                        <div className="mt-1 text-xs text-slate-500">
                          {Object.entries(entry.data).slice(0, 3).map(([key, value]) => (
                            <span key={key} className="mr-3">
                              {key}: <span className="text-slate-400">{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="text-right text-xs text-slate-500 whitespace-nowrap">
                      <div>{formatTime(entry.timestamp)}</div>
                      <div>{formatDate(entry.timestamp)}</div>
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-slate-700 flex items-center justify-between">
            <div className="text-sm text-slate-400">
              Showing {(page - 1) * perPage + 1} to {Math.min(page * perPage, total)} of {total}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-slate-700 hover:bg-slate-600 text-white"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <span className="text-sm text-slate-300 px-3">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-2 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed bg-slate-700 hover:bg-slate-600 text-white"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
