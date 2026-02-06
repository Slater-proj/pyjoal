import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useStore } from '../../store/useStore'
import { act } from '@testing-library/react'

// Mock the API module
vi.mock('../../services/api', () => ({
  api: {
    getConfig: vi.fn(),
    updateConfig: vi.fn(),
    getClients: vi.fn(),
    getTorrents: vi.fn(),
    getStats: vi.fn(),
    addTorrent: vi.fn(),
    removeTorrent: vi.fn(),
    reloadTorrents: vi.fn(),
    start: vi.fn(),
    stop: vi.fn(),
    uploadTorrent: vi.fn(),
    startTorrent: vi.fn(),
    stopTorrent: vi.fn(),
  },
  getToken: vi.fn(() => null),
}))

describe('useStore', () => {
  beforeEach(() => {
    // Reset store state between tests
    const store = useStore.getState()
    useStore.setState({
      config: null,
      torrents: [],
      stats: null,
      clients: [],
      ws: null,
      connected: false,
      toasts: [],
    })
  })

  describe('initial state', () => {
    it('should have null config initially', () => {
      expect(useStore.getState().config).toBeNull()
    })

    it('should have empty torrents array', () => {
      expect(useStore.getState().torrents).toEqual([])
    })

    it('should have null stats initially', () => {
      expect(useStore.getState().stats).toBeNull()
    })

    it('should have empty clients array', () => {
      expect(useStore.getState().clients).toEqual([])
    })

    it('should not be connected initially', () => {
      expect(useStore.getState().connected).toBe(false)
    })

    it('should have empty toasts array', () => {
      expect(useStore.getState().toasts).toEqual([])
    })
  })

  describe('setters', () => {
    it('should set config', () => {
      const config = {
        minUploadRate: 30,
        maxUploadRate: 160,
        simultaneousSeed: 20,
        client: 'qbittorrent-5.1.4.client',
        keepTorrentWithZeroLeechers: true,
        uploadRatioTarget: -1,
        seedingDurationLimit: -1,
        announceInterval: 30,
        announceJitter: 30,
        minStatsUpdateInterval: 3,
        enableSpeedVariation: true,
        speedVariationPercent: 20,
        seedingOnlyMode: true,
      }
      act(() => {
        useStore.getState().setConfig(config)
      })
      expect(useStore.getState().config).toEqual(config)
    })

    it('should set torrents', () => {
      const torrents = [
        { id: '1', name: 'test.torrent', size: 1024, uploaded: 0, uploadSpeed: 0, ratio: 0, seeders: 0, leechers: 0, state: 'idle', addedAt: '', lastAnnounce: null, nextAnnounce: null, tracker: null, seedingTime: 0 },
      ]
      act(() => {
        useStore.getState().setTorrents(torrents)
      })
      expect(useStore.getState().torrents).toEqual(torrents)
    })

    it('should set stats', () => {
      const stats = {
        totalUploaded: 5000,
        totalRatio: 1.5,
        activeTorrents: 3,
        avgUploadSpeed: 100,
        isRunning: true,
        totalTorrents: 10,
        totalDownloaded: 3333,
        uploadSpeed: 150,
        startedAt: null,
        uptime: null,
      }
      act(() => {
        useStore.getState().setStats(stats)
      })
      expect(useStore.getState().stats).toEqual(stats)
    })

    it('should set clients', () => {
      const clients = ['qbittorrent-5.1.4.client', 'transmission-4.0.6.client']
      act(() => {
        useStore.getState().setClients(clients)
      })
      expect(useStore.getState().clients).toEqual(clients)
    })
  })

  describe('toast management', () => {
    it('should add a toast notification', () => {
      act(() => {
        useStore.getState().addToast('Test message', 'success')
      })
      const toasts = useStore.getState().toasts
      expect(toasts).toHaveLength(1)
      expect(toasts[0].message).toBe('Test message')
      expect(toasts[0].type).toBe('success')
      expect(toasts[0].id).toBeDefined()
    })

    it('should add multiple toasts', () => {
      act(() => {
        useStore.getState().addToast('First', 'success')
        useStore.getState().addToast('Second', 'error')
        useStore.getState().addToast('Third', 'info')
      })
      expect(useStore.getState().toasts).toHaveLength(3)
    })

    it('should remove a toast by id', () => {
      act(() => {
        useStore.getState().addToast('To remove', 'info')
      })
      const toastId = useStore.getState().toasts[0].id
      act(() => {
        useStore.getState().removeToast(toastId)
      })
      expect(useStore.getState().toasts).toHaveLength(0)
    })

    it('should only remove the targeted toast', () => {
      act(() => {
        useStore.getState().addToast('Keep me', 'success')
        useStore.getState().addToast('Remove me', 'error')
      })
      const removeId = useStore.getState().toasts[1].id
      act(() => {
        useStore.getState().removeToast(removeId)
      })
      const remaining = useStore.getState().toasts
      expect(remaining).toHaveLength(1)
      expect(remaining[0].message).toBe('Keep me')
    })
  })

  describe('API actions', () => {
    it('should fetch config and update store', async () => {
      const { api } = await import('../../services/api')
      const mockConfig = {
        minUploadRate: 50,
        maxUploadRate: 200,
        simultaneousSeed: 10,
        client: 'transmission-4.0.6.client',
        keepTorrentWithZeroLeechers: false,
        uploadRatioTarget: 2.0,
        seedingDurationLimit: 3600,
        announceInterval: 45,
        announceJitter: 15,
        minStatsUpdateInterval: 5,
        enableSpeedVariation: false,
        speedVariationPercent: 10,
        seedingOnlyMode: false,
      }
      vi.mocked(api.getConfig).mockResolvedValueOnce(mockConfig)

      await act(async () => {
        await useStore.getState().fetchConfig()
      })
      expect(useStore.getState().config).toEqual(mockConfig)
    })

    it('should handle fetch config error gracefully', async () => {
      const { api } = await import('../../services/api')
      vi.mocked(api.getConfig).mockRejectedValueOnce(new Error('Network error'))
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      await act(async () => {
        await useStore.getState().fetchConfig()
      })
      expect(useStore.getState().config).toBeNull()
      consoleSpy.mockRestore()
    })

    it('should fetch stats and update store', async () => {
      const { api } = await import('../../services/api')
      const mockStats = {
        totalUploaded: 10000,
        totalRatio: 2.0,
        activeTorrents: 5,
        avgUploadSpeed: 200,
        isRunning: true,
        totalTorrents: 15,
        totalDownloaded: 5000,
        uploadSpeed: 250,
        startedAt: '2024-01-01T00:00:00Z',
        uptime: 3600,
      }
      vi.mocked(api.getStats).mockResolvedValueOnce(mockStats)

      await act(async () => {
        await useStore.getState().fetchStats()
      })
      expect(useStore.getState().stats).toEqual(mockStats)
    })

    it('should fetch torrents and update store', async () => {
      const { api } = await import('../../services/api')
      const mockTorrents = [
        { id: 'abc', name: 'Test', size: 1024, uploaded: 512, uploadSpeed: 50, ratio: 0.5, seeders: 10, leechers: 5, state: 'seeding', addedAt: '', lastAnnounce: null, nextAnnounce: null, tracker: 'http://tracker.test', seedingTime: 100 },
      ]
      vi.mocked(api.getTorrents).mockResolvedValueOnce(mockTorrents)

      await act(async () => {
        await useStore.getState().fetchTorrents()
      })
      expect(useStore.getState().torrents).toEqual(mockTorrents)
    })
  })
})
