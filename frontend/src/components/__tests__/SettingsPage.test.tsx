import { describe, it, expect, vi, beforeEach } from 'vitest'
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

// Mock store
vi.mock('../../store/useStore', () => ({
  useStore: () => ({
    config: {
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
    },
    clients: ['qbittorrent-5.1.4.client', 'transmission-4.0.6.client'],
    fetchClients: vi.fn(),
    updateConfig: vi.fn(),
    addToast: vi.fn(),
  }),
}))

describe('SettingsPage', () => {
  it('should render the settings form', () => {
    render(<SettingsPage />)
    expect(screen.getByText('Save Configuration')).toBeInTheDocument()
  })

  it('should display client selector', () => {
    render(<SettingsPage />)
    expect(screen.getByText('Client')).toBeInTheDocument()
  })

  it('should display upload rate settings', () => {
    render(<SettingsPage />)
    expect(screen.getByText('Min Upload Rate (KB/s)')).toBeInTheDocument()
    expect(screen.getByText('Max Upload Rate (KB/s)')).toBeInTheDocument()
  })

  it('should display simultaneous seed setting', () => {
    render(<SettingsPage />)
    expect(screen.getByText('Simultaneous Seeds')).toBeInTheDocument()
  })

  it('should show discretion settings section', () => {
    render(<SettingsPage />)
    expect(screen.getByText('Discretion Settings')).toBeInTheDocument()
  })
})
