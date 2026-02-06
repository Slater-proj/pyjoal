import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import BottomNav from '../BottomNav'

describe('BottomNav', () => {
  it('should render all navigation items', () => {
    const mockOnNavigate = vi.fn()
    render(<BottomNav currentPage="dashboard" onNavigate={mockOnNavigate} />)
    
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Configuration')).toBeInTheDocument() // Correct text
    expect(screen.getByText('History')).toBeInTheDocument()
  })

  it('should highlight the current page', () => {
    const mockOnNavigate = vi.fn()
    render(<BottomNav currentPage="settings" onNavigate={mockOnNavigate} />)
    
    const settingsButton = screen.getByText('Configuration').closest('button')
    expect(settingsButton).toHaveClass('text-blue-400') // Active state
  })

  it('should call onNavigate when navigation item is clicked', () => {
    const mockOnNavigate = vi.fn()
    render(<BottomNav currentPage="dashboard" onNavigate={mockOnNavigate} />)
    
    fireEvent.click(screen.getByText('History'))
    expect(mockOnNavigate).toHaveBeenCalledWith('history')
  })

  it('should render SVG icons for each page', () => {
    const mockOnNavigate = vi.fn()
    render(<BottomNav currentPage="dashboard" onNavigate={mockOnNavigate} />)
    
    // Check that SVG elements are present
    const svgElements = document.querySelectorAll('svg')
    expect(svgElements).toHaveLength(3) // Dashboard, Settings, History icons
  })
})