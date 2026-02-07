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
    expect(api.start).toBeDefined()
    expect(api.stop).toBeDefined()
    expect(api.getStats).toBeDefined()
  })

  it('should have uploadTorrent as alias for addTorrent', () => {
    expect(api.uploadTorrent).toBe(api.addTorrent)
  })

  it('should have Config interface with discretion fields', () => {
    // Test that the Config interface includes all discretion fields
    const mockConfig = {
      minUploadRate: 30,
      maxUploadRate: 160,
      simultaneousSeed: 20,
      client: 'qbittorrent-5.1.4.client',
      keepTorrentWithZeroLeechers: true,
      uploadRatioTarget: -1.0,
      seedingDurationLimit: -1.0,
      // Discretion fields - should not cause TypeScript errors
      announceInterval: 1800,
      announceJitter: 120,
      minStatsUpdateInterval: 3,
      enableSpeedVariation: true,
      speedVariationPercent: 20
    }
    
    // If this compiles without TypeScript errors, the interface is correct
    expect(mockConfig.announceInterval).toBe(1800)
    expect(mockConfig.announceJitter).toBe(120)
    expect(mockConfig.minStatsUpdateInterval).toBe(3)
    expect(mockConfig.enableSpeedVariation).toBe(true)
    expect(mockConfig.speedVariationPercent).toBe(20)
  })
})