import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import BottomNav from '../BottomNav'

describe('BottomNav', () => {
  it('should render all navigation items', () => {
    const mockSetCurrentPage = vi.fn()
    render(<BottomNav currentPage="dashboard" setCurrentPage={mockSetCurrentPage} />)
    
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
    expect(screen.getByText('History')).toBeInTheDocument()
  })

  it('should highlight the current page', () => {
    const mockSetCurrentPage = vi.fn()
    render(<BottomNav currentPage="settings" setCurrentPage={mockSetCurrentPage} />)
    
    const settingsButton = screen.getByText('Settings').closest('button')
    expect(settingsButton).toHaveClass('text-blue-400') // Active state
  })

  it('should call setCurrentPage when navigation item is clicked', () => {
    const mockSetCurrentPage = vi.fn()
    render(<BottomNav currentPage="dashboard" setCurrentPage={mockSetCurrentPage} />)
    
    fireEvent.click(screen.getByText('History'))
    expect(mockSetCurrentPage).toHaveBeenCalledWith('history')
  })

  it('should render correct icons for each page', () => {
    const mockSetCurrentPage = vi.fn()
    render(<BottomNav currentPage="dashboard" setCurrentPage={mockSetCurrentPage} />)
    
    // Check that SVG icons are present (assuming they're rendered as svg elements)
    const svgElements = screen.getAllByRole('img', { hidden: true })
    expect(svgElements).toHaveLength(3) // Dashboard, Settings, History icons
  })
})