import { Radio, FileUp, Database, X } from 'lucide-react'
import clsx from 'clsx'
import { useEffect, useRef, useState } from 'react'

type DataSourceState = { source: 'simulation' } | { source: 'csv'; filename: string; step: number; steps: number }

export default function DataSourceSelector({ apiBase }: { apiBase: string }) {
  const [state, setState] = useState<DataSourceState>({ source: 'simulation' })
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  const refresh = () => {
    fetch(`${apiBase}/api/datasource`).then(r => r.json()).then(setState).catch(() => {})
  }

  useEffect(() => {
    refresh()
    // Step count only moves forward on the backend's own tick, so poll rather than
    // wait on a websocket event for what's a low-stakes progress readout.
    const id = setInterval(refresh, 5000)
    return () => clearInterval(id)
  }, [])

  const switchToSimulation = async () => {
    setError(null)
    await fetch(`${apiBase}/api/datasource/simulation`, { method: 'POST' })
    refresh()
  }

  const handleFile = async (file: File) => {
    setUploading(true)
    setError(null)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch(`${apiBase}/api/datasource/csv`, { method: 'POST', body: form })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Upload failed')
      setState(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed')
    }
    setUploading(false)
  }

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 flex items-center gap-2 flex-wrap">
      <span title="Data Source" className="shrink-0">
        <Database className="w-4 h-4 text-gray-500" />
      </span>

      <div className="flex gap-1.5">
        <button
          onClick={switchToSimulation}
          className={clsx(
            'flex items-center gap-1.5 text-xs font-medium px-2 py-2 rounded-lg transition',
            state.source === 'simulation' ? 'bg-blue-600 hover:bg-blue-700 text-white' : 'bg-gray-700 hover:bg-gray-600 text-white'
          )}
          title="Scripted demo data"
        >
          <Radio className="w-3.5 h-3.5" />
          Simulation
        </button>

        <button
          onClick={() => fileInput.current?.click()}
          disabled={uploading}
          className={clsx(
            'flex items-center gap-1.5 text-xs font-medium px-2 py-2 rounded-lg transition',
            state.source === 'csv' ? 'bg-blue-600 hover:bg-blue-700 text-white' : 'bg-gray-700 hover:bg-gray-600 text-white',
            uploading && 'opacity-60 cursor-wait'
          )}
          title="Replay sensor readings from an uploaded CSV"
        >
          <FileUp className="w-3.5 h-3.5" />
          {uploading ? 'Uploading…' : 'CSV Upload'}
        </button>
        <input
          ref={fileInput}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={e => {
            const file = e.target.files?.[0]
            if (file) handleFile(file)
            e.target.value = ''
          }}
        />
      </div>

      {state.source === 'csv' && (
        <span className="text-xs text-gray-400 whitespace-nowrap">
          {state.step % state.steps + 1}/{state.steps}
        </span>
      )}

      {error && (
        <div className="flex items-start gap-1.5 text-xs text-red-400 bg-red-900/20 border border-red-900/50 rounded px-2 py-1.5 w-full">
          <span className="flex-1">{error}</span>
          <button onClick={() => setError(null)}><X className="w-3.5 h-3.5" /></button>
        </div>
      )}
    </div>
  )
}
