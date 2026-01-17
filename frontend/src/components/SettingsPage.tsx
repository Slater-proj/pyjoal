import { useState, useEffect } from 'react'
import { Save, RefreshCw, HelpCircle } from 'lucide-react'
import { useStore } from '../store/useStore'
import axios from 'axios'

// FormData type - ratio and duration can be string or number during editing
interface FormDataType {
  minUploadRate: number
  maxUploadRate: number
  simultaneousSeed: number
  client: string
  keepTorrentWithZeroLeechers: boolean
  uploadRatioTarget: number | string
  seedingDurationLimit: number | string
  announceInterval: number | string
  announceJitter: number | string
  minStatsUpdateInterval: number | string
  enableSpeedVariation: boolean
  speedVariationPercent: number | string
  seedingOnlyMode: boolean
  // Realistic Behavior Timing
  pauseDurationMin: number | string
  pauseDurationMax: number | string
  reducedSpeedDurationMin: number | string
  reducedSpeedDurationMax: number | string
  stateChangeIntervalMin: number | string
  stateChangeIntervalMax: number | string
  reducedSpeedKbps: number | string
}

export default function SettingsPage() {
  const { config, clients, fetchClients, updateConfig, addToast } = useStore()
  const [saving, setSaving] = useState(false)
  const [formData, setFormData] = useState<FormDataType>({
    minUploadRate: 30,
    maxUploadRate: 160,
    simultaneousSeed: 20,
    client: 'qbittorrent-4.6.0.client',
    keepTorrentWithZeroLeechers: true,
    uploadRatioTarget: -1,
    seedingDurationLimit: -1,
    // Discretion & Timing Settings
    announceInterval: 30,
    announceJitter: 30,
    minStatsUpdateInterval: 3,
    enableSpeedVariation: true,
    speedVariationPercent: 20,
    // Behavior Mode Settings
    seedingOnlyMode: true,
    // Realistic Behavior Timing
    pauseDurationMin: 30,
    pauseDurationMax: 180,
    reducedSpeedDurationMin: 60,
    reducedSpeedDurationMax: 240,
    stateChangeIntervalMin: 2,
    stateChangeIntervalMax: 8,
    reducedSpeedKbps: 5
  })

  useEffect(() => {
    if (config) {
      setFormData(config as FormDataType)
    }
  }, [config])

  useEffect(() => {
    fetchClients()
  }, [fetchClients])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Normalize all numeric values before validation (convert any string to number)
    const normalizedData = {
      ...formData,
      minUploadRate: Number(formData.minUploadRate) || 0,
      maxUploadRate: Number(formData.maxUploadRate) || 0,
      simultaneousSeed: Number(formData.simultaneousSeed) || 1,
      uploadRatioTarget: formData.uploadRatioTarget === '' || formData.uploadRatioTarget === '-' ? -1 : Number(formData.uploadRatioTarget),
      seedingDurationLimit: formData.seedingDurationLimit === '' || formData.seedingDurationLimit === '-' ? -1 : Number(formData.seedingDurationLimit),
      announceInterval: Number(formData.announceInterval) || 30,
      announceJitter: Number(formData.announceJitter) || 30,
      minStatsUpdateInterval: Number(formData.minStatsUpdateInterval) || 3,
      speedVariationPercent: Number(formData.speedVariationPercent) || 20,
      // Realistic Behavior Timing
      pauseDurationMin: Number(formData.pauseDurationMin) || 30,
      pauseDurationMax: Number(formData.pauseDurationMax) || 180,
      reducedSpeedDurationMin: Number(formData.reducedSpeedDurationMin) || 60,
      reducedSpeedDurationMax: Number(formData.reducedSpeedDurationMax) || 240,
      stateChangeIntervalMin: Number(formData.stateChangeIntervalMin) || 2,
      stateChangeIntervalMax: Number(formData.stateChangeIntervalMax) || 8,
      reducedSpeedKbps: Number(formData.reducedSpeedKbps) || 5,
    }
    
    // Client-side validation before sending to server
    const errors: string[] = []
    
    if (normalizedData.minUploadRate < 0) {
      errors.push("Minimum speed cannot be negative")
    }
    if (normalizedData.maxUploadRate < 0) {
      errors.push("Maximum speed cannot be negative")
    }
    if (normalizedData.minUploadRate > 1000000) {
      errors.push("Minimum speed cannot exceed 1000 MB/s (1000000 KB/s)")
    }
    if (normalizedData.maxUploadRate > 1000000) {
      errors.push("Maximum speed cannot exceed 1000 MB/s (1000000 KB/s)")
    }
    if (normalizedData.maxUploadRate > 0 && normalizedData.maxUploadRate < normalizedData.minUploadRate) {
      errors.push(`Maximum speed (${normalizedData.maxUploadRate} KB/s) must be >= minimum speed (${normalizedData.minUploadRate} KB/s)`)
    }
    if (normalizedData.simultaneousSeed < 1) {
      errors.push("Simultaneous seeds must be at least 1")
    }
    if (normalizedData.simultaneousSeed > 1000) {
      errors.push("Simultaneous seeds cannot exceed 1000")
    }
    if (normalizedData.uploadRatioTarget < -1) {
      errors.push("Ratio target must be -1 (unlimited) or a positive number")
    }
    if (normalizedData.seedingDurationLimit < -1) {
      errors.push("Seeding duration must be -1 (unlimited) or a positive number")
    }
    if (normalizedData.seedingDurationLimit > 8760) {
      errors.push("Seeding duration cannot exceed 8760 hours (1 year)")
    }
    
    if (errors.length > 0) {
      addToast(`❌ ${errors[0]}`, 'error')
      return
    }
    
    setSaving(true)
    try {
      console.log('🔧 SettingsPage: Submitting config:', normalizedData)
      await updateConfig(normalizedData)
      // Update local form with normalized values
      setFormData(normalizedData)
      addToast('✅ Configuration updated successfully!', 'success')
    } catch (error: any) {
      console.error('❌ SettingsPage: Failed to update config:', error)
      
      // Use the user-friendly message from the store
      const errorMsg = error.isUserFriendly ? error.message : 'Failed to update configuration'
      
      addToast(`❌ ${errorMsg}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleReset = async () => {
    if (!confirm('Reset configuration to default values?')) return
    setSaving(true)
    try {
      await axios.post('/api/config/reset')
      // Fetch updated config
      const { data } = await axios.get('/api/config')
      setFormData(data)
    } catch (error) {
      console.error('Failed to reset config:', error)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="w-full max-w-6xl mx-auto px-4">
      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-700">
          <h2 className="text-xl font-bold text-white">Configuration</h2>
          <p className="text-slate-400 text-sm mt-1">
            Manage your PyJOAL settings
          </p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Upload Rate Section */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wide">
              Upload Rate
            </h3>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-slate-400 mb-2">
                  Minimum (KB/s)
                </label>
                <input
                  type="number"
                  value={formData.minUploadRate}
                  onChange={(e) => handleChange('minUploadRate', parseInt(e.target.value))}
                  className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  min="0"
                  max="1000000"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-2">
                  Maximum (KB/s)
                </label>
                <input
                  type="number"
                  value={formData.maxUploadRate}
                  onChange={(e) => handleChange('maxUploadRate', parseInt(e.target.value))}
                  className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  min="0"
                  max="1000000"
                />
                <p className="text-slate-500 text-xs mt-1">Limit: 1000000 KB/s (1000 MB/s max)</p>
              </div>
            </div>
          </div>

          {/* Seeding Section */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wide">
              Seeding
            </h3>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-slate-400 mb-2">
                  Simultaneous Seeds
                </label>
                <input
                  type="number"
                  value={formData.simultaneousSeed}
                  onChange={(e) => handleChange('simultaneousSeed', parseInt(e.target.value))}
                  className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  min="1"
                  max="100"
                />
              </div>
              <div>
                <label className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                  Ratio Target
                  <div className="group relative">
                    <HelpCircle className="w-4 h-4 text-slate-500 cursor-help" />
                    <div className="invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-700 text-slate-300 text-xs rounded-lg whitespace-nowrap z-10 shadow-lg">
                      Set -1 for unlimited seeding.<br/>
                      Or set ratio (e.g. 2.0 = 200% upload)
                    </div>
                  </div>
                </label>
                <input
                  type="text"
                  value={formData.uploadRatioTarget === -1 ? '' : formData.uploadRatioTarget}
                  onChange={(e) => {
                    const value = e.target.value
                    // Allow empty, minus sign, or numbers while typing
                    if (value === '' || value === '-' || value === '-1' || !isNaN(parseFloat(value))) {
                      handleChange('uploadRatioTarget', value)
                    }
                  }}
                  onBlur={(e) => {
                    // On blur, normalize to number or keep as-is for validation
                    const value = e.target.value
                    if (value === '' || value === '-') {
                      handleChange('uploadRatioTarget', -1)
                    } else {
                      const parsed = parseFloat(value)
                      if (!isNaN(parsed)) {
                        handleChange('uploadRatioTarget', parsed)
                      }
                    }
                  }}
                  className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Empty = unlimited (-1)"
                />
              </div>
            </div>

            <div>
              <label className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                Seeding Duration Limit (hours)
                <div className="group relative">
                  <HelpCircle className="w-4 h-4 text-slate-500 cursor-help" />
                  <div className="invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-700 text-slate-300 text-xs rounded-lg whitespace-nowrap z-10 shadow-lg">
                    Set -1 for unlimited duration.<br/>
                    Examples: 24h = 1 day, 168h = 1 week
                  </div>
                </div>
              </label>
              <input
                type="text"
                value={formData.seedingDurationLimit === -1 ? '' : formData.seedingDurationLimit}
                onChange={(e) => {
                  const value = e.target.value
                  // Allow empty, minus sign, or numbers while typing
                  if (value === '' || value === '-' || value === '-1' || !isNaN(parseFloat(value))) {
                    handleChange('seedingDurationLimit', value)
                  }
                }}
                onBlur={(e) => {
                  // On blur, normalize to number or keep as-is for validation
                  const value = e.target.value
                  if (value === '' || value === '-') {
                    handleChange('seedingDurationLimit', -1)
                  } else {
                    const parsed = parseFloat(value)
                    if (!isNaN(parsed)) {
                      handleChange('seedingDurationLimit', parsed)
                    }
                  }
                }}
                className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Empty = unlimited (-1)"
              />
              <p className="text-slate-500 text-xs mt-1">
                Torrents will be archived after this duration
              </p>
            </div>

            <div>
              <label className="flex items-center gap-3 cursor-pointer p-3 bg-slate-700/50 rounded-lg border border-slate-600 hover:bg-slate-700 transition-colors">
                <input
                  type="checkbox"
                  checked={formData.keepTorrentWithZeroLeechers}
                  onChange={(e) => handleChange('keepTorrentWithZeroLeechers', e.target.checked)}
                  className="w-5 h-5 text-blue-600 bg-slate-700 border-slate-500 rounded focus:ring-2 focus:ring-blue-500"
                />
                <div>
                  <span className="text-white font-medium">Keep torrents with no peers</span>
                  <p className="text-slate-400 text-sm">Continue seeding even when there are no leechers</p>
                </div>
              </label>
            </div>
          </div>

          {/* Client Section */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wide">
              BitTorrent Client
            </h3>
            
            <div>
              <label className="block text-sm text-slate-400 mb-2">
                Emulated Client
              </label>
              <select
                value={formData.client}
                onChange={(e) => handleChange('client', e.target.value)}
                className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {clients.length === 0 ? (
                  <option value={formData.client}>{formData.client}</option>
                ) : (
                  clients.map((client) => (
                    <option key={client} value={client}>
                      {client.replace('.client', '').replace(/-/g, ' ')}
                    </option>
                  ))
                )}
              </select>
            </div>
          </div>

          {/* Discretion & Anti-Detection Settings */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wide flex items-center gap-2">
              <span>🎭</span>
              <span>Discretion & Anti-Detection</span>
            </h3>
            <p className="text-sm text-slate-400">
              Configure timing parameters to avoid detection by trackers. These settings help make your seeding behavior appear more natural.
            </p>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Announce Interval */}
              <div>
                <label className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                  Announce Interval (seconds)
                  <div className="group relative">
                    <HelpCircle className="w-4 h-4 text-slate-500 cursor-help" />
                    <div className="invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-700 text-slate-300 text-xs rounded-lg whitespace-nowrap z-10 shadow-lg">
                      Base time between announces (15-300s)
                    </div>
                  </div>
                </label>
                <input
                  type="number"
                  value={formData.announceInterval ?? 30}
                  onChange={(e) => {
                    const value = e.target.value
                    if (value === '') {
                      handleChange('announceInterval', '')
                    } else {
                      const parsed = parseInt(value)
                      handleChange('announceInterval', isNaN(parsed) ? 30 : Math.max(15, Math.min(300, parsed)))
                    }
                  }}
                  onBlur={(e) => {
                    if (e.target.value === '' || parseInt(e.target.value) < 15) {
                      handleChange('announceInterval', 30)
                    }
                  }}
                  className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  min="15"
                  max="300"
                  placeholder="30"
                />
              </div>

              {/* Announce Jitter */}
              <div>
                <label className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                  Announce Jitter (±seconds)
                  <div className="group relative">
                    <HelpCircle className="w-4 h-4 text-slate-500 cursor-help" />
                    <div className="invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-700 text-slate-300 text-xs rounded-lg whitespace-nowrap z-10 shadow-lg">
                      Random timing variation to avoid synchronization
                    </div>
                  </div>
                </label>
                <input
                  type="number"
                  value={formData.announceJitter ?? 30}
                  onChange={(e) => {
                    const value = e.target.value
                    if (value === '') {
                      handleChange('announceJitter', '')
                    } else {
                      const parsed = parseInt(value)
                      handleChange('announceJitter', isNaN(parsed) ? 30 : Math.max(0, Math.min(180, parsed)))
                    }
                  }}
                  onBlur={(e) => {
                    if (e.target.value === '' || parseInt(e.target.value) < 0) {
                      handleChange('announceJitter', 30)
                    }
                  }}
                  className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  min="0"
                  max="180"
                  placeholder="30"
                />
              </div>

              {/* Min Stats Update Interval */}
              <div>
                <label className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                  Min Stats Update Interval (seconds)
                  <div className="group relative">
                    <HelpCircle className="w-4 h-4 text-slate-500 cursor-help" />
                    <div className="invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-700 text-slate-300 text-xs rounded-lg whitespace-nowrap z-10 shadow-lg">
                      Minimum time between speed updates (1-30s)
                    </div>
                  </div>
                </label>
                <input
                  type="number"
                  value={formData.minStatsUpdateInterval ?? 3}
                  onChange={(e) => {
                    const value = e.target.value
                    if (value === '') {
                      handleChange('minStatsUpdateInterval', '')
                    } else {
                      const parsed = parseInt(value)
                      handleChange('minStatsUpdateInterval', isNaN(parsed) ? 3 : Math.max(1, Math.min(30, parsed)))
                    }
                  }}
                  onBlur={(e) => {
                    if (e.target.value === '' || parseInt(e.target.value) < 1) {
                      handleChange('minStatsUpdateInterval', 3)
                    }
                  }}
                  className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  min="1"
                  max="30"
                  placeholder="3"
                />
              </div>

              {/* Speed Variation Percent */}
              <div>
                <label className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                  Speed Variation (±%)
                  <div className="group relative">
                    <HelpCircle className="w-4 h-4 text-slate-500 cursor-help" />
                    <div className="invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-700 text-slate-300 text-xs rounded-lg whitespace-nowrap z-10 shadow-lg">
                      Realistic speed fluctuation percentage (0-50%)
                    </div>
                  </div>
                </label>
                <input
                  type="number"
                  value={formData.speedVariationPercent ?? 20}
                  onChange={(e) => {
                    const value = e.target.value
                    if (value === '') {
                      handleChange('speedVariationPercent', '')
                    } else {
                      const parsed = parseInt(value)
                      handleChange('speedVariationPercent', isNaN(parsed) ? 20 : Math.max(0, Math.min(50, parsed)))
                    }
                  }}
                  onBlur={(e) => {
                    if (e.target.value === '' || parseInt(e.target.value) < 0) {
                      handleChange('speedVariationPercent', 20)
                    }
                  }}
                  className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  min="0"
                  max="50"
                  placeholder="20"
                />
              </div>
            </div>

            {/* Enable Speed Variation */}
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="enableSpeedVariation"
                checked={formData.enableSpeedVariation ?? true}
                onChange={(e) => handleChange('enableSpeedVariation', e.target.checked)}
                className="w-4 h-4 text-blue-600 bg-slate-700 border-slate-600 rounded focus:ring-2 focus:ring-blue-500"
              />
              <label htmlFor="enableSpeedVariation" className="text-sm text-slate-300 cursor-pointer">
                Enable realistic speed variations (Recommended for stealth)
              </label>
            </div>
          </div>

          {/* Realistic Behavior Timing */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wide flex items-center gap-2">
              <span>⏱️</span>
              <span>Realistic Behavior Timing</span>
            </h3>
            <p className="text-sm text-slate-400">
              Configure how PyJOAL simulates realistic human seeding patterns. State changes (pauses, reduced speed) should happen like a real user would behave.
            </p>
            
            {/* State Change Interval */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                  State Change Interval Min (hours)
                  <div className="group relative">
                    <HelpCircle className="w-4 h-4 text-slate-500 cursor-help" />
                    <div className="invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-700 text-slate-300 text-xs rounded-lg whitespace-nowrap z-10 shadow-lg">
                      Minimum time between torrent state changes
                    </div>
                  </div>
                </label>
                <input
                  type="number"
                  value={formData.stateChangeIntervalMin ?? 2}
                  onChange={(e) => {
                    const value = e.target.value
                    if (value === '') {
                      handleChange('stateChangeIntervalMin', '')
                    } else {
                      const parsed = parseFloat(value)
                      handleChange('stateChangeIntervalMin', isNaN(parsed) ? 2 : Math.max(0.5, parsed))
                    }
                  }}
                  onBlur={(e) => {
                    if (e.target.value === '' || parseFloat(e.target.value) < 0.5) {
                      handleChange('stateChangeIntervalMin', 2)
                    }
                  }}
                  step="0.5"
                  className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  min="0.5"
                  placeholder="2"
                />
              </div>
              <div>
                <label className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                  State Change Interval Max (hours)
                  <div className="group relative">
                    <HelpCircle className="w-4 h-4 text-slate-500 cursor-help" />
                    <div className="invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-700 text-slate-300 text-xs rounded-lg whitespace-nowrap z-10 shadow-lg">
                      Maximum time between torrent state changes
                    </div>
                  </div>
                </label>
                <input
                  type="number"
                  value={formData.stateChangeIntervalMax ?? 8}
                  onChange={(e) => {
                    const value = e.target.value
                    if (value === '') {
                      handleChange('stateChangeIntervalMax', '')
                    } else {
                      const parsed = parseFloat(value)
                      handleChange('stateChangeIntervalMax', isNaN(parsed) ? 8 : Math.max(1, parsed))
                    }
                  }}
                  onBlur={(e) => {
                    if (e.target.value === '' || parseFloat(e.target.value) < 1) {
                      handleChange('stateChangeIntervalMax', 8)
                    }
                  }}
                  step="0.5"
                  className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  min="1"
                  placeholder="8"
                />
              </div>
            </div>

            {/* Pause Duration */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                  Pause Duration Min (minutes)
                  <div className="group relative">
                    <HelpCircle className="w-4 h-4 text-slate-500 cursor-help" />
                    <div className="invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-700 text-slate-300 text-xs rounded-lg whitespace-nowrap z-10 shadow-lg">
                      Minimum duration when torrent is paused
                    </div>
                  </div>
                </label>
                <input
                  type="number"
                  value={formData.pauseDurationMin ?? 30}
                  onChange={(e) => {
                    const value = e.target.value
                    if (value === '') {
                      handleChange('pauseDurationMin', '')
                    } else {
                      const parsed = parseInt(value)
                      handleChange('pauseDurationMin', isNaN(parsed) ? 30 : Math.max(5, parsed))
                    }
                  }}
                  onBlur={(e) => {
                    if (e.target.value === '' || parseInt(e.target.value) < 5) {
                      handleChange('pauseDurationMin', 30)
                    }
                  }}
                  className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  min="5"
                  placeholder="30"
                />
              </div>
              <div>
                <label className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                  Pause Duration Max (minutes)
                  <div className="group relative">
                    <HelpCircle className="w-4 h-4 text-slate-500 cursor-help" />
                    <div className="invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-700 text-slate-300 text-xs rounded-lg whitespace-nowrap z-10 shadow-lg">
                      Maximum duration when torrent is paused
                    </div>
                  </div>
                </label>
                <input
                  type="number"
                  value={formData.pauseDurationMax ?? 180}
                  onChange={(e) => {
                    const value = e.target.value
                    if (value === '') {
                      handleChange('pauseDurationMax', '')
                    } else {
                      const parsed = parseInt(value)
                      handleChange('pauseDurationMax', isNaN(parsed) ? 180 : Math.max(10, parsed))
                    }
                  }}
                  onBlur={(e) => {
                    if (e.target.value === '' || parseInt(e.target.value) < 10) {
                      handleChange('pauseDurationMax', 180)
                    }
                  }}
                  className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  min="10"
                  placeholder="180"
                />
              </div>
            </div>

            {/* Reduced Speed Duration */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                  Reduced Speed Duration Min (minutes)
                  <div className="group relative">
                    <HelpCircle className="w-4 h-4 text-slate-500 cursor-help" />
                    <div className="invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-700 text-slate-300 text-xs rounded-lg whitespace-nowrap z-10 shadow-lg">
                      Minimum duration in reduced speed mode
                    </div>
                  </div>
                </label>
                <input
                  type="number"
                  value={formData.reducedSpeedDurationMin ?? 60}
                  onChange={(e) => {
                    const value = e.target.value
                    if (value === '') {
                      handleChange('reducedSpeedDurationMin', '')
                    } else {
                      const parsed = parseInt(value)
                      handleChange('reducedSpeedDurationMin', isNaN(parsed) ? 60 : Math.max(10, parsed))
                    }
                  }}
                  onBlur={(e) => {
                    if (e.target.value === '' || parseInt(e.target.value) < 10) {
                      handleChange('reducedSpeedDurationMin', 60)
                    }
                  }}
                  className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  min="10"
                  placeholder="60"
                />
              </div>
              <div>
                <label className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                  Reduced Speed Duration Max (minutes)
                  <div className="group relative">
                    <HelpCircle className="w-4 h-4 text-slate-500 cursor-help" />
                    <div className="invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-700 text-slate-300 text-xs rounded-lg whitespace-nowrap z-10 shadow-lg">
                      Maximum duration in reduced speed mode
                    </div>
                  </div>
                </label>
                <input
                  type="number"
                  value={formData.reducedSpeedDurationMax ?? 240}
                  onChange={(e) => {
                    const value = e.target.value
                    if (value === '') {
                      handleChange('reducedSpeedDurationMax', '')
                    } else {
                      const parsed = parseInt(value)
                      handleChange('reducedSpeedDurationMax', isNaN(parsed) ? 240 : Math.max(30, parsed))
                    }
                  }}
                  onBlur={(e) => {
                    if (e.target.value === '' || parseInt(e.target.value) < 30) {
                      handleChange('reducedSpeedDurationMax', 240)
                    }
                  }}
                  className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  min="30"
                  placeholder="240"
                />
              </div>
            </div>

            {/* Reduced Speed kB/s */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                  Reduced Speed (kB/s)
                  <div className="group relative">
                    <HelpCircle className="w-4 h-4 text-slate-500 cursor-help" />
                    <div className="invisible group-hover:visible opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-700 text-slate-300 text-xs rounded-lg whitespace-nowrap z-10 shadow-lg">
                      Upload speed when in "Reduced seeding" mode (~1-10 kB/s is realistic)
                    </div>
                  </div>
                </label>
                <input
                  type="number"
                  value={formData.reducedSpeedKbps ?? 5}
                  onChange={(e) => {
                    const value = e.target.value
                    if (value === '') {
                      handleChange('reducedSpeedKbps', '')
                    } else {
                      const parsed = parseInt(value)
                      handleChange('reducedSpeedKbps', isNaN(parsed) ? 5 : Math.max(1, Math.min(50, parsed)))
                    }
                  }}
                  onBlur={(e) => {
                    if (e.target.value === '' || parseInt(e.target.value) < 1) {
                      handleChange('reducedSpeedKbps', 5)
                    }
                  }}
                  className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  min="1"
                  max="50"
                  placeholder="5"
                />
              </div>
            </div>

            <div className="text-xs text-slate-500 space-y-1 mt-2">
              <p>💡 <strong>Tips:</strong> For realistic behavior:</p>
              <p>• State changes should happen every few hours (2-8h), not minutes</p>
              <p>• Pauses should last 30min to 3 hours like a real user away</p>
              <p>• Reduced speed should be very low (~5 kB/s) like background seeding</p>
            </div>
          </div>

          {/* Torrent Behavior Mode */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wide flex items-center gap-2">
              <span>🎯</span>
              <span>Torrent Behavior Mode</span>
            </h3>
            <p className="text-sm text-slate-400">
              Choose how PyJOAL simulates torrent behavior. Most users should use "Seeding Only" mode.
            </p>
            
            <div className="grid grid-cols-1 gap-4">
              {/* Seeding Only Mode Toggle */}
              <div className="bg-slate-700 rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-medium text-slate-300">Seeding Only Mode</h4>
                    <p className="text-xs text-slate-400 mt-1">
                      {formData.seedingOnlyMode 
                        ? "✅ Pure seeding - torrents appear already downloaded (Recommended)" 
                        : "📥 Download simulation - simulates full download + seeding cycle"}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">Download Sim</span>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.seedingOnlyMode ?? true}
                        onChange={(e) => handleChange('seedingOnlyMode', e.target.checked)}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-slate-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                    <span className="text-xs text-slate-400">Seeding Only</span>
                  </div>
                </div>
                
                <div className="text-xs text-slate-400 space-y-1">
                  <p><strong>Seeding Only Mode (Recommended):</strong></p>
                  <p>• Torrents appear as already 100% downloaded</p>
                  <p>• Realistic for when your real client downloads first</p>
                  <p>• Sends "completed" event immediately</p>
                  <p>• More natural and safer behavior</p>
                  
                  {!formData.seedingOnlyMode && (
                    <div className="mt-3 pt-2 border-t border-slate-600">
                      <p><strong>Download Simulation Mode:</strong></p>
                      <p>• Simulates downloading then seeding</p>
                      <p>• May appear more suspicious to some trackers</p>
                      <p>• Use only if you understand the implications</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t border-slate-700">
            <button
              type="button"
              onClick={handleReset}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2.5 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw className="w-4 h-4" />
              Reset to Defaults
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex-1 flex items-center justify-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              {saving ? 'Saving...' : 'Save Configuration'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
