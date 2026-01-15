import { render, screen } from '@testing-library/react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import App from '../App'

// Mock the store
vi.mock('../store/useStore', () => ({
  default: () => ({
    stats: {
      isRunning: false,
      activeTorrents: 0,
      totalTorrents: 0,
      totalUploaded: 0,
      totalDownloaded: 0,
      uploadSpeed: 0,
      startedAt: null,
      uptime: null
    },
    torrents: [],
    config: {
      minUploadRate: 30,
      maxUploadRate: 160,
      simultaneousSeed: 20,
      client: 'qbittorrent-4.6.0.client',
      keepTorrentWithZeroLeechers: true,
      uploadRatioTarget: -1.0,
      seedingDurationLimit: -1.0
    },
    history: [],
    connected: false,
    fetchStats: vi.fn(),
    fetchTorrents: vi.fn(),
    fetchConfig: vi.fn(),
    fetchHistory: vi.fn(),
    updateConfig: vi.fn(),
    start: vi.fn(),
    stop: vi.fn(),
    addTorrent: vi.fn(),
    removeTorrent: vi.fn(),
    startTorrent: vi.fn(),
    stopTorrent: vi.fn(),
    connectWebSocket: vi.fn(),
    setShowSettings: vi.fn(),
    setShowLogs: vi.fn(),
    showSettings: false,
    showLogs: false
  })
}))

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders PyJOAL title', () => {
    render(<App />)
    expect(screen.getByText('PyJOAL')).toBeInTheDocument()
  })

  it('renders dashboard page by default', () => {
    render(<App />)
    expect(screen.getByText('PyJOAL')).toBeInTheDocument()
    // Should see some dashboard elements like stats or controls
  })

  it('has correct layout structure', () => {
    render(<App />)
    const appContainer = document.querySelector('.min-h-screen')
    expect(appContainer).toBeInTheDocument()
  })
})