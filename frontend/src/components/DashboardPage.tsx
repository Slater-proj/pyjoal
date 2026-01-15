import { useCallback, useRef } from 'react'
import { useDropzone } from 'react-dropzone'
import { Plus, FolderOpen } from 'lucide-react'
import ClientInfoPanel from './ClientInfoPanel'
import TorrentsTableNew from './TorrentsTableNew'
import { useStore } from '../store/useStore'

export default function DashboardPage() {
  const { addTorrent } = useStore()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    for (const file of acceptedFiles) {
      if (file.name.endsWith('.torrent')) {
        try {
          await addTorrent(file)
        } catch (error) {
          console.error('Failed to add torrent:', error)
        }
      }
    }
  }, [addTorrent])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/x-bittorrent': ['.torrent'] },
    multiple: true,
    noClick: true,
    noKeyboard: true
  })

  const handleAddClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files) {
      for (const file of Array.from(files)) {
        if (!file.name.endsWith('.torrent')) {
          console.warn(`Skipping non-torrent file: ${file.name}`)
          continue
        }
        try {
          await addTorrent(file)
        } catch (error) {
          // Error is already handled by the store with toast notification
          console.error('Failed to add torrent:', error)
        }
      }
    }
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div {...getRootProps()} className="min-h-full relative">
      {/* Completely hidden dropzone input - do not render default input */}
      <div style={{ display: 'none' }}>
        <input {...getInputProps()} />
      </div>
      
      {/* Hidden file input for button */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".torrent"
        multiple
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />
      
      {/* Global drag overlay */}
      {isDragActive && (
        <div className="fixed inset-0 bg-blue-500/20 z-40 flex items-center justify-center pointer-events-none">
          <div className="bg-slate-800 rounded-lg p-8 border-2 border-dashed border-blue-500">
            <p className="text-blue-400 text-xl font-semibold">Drop .torrent files here</p>
          </div>
        </div>
      )}

      {/* Improved layout for 1080p+ - Horizontal layout with wider torrent table */}
      <div className="flex flex-col xl:flex-row gap-6">
        
        {/* TOP/LEFT SECTION - Control Panel - Optimized width */}
        <aside className="w-full xl:w-96 flex-shrink-0">
          <div className="xl:sticky xl:top-20 space-y-4">
            {/* Client Info Panel */}
            <ClientInfoPanel />
            
            {/* ADD TORRENT BUTTON - Main action, very visible */}
            <button
              onClick={handleAddClick}
              className="w-full flex items-center justify-center gap-3 py-4 px-6 rounded-lg font-bold text-lg transition-all duration-200 border-2 shadow-lg bg-blue-600 hover:bg-blue-500 border-blue-400 text-white cursor-pointer hover:shadow-blue-500/25"
            >
              <Plus className="w-6 h-6" />
              <span>ADD TORRENTS</span>
            </button>

            {/* Info about auto-loading */}
            <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-4">
              <div className="flex items-start gap-3">
                <FolderOpen className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm">
                  <p className="text-slate-300 font-medium mb-1">Auto-import folder</p>
                  <p className="text-slate-500 text-xs">
                    Place <code className="bg-slate-700 px-1.5 py-0.5 rounded">.torrent</code> files in the <code className="bg-slate-700 px-1.5 py-0.5 rounded">/torrents</code> folder - they are loaded automatically!
                  </p>
                </div>
              </div>
            </div>
          </div>
        </aside>

        {/* MAIN SECTION - Torrents List - Takes remaining space */}
        <section className="flex-1 min-w-0">
          <TorrentsTableNew />
        </section>
      </div>
    </div>
  )
}
