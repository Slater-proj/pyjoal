import { useEffect, useState } from 'react'
import BottomNav from './components/BottomNav'
import Header from './components/Header'
import DashboardPage from './components/DashboardPage'
import SettingsPage from './components/SettingsPage'
import HistoryPage from './components/HistoryPage'
import Toast from './components/Toast'
import LogConsole from './components/LogConsole'
import { useStore } from './store/useStore'

type Page = 'dashboard' | 'settings' | 'history'

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('dashboard')
  const [appVersion, setAppVersion] = useState<string>('dev')
  const { connectWebSocket, fetchConfig, fetchTorrents, fetchStats, fetchClients, toasts, removeToast, loadingStatus } = useStore()

  useEffect(() => {
    // Fetch app version (with auth token)
    const token = (window as any).__PYJOAL_TOKEN__ || ''
    fetch('/api/version', { headers: { 'X-API-Token': token } })
      .then(res => res.json())
      .then(data => setAppVersion(data.version || 'dev'))
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      {/* Header with Health Monitoring */}
      <Header appVersion={appVersion} />

      {/* Main Content - Full width */}
      <main className="flex-1 w-full px-4 sm:px-6 lg:px-8 py-4 pb-20">
          {loadingStatus && (
            <div className="mb-4 px-4 py-3 bg-blue-900/50 border border-blue-500/30 rounded-lg flex items-center gap-3">
              <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
              <span className="text-blue-300 text-sm">
                {loadingStatus === 'loading_torrents' ? 'Loading torrents...' : 'Initializing...'}
              </span>
            </div>
          )}
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
