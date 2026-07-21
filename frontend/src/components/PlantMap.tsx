import { useMemo } from 'react'
import { Flame, ShieldAlert, Zap, Wrench, Search, History } from 'lucide-react'
import { ZoneRisk, ZoneMeta, WorkerLocation } from '../App'

const WORKER_DOT = '#0a0a0a' // solid black dots — presence markers, distinct from the heat gradient

const SEVERITY_LABEL: Record<string, string> = {
  extreme: 'Extreme', critical: 'Critical', warning: 'Warning', normal: 'Normal',
}

// Static per-zone hazard rating, independent of live risk severity — the heat gradient
// already conveys "how dangerous is it right now"; this conveys "how dangerous is this
// kind of zone by nature," a fixed dot rather than something that competes with the
// color-coded tile for attention.
const HAZARD_COLOR: Record<string, string> = { high: '#fb7185', medium: '#fbbf24', low: '#94a3b8' }

// One icon per permit work type — an active hazardous permit overlaid directly on the
// zone it's in, not just buried in a side panel list.
const PERMIT_ICON: Record<string, typeof Flame> = {
  hot_work: Flame,
  confined_space_entry: ShieldAlert,
  electrical_isolation: Zap,
  general_maintenance: Wrench,
  inspection: Search,
}

// Multi-stop heat gradient (green -> light yellow -> gold -> orange -> red), rather than a
// single linear hue sweep — a plain green(0)->red(1) lerp spends most of its range as murky
// orange, so a merely-elevated neighbor and an actually-critical zone read as the same
// muddy color. These stops deliberately widen the "light yellow" band for zones that are
// only picking up bleed from a nearby hazard, and push true red to kick in by the time a
// zone reaches "critical" (score 0.8) rather than only at "extreme" (1.0).
const COLOR_STOPS: { t: number; h: number; s: number; l: number }[] = [
  { t: 0.00, h: 118, s: 62, l: 45 }, // green — normal
  { t: 0.10, h: 90, s: 62, l: 60 },  // faint yellow-green — earliest hint of a nearby hazard
  { t: 0.22, h: 56, s: 78, l: 74 },  // light yellow — this is the "surrounding zone" color
  { t: 0.40, h: 42, s: 88, l: 60 },  // gold
  { t: 0.58, h: 26, s: 90, l: 52 },  // orange — warning
  { t: 0.80, h: 5, s: 82, l: 44 },   // red — critical
  { t: 1.00, h: 0, s: 88, l: 38 },   // rich red — extreme (lighter to blend with spread)
]

function scoreToColor(score: number): string {
  const s = Math.max(0, Math.min(1, score))
  for (let i = 0; i < COLOR_STOPS.length - 1; i++) {
    const a = COLOR_STOPS[i], b = COLOR_STOPS[i + 1]
    if (s <= b.t) {
      const f = (s - a.t) / (b.t - a.t)
      return `hsl(${a.h + (b.h - a.h) * f}, ${a.s + (b.s - a.s) * f}%, ${a.l + (b.l - a.l) * f}%)`
    }
  }
  const last = COLOR_STOPS[COLOR_STOPS.length - 1]
  return `hsl(${last.h}, ${last.s}%, ${last.l}%)`
}

const GRADIENT_CSS = `linear-gradient(to top, ${COLOR_STOPS.map(s => `hsl(${s.h},${s.s}%,${s.l}%) ${s.t * 100}%`).join(', ')})`

// Deterministic pseudo-random 0..1 pair (seeded by worker_id) — stable across re-renders/polls
// so dots don't jump around, but still scattered rather than stacked in one spot.
function hashUnit(seed: string): { u: number; v: number } {
  let h = 0
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0
  const u = (h % 1000) / 1000
  const v = (Math.floor(h / 1000) % 1000) / 1000
  return { u, v }
}

function polygonCentroid(poly: number[][]): [number, number] {
  let sx = 0, sy = 0
  for (const [x, y] of poly) { sx += x; sy += y }
  return [sx / poly.length, sy / poly.length]
}

function polygonBBox(poly: number[][]) {
  const xs = poly.map(p => p[0]), ys = poly.map(p => p[1])
  return { minX: Math.min(...xs), maxX: Math.max(...xs), minY: Math.min(...ys), maxY: Math.max(...ys) }
}

// Standard ray-casting point-in-polygon test.
function pointInPolygon(x: number, y: number, poly: number[][]): boolean {
  let inside = false
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i]
    const [xj, yj] = poly[j]
    const intersect = (yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi
    if (intersect) inside = !inside
  }
  return inside
}

const GRID_COLS = 56
// Distance (in plant coordinate units) beyond which a zone's risk barely bleeds into its
// surroundings — controls how far a critical/extreme zone's red visibly spreads into
// neighboring, otherwise-normal zones before fading back to green.
const BLEED_RADIUS = 300

// Groups 1D positions that are close together, splitting into a new group wherever the
// gap between consecutive (sorted) positions exceeds ~12% of the total span. Used to find
// the plant's actual row/column structure from zone centroids, instead of hardcoding a
// layout — so any plant.config.yaml (any zone count/arrangement) still tiles cleanly.
function clusterAxis<T>(items: T[], pos: (t: T) => number, extent: number): T[][] {
  const sorted = [...items].sort((a, b) => pos(a) - pos(b))
  const threshold = Math.max(extent * 0.12, 1)
  const groups: T[][] = [[sorted[0]]]
  for (let i = 1; i < sorted.length; i++) {
    if (pos(sorted[i]) - pos(sorted[i - 1]) > threshold) groups.push([])
    groups[groups.length - 1].push(sorted[i])
  }
  return groups
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

  const layout = useMemo(() => {
    if (zoneList.length === 0) return null

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
    for (const z of zoneList) {
      for (const [x, y] of z.boundary) {
        minX = Math.min(minX, x); maxX = Math.max(maxX, x)
        minY = Math.min(minY, y); maxY = Math.max(maxY, y)
      }
    }
    const padX = (maxX - minX) * 0.08 || 20
    const padY = (maxY - minY) * 0.08 || 20
    minX -= padX; maxX += padX; minY -= padY; maxY += padY
    const width = maxX - minX
    const height = maxY - minY

    const zoneInfo = zoneList.map(z => {
      const [cx, cy] = polygonCentroid(z.boundary)
      const risk = zoneRisks[z.zone_id]
      const score = risk?.risk?.compound_score ?? 0
      const severity = risk?.risk?.severity || 'normal'
      const activePermit = (risk?.permits ?? []).find((p: any) => p.status === 'active') ?? null
      // Same backend-owned gate PrecautionWatch uses (incident.score / compliance
      // precaution_eligible are only ever nonzero for a genuinely close vector match) —
      // this badge just mirrors that judgment on the map, it never re-derives it.
      const ao = risk?.risk?.agent_outputs
      const hasPrecaution = Boolean(
        (ao?.incident?.score ?? 0) > 0 || ao?.compliance?.citations?.some((c: any) => c.precaution_eligible)
      )
      return { zone: z, cx, cy, score, severity, activePermit, hasPrecaution, bbox: polygonBBox(z.boundary) }
    })

    // Zone ownership is a straight-line partition, not a shape-traced one: cluster zones
    // into rows by Y, then within each row cluster into columns by X, and split with plain
    // horizontal/vertical lines at the midpoints between neighbors. That guarantees every
    // border is a straight line (geometrically, not by smoothing) and the grid fully tiles
    // with no gaps, while still being derived from each zone's real position — not hardcoded.
    const rowGroups = clusterAxis(zoneInfo, z => z.cy, height)
    const rowAvgY = rowGroups.map(g => g.reduce((s, z) => s + z.cy, 0) / g.length)
    const rowBounds = [minY, ...rowAvgY.slice(0, -1).map((y, i) => (y + rowAvgY[i + 1]) / 2), maxY]

    const rowBands = rowGroups.map((group, i) => {
      const sorted = [...group].sort((a, b) => a.cx - b.cx)
      const colAvgX = sorted.map(z => z.cx)
      const colBounds = [minX, ...colAvgX.slice(0, -1).map((x, j) => (x + colAvgX[j + 1]) / 2), maxX]
      const cols = sorted.map((z, j) => ({ xStart: colBounds[j], xEnd: colBounds[j + 1], zoneId: z.zone.zone_id }))
      return { yStart: rowBounds[i], yEnd: rowBounds[i + 1], cols }
    })

    function ownerAt(px: number, py: number): string | null {
      const band = rowBands.find(b => py >= b.yStart && py <= b.yEnd) ?? rowBands[rowBands.length - 1]
      const col = band.cols.find(c => px >= c.xStart && px <= c.xEnd) ?? band.cols[band.cols.length - 1]
      return col?.zoneId ?? null
    }

    const severityById = Object.fromEntries(zoneInfo.map(z => [z.zone.zone_id, z.severity]))

    // Heat diffusion: for each cell, compute blended score from all zones.
    // Critical/extreme zones spread their color into neighbors using distance
    // from the zone's nearest boundary edge (not centroid), creating a smooth
    // gradient that fades from the critical zone outward.
    const INSIDE_WEIGHT = 6
    const gridCols = GRID_COLS
    const gridRows = Math.max(10, Math.round(gridCols * (height / width)))
    const cellW = width / gridCols
    const cellH = height / gridRows

    // Distance from point to nearest edge segment of a polygon
    function distToPolygon(px: number, py: number, poly: number[][]): number {
      let minD = Infinity
      for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
        const [ax, ay] = poly[j], [bx, by] = poly[i]
        const dx = bx - ax, dy = by - ay
        const t = Math.max(0, Math.min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
        const d = Math.hypot(px - (ax + t * dx), py - (ay + t * dy))
        if (d < minD) minD = d
      }
      return minD
    }

    type Cell = { x: number; y: number; color: string; owner: string | null; isHot: boolean }
    const grid: Cell[][] = []
    for (let row = 0; row < gridRows; row++) {
      const rowCells: Cell[] = []
      for (let col = 0; col < gridCols; col++) {
        const px = minX + (col + 0.5) * cellW
        const py = minY + (row + 0.5) * cellH
        const owner = ownerAt(px, py)
        const ownerZone = zoneInfo.find(z => z.zone.zone_id === owner)
        const ownerScore = ownerZone?.score ?? 0

        // Compute max bleed influence from other hot zones based on edge distance
        let bleedScore = ownerScore
        for (const zi of zoneInfo) {
          if (zi.zone.zone_id === owner) continue
          if (zi.score < 0.5) continue // only spread from warning+ zones
          const inside = pointInPolygon(px, py, zi.zone.boundary)
          const edgeDist = inside ? 0 : distToPolygon(px, py, zi.zone.boundary)
          const influence = Math.max(0, 1 - edgeDist / BLEED_RADIUS)
          const contributed = zi.score * Math.pow(influence, 1.5)
          if (contributed > bleedScore) bleedScore = contributed
        }

        // Inside own zone: blend own score with bleed (bleed wins if higher)
        const isInside = ownerZone ? pointInPolygon(px, py, ownerZone.zone.boundary) : false
        let finalScore: number
        if (isInside) {
          // Own zone: use max of own score and bleed, with smooth blend near edges
          const edgeDistOwn = distToPolygon(px, py, ownerZone!.zone.boundary)
          const depthFactor = Math.min(1, edgeDistOwn / (BLEED_RADIUS * 0.3))
          finalScore = ownerScore * depthFactor + bleedScore * (1 - depthFactor)
          if (finalScore < ownerScore) finalScore = ownerScore
        } else {
          finalScore = bleedScore
        }

        const ownerSeverity = owner ? severityById[owner] : 'normal'
        const isHot = ownerSeverity === 'extreme' || ownerSeverity === 'critical'
        rowCells.push({ x: minX + col * cellW, y: minY + row * cellH, color: scoreToColor(finalScore), owner, isHot })
      }
      grid.push(rowCells)
    }

    // Trace a blocky outline around each zone's cell footprint: for every cell that
    // belongs to a zone, emit a border segment on any side whose neighbor (or grid edge)
    // isn't that same zone.
    const bordersByZone: Record<string, string> = {}
    for (let row = 0; row < gridRows; row++) {
      for (let col = 0; col < gridCols; col++) {
        const cell = grid[row][col]
        if (!cell.owner) continue
        const owner = cell.owner
        const { x, y } = cell
        let d = ''
        if (row === 0 || grid[row - 1][col].owner !== owner) d += `M${x},${y} L${x + cellW},${y} `
        if (row === gridRows - 1 || grid[row + 1][col].owner !== owner) d += `M${x},${y + cellH} L${x + cellW},${y + cellH} `
        if (col === 0 || grid[row][col - 1].owner !== owner) d += `M${x},${y} L${x},${y + cellH} `
        if (col === gridCols - 1 || grid[row][col + 1].owner !== owner) d += `M${x + cellW},${y} L${x + cellW},${y + cellH} `
        if (d) bordersByZone[owner] = (bordersByZone[owner] || '') + d
      }
    }

    const cells = grid.flat()

    return { minX, minY, width, height, cellW, cellH, cells, bordersByZone, zoneInfo }
  }, [zoneList, zoneRisks])

  if (!layout) {
    return (
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Plant Risk Heatmap</h2>
        <div className="text-xs text-gray-600 mt-4">Loading plant layout...</div>
      </div>
    )
  }

  const { minX, minY, width, height, cellW, cellH, cells, bordersByZone, zoneInfo } = layout
  const borderW = Math.min(cellW, cellH)

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Plant Risk Heatmap</h2>
        <span className="text-[10px] text-gray-600 uppercase tracking-wider">{zoneList.length} zones</span>
      </div>

      <div className="flex gap-4">
        <div className="relative flex-1 rounded-md overflow-hidden border border-black/50" style={{ height: 380 }}>
          <svg
            viewBox={`${minX} ${minY} ${width} ${height}`}
            preserveAspectRatio="none"
            className="absolute inset-0 w-full h-full"
          >
            {/* Diffused heat grid — real gas/risk spread across the actual plant layout.
                Cells belonging to a currently hot zone pulse in place, so the alarm
                reads as part of the grid itself rather than a shape drawn over it. */}
            <g>
              {cells.map((c, i) => (
                <rect
                  key={i} x={c.x} y={c.y} width={cellW + 0.5} height={cellH + 0.5}
                  fill={c.color} stroke="rgba(0,0,0,0.12)" strokeWidth={Math.min(cellW, cellH) * 0.04}
                  style={{ animation: c.isHot ? 'pulseCell 1.6s ease-in-out infinite' : undefined }}
                />
              ))}
            </g>

            {/* Zone borders — traced along the grid cells each zone actually occupies,
                so the boundary is grid-shaped (sized to the zone's real footprint)
                instead of a separate circle/polygon drawn on top. Double-stroked (dark
                under white) so it stays legible against every color in the gradient. */}
            <g fill="none" strokeLinecap="square" strokeLinejoin="miter">
              {zoneInfo.map(zi => (
                <path key={`border-dark-${zi.zone.zone_id}`} d={bordersByZone[zi.zone.zone_id] || ''} stroke="rgba(0,0,0,0.65)" strokeWidth={borderW * 0.55} />
              ))}
              {zoneInfo.map(zi => (
                <path key={`border-light-${zi.zone.zone_id}`} d={bordersByZone[zi.zone.zone_id] || ''} stroke="rgba(255,255,255,0.9)" strokeWidth={borderW * 0.28} />
              ))}
            </g>

            {/* Invisible click targets — real zone shape, for accurate hit-testing */}
            <g>
              {zoneInfo.map(zi => (
                <polygon
                  key={zi.zone.zone_id}
                  points={zi.zone.boundary.map(p => p.join(',')).join(' ')}
                  fill="transparent"
                  className="cursor-pointer"
                  onClick={() => onZoneClick(zi.zone.zone_id)}
                >
                  <title>{zi.zone.name}</title>
                </polygon>
              ))}
            </g>

            {/* Worker initials — scattered within each zone's real footprint */}
            <g>
              {zoneInfo.flatMap(zi => {
                const zoneWorkers = workersByZone[zi.zone.zone_id] || []
                const { minX: bx, minY: by, maxX: bX, maxY: bY } = zi.bbox
                return zoneWorkers.map(w => {
                  const { u, v } = hashUnit(w.worker_id)
                  const wx = bx + 0.2 * (bX - bx) + u * 0.6 * (bX - bx)
                  const wy = by + 0.2 * (bY - by) + v * 0.6 * (bY - by)
                  const r = Math.min(cellW, cellH) * 1.1
                  const initial = (w.name || '?')[0].toUpperCase()
                  return (
                    <g key={w.worker_id}>
                      <circle cx={wx} cy={wy} r={r}
                        fill="#1e293b" stroke="white" strokeWidth={r * 0.2}
                      />
                      <text x={wx} y={wy} textAnchor="middle" dominantBaseline="central"
                        fill="white" fontSize={r * 1.3} fontWeight="bold"
                      >{initial}</text>
                      <title>{w.name} — {w.role}</title>
                    </g>
                  )
                })
              })}
            </g>
          </svg>

          {/* Zone name / severity / score labels — HTML overlay for crisp, readable text.
              Always present so severity is never conveyed by color alone. */}
          {zoneInfo.map(zi => {
            const leftPct = ((zi.cx - minX) / width) * 100
            const topPct = ((zi.bbox.minY - minY) / height) * 100
            return (
              <div
                key={`label-${zi.zone.zone_id}`}
                className="absolute pointer-events-none flex flex-col items-center -translate-x-1/2"
                style={{ left: `${leftPct}%`, top: `${topPct}%`, marginTop: 4 }}
              >
                <span className="flex items-center gap-1">
                  <span
                    className="w-1.5 h-1.5 rounded-full shrink-0 border border-black/40"
                    style={{ backgroundColor: HAZARD_COLOR[zi.zone.hazard_classification] || HAZARD_COLOR.low }}
                    title={`Hazard classification: ${zi.zone.hazard_classification}`}
                  />
                  <span className="text-[11px] font-extrabold leading-tight text-white drop-shadow-[0_1px_3px_rgba(0,0,0,0.95)] text-center whitespace-nowrap">
                    {zi.zone.name}
                  </span>
                  {zi.activePermit && (() => {
                    const Icon = PERMIT_ICON[zi.activePermit.work_type] || Wrench
                    return (
                      <span className="bg-black/60 rounded-full p-0.5 pointer-events-auto" title={`Active permit: ${zi.activePermit.permit_id} (${zi.activePermit.work_type.replace(/_/g, ' ')})`}>
                        <Icon className="w-2.5 h-2.5 text-amber-300" />
                      </span>
                    )
                  })()}
                  {zi.hasPrecaution && (
                    <span
                      className="bg-black/60 rounded-full p-0.5 pointer-events-auto cursor-pointer"
                      title="Precaution: current conditions resemble a past incident/near-miss or regulation match — see Precaution Watch"
                      onClick={() => onZoneClick(zi.zone.zone_id)}
                    >
                      <History className="w-2.5 h-2.5 text-blue-300" />
                    </span>
                  )}
                </span>
                <span className="flex items-center gap-1 mt-0.5">
                  <span className="text-[8.5px] font-bold uppercase tracking-wider text-white/95 bg-black/50 rounded px-1 py-0.5">
                    {SEVERITY_LABEL[zi.severity] || zi.severity}
                  </span>
                  <span className="text-[9.5px] font-extrabold text-white bg-black/50 rounded px-1 py-0.5">
                    {(zi.score * 100).toFixed(0)}%
                  </span>
                </span>
              </div>
            )
          })}
        </div>

        {/* Legend — continuous gradient bar (since color is now driven by score, blended
            spatially) plus the worker-dot marker */}
        <div className="flex flex-col items-center gap-2 pt-1 w-14">
          <span className="text-[10px] text-gray-500 uppercase tracking-wider mb-1 text-center">Risk</span>
          <div
            className="w-4 rounded"
            style={{ height: 160, background: GRADIENT_CSS }}
          />
          <div className="flex flex-col items-center text-[8px] text-gray-500 -mt-1">
            <span>High</span>
          </div>
          <div className="w-px h-3" />
          <div className="w-3.5 h-3.5 rounded-full border-2 border-white/80 bg-slate-800 flex items-center justify-center text-[7px] font-bold text-white">A</div>
          <span className="text-[9px] text-gray-400 text-center leading-tight">Worker<br />present</span>
          <div className="w-px h-3" />
          <div className="flex gap-1">
            {(['high', 'medium', 'low'] as const).map(h => (
              <span key={h} className="w-1.5 h-1.5 rounded-full border border-black/40" style={{ backgroundColor: HAZARD_COLOR[h] }} title={`${h} hazard classification`} />
            ))}
          </div>
          <span className="text-[9px] text-gray-400 text-center leading-tight">Hazard<br />class</span>
          <div className="w-px h-3" />
          <Flame className="w-3 h-3 text-amber-300" />
          <span className="text-[9px] text-gray-400 text-center leading-tight">Active<br />permit</span>
          <div className="w-px h-3" />
          <History className="w-3 h-3 text-blue-300" />
          <span className="text-[9px] text-gray-400 text-center leading-tight">Precaution<br />match</span>
        </div>
      </div>
    </div>
  )
}
