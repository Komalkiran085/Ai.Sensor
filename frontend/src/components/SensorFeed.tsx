import { ZoneRisk } from '../App'
import { getReading } from '../lib/readings'
import { Thermometer, Wind, Flame, Droplets } from 'lucide-react'
import clsx from 'clsx'

const SEVERITY_BG: Record<string, string> = {
  extreme: 'bg-red-900/30 border-red-700',
  critical: 'bg-orange-900/30 border-orange-700',
  warning: 'bg-yellow-900/30 border-yellow-700',
  normal: 'bg-gray-800/30 border-gray-700',
}

export default function SensorFeed({ zoneRisks }: { zoneRisks: Record<string, ZoneRisk> }) {
  const zones = Object.values(zoneRisks)

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 h-full flex flex-col">
      <h2 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">Live Sensor Feed</h2>
      <div className="space-y-2 flex-1 min-h-0 overflow-y-auto">
        {zones.length === 0 && <p className="text-gray-500 text-sm">Waiting for sensor data...</p>}
        {zones.map(z => {
          const sev = z.risk?.severity || 'normal'
          return (
            <div key={z.zone_id} className={clsx('p-2 rounded-lg border', SEVERITY_BG[sev])}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-bold text-gray-200">{z.zone_name?.replace(/_/g, ' ') ?? z.zone_id}</span>
                <span className={clsx('text-xs font-bold px-2 py-0.5 rounded-full', {
                  'bg-red-500/20 text-red-400': sev === 'extreme',
                  'bg-orange-500/20 text-orange-400': sev === 'critical',
                  'bg-yellow-500/20 text-yellow-400': sev === 'warning',
                  'bg-gray-500/20 text-gray-400': sev === 'normal',
                })}>{sev.toUpperCase()}</span>
              </div>
              <div className="grid grid-cols-4 gap-1 text-[10px] text-gray-400">
                <div className="flex items-center gap-1"><Wind className="w-3 h-3" /> CO: {getReading(z.readings, 'co_ppm') ?? '-'}</div>
                <div className="flex items-center gap-1"><Droplets className="w-3 h-3" /> H2S: {getReading(z.readings, 'h2s_ppm') ?? '-'}</div>
                <div className="flex items-center gap-1"><Flame className="w-3 h-3" /> CH4: {getReading(z.readings, 'methane_ppm') ?? '-'}</div>
                <div className="flex items-center gap-1"><Thermometer className="w-3 h-3" /> {getReading(z.readings, 'temperature') ?? '-'}°C</div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
