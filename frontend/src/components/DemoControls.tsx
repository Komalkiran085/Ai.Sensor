import { useState } from 'react'
import { Play, RotateCcw, History, Info } from 'lucide-react'
import { ZoneMeta, DemoScenario } from '../App'

type Props = {
  zones: ZoneMeta[]
  scenarios: DemoScenario[]
  scenarioZone: string
  onZoneChange: (zoneId: string) => void
  scenarioActive: boolean
  onTrigger: () => void
  onTriggerNamed: (zoneId: string) => void
  onReset: () => void
}

export default function DemoControls({
  zones, scenarios, scenarioZone, onZoneChange, scenarioActive, onTrigger, onTriggerNamed, onReset,
}: Props) {
  const [showInfo, setShowInfo] = useState<string | null>(null)

  if (scenarioActive) {
    return (
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 flex items-center gap-3">
        <span className="text-xs text-gray-400 font-semibold uppercase mr-2">Demo</span>
        <button
          onClick={onReset}
          className="flex items-center gap-1.5 bg-gray-600 hover:bg-gray-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition"
        >
          <RotateCcw className="w-4 h-4" /> Reset to Normal
        </button>
      </div>
    )
  }

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 flex items-center gap-3 flex-wrap">
      <span className="text-xs text-gray-400 font-semibold uppercase mr-1">Demo</span>

      {scenarios.map(s => (
        <div key={s.id} className="relative">
          <button
            onClick={() => onTriggerNamed(s.zone_id)}
            onMouseEnter={() => setShowInfo(s.id)}
            onMouseLeave={() => setShowInfo(null)}
            className="flex items-center gap-1.5 bg-red-600 hover:bg-red-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition"
          >
            <History className="w-4 h-4" /> {s.label}
            <Info className="w-3.5 h-3.5 opacity-70" />
          </button>
          {showInfo === s.id && (
            <div className="absolute z-10 top-full mt-2 left-0 w-72 bg-gray-800 border border-gray-700 rounded-lg p-3 text-[11px] text-gray-300 leading-relaxed shadow-xl">
              {s.description}
            </div>
          )}
        </div>
      ))}

      <div className="w-px h-8 bg-gray-800 mx-1" />

      <select
        value={scenarioZone}
        onChange={e => onZoneChange(e.target.value)}
        className="bg-gray-800 text-gray-200 text-sm rounded-lg px-2 py-2 border border-gray-700 focus:outline-none focus:border-blue-500"
      >
        {zones.map(z => (
          <option key={z.zone_id} value={z.zone_id}>{z.name}</option>
        ))}
      </select>
      <button
        onClick={onTrigger}
        className="flex items-center gap-1.5 bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium px-4 py-2 rounded-lg transition"
      >
        <Play className="w-4 h-4" /> Trigger Custom Zone
      </button>
    </div>
  )
}
