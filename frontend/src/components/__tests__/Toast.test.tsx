import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Toast from '../Toast'

describe('Toast Component', () => {
  it('should render success toast correctly', () => {
    const mockOnClose = vi.fn()

    render(<Toast type="success" message="Operation successful" onClose={mockOnClose} />)
    
    expect(screen.getByText('Operation successful')).toBeInTheDocument()
    expect(screen.getByRole('button')).toBeInTheDocument() // Close button
  })

  it('should render error toast correctly', () => {
    const mockOnClose = vi.fn()

    render(<Toast type="error" message="Something went wrong" onClose={mockOnClose} />)
    
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    expect(screen.getByRole('button')).toBeInTheDocument() // Close button
  })

  it('should render info toast correctly', () => {
    const mockOnClose = vi.fn()

    render(<Toast type="info" message="Information message" onClose={mockOnClose} />)
    
    expect(screen.getByText('Information message')).toBeInTheDocument()
    expect(screen.getByRole('button')).toBeInTheDocument() // Close button
  })

  it('should auto-close after timeout', async () => {
    vi.useFakeTimers()
    const mockOnClose = vi.fn()

    render(<Toast type="success" message="Auto close test" onClose={mockOnClose} duration={1000} />)
    
    // Fast-forward time
    vi.advanceTimersByTime(1000)
    
    expect(mockOnClose).toHaveBeenCalled()
    vi.useRealTimers()
  })

  it('should close when close button is clicked', () => {
    const mockOnClose = vi.fn()

    render(<Toast type="error" message="Manual close test" onClose={mockOnClose} />)
    
    const closeButton = screen.getByRole('button')
    fireEvent.click(closeButton)
    
    expect(mockOnClose).toHaveBeenCalled()
  })

  it('should display correct icon for each type', () => {
    const mockOnClose = vi.fn()
    
    const { rerender } = render(<Toast type="success" message="Success" onClose={mockOnClose} />)
    expect(document.querySelector('svg')).toBeInTheDocument()
    
    rerender(<Toast type="error" message="Error" onClose={mockOnClose} />)
    expect(document.querySelector('svg')).toBeInTheDocument()
    
    rerender(<Toast type="info" message="Info" onClose={mockOnClose} />)
    expect(document.querySelector('svg')).toBeInTheDocument()
  })
})