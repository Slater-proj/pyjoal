import '@testing-library/jest-dom'

// Mock window.WebSocket
global.WebSocket = class MockWebSocket {
  constructor(url: string) {
    this.url = url
  }
  
  url: string
  onopen?: () => void
  onclose?: () => void
  onmessage?: (event: { data: string }) => void
  onerror?: () => void
  
  send = jest.fn()
  close = jest.fn()
} as any

// Mock window.__PYJOAL_TOKEN__
Object.defineProperty(window, '__PYJOAL_TOKEN__', {
  value: 'test-token',
  writable: true
})