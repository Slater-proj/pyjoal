import { useState, useEffect } from 'react'
import { Settings, Save } from 'lucide-react'
import { useStore } from '../store/useStore'

export default function ConfigPanel() {
  const { config, clients, fetchClients, updateConfig, addToast } = useStore()
  const [isOpen, setIsOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [formData, setFormData] = useState({
    minUploadRate: 30,
    maxUploadRate: 160,
    simultaneousSeed: 20,
    client: 'qbittorrent-4.6.0.client',
    keepTorrentWithZeroLeechers: true,
    uploadRatioTarget: -1.0,
    seedingDurationLimit: -1.0,
    // Discretion & Timing Settings
    announceInterval: 30,
    announceJitter: 30,
    minStatsUpdateInterval: 3,
    enableSpeedVariation: true,
    speedVariationPercent: 20
  })

  useEffect(() => {
    if (config) {
      setFormData(config)
    }
  }, [config])

  useEffect(() => {
    fetchClients()
  }, [fetchClients])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      console.log('🔧 ConfigPanel: Submitting config:', formData)
      await updateConfig(formData)
      addToast('✅ Configuration mise à jour avec succès !', 'success')
    } catch (error: any) {
      console.error('❌ ConfigPanel: Configuration update error:', error)
      
      // Use the user-friendly message from the store
      const errorMsg = error.isUserFriendly ? error.message : 'Erreur lors de la mise à jour de la configuration'
      
      addToast(`❌ ${errorMsg}`, 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-700/50 transition-colors"
      >
        <div className="flex items-center space-x-3">
          <Settings className="w-5 h-5 text-slate-400" />
          <h2 className="text-xl font-bold text-white">Configuration</h2>
        </div>
        <span className="text-slate-400">
          {isOpen ? '▼' : '▶'}
        </span>
      </button>

      {isOpen && (
        <form onSubmit={handleSubmit} className="px-6 py-6 border-t border-slate-700 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Upload Rate */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Min Upload Rate (kB/s)
              </label>
              <input
                type="number"
                value={formData.minUploadRate}
                onChange={(e) => handleChange('minUploadRate', parseInt(e.target.value))}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                min="0"
                max="1000000"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Max Upload Rate (kB/s)
              </label>
              <input
                type="number"
                value={formData.maxUploadRate}
                onChange={(e) => handleChange('maxUploadRate', parseInt(e.target.value))}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                min="0"
                max="1000000"
              />
            </div>

            {/* Simultaneous Seeds */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Simultaneous Seeds
              </label>
              <input
                type="number"
                value={formData.simultaneousSeed}
                onChange={(e) => handleChange('simultaneousSeed', parseInt(e.target.value))}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                min="1"
                max="100"
              />
            </div>

            {/* Upload Ratio Target */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Upload Ratio Target (-1 = never remove)
              </label>
              <input
                type="number"
                step="0.1"
                value={formData.uploadRatioTarget}
                onChange={(e) => {
                  const value = e.target.value
                  if (value === '' || value === '-') {
                    // Allow empty or just minus sign while typing
                    handleChange('uploadRatioTarget', value === '' ? -1 : value)
                  } else {
                    const parsed = parseFloat(value)
                    if (!isNaN(parsed)) {
                      handleChange('uploadRatioTarget', parsed)
                    }
                  }
                }}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="-1 = unlimited"
              />
            </div>

            {/* Seeding Duration Limit */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Seeding Duration Limit (hours, -1 = unlimited)
              </label>
              <input
                type="number"
                step="1"
                value={formData.seedingDurationLimit}
                onChange={(e) => {
                  const value = e.target.value
                  if (value === '' || value === '-') {
                    // Allow empty or just minus sign while typing
                    handleChange('seedingDurationLimit', value === '' ? -1 : value)
                  } else {
                    const parsed = parseFloat(value)
                    if (!isNaN(parsed)) {
                      handleChange('seedingDurationLimit', parsed)
                    }
                  }
                }}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="-1 = unlimited"
              />
            </div>

            {/* Client Selection */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-slate-300 mb-2">
                BitTorrent Client
              </label>
              <select
                value={formData.client}
                onChange={(e) => handleChange('client', e.target.value)}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {clients.map((client) => (
                  <option key={client} value={client}>
                    {client}
                  </option>
                ))}
              </select>
            </div>

            {/* Keep Torrents with Zero Leechers */}
            <div className="md:col-span-2">
              <label className="flex items-center space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.keepTorrentWithZeroLeechers}
                  onChange={(e) => handleChange('keepTorrentWithZeroLeechers', e.target.checked)}
                  className="w-5 h-5 text-blue-600 bg-slate-700 border-slate-600 rounded focus:ring-2 focus:ring-blue-500"
                />
                <span className="text-slate-300">
                  Keep torrents with zero leechers/seeders
                </span>
              </label>
            </div>
          </div>

          {/* Discretion & Timing Settings Section */}
          <div className="border-t border-slate-600 pt-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center space-x-2">
              <span>🎭</span>
              <span>Discretion & Timing Settings</span>
            </h3>
            <p className="text-sm text-slate-400 mb-4">
              Advanced settings to improve stealth and avoid detection by tracker analysis.
            </p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Announce Interval */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Announce Interval (seconds)
                </label>
                <input
                  type="number"
                  value={formData.announceInterval}
                  onChange={(e) => handleChange('announceInterval', parseInt(e.target.value))}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  min="15"
                  max="300"
                />
                <p className="text-xs text-slate-500 mt-1">Base time between announces (15-300s)</p>
              </div>

              {/* Announce Jitter */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Announce Jitter (±seconds)
                </label>
                <input
                  type="number"
                  value={formData.announceJitter}
                  onChange={(e) => handleChange('announceJitter', parseInt(e.target.value))}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  min="0"
                  max="180"
                />
                <p className="text-xs text-slate-500 mt-1">Random timing variation to avoid synchronization</p>
              </div>

              {/* Min Stats Update Interval */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Min Stats Update Interval (seconds)
                </label>
                <input
                  type="number"
                  value={formData.minStatsUpdateInterval}
                  onChange={(e) => handleChange('minStatsUpdateInterval', parseInt(e.target.value))}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  min="1"
                  max="30"
                />
                <p className="text-xs text-slate-500 mt-1">Minimum time between speed updates (1-30s)</p>
              </div>

              {/* Speed Variation Percent */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Speed Variation (±%)
                </label>
                <input
                  type="number"
                  value={formData.speedVariationPercent}
                  onChange={(e) => handleChange('speedVariationPercent', parseInt(e.target.value))}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  min="0"
                  max="50"
                />
                <p className="text-xs text-slate-500 mt-1">Realistic speed fluctuation percentage (0-50%)</p>
              </div>

              {/* Enable Speed Variation */}
              <div className="md:col-span-2">
                <label className="flex items-center space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.enableSpeedVariation}
                    onChange={(e) => handleChange('enableSpeedVariation', e.target.checked)}
                    className="w-5 h-5 text-blue-600 bg-slate-700 border-slate-600 rounded focus:ring-2 focus:ring-blue-500"
                  />
                  <span className="text-slate-300">
                    Enable realistic speed variations
                  </span>
                  <span className="text-slate-500 text-sm">(Recommended for stealth)</span>
                </label>
              </div>
            </div>
          </div>

          {/* Submit Button */}
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={saving}
              className="flex items-center space-x-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors disabled:opacity-50"
            >
              <Save className="w-5 h-5" />
              <span>{saving ? 'Saving...' : 'Save Configuration'}</span>
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
