import { useEffect, useState } from 'react'
import BottomNav from './components/BottomNav'
import DashboardPage from './components/DashboardPage'
import SettingsPage from './components/SettingsPage'
import HistoryPage from './components/HistoryPage'
import Toast from './components/Toast'
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
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-blue-400">JOAL</h1>
              <span className="text-slate-500 text-sm bg-slate-700/50 px-2 py-0.5 rounded">v3.0.0</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 pb-24">
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
    </div>
  )
}

export default App
