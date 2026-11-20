import { useEffect, useState } from 'react'
import { getToken } from '../services/api'

interface TestConfig {
  announceInterval?: number
  announceJitter?: number
  minStatsUpdateInterval?: number
  enableSpeedVariation?: boolean
  speedVariationPercent?: number
  [key: string]: any
}

export default function DiscretionTestPanel() {
  const [config, setConfig] = useState<TestConfig | null>(null)
  
  useEffect(() => {
    // Test direct de l'API
    // Token injected by the backend at runtime (never hardcode secrets here)
    fetch('/api/config', {
      headers: {
        'X-API-Token': getToken() || ''
      }
    })
    .then(res => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      return res.json()
    })
    .then((data: TestConfig) => {
      console.log('🧪 Test Config:', data)
      setConfig(data)
    })
    .catch(err => console.error('❌ Config fetch error:', err))
  }, [])

  if (!config) {
    return <div className="p-4 bg-red-900 text-white">Loading config...</div>
  }

  return (
    <div className="fixed top-4 right-4 p-4 bg-yellow-600 text-black z-50 max-w-md">
      <h3 className="font-bold">🧪 DISCRETION TEST</h3>
      <div className="text-xs mt-2">
        <div>announceInterval: {config.announceInterval || 'MISSING'}</div>
        <div>announceJitter: {config.announceJitter || 'MISSING'}</div>
        <div>minStatsUpdateInterval: {config.minStatsUpdateInterval || 'MISSING'}</div>
        <div>enableSpeedVariation: {config.enableSpeedVariation ? 'YES' : 'NO'}</div>
        <div>speedVariationPercent: {config.speedVariationPercent || 'MISSING'}</div>
      </div>
      <button 
        onClick={() => setConfig(null)}
        className="mt-2 px-2 py-1 bg-red-600 text-white text-xs"
      >
        Close
      </button>
    </div>
  )
}