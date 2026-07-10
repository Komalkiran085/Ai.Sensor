import { ZoneRisk } from '../App'
import clsx from 'clsx'

const ZONE_LAYOUT: Record<string, { x: number; y: number; w: number; h: number }> = {
  BLAST_FURNACE_1: { x: 50, y: 30, w: 200, h: 120 },
  BATTERY_3:       { x: 280, y: 30, w: 200, h: 120 },
  STORAGE_TANK_A:  { x: 510, y: 30, w: 180, h: 120 },
  WORKSHOP_B:      { x: 50, y: 180, w: 200, h: 110 },
  CONTROL_ROOM:    { x: 280, y: 180, w: 200, h: 110 },
  UTILITY_AREA:    { x: 510, y: 180, w: 180, h: 110 },
}

const ZONE_LABELS: Record<string, string> = {
  BLAST_FURNACE_1: 'Blast Furnace 1',
  BATTERY_3: 'Coke Oven Battery 3',
  STORAGE_TANK_A: 'Chemical Storage A',
  WORKSHOP_B: 'Workshop B',
  CONTROL_ROOM: 'Control Room',
  UTILITY_AREA: 'Utility Area',
}

const SEVERITY_COLORS: Record<string, { fill: string; stroke: string; text: string }> = {
  extreme:  { fill: '#7f1d1d', stroke: '#ef4444', text: '#fca5a5' },
  critical: { fill: '#7c2d12', stroke: '#f97316', text: '#fdba74' },
  warning:  { fill: '#78350f', stroke: '#eab308', text: '#fde047' },
  normal:   { fill: '#1e293b', stroke: '#475569', text: '#94a3b8' },
}

export default function PlantMap({ zoneRisks, onZoneClick }: { zoneRisks: Record<string, ZoneRisk>; onZoneClick: (zone: string) => void }) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
      <h2 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">Plant Geospatial Heatmap</h2>
      <svg viewBox="0 0 740 320" className="w-full" style={{ maxHeight: '400px' }}>
        {/* Grid background */}
        <defs>
          <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="#1e293b" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width="740" height="320" fill="#0f172a" rx="8" />
        <rect width="740" height="320" fill="url(#grid)" rx="8" />

        {Object.entries(ZONE_LAYOUT).map(([zoneId, pos]) => {
          const risk = zoneRisks[zoneId]
          const severity = risk?.risk?.severity || 'normal'
          const colors = SEVERITY_COLORS[severity] || SEVERITY_COLORS.normal
          const score = risk?.risk?.compound_score ?? 0
          const co = risk?.reading?.co_ppm ?? '-'

          return (
            <g key={zoneId} onClick={() => onZoneClick(zoneId)} className="cursor-pointer">
              <rect
                x={pos.x} y={pos.y} width={pos.w} height={pos.h}
                rx={6}
                fill={colors.fill}
                stroke={colors.stroke}
                strokeWidth={severity === 'extreme' || severity === 'critical' ? 2.5 : 1.5}
                opacity={0.9}
              >
                {(severity === 'extreme' || severity === 'critical') && (
                  <animate attributeName="opacity" values="0.9;0.5;0.9" dur="1.5s" repeatCount="indefinite" />
                )}
              </rect>

              <text x={pos.x + pos.w / 2} y={pos.y + 22} textAnchor="middle" fontSize="11" fontWeight="bold" fill={colors.text}>
                {ZONE_LABELS[zoneId]}
              </text>

              <text x={pos.x + pos.w / 2} y={pos.y + 45} textAnchor="middle" fontSize="10" fill="#94a3b8">
                CO: {co} ppm
              </text>

              <text x={pos.x + pos.w / 2} y={pos.y + 65} textAnchor="middle" fontSize="10" fill="#94a3b8">
                H2S: {risk?.reading?.h2s_ppm ?? '-'} ppm
              </text>

              {/* Risk score badge */}
              <rect x={pos.x + pos.w - 55} y={pos.y + pos.h - 30} width={45} height={20} rx={4} fill={colors.stroke} opacity={0.3} />
              <text x={pos.x + pos.w - 32} y={pos.y + pos.h - 16} textAnchor="middle" fontSize="10" fontWeight="bold" fill={colors.text}>
                {(score * 100).toFixed(0)}%
              </text>

              {/* Severity label */}
              <text x={pos.x + 10} y={pos.y + pos.h - 12} fontSize="9" fontWeight="600" fill={colors.stroke} style={{ textTransform: 'uppercase' }}>
                {severity.toUpperCase()}
              </text>
            </g>
          )
        })}
      </svg>

      <div className="flex items-center gap-4 mt-3 justify-center">
        {['normal', 'warning', 'critical', 'extreme'].map(s => (
          <div key={s} className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: SEVERITY_COLORS[s].stroke }} />
            <span className="text-xs text-gray-400 capitalize">{s}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
