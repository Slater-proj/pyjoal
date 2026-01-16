import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ClientInfoPanel from '../ClientInfoPanel'
import { useStore } from '../../store/useStore'

// Mock the store
vi.mock('../../store/useStore')

describe('ClientInfoPanel', () => {
  const mockUseStore = useStore as any

  beforeEach(() => {
    mockUseStore.mockReturnValue({
      stats: {
        isRunning: false,
        uploadSpeed: 1024000, // 1 MB/s
        totalUploaded: 1024 * 1024 * 1024 * 5, // 5 GB
        totalTorrents: 10,
        activeTorrents: 3
      },
      config: {
        client: 'qbittorrent-4.6.0.client',
        minUploadRate: 30, // 30 KB/s
        maxUploadRate: 160 // 160 KB/s
      },
      startSeeding: vi.fn(),
      stopSeeding: vi.fn()
    })
  })

  it('should render client name correctly', () => {
    render(<ClientInfoPanel />)
    expect(screen.getByText('qbittorrent 4.6.0')).toBeInTheDocument()
  })

  it('should display upload speed limits correctly', () => {
    render(<ClientInfoPanel />)
    
    // Check for the configuration section header
    expect(screen.getByText('Upload Speed Limits')).toBeInTheDocument()
    
    // Check for min and max speed labels
    expect(screen.getByText('Min')).toBeInTheDocument()
    expect(screen.getByText('Max')).toBeInTheDocument()
    
    // Check for min speed value (30 KB/s)
    expect(screen.getByText('30 KB/s')).toBeInTheDocument()
    
    // Check for max speed value (160 KB/s) 
    expect(screen.getByText('160 KB/s')).toBeInTheDocument()
  })

  it('should display current upload speed', () => {
    render(<ClientInfoPanel />)
    expect(screen.getByText('1 MB/s')).toBeInTheDocument()
  })

  it('should show paused status when not running', () => {
    render(<ClientInfoPanel />)
    expect(screen.getByText('Paused')).toBeInTheDocument()
    expect(screen.getByText('START SEEDING')).toBeInTheDocument()
  })

  it('should show seeding active status when running', () => {
    mockUseStore.mockReturnValue({
      ...mockUseStore(),
      stats: {
        ...mockUseStore().stats,
        isRunning: true
      }
    })

    render(<ClientInfoPanel />)
    expect(screen.getByText('Seeding Active')).toBeInTheDocument()
    expect(screen.getByText('STOP SEEDING')).toBeInTheDocument()
  })

  it('should display torrent counts correctly', () => {
    render(<ClientInfoPanel />)
    
    // Find the table rows and check values
    const totalTorrentsRow = screen.getByText('Total Torrents').closest('tr')
    const activeTorrentsRow = screen.getByText('Active Torrents').closest('tr')
    
    expect(totalTorrentsRow).toHaveTextContent('10')
    expect(activeTorrentsRow).toHaveTextContent('3')
  })

  it('should format total uploaded correctly', () => {
    render(<ClientInfoPanel />)
    expect(screen.getByText('5 GB')).toBeInTheDocument()
  })

  it('should handle missing config gracefully', () => {
    mockUseStore.mockReturnValue({
      ...mockUseStore(),
      config: null
    })

    render(<ClientInfoPanel />)
    
    // Should show default values
    expect(screen.getByText('Unknown Client')).toBeInTheDocument()
    expect(screen.getByText('0 B/s')).toBeInTheDocument() // Min and max should show 0
  })
})