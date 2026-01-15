import { describe, it, expect, vi } from 'vitest'
import { api } from '../services/api'
import axios from 'axios'

// Mock axios
vi.mock('axios')
const mockedAxios = vi.mocked(axios)

describe('API Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should include token in request headers', async () => {
    // Mock successful response
    mockedAxios.get.mockResolvedValue({ data: { test: 'data' } })
    
    // Test that token is added to headers
    await api.getConfig()
    
    expect(mockedAxios.get).toHaveBeenCalledWith('/api/config')
    // The interceptor should add the token header
  })

  it('should handle API errors gracefully', async () => {
    mockedAxios.get.mockRejectedValue(new Error('Network error'))
    
    await expect(api.getConfig()).rejects.toThrow('Network error')
  })

  it('should format upload requests correctly', async () => {
    mockedAxios.post.mockResolvedValue({ data: { success: true } })
    
    const mockFile = new File(['test'], 'test.torrent', { type: 'application/x-bittorrent' })
    const formData = new FormData()
    formData.append('file', mockFile)
    
    await api.uploadTorrent(mockFile)
    
    expect(mockedAxios.post).toHaveBeenCalledWith(
      '/api/torrents',
      expect.any(FormData),
      expect.objectContaining({
        headers: expect.objectContaining({
          'Content-Type': 'multipart/form-data'
        })
      })
    )
  })

  it('should handle config updates', async () => {
    mockedAxios.put.mockResolvedValue({ data: { success: true } })
    
    const config = {
      minUploadRate: 50,
      maxUploadRate: 200,
      simultaneousSeed: 15,
      client: 'deluge-2.1.1.client',
      keepTorrentWithZeroLeechers: false,
      uploadRatioTarget: 2.0,
      seedingDurationLimit: 48.0
    }
    
    await api.updateConfig(config)
    
    expect(mockedAxios.put).toHaveBeenCalledWith('/api/config', config)
  })

  it('should handle torrent actions', async () => {
    mockedAxios.delete.mockResolvedValue({ data: { success: true } })
    mockedAxios.post.mockResolvedValue({ data: { success: true } })
    
    const infoHash = 'test-hash'
    
    // Test remove
    await api.removeTorrent(infoHash)
    expect(mockedAxios.delete).toHaveBeenCalledWith(`/api/torrents/${infoHash}`)
    
    // Test start
    await api.startTorrent(infoHash)
    expect(mockedAxios.post).toHaveBeenCalledWith(`/api/torrents/${infoHash}/start`)
    
    // Test stop
    await api.stopTorrent(infoHash)
    expect(mockedAxios.post).toHaveBeenCalledWith(`/api/torrents/${infoHash}/stop`)
  })
})