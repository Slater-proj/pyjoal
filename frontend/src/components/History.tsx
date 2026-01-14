import { useState, useEffect } from 'react'
import { Clock, Activity, AlertCircle, CheckCircle, X, Plus, Minus, Settings as SettingsIcon, Trash2 } from 'lucide-react'
import axios from 'axios'

interface HistoryEntry {
  timestamp: string
  eventType: string
  message: string
  data: Record<string, any>
}

interface HistorySummary {
  totalEntries: number
  countsByType: Record<string, number>
  recentActivity: number
  oldestEntry: string | null
  newestEntry: string | null
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
  system_start: 'text-green-400',
  system_stop: 'text-red-400',
  torrent_added: 'text-blue-400',
  torrent_removed: 'text-orange-400',
  announce_success: 'text-green-400',
  announce_failed: 'text-red-400',
  config_updated: 'text-purple-400',
}

const EVENT_LABELS: Record<string, string> = {
  system_start: 'System Started',
  system_stop: 'System Stopped',
  torrent_added: 'Torrent Added',
  torrent_removed: 'Torrent Removed',
  announce_success: 'Announce Success',
  announce_failed: 'Announce Failed',
  config_updated: 'Config Updated',
}

export default function History() {
  const [entries, setEntries] = useState<HistoryEntry[]>([])
  const [summary, setSummary] = useState<HistorySummary | null>(null)
  const [filter, setFilter] = useState<string>('all')
  const [limit] = useState<number>(100)
  const [loading, setLoading] = useState<boolean>(false)

  const fetchHistory = async () => {
    setLoading(true)
    try {
      const params: any = { limit }
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

  const fetchSummary = async () => {
    try {
      const { data } = await axios.get('/api/history/summary')
      setSummary(data)
    } catch (error) {
      console.error('Failed to fetch summary:', error)
    }
  }

  const clearHistory = async () => {
    if (!confirm('Are you sure you want to clear all history?')) return

    try {
      await axios.delete('/api/history')
      await fetchHistory()
      await fetchSummary()
    } catch (error) {
      console.error('Failed to clear history:', error)
    }
  }

  useEffect(() => {
    fetchHistory()
    fetchSummary()

    // Refresh every 10 seconds
    const interval = setInterval(() => {
      fetchHistory()
      fetchSummary()
    }, 10000)

    return () => clearInterval(interval)
  }, [filter, limit])

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleString()
  }

  const formatRelativeTime = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const seconds = Math.floor(diff / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    if (days > 0) return `${days}d ago`
    if (hours > 0) return `${hours}h ago`
    if (minutes > 0) return `${minutes}m ago`
    return `${seconds}s ago`
  }

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Clock className="w-5 h-5 text-slate-400" />
          <h2 className="text-xl font-bold text-white">History</h2>
        </div>

        <button
          onClick={clearHistory}
          className="flex items-center space-x-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
        >
          <Trash2 className="w-4 h-4" />
          <span>Clear History</span>
        </button>
      </div>

      {/* Summary Stats */}
      {summary && (
        <div className="px-6 py-4 bg-slate-700/50 border-b border-slate-700">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-slate-400 text-sm">Total Events</p>
              <p className="text-2xl font-bold text-white">{summary.totalEntries}</p>
            </div>
            <div>
              <p className="text-slate-400 text-sm">Recent (1h)</p>
              <p className="text-2xl font-bold text-green-400">{summary.recentActivity}</p>
            </div>
            <div>
              <p className="text-slate-400 text-sm">Success</p>
              <p className="text-2xl font-bold text-green-400">
                {summary.countsByType.announce_success || 0}
              </p>
            </div>
            <div>
              <p className="text-slate-400 text-sm">Failed</p>
              <p className="text-2xl font-bold text-red-400">
                {summary.countsByType.announce_failed || 0}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="px-6 py-4 border-b border-slate-700 flex flex-wrap gap-2">
        <button
          onClick={() => setFilter('all')}
          className={`px-3 py-1 rounded ${
            filter === 'all'
              ? 'bg-blue-600 text-white'
              : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
          }`}
        >
          All
        </button>
        {Object.entries(EVENT_LABELS).map(([type, label]) => (
          <button
            key={type}
            onClick={() => setFilter(type)}
            className={`px-3 py-1 rounded ${
              filter === type
                ? 'bg-blue-600 text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* History Entries */}
      <div className="divide-y divide-slate-700 max-h-[600px] overflow-y-auto">
        {loading ? (
          <div className="px-6 py-12 text-center text-slate-400">
            Loading history...
          </div>
        ) : entries.length === 0 ? (
          <div className="px-6 py-12 text-center text-slate-400">
            No history entries found
          </div>
        ) : (
          entries.map((entry, index) => {
            const Icon = EVENT_ICONS[entry.eventType] || Activity
            const color = EVENT_COLORS[entry.eventType] || 'text-slate-400'

            return (
              <div key={index} className="px-6 py-3 hover:bg-slate-700/50 transition-colors">
                <div className="flex items-start space-x-3">
                  <div className={`p-2 rounded-lg bg-slate-700 ${color}`}>
                    <Icon className="w-4 h-4" />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-white font-medium">{entry.message}</p>
                      <span className="text-slate-400 text-sm whitespace-nowrap ml-4">
                        {formatRelativeTime(entry.timestamp)}
                      </span>
                    </div>

                    <p className="text-slate-400 text-sm">
                      {formatTimestamp(entry.timestamp)}
                    </p>

                    {Object.keys(entry.data).length > 0 && (
                      <div className="mt-2 text-xs text-slate-500 bg-slate-900/50 rounded p-2">
                        {Object.entries(entry.data).map(([key, value]) => (
                          <div key={key}>
                            <span className="text-slate-400">{key}:</span>{' '}
                            <span className="text-slate-300">
                              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
