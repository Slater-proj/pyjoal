import { useState, useEffect } from 'react'
import { Activity, AlertCircle, CheckCircle, X, Plus, Minus, Settings as SettingsIcon, Trash2, RefreshCw } from 'lucide-react'
import axios from 'axios'

interface HistoryEntry {
  timestamp: string
  eventType: string
  message: string
  data: Record<string, any>
}

const EVENT_ICONS: Record<string, any> = {
  system_start: CheckCircle,
  system_stop: X,
  torrent_added: Plus,
  torrent_removed: Minus,
  announce_success: Activity,
  announce_failed: AlertCircle,
  config_updated: SettingsIcon,
}

const EVENT_COLORS: Record<string, string> = {
  system_start: 'text-green-400 bg-green-500/10',
  system_stop: 'text-red-400 bg-red-500/10',
  torrent_added: 'text-blue-400 bg-blue-500/10',
  torrent_removed: 'text-orange-400 bg-orange-500/10',
  announce_success: 'text-green-400 bg-green-500/10',
  announce_failed: 'text-red-400 bg-red-500/10',
  config_updated: 'text-purple-400 bg-purple-500/10',
}

export default function HistoryPage() {
  const [entries, setEntries] = useState<HistoryEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState<string>('all')

  const fetchHistory = async () => {
    setLoading(true)
    try {
      const params: any = { limit: 200 }
      if (filter !== 'all') {
        params.event_type = filter
      }
      const { data } = await axios.get('/api/history', { params })
      setEntries(data.entries)
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
  }, [filter])

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const filters = [
    { id: 'all', label: 'All' },
    { id: 'announce_success', label: 'Success' },
    { id: 'announce_failed', label: 'Failed' },
    { id: 'torrent_added', label: 'Added' },
    { id: 'torrent_removed', label: 'Removed' },
  ]

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white">Event History</h2>
            <p className="text-slate-400 text-sm mt-1">
              {entries.length} events
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
        <div className="px-6 py-3 border-b border-slate-700 flex gap-2 overflow-x-auto">
          {filters.map((f) => (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                filter === f.id
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Events List */}
        <div className="divide-y divide-slate-700 max-h-[calc(100vh-350px)] overflow-y-auto">
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
              const Icon = EVENT_ICONS[entry.eventType] || Activity
              const colors = EVENT_COLORS[entry.eventType] || 'text-slate-400 bg-slate-500/10'
              const [textColor, bgColor] = colors.split(' ')

              return (
                <div key={index} className="px-6 py-3 hover:bg-slate-700/30 transition-colors">
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-lg ${bgColor}`}>
                      <Icon className={`w-4 h-4 ${textColor}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-white text-sm">{entry.message}</p>
                      {Object.keys(entry.data).length > 0 && (
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
      </div>
    </div>
  )
}
