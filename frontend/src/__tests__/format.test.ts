import { describe, it, expect } from 'vitest'
import { formatBytes, formatSpeed, formatDuration, formatRatio, formatPercentage } from '../utils/format'

describe('formatBytes', () => {
  it('should return "0 B" for zero', () => {
    expect(formatBytes(0)).toBe('0 B')
  })

  it('should format bytes', () => {
    expect(formatBytes(500)).toBe('500 B')
  })

  it('should format kilobytes', () => {
    expect(formatBytes(1024)).toBe('1.0 KB')
    expect(formatBytes(1536)).toBe('1.5 KB')
  })

  it('should format megabytes', () => {
    expect(formatBytes(1048576)).toBe('1.0 MB')
    expect(formatBytes(5 * 1048576)).toBe('5.0 MB')
  })

  it('should format gigabytes', () => {
    expect(formatBytes(1073741824)).toBe('1.0 GB')
    expect(formatBytes(5 * 1073741824)).toBe('5.0 GB')
  })

  it('should format terabytes', () => {
    expect(formatBytes(1099511627776)).toBe('1.0 TB')
  })
})

describe('formatSpeed', () => {
  it('should format KB/s for small speeds', () => {
    expect(formatSpeed(100)).toBe('100 KB/s')
    expect(formatSpeed(512)).toBe('512 KB/s')
  })

  it('should format MB/s for large speeds', () => {
    expect(formatSpeed(1024)).toBe('1.0 MB/s')
    expect(formatSpeed(2048)).toBe('2.0 MB/s')
  })

  it('should handle zero speed', () => {
    expect(formatSpeed(0)).toBe('0 KB/s')
  })
})

describe('formatDuration', () => {
  it('should return "0s" for zero', () => {
    expect(formatDuration(0)).toBe('0s')
  })

  it('should format seconds only', () => {
    expect(formatDuration(45)).toBe('45s')
  })

  it('should format minutes and seconds', () => {
    expect(formatDuration(125)).toBe('2m 5s')
  })

  it('should format hours, minutes, seconds', () => {
    expect(formatDuration(3661)).toBe('1h 1m 1s')
  })

  it('should format days', () => {
    expect(formatDuration(86400)).toBe('1d')
    expect(formatDuration(90061)).toBe('1d 1h 1m 1s')
  })

  it('should omit zero-value units', () => {
    expect(formatDuration(3600)).toBe('1h')
    expect(formatDuration(60)).toBe('1m')
  })
})

describe('formatRatio', () => {
  it('should return "0.00" when both are zero', () => {
    expect(formatRatio(0, 0)).toBe('0.00')
  })

  it('should return infinity symbol when downloaded is zero but uploaded > 0', () => {
    expect(formatRatio(1000, 0)).toBe('∞')
  })

  it('should calculate ratio correctly', () => {
    expect(formatRatio(2000, 1000)).toBe('2.00')
    expect(formatRatio(1500, 1000)).toBe('1.50')
  })

  it('should handle fractional ratios', () => {
    expect(formatRatio(500, 1000)).toBe('0.50')
  })
})

describe('formatPercentage', () => {
  it('should format percentage with one decimal', () => {
    expect(formatPercentage(50)).toBe('50.0%')
    expect(formatPercentage(99.9)).toBe('99.9%')
    expect(formatPercentage(0)).toBe('0.0%')
  })
})
