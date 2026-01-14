import { Home, Settings, Clock } from 'lucide-react'

interface BottomNavProps {
  currentPage: 'dashboard' | 'settings' | 'history'
  onNavigate: (page: 'dashboard' | 'settings' | 'history') => void
}

export default function BottomNav({ currentPage, onNavigate }: BottomNavProps) {
  const navItems = [
    { id: 'dashboard' as const, label: 'Dashboard', icon: Home },
    { id: 'settings' as const, label: 'Configuration', icon: Settings },
    { id: 'history' as const, label: 'History', icon: Clock },
  ]

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-slate-800 border-t border-slate-700 shadow-2xl z-50">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-3 h-16">
          {navItems.map((item) => {
            const isActive = currentPage === item.id
            return (
              <button
                key={item.id}
                onClick={() => onNavigate(item.id)}
                className={`flex flex-col sm:flex-row items-center justify-center gap-1 sm:gap-3 h-full transition-all ${
                  isActive
                    ? 'text-blue-400 bg-slate-700/50 border-t-2 border-blue-400'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/30 border-t-2 border-transparent'
                }`}
              >
                <item.icon className="w-5 h-5" />
                <span className="text-xs sm:text-sm font-medium">{item.label}</span>
              </button>
            )
          })}
        </div>
      </div>
    </nav>
  )
}
