import { useState, useEffect } from 'react'
import { Save, RefreshCw, HelpCircle } from 'lucide-react'
import { useStore } from '../store/useStore'
import axios from 'axios'

export default function SettingsPage() {
  const { config, clients, fetchClients, updateConfig, addToast } = useStore()
  const [saving, setSaving] = useState(false)
  const [formData, setFormData] = useState({
    minUploadRate: 30,
    maxUploadRate: 160,
    simultaneousSeed: 20,
    client: 'qbittorrent-4.6.0.client',
    keepTorrentWithZeroLeechers: true,
    uploadRatioTarget: -1.0,
    seedingDurationLimit: -1.0
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
    
    // Client-side validation before sending to server
    const errors: string[] = []
    
    if (formData.minUploadRate < 0) {
      errors.push("La vitesse minimum ne peut pas être négative")
    }
    if (formData.maxUploadRate < 0) {
      errors.push("La vitesse maximum ne peut pas être négative")
    }
    if (formData.minUploadRate > 100000) {
      errors.push("La vitesse minimum ne peut pas dépasser 100 MB/s (100000 KB/s)")
    }
    if (formData.maxUploadRate > 100000) {
      errors.push("La vitesse maximum ne peut pas dépasser 100 MB/s (100000 KB/s)")
    }
    if (formData.maxUploadRate > 0 && formData.maxUploadRate < formData.minUploadRate) {
      errors.push(`La vitesse maximum (${formData.maxUploadRate} KB/s) doit être supérieure ou égale à la vitesse minimum (${formData.minUploadRate} KB/s)`)
    }
    if (formData.simultaneousSeed < 1) {
      errors.push("Le nombre de seeds simultanés doit être au moins 1")
    }
    if (formData.simultaneousSeed > 1000) {
      errors.push("Le nombre de seeds simultanés ne peut pas dépasser 1000")
    }
    if (formData.uploadRatioTarget < -1) {
      errors.push("Le ratio cible doit être -1 (illimité) ou un nombre positif")
    }
    if (formData.seedingDurationLimit < -1) {
      errors.push("La durée de seed doit être -1 (illimitée) ou un nombre positif")
    }
    if (formData.seedingDurationLimit > 8760) {
      errors.push("La durée de seed ne peut pas dépasser 8760 heures (1 an)")
    }
    
    if (errors.length > 0) {
      addToast(`❌ ${errors[0]}`, 'error')
      return
    }
    
    setSaving(true)
    try {
      console.log('🔧 SettingsPage: Submitting config:', formData)
      await updateConfig(formData)
      addToast('✅ Configuration mise à jour avec succès !', 'success')
    } catch (error: any) {
      console.error('❌ SettingsPage: Failed to update config:', error)
      
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
    <div className="max-w-2xl mx-auto">
      <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-700">
          <h2 className="text-xl font-bold text-white">Configuration</h2>
          <p className="text-slate-400 text-sm mt-1">
            Manage your JOAL settings
          </p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Upload Rate Section */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wide">
              Upload Rate
            </h3>
            
            <div className="grid grid-cols-2 gap-4">
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
                  max="100000"
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
                  max="100000"
                />
                <p className="text-slate-500 text-xs mt-1">Limite : 100000 KB/s (100 MB/s max)</p>
              </div>
            </div>
          </div>

          {/* Seeding Section */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wide">
              Seeding
            </h3>
            
            <div className="grid grid-cols-2 gap-4">
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
                    <div className="invisible group-hover:visible absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-700 text-slate-300 text-xs rounded-lg whitespace-nowrap z-10 shadow-lg">
                      Set -1 for unlimited seeding.<br/>
                      Or set ratio (e.g. 2.0 = 200% upload)
                    </div>
                  </div>
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
                  className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="-1 = unlimited"
                />
              </div>
            </div>

            <div>
              <label className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                Seeding Duration Limit (hours)
                <div className="group relative">
                  <HelpCircle className="w-4 h-4 text-slate-500 cursor-help" />
                  <div className="invisible group-hover:visible absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-700 text-slate-300 text-xs rounded-lg whitespace-nowrap z-10 shadow-lg">
                    Set -1 for unlimited duration.<br/>
                    Examples: 24h = 1 day, 168h = 1 week
                  </div>
                </div>
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
                className="w-full px-4 py-2.5 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="-1 = unlimited"
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
