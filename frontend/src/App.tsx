import { useEffect, useState } from 'react'
import BottomNav from './components/BottomNav'
import DashboardPage from './components/DashboardPage'
import SettingsPage from './components/SettingsPage'
import HistoryPage from './components/HistoryPage'
import Toast from './components/Toast'
import LogConsole from './components/LogConsole'
import { useStore } from './store/useStore'

type Page = 'dashboard' | 'settings' | 'history'

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('dashboard')
  const { connectWebSocket, fetchConfig, fetchTorrents, fetchStats, fetchClients, toasts, removeToast } = useStore()

  useEffect(() => {
    // Initial data fetch
    fetchConfig()
    fetchTorrents()
    fetchStats()
    fetchClients()

    // Connect WebSocket for real-time updates
    connectWebSocket()

    // Cleanup on unmount
    return () => {
      useStore.getState().disconnectWebSocket()
    }
  }, [])

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <DashboardPage />
      case 'settings':
        return <SettingsPage />
      case 'history':
        return <HistoryPage />
      default:
        return <DashboardPage />
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white flex flex-col">
      {/* Header - Compact */}
      <header className="bg-slate-800 border-b border-slate-700 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-blue-400">PyJOAL</h1>
              <span className="text-slate-500 text-xs bg-slate-700/50 px-2 py-1 rounded">v1.0.0</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content - Optimized spacing */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-4 pb-20">
        {renderPage()}
      </main>

      {/* Bottom Navigation */}
      <BottomNav currentPage={currentPage} onNavigate={setCurrentPage} />

      {/* Toast Notifications */}
      <div className="fixed top-20 right-4 z-50 space-y-2">
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            message={toast.message}
            type={toast.type}
            onClose={() => removeToast(toast.id)}
          />
        ))}
      </div>

      {/* Log Console */}
      <LogConsole />
    </div>
  )
}

export default App
