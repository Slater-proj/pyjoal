import { Upload, Download, Activity, Clock } from 'lucide-react'
import { useStore } from '../store/useStore'

export default function Dashboard() {
  const { stats } = useStore()

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const formatSpeed = (bytesPerSec: number) => {
    return formatBytes(bytesPerSec) + '/s'
  }

  const formatUptime = (seconds: number | null) => {
    if (!seconds) return 'N/A'
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}h ${minutes}m`
  }

  const statCards = [
    {
      icon: Activity,
      label: 'Active Torrents',
      value: `${stats?.activeTorrents || 0} / ${stats?.totalTorrents || 0}`,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10'
    },
    {
      icon: Upload,
      label: 'Upload Speed',
      value: formatSpeed(stats?.uploadSpeed || 0),
      color: 'text-green-400',
      bgColor: 'bg-green-500/10'
    },
    {
      icon: Download,
      label: 'Total Uploaded',
      value: formatBytes(stats?.totalUploaded || 0),
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10'
    },
    {
      icon: Clock,
      label: 'Uptime',
      value: formatUptime(stats?.uptime || null),
      color: 'text-orange-400',
      bgColor: 'bg-orange-500/10'
    }
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {statCards.map((card, index) => (
        <div
          key={index}
          className="bg-slate-800 rounded-lg p-6 border border-slate-700 hover:border-slate-600 transition-all"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm mb-1">{card.label}</p>
              <p className="text-2xl font-bold text-white">{card.value}</p>
            </div>
            <div className={`p-3 rounded-lg ${card.bgColor}`}>
              <card.icon className={`w-6 h-6 ${card.color}`} />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
