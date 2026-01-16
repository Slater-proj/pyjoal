import { useEffect, useState } from 'react'
import BottomNav from './components/BottomNav'
import DashboardPage from './components/DashboardPage'
import SettingsPage from './components/SettingsPage'
import HistoryPage from './components/HistoryPage'
import Toast from './components/Toast'
import LogConsole from './components/LogConsole'
import DiscretionTestPanel from './components/DiscretionTestPanel'
import { useStore } from './store/useStore'

type Page = 'dashboard' | 'settings' | 'history'

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('dashboard')
  const [appVersion, setAppVersion] = useState<string>('dev')
  const { connectWebSocket, fetchConfig, fetchTorrents, fetchStats, fetchClients, toasts, removeToast } = useStore()

  useEffect(() => {
    // Fetch app version
    fetch('/api/version')
      .then(res => res.json())
      .then(data => setAppVersion(data.version))
      .catch(() => setAppVersion('dev'))

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
        <div className="w-full px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-blue-400">PyJOAL</h1>
              <span className="text-slate-500 text-xs bg-slate-700/50 px-2 py-1 rounded">v{appVersion}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content - Full width */}
      <main className="flex-1 w-full px-4 sm:px-6 lg:px-8 py-4 pb-20">
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
      {/* Test Panel for Discretion Settings */}
      <DiscretionTestPanel />
      {/* Log Console */}
      <LogConsole />
    </div>
  )
}

export default App
