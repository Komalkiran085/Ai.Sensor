import { Database, Radio, FileUp } from 'lucide-react'
import clsx from 'clsx'
import { useState } from 'react'

const SOURCES = [
  { id: 'simulation', label: 'Simulation', icon: Radio, desc: 'Scripted demo data', active: true },
  { id: 'opcua', label: 'OPC-UA', icon: Database, desc: 'SCADA integration', active: false },
  { id: 'csv', label: 'CSV Upload', icon: FileUp, desc: 'Historical data', active: false },
]

export default function DataSourceSelector() {
  const [selected, setSelected] = useState('simulation')

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-3 flex items-center gap-3">
      <span className="text-[10px] text-gray-500 uppercase font-bold tracking-wider">Data Source</span>
      <div className="flex gap-1">
        {SOURCES.map(s => (
          <button
            key={s.id}
            onClick={() => s.active && setSelected(s.id)}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition',
              selected === s.id
                ? 'bg-blue-600 text-white'
                : s.active
                  ? 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                  : 'bg-gray-800/50 text-gray-600 cursor-not-allowed'
            )}
            title={s.desc}
          >
            <s.icon className="w-3 h-3" />
            {s.label}
            {!s.active && <span className="text-[8px] bg-gray-700 px-1 rounded">Soon</span>}
          </button>
        ))}
      </div>
    </div>
  )
}
