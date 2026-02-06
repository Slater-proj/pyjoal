import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import SettingsPage from '../SettingsPage'

// Mock axios
vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}))

// Stable references to prevent infinite re-render loops
const mockFetchClients = vi.fn()
const mockUpdateConfig = vi.fn()
const mockAddToast = vi.fn()
const mockConfig = {
  minUploadRate: 30,
  maxUploadRate: 160,
  simultaneousSeed: 20,
  client: 'qbittorrent-5.1.4.client',
  keepTorrentWithZeroLeechers: true,
  uploadRatioTarget: -1,
  seedingDurationLimit: -1,
  announceInterval: 30,
  announceJitter: 30,
  minStatsUpdateInterval: 3,
  enableSpeedVariation: true,
  speedVariationPercent: 20,
  seedingOnlyMode: true,
  pauseDurationMin: 30,
  pauseDurationMax: 180,
  reducedSpeedDurationMin: 60,
  reducedSpeedDurationMax: 240,
  stateChangeIntervalMin: 2,
  stateChangeIntervalMax: 8,
  reducedSpeedKbps: 5,
}
const mockClients = ['qbittorrent-5.1.4.client', 'transmission-4.0.6.client']

// Mock store with stable references
vi.mock('../../store/useStore', () => ({
  useStore: () => ({
    config: mockConfig,
    clients: mockClients,
    fetchClients: mockFetchClients,
    updateConfig: mockUpdateConfig,
    addToast: mockAddToast,
  }),
}))

describe('SettingsPage', () => {
  it('should render the settings form', () => {
    render(<SettingsPage />)
    expect(screen.getByText('Save Configuration')).toBeInTheDocument()
  })

  it('should display configuration header', () => {
    render(<SettingsPage />)
    expect(screen.getByText('Configuration')).toBeInTheDocument()
  })

  it('should display upload rate settings', () => {
    render(<SettingsPage />)
    expect(screen.getByText('Minimum (KB/s)')).toBeInTheDocument()
    expect(screen.getByText('Maximum (KB/s)')).toBeInTheDocument()
  })

  it('should display simultaneous seed setting', () => {
    render(<SettingsPage />)
    expect(screen.getByText('Simultaneous Seeds')).toBeInTheDocument()
  })

  it('should show upload rate section', () => {
    render(<SettingsPage />)
    expect(screen.getByText('Upload Rate')).toBeInTheDocument()
  })
})
