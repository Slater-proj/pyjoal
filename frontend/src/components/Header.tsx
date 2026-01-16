import { Play, Pause, Activity } from 'lucide-react'
import { useStore } from '../store/useStore'
import HealthBadge from './HealthBadge'

export default function Header() {
  const { stats, startSeeding, stopSeeding, connected } = useStore()
  const isRunning = stats?.isRunning || false

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

  return (
    <header className="bg-slate-800 border-b border-slate-700 shadow-lg">
      <div className="container mx-auto px-4 py-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-3xl font-bold text-blue-400">JOAL</h1>
            <span className="text-slate-500 text-sm bg-slate-700 px-2 py-0.5 rounded">v3.0.0</span>
            <div className={`flex items-center space-x-2 text-sm ${connected ? 'text-green-400' : 'text-slate-500'}`}>
              <Activity className={`w-4 h-4 ${connected ? 'animate-pulse' : ''}`} />
              <span>{connected ? 'Live' : 'Offline'}</span>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <HealthBadge />
            <button
              onClick={handleToggle}
              className={`
                flex items-center space-x-2 px-6 py-3 rounded-lg font-semibold
                transition-all duration-200 transform hover:scale-105
                ${isRunning 
                  ? 'bg-red-600 hover:bg-red-700 text-white' 
                  : 'bg-green-600 hover:bg-green-700 text-white'}
              `}
            >
            {isRunning ? (
              <>
                <Pause className="w-5 h-5" />
                <span>Stop Seeding</span>
              </>
            ) : (
              <>
                <Play className="w-5 h-5" />
                <span>Start Seeding</span>
              </>
            )}
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
