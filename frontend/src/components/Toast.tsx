import { useEffect, useRef } from 'react'
import { CheckCircle, XCircle, AlertCircle, X } from 'lucide-react'

interface ToastProps {
  message: string
  type: 'success' | 'error' | 'info'
  onClose: () => void
  duration?: number
}

export default function Toast({ message, type, onClose, duration = 3000 }: ToastProps) {
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose

  useEffect(() => {
    const timer = setTimeout(() => {
      onCloseRef.current()
    }, duration)
    return () => clearTimeout(timer)
  }, [duration])

  const icons = {
    success: <CheckCircle className="w-5 h-5 text-green-400" />,
    error: <XCircle className="w-5 h-5 text-red-400" />,
    info: <AlertCircle className="w-5 h-5 text-blue-400" />
  }

  const colors = {
    success: 'bg-green-500/10 border-green-500/50',
    error: 'bg-red-500/10 border-red-500/50',
    info: 'bg-blue-500/10 border-blue-500/50'
  }

  return (
    <div className={`fixed top-20 right-4 z-50 animate-slide-in-right`}>
      <div className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${colors[type]} bg-slate-800 shadow-xl min-w-[300px] max-w-[500px]`}>
        {icons[type]}
        <p className="flex-1 text-white text-sm font-medium">{message}</p>
        <button 
          onClick={onClose}
          className="text-slate-400 hover:text-white transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
