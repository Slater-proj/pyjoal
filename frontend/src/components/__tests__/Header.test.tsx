import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import Header from '../Header'

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

// Mock store
vi.mock('../../store/useStore', () => ({
  useStore: () => ({
    connected: true
  })
}))

describe('Header', () => {
  beforeEach(() => {
    mockFetch.mockClear()
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  it('should render header with app version', () => {
    render(<Header appVersion="1.7.4" />)
    
    expect(screen.getByText('PyJOAL')).toBeInTheDocument()
    expect(screen.getByText('v1.7.4')).toBeInTheDocument()
  })

  it('should show Live status when connected', () => {
    render(<Header appVersion="1.7.4" />)
    
    expect(screen.getByText('Live')).toBeInTheDocument()
    // The text-green-400 class is on the parent div, not the span
    expect(screen.getByText('Live').closest('div')).toHaveClass('text-green-400')
  })

  it('should show Health badge', () => {
    render(<Header appVersion="1.7.4" />)
    
    expect(screen.getByText('Health')).toBeInTheDocument()
  })

  it('should show Live tooltip on hover', async () => {
    render(<Header appVersion="1.7.4" />)
    
    const liveElement = screen.getByText('Live').closest('div')
    fireEvent.mouseEnter(liveElement!)
    
    await waitFor(() => {
      expect(screen.getByText('WebSocket Connection')).toBeInTheDocument()
      expect(screen.getByText('• Auto-updating logs')).toBeInTheDocument()
      expect(screen.getByText('• Real-time statistics')).toBeInTheDocument()
    })
  })

  it('should show Health tooltip on hover', async () => {
    // Mock health API responses
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ icon: '🟢' })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          overall_status: 'healthy',
          checks: {
            memory: { status: 'ok', value: '512 MB' },
            uptime: { status: 'ok', value: '2h 15m' }
          },
          timestamp: new Date().toISOString()
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          current_version: '1.7.4',
          latest_version: 'unknown',
          update_available: false,
          is_dev_version: true
        })
      })

    render(<Header appVersion="1.7.4" />)
    
    // Wait for health data to load
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/system/health/status')
    })

    const healthElement = screen.getByText('Health').closest('div')
    fireEvent.mouseEnter(healthElement!)
    
    await waitFor(() => {
      expect(screen.getByText('System Health')).toBeInTheDocument()
    })
  })

  it('should show version info in health tooltip', async () => {
    // Mock health and version APIs
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ icon: '🟢' })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          overall_status: 'healthy',
          checks: {
            memory: { status: 'ok', value: '512 MB' }
          },
          timestamp: new Date().toISOString()
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          current_version: '1.7.4',
          latest_version: 'unknown',
          update_available: false,
          is_dev_version: true
        })
      })

    render(<Header appVersion="1.7.4" />)
    
    // Wait for APIs to be called
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/system/version/check')
    })

    const healthElement = screen.getByText('Health').closest('div')
    fireEvent.mouseEnter(healthElement!)
    
    await waitFor(() => {
      expect(screen.getByText('📦 Version:')).toBeInTheDocument()
      expect(screen.getByText('🚀 Development version')).toBeInTheDocument()
    })
  })

  it('should show update available notification', async () => {
    // Mock APIs with update available
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ icon: '🟢' })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          overall_status: 'healthy',
          checks: {},
          timestamp: new Date().toISOString()
        })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          current_version: '1.7.4',
          latest_version: '1.7.5',
          update_available: true,
          release_url: 'https://github.com/repo/releases/tag/v1.7.5'
        })
      })

    render(<Header appVersion="1.7.4" />)
    
    // Wait for APIs
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(3)
    })

    const healthElement = screen.getByText('Health').closest('div')
    fireEvent.mouseEnter(healthElement!)
    
    await waitFor(() => {
      expect(screen.getByText('Update available: 1.7.5')).toBeInTheDocument()
      expect(screen.getByText('View release notes →')).toBeInTheDocument()
    })
  })

  it('should handle API errors gracefully', async () => {
    // Mock API errors
    mockFetch
      .mockRejectedValueOnce(new Error('Network error'))
      .mockRejectedValueOnce(new Error('Network error'))
      .mockRejectedValueOnce(new Error('Network error'))

    render(<Header appVersion="1.7.4" />)
    
    // Should not crash and should show default health status
    await waitFor(() => {
      expect(screen.getByText('Health')).toBeInTheDocument()
    })
  })

  it('should have proper responsive classes', () => {
    render(<Header appVersion="1.7.4" />)
    
    const header = screen.getByRole('banner')
    const headerContent = header.firstChild as HTMLElement
    
    expect(headerContent).toHaveClass('w-full', 'px-4', 'sm:px-6', 'lg:px-8')
  })
})