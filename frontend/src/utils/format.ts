/**
 * Utility functions for formatting values
 */

export function formatBytes(bytesValue: number): string {
  if (bytesValue === 0) {
    return "0 B"
  }
  
  const units = ["B", "KB", "MB", "GB", "TB"]
  let unitIndex = 0
  let size = bytesValue
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex += 1
  }
  
  if (unitIndex === 0) {
    return `${Math.floor(size)} ${units[unitIndex]}`
  } else {
    return `${size.toFixed(1)} ${units[unitIndex]}`
  }
}

export function formatSpeed(speedKbps: number): string {
  if (speedKbps < 1024) {
    return `${Math.floor(speedKbps)} KB/s`
  } else {
    const speedMbps = speedKbps / 1024
    return `${speedMbps.toFixed(1)} MB/s`
  }
}

export function formatDuration(seconds: number): string {
  if (seconds === 0) {
    return "0s"
  }
  
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  
  const parts: string[] = []
  if (days > 0) {
    parts.push(`${days}d`)
  }
  if (hours > 0) {
    parts.push(`${hours}h`)
  }
  if (minutes > 0) {
    parts.push(`${minutes}m`)
  }
  if (secs > 0 || parts.length === 0) {
    parts.push(`${secs}s`)
  }
  
  return parts.join(" ")
}

export function formatRatio(uploaded: number, downloaded: number): string {
  if (downloaded === 0) {
    if (uploaded > 0) {
      return "∞"
    }
    return "0.00"
  }
  
  const ratio = uploaded / downloaded
  return ratio.toFixed(2)
}

export function formatPercentage(value: number): string {
  return `${value.toFixed(1)}%`
}