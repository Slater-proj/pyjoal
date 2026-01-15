import { useEffect, useRef, useState, useCallback } from 'react'
import { Terminal, X, ChevronDown, Trash2, Pause, Play, GripHorizontal } from 'lucide-react'
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
  const [height, setHeight] = useState(256) // hauteur initiale en pixels
  const [isResizing, setIsResizing] = useState(false)
  const logsEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const { ws } = useStore()

  // Gestion du redimensionnement
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
  }, [])

  useEffect(() => {
    if (!isResizing) return

    const handleMouseMove = (e: MouseEvent) => {
      const newHeight = window.innerHeight - e.clientY
      // Limiter entre 150px et 80% de la hauteur de l'écran
      const clampedHeight = Math.min(Math.max(newHeight, 150), window.innerHeight * 0.8)
      setHeight(clampedHeight)
    }

    const handleMouseUp = () => {
      setIsResizing(false)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    
    // Empêcher la sélection de texte pendant le resize
    document.body.style.userSelect = 'none'
    document.body.style.cursor = 'ns-resize'

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.userSelect = ''
      document.body.style.cursor = ''
    }
  }, [isResizing])

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
    // Scroll automatiquement UNIQUEMENT si l'utilisateur est déjà en bas
    if (autoScroll && containerRef.current) {
      const { scrollHeight } = containerRef.current
      containerRef.current.scrollTop = scrollHeight
    }
  }, [logs, autoScroll])

  const handleScroll = () => {
    if (!containerRef.current) return
    
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current
    // Considérer qu'on est en bas si on est à moins de 100px du bas
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 100
    
    // Mettre à jour l'état auto-scroll seulement si ça change
    if (isAtBottom !== autoScroll) {
      setAutoScroll(isAtBottom)
    }
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
    <div className="fixed bottom-0 left-0 right-0 h-64 z-50 bg-slate-900 border-t border-slate-700 shadow-2xl flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800 border-b border-slate-700 flex-shrink-0">
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
                if (containerRef.current) {
                  containerRef.current.scrollTop = containerRef.current.scrollHeight
                }
                setAutoScroll(true)
              }}
              className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-600/20 text-blue-400 rounded hover:bg-blue-600/30"
              title="Scroll to bottom"
            >
              <ChevronDown className="w-3 h-3" />
              Bas
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
        className="flex-1 overflow-y-scroll p-2 font-mono text-xs"
      >
        {logs.length === 0 ? (
          <div className="text-center text-slate-500 py-8">
            No logs yet. Logs will appear here in real-time.
          </div>
        ) : (
          <div className="space-y-0">
            {logs.map((log, index) => (
              <div key={index} className="flex gap-2 hover:bg-slate-800/50 px-1.5 py-0.5 rounded text-xs">
                <span className="text-slate-500 flex-shrink-0 w-20">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
                <span className={`flex-shrink-0 w-14 text-center px-1 py-0 rounded font-medium ${getLevelBadgeColor(log.level)}`}>
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
