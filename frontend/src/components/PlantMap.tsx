import { ZoneRisk, ZoneMeta, WorkerLocation } from '../App'

const WORKER_COLOR = '#38bdf8' // sky-blue — a distinct hue from the severity palette, since this is a different signal (presence, not risk)

function initials(name: string): string {
  return name.split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase()
}

// Severity palette — validated for CVD + normal-vision separation between adjacent
// steps (dataviz skill: worst adjacent pair ΔE 15.3 CVD / 20.7 normal, both pass).
// Never rely on color alone — every zone also carries a text severity label.
const SEVERITY_COLORS: Record<string, { fill: string; stroke: string; text: string; glow: string }> = {
  extreme:  { fill: '#5c0a22', stroke: '#fb7185', text: '#fecdd3', glow: 'rgba(251,113,133,0.55)' },
  critical: { fill: '#9a3412', stroke: '#fb923c', text: '#fed7aa', glow: 'rgba(251,146,60,0.5)' },
  warning:  { fill: '#854d0e', stroke: '#fde047', text: '#fef9c3', glow: 'rgba(253,224,71,0.45)' },
  normal:   { fill: '#1e2b3f', stroke: '#64748b', text: '#cbd5e1', glow: 'transparent' },
}

export default function PlantMap({
  zones, zoneRisks, workers, onZoneClick,
}: {
  zones: Record<string, ZoneMeta>
  zoneRisks: Record<string, ZoneRisk>
  workers: WorkerLocation[]
  onZoneClick: (zoneId: string) => void
}) {
  const workersByZone: Record<string, WorkerLocation[]> = {}
  for (const w of workers) {
    (workersByZone[w.zone_id] ??= []).push(w)
  }
  const zoneList = Object.values(zones)

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Plant Risk Heatmap</h2>
        <span className="text-[10px] text-gray-600 uppercase tracking-wider">{zoneList.length} zones</span>
      </div>

      <div className="flex gap-4">
        <div className="flex-1 grid grid-cols-3 grid-rows-2 gap-3" style={{ minHeight: '360px' }}>
          {zoneList.map(zone => {
            const risk = zoneRisks[zone.zone_id]
            const severity = risk?.risk?.severity || 'normal'
            const colors = SEVERITY_COLORS[severity] || SEVERITY_COLORS.normal
            const score = risk?.risk?.compound_score ?? 0
            const isHot = severity === 'extreme' || severity === 'critical'
            const zoneWorkers = workersByZone[zone.zone_id] || []

            return (
              <button
                key={zone.zone_id}
                onClick={() => onZoneClick(zone.zone_id)}
                className="relative rounded-lg border-2 p-3 flex flex-col justify-between text-left transition-transform hover:scale-[1.02] focus:outline-none"
                style={{
                  backgroundColor: colors.fill,
                  borderColor: colors.stroke,
                  boxShadow: severity !== 'normal' ? `0 0 14px 1px ${colors.glow}` : 'none',
                  animation: isHot ? 'pulseCell 1.6s ease-in-out infinite' : undefined,
                }}
              >
                <div>
                  <div className="text-[13px] font-bold leading-tight" style={{ color: colors.text }}>
                    {zone.name}
                  </div>
                  <div
                    className="text-[9.5px] font-semibold uppercase tracking-wider mt-0.5"
                    style={{ color: colors.stroke }}
                  >
                    {severity}
                  </div>
                </div>

                <div className="flex items-end justify-between mt-3">
                  <div className="flex -space-x-2">
                    {zoneWorkers.map(w => (
                      <div
                        key={w.worker_id}
                        title={`${w.name} — ${w.role}`}
                        className="w-6 h-6 rounded-full flex items-center justify-center text-[8px] font-bold border"
                        style={{ backgroundColor: WORKER_COLOR, borderColor: colors.fill, color: '#04222f' }}
                      >
                        {initials(w.name)}
                      </div>
                    ))}
                  </div>
                  <div
                    className="rounded px-2 py-0.5 text-[11px] font-extrabold"
                    style={{ backgroundColor: `${colors.stroke}38`, color: colors.text }}
                  >
                    {(score * 100).toFixed(0)}%
                  </div>
                </div>
              </button>
            )
          })}
        </div>

        {/* Legend — discrete severity scale, since each cell holds one category rather
            than a continuous value */}
        <div className="flex flex-col items-center gap-2 pt-1">
          <span className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">Legend</span>
          {['extreme', 'critical', 'warning', 'normal'].map(s => (
            <div key={s} className="flex flex-col items-center gap-1">
              <div
                className="w-8 h-8 rounded border"
                style={{ backgroundColor: SEVERITY_COLORS[s].fill, borderColor: SEVERITY_COLORS[s].stroke }}
              />
              <span className="text-[9px] text-gray-400 capitalize">{s}</span>
            </div>
          ))}
          <div className="w-px h-3" />
          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: WORKER_COLOR }} />
          <span className="text-[9px] text-gray-400 text-center leading-tight">Worker<br />present</span>
        </div>
      </div>
    </div>
  )
}
