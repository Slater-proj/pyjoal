import { describe, it, expect, beforeEach, vi } from 'vitest'
import { formatBytes, formatDuration, formatSpeed } from '../utils/format'

describe('Format Utils', () => {
  describe('formatBytes', () => {
    it('should format bytes correctly', () => {
      expect(formatBytes(0)).toBe('0 B')
      expect(formatBytes(1024)).toBe('1.0 KB')
      expect(formatBytes(1024 * 1024)).toBe('1.0 MB')
      expect(formatBytes(1024 * 1024 * 1024)).toBe('1.0 GB')
      expect(formatBytes(1024 * 1024 * 1024 * 1024)).toBe('1.0 TB')
    })

    it('should handle decimal places', () => {
      expect(formatBytes(1536)).toBe('1.5 KB') // 1.5 * 1024
      expect(formatBytes(2.5 * 1024 * 1024)).toBe('2.5 MB')
    })
  })

  describe('formatDuration', () => {
    it('should format seconds correctly', () => {
      expect(formatDuration(30)).toBe('30s')
      expect(formatDuration(90)).toBe('1m 30s')
      expect(formatDuration(3661)).toBe('1h 1m 1s')
      expect(formatDuration(86461)).toBe('1d 1m 1s') // More than 24h
    })

    it('should handle zero duration', () => {
      expect(formatDuration(0)).toBe('0s')
    })
  })

  describe('formatSpeed', () => {
    it('should format speed in KB/s', () => {
      expect(formatSpeed(0)).toBe('0 KB/s')
      expect(formatSpeed(1024)).toBe('1.0 MB/s')
      expect(formatSpeed(50 * 1024)).toBe('50.0 MB/s')
    })

    it('should handle small speeds', () => {
      expect(formatSpeed(500)).toBe('500 KB/s')
      expect(formatSpeed(1.5 * 1024)).toBe('1.5 MB/s')
    })
  })
})