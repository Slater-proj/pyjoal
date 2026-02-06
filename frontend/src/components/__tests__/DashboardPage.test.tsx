import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import DashboardPage from '../DashboardPage'

// Mock dependent components
vi.mock('../ClientInfoPanel', () => ({
  default: () => <div data-testid="client-info-panel">ClientInfoPanel</div>
}))

vi.mock('../TorrentsTableNew', () => ({
  default: () => <div data-testid="torrents-table">TorrentsTable</div>
}))

// Mock react-dropzone
vi.mock('react-dropzone', () => ({
  useDropzone: () => ({
    getRootProps: () => ({}),
    getInputProps: () => ({}),
    isDragActive: false,
  }),
}))

// Mock store
vi.mock('../../store/useStore', () => ({
  useStore: () => ({
    addTorrent: vi.fn(),
  }),
}))

describe('DashboardPage', () => {
  it('should render ClientInfoPanel', () => {
    render(<DashboardPage />)
    expect(screen.getByTestId('client-info-panel')).toBeInTheDocument()
  })

  it('should render TorrentsTable', () => {
    render(<DashboardPage />)
    expect(screen.getByTestId('torrents-table')).toBeInTheDocument()
  })

  it('should render the add torrent button', () => {
    render(<DashboardPage />)
    // The component has a hidden file input for torrent upload
    const fileInput = document.querySelector('input[type="file"]')
    expect(fileInput).toBeInTheDocument()
    expect(fileInput).toHaveAttribute('accept', '.torrent')
  })

  it('should support multiple file selection', () => {
    render(<DashboardPage />)
    const fileInput = document.querySelector('input[type="file"]')
    expect(fileInput).toHaveAttribute('multiple')
  })
})
