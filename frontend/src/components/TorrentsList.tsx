import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, Trash2, Circle } from 'lucide-react'
import { useStore } from '../store/useStore'

export default function TorrentsList() {
  const { torrents, addTorrent, removeTorrent } = useStore()

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    for (const file of acceptedFiles) {
      if (file.name.endsWith('.torrent')) {
        try {
          await addTorrent(file)
        } catch (error) {
          console.error('Failed to add torrent:', error)
          alert(`Failed to add ${file.name}`)
        }
      }
    }
  }, [addTorrent])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/x-bittorrent': ['.torrent'] },
    multiple: true
  })

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

  const handleRemove = async (infoHash: string) => {
    if (confirm('Are you sure you want to remove this torrent?')) {
      try {
        await removeTorrent(infoHash)
      } catch (error) {
        console.error('Failed to remove torrent:', error)
      }
    }
  }

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-700">
        <h2 className="text-xl font-bold text-white">Torrents</h2>
      </div>

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`
          m-6 border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
          transition-all duration-200
          ${isDragActive 
            ? 'border-blue-500 bg-blue-500/10' 
            : 'border-slate-600 hover:border-slate-500 hover:bg-slate-700/50'}
        `}
      >
        <input {...getInputProps()} />
        <Upload className="w-12 h-12 mx-auto mb-4 text-slate-400" />
        {isDragActive ? (
          <p className="text-blue-400">Drop torrents here...</p>
        ) : (
          <div>
            <p className="text-white font-semibold mb-2">
              Drag & drop .torrent files here
            </p>
            <p className="text-slate-400 text-sm">or click to browse</p>
          </div>
        )}
      </div>

      {/* Torrents List */}
      <div className="divide-y divide-slate-700">
        {torrents.length === 0 ? (
          <div className="px-6 py-12 text-center text-slate-400">
            No torrents added yet. Drop some .torrent files above!
          </div>
        ) : (
          torrents.map((torrent) => (
            <div
              key={torrent.id}
              className="px-6 py-4 hover:bg-slate-700/50 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0 mr-4">
                  <div className="flex items-center space-x-3 mb-2">
                    <Circle
                      className={`w-3 h-3 flex-shrink-0 ${
                        torrent.state === 'seeding'
                          ? 'text-green-500 fill-green-500'
                          : 'text-slate-500'
                      }`}
                    />
                    <h3 className="text-white font-semibold truncate">
                      {torrent.name}
                    </h3>
                  </div>
                  
                  <div className="flex flex-wrap gap-4 text-sm text-slate-400">
                    <span>Size: {formatBytes(torrent.size)}</span>
                    <span>Uploaded: {formatBytes(torrent.uploaded)}</span>
                    <span>Ratio: {torrent.ratio.toFixed(2)}</span>
                    <span>Speed: {formatSpeed(torrent.uploadSpeed)}</span>
                    <span className="text-green-400">{torrent.seeders} seeders</span>
                    <span className="text-blue-400">{torrent.leechers} leechers</span>
                  </div>
                </div>

                <button
                  onClick={() => handleRemove(torrent.id)}
                  className="flex-shrink-0 p-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors"
                  title="Remove torrent"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
