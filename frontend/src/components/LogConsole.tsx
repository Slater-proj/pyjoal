import { useEffect, useRef, useState } from 'react'
import { Terminal, X, ChevronDown, Trash2, Pause, Play } from 'lucide-react'
import { useStore } from '../store/useStore'

interface LogEntry {
  timestamp: string
  level: string
  logger: string
  message: string
}

export default function LogConsole() {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const logsEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const { ws } = useStore()

  useEffect(() => {
    // Fetch recent logs on mount
    const fetchRecentLogs = async () => {
      try {
        const response = await fetch('/api/logs/recent?count=100')
        const data = await response.json()
        setLogs(data.logs || [])
      } catch (error) {
        console.error('Failed to fetch recent logs:', error)
      }
    }
    
    if (isOpen) {
      fetchRecentLogs()
    }
  }, [isOpen])

  useEffect(() => {
    if (!ws || isPaused) return

    const handleMessage = (event: MessageEvent) => {
      try {
        const message = JSON.parse(event.data)
        
        if (message.type === 'logs' && message.data) {
          setLogs(prev => {
            const newLogs = [...prev, ...message.data]
            // Keep only last 500 logs
            if (newLogs.length > 500) {
              return newLogs.slice(-500)
            }
            return newLogs
          })
        }
      } catch (error) {
        console.error('Failed to parse log message:', error)
      }
    }

    ws.addEventListener('message', handleMessage)
    return () => ws.removeEventListener('message', handleMessage)
  }, [ws, isPaused])

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, autoScroll])

  const handleScroll = () => {
    if (!containerRef.current) return
    
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50
    setAutoScroll(isAtBottom)
  }

  const clearLogs = () => {
    setLogs([])
  }

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'DEBUG': return 'text-slate-400'
      case 'INFO': return 'text-blue-400'
      case 'WARNING': return 'text-yellow-400'
      case 'ERROR': return 'text-red-400'
      case 'CRITICAL': return 'text-red-600 font-bold'
      default: return 'text-slate-300'
    }
  }

  const getLevelBadgeColor = (level: string) => {
    switch (level) {
      case 'DEBUG': return 'bg-slate-600/50 text-slate-300'
      case 'INFO': return 'bg-blue-600/50 text-blue-300'
      case 'WARNING': return 'bg-yellow-600/50 text-yellow-300'
      case 'ERROR': return 'bg-red-600/50 text-red-300'
      case 'CRITICAL': return 'bg-red-700 text-white'
      default: return 'bg-slate-600/50 text-slate-300'
    }
  }

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 z-50 flex items-center gap-2 px-4 py-3 bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded-lg shadow-lg transition-all"
        title="Open log console"
      >
        <Terminal className="w-5 h-5 text-green-400" />
        <span className="text-white font-medium">Logs</span>
      </button>
    )
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-slate-900 border-t border-slate-700 shadow-2xl"
      style={{ height: '40vh', maxHeight: '600px' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <Terminal className="w-5 h-5 text-green-400" />
          <h3 className="text-white font-semibold">Application Logs</h3>
          <span className="text-xs text-slate-400">({logs.length} entries)</span>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Auto-scroll indicator */}
          {!autoScroll && (
            <button
              onClick={() => {
                setAutoScroll(true)
                logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
              }}
              className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-600/20 text-blue-400 rounded hover:bg-blue-600/30"
              title="Resume auto-scroll"
            >
              <ChevronDown className="w-3 h-3" />
              Auto-scroll
            </button>
          )}
          
          {/* Pause/Resume */}
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={`p-1.5 rounded transition-colors ${
              isPaused 
                ? 'bg-yellow-600/20 text-yellow-400 hover:bg-yellow-600/30' 
                : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
            }`}
            title={isPaused ? 'Resume' : 'Pause'}
          >
            {isPaused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
          </button>
          
          {/* Clear logs */}
          <button
            onClick={clearLogs}
            className="p-1.5 bg-slate-700 text-slate-400 hover:bg-slate-600 rounded transition-colors"
            title="Clear logs"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          
          {/* Close */}
          <button
            onClick={() => setIsOpen(false)}
            className="p-1.5 bg-slate-700 text-slate-400 hover:bg-slate-600 rounded transition-colors"
            title="Close console"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Logs container */}
      <div 
        ref={containerRef}
        onScroll={handleScroll}
        className="overflow-y-auto p-3 font-mono text-xs"
        style={{ height: 'calc(100% - 48px)' }}
      >
        {logs.length === 0 ? (
          <div className="text-center text-slate-500 py-8">
            No logs yet. Logs will appear here in real-time.
          </div>
        ) : (
          <div className="space-y-0.5">
            {logs.map((log, index) => (
              <div key={index} className="flex gap-2 hover:bg-slate-800/50 px-2 py-1 rounded">
                <span className="text-slate-500 flex-shrink-0 w-32">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
                <span className={`flex-shrink-0 w-16 text-center px-1.5 py-0.5 rounded text-xs font-medium ${getLevelBadgeColor(log.level)}`}>
                  {log.level}
                </span>
                <span className={`flex-1 break-all ${getLevelColor(log.level)}`}>
                  {log.message}
                </span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>
    </div>
  )
}
