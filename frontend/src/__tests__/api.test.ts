import { describe, it, expect } from 'vitest'
import { api } from '../services/api'

describe('API Service', () => {
  it('should have all required methods', () => {
    // Test that all API methods exist
    expect(api.getConfig).toBeDefined()
    expect(api.updateConfig).toBeDefined()
    expect(api.getClients).toBeDefined()
    expect(api.getTorrents).toBeDefined()
    expect(api.addTorrent).toBeDefined()
    expect(api.uploadTorrent).toBeDefined() // alias
    expect(api.removeTorrent).toBeDefined()
    expect(api.startTorrent).toBeDefined()
    expect(api.stopTorrent).toBeDefined()
    expect(api.start).toBeDefined()
    expect(api.stop).toBeDefined()
    expect(api.getStats).toBeDefined()
  })

  it('should have uploadTorrent as alias for addTorrent', () => {
    expect(api.uploadTorrent).toBe(api.addTorrent)
  })
})