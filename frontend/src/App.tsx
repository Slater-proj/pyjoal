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
