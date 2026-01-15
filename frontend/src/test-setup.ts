import '@testing-library/jest-dom'

// Mock window object for tests
Object.defineProperty(window, '__PYJOAL_TOKEN__', {
  value: 'test-token',
  writable: true,
})