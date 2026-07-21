import { useEffect, useRef, useState } from 'react'
import { History, BookOpen, Clock } from 'lucide-react'
import clsx from 'clsx'
import { ZoneRisk, ZoneMeta } from '../App'

// Requires the same match to qualify on 2 consecutive ticks (~10s) before it's shown,
// and holds it visible for a minimum window after it stops qualifying — persistence to
// appear AND to disappear, so a score oscillating right at the backend's cutoff can't
// flicker in and out every 5s tick.
const CONFIRM_TICKS = 2
const HYSTERESIS_MS = 60_000
const SIMILARITY_CUTOFF = 0.5

type PrecautionEntry = {
  key: string
  zoneId: string
  zoneName: string
  severity: string
  mechanism: 'incident' | 'compliance'
  distance: number
  matchType?: 'incident' | 'near_miss'
  date?: string | null
  description?: string
  incidentSeverity?: string
  reportedBy?: string
  rootCause?: string
  clauseRef?: string
  source?: string
  content?: string
}

function similarityTier(distance: number): 'Strong' | 'Moderate' | 'Slight' {
  if (distance < SIMILARITY_CUTOFF / 3) return 'Strong'
  if (distance < (2 * SIMILARITY_CUTOFF) / 3) return 'Moderate'
  return 'Slight'
}

function buildCandidates(zoneRisks: Record<string, ZoneRisk>, zones: Record<string, ZoneMeta>): Record<string, PrecautionEntry> {
  const out: Record<string, PrecautionEntry> = {}
  for (const [zoneId, zr] of Object.entries(zoneRisks)) {
    const zoneName = zones[zoneId]?.name || zr.zone_name || zoneId
    const severity = zr.risk?.severity || 'normal'
    const ao = zr.risk?.agent_outputs

    // Backend already gates this at SIMILARITY_CUTOFF (incident_agent.py) — score is
    // only ever >0 for a genuinely close, vector-retrieved match. The UI never
    // re-derives that judgment, only displays it.
    const incident = ao?.incident
    const closest = incident?.matches?.[0]
    if (incident && incident.score > 0 && closest) {
      const key = `${zoneId}:incident:${closest.type}-${closest.id}`
      out[key] = {
        key, zoneId, zoneName, severity, mechanism: 'incident',
        distance: closest.distance ?? 0,
        matchType: closest.type, date: closest.date, description: closest.description,
        incidentSeverity: closest.severity, reportedBy: closest.reported_by, rootCause: closest.root_cause,
      }
    }

    // Same reasoning, mirrored gate from compliance_agent.py's precaution_eligible flag.
    const eligible = ao?.compliance?.citations?.find(c => c.precaution_eligible)
    if (eligible) {
      const key = `${zoneId}:compliance:${eligible.clause_ref}`
      out[key] = {
        key, zoneId, zoneName, severity, mechanism: 'compliance',
        distance: eligible.distance ?? 0,
        clauseRef: eligible.clause_ref, source: eligible.source, content: eligible.content,
      }
    }
  }
  return out
}

type Tracked = { count: number; lastTrue: number; firstConfirmedAt: number; entry: PrecautionEntry }

export default function PrecautionWatch({
  zoneRisks, zones, onZoneClick, compact,
}: {
  zoneRisks: Record<string, ZoneRisk>
  zones: Record<string, ZoneMeta>
  onZoneClick: (zoneId: string) => void
  compact?: boolean
}) {
  const seenRef = useRef<Map<string, Tracked>>(new Map())
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [, bump] = useState(0)
  const lastProcessedRef = useRef<Record<string, ZoneRisk> | null>(null)

  useEffect(() => {
    // Guards against processing the same tick's data twice — e.g. React StrictMode's
    // dev-mode mount→cleanup→mount replay — which would otherwise satisfy the 2-tick
    // confirm threshold off a single real backend tick with zero elapsed time.
    if (zoneRisks === lastProcessedRef.current) return
    lastProcessedRef.current = zoneRisks

    const candidates = buildCandidates(zoneRisks, zones)
    const now = Date.now()
    const seen = seenRef.current

    // "2 consecutive ticks" means consecutive: a not-yet-confirmed key that drops out
    // of this tick's candidates loses its progress entirely, rather than being left
    // untouched until the (much longer) hysteresis prune below fires. Once an entry IS
    // confirmed, absence no longer resets it — that's what the hysteresis hold is for.
    for (const [key, tracked] of seen) {
      if (tracked.firstConfirmedAt === 0 && !(key in candidates)) seen.delete(key)
    }

    for (const [key, entry] of Object.entries(candidates)) {
      const existing = seen.get(key)
      if (existing) {
        existing.count += 1
        existing.lastTrue = now
        existing.entry = entry // refresh displayed fields (distance/severity/etc.) every qualifying tick
      } else {
        seen.set(key, { count: 1, lastTrue: now, firstConfirmedAt: 0, entry })
      }
    }
    for (const tracked of seen.values()) {
      if (tracked.count >= CONFIRM_TICKS && tracked.firstConfirmedAt === 0) tracked.firstConfirmedAt = now
    }
    // Confirmed entries only get pruned after the full hysteresis hold of continuous
    // absence — never-confirmed ones were already deleted above, so nothing here needs
    // to check firstConfirmedAt again.
    for (const [key, tracked] of Array.from(seen.entries())) {
      if (!(key in candidates) && now - tracked.lastTrue > HYSTERESIS_MS) seen.delete(key)
    }
    bump(n => n + 1)
  }, [zoneRisks, zones])

  const entries = Array.from(seenRef.current.entries())
    .filter(([, t]) => t.count >= CONFIRM_TICKS)
    .map(([key, t]) => ({ ...t.entry, key, activeSince: t.firstConfirmedAt }))
    .sort((a, b) => {
      const hot = (s: string) => s === 'critical' || s === 'extreme'
      return Number(hot(a.severity)) - Number(hot(b.severity))
    })

  if (entries.length === 0) return null

  const toggleExpand = (key: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  return (
    <div className={clsx('bg-gray-900 rounded-xl border border-blue-900/40', compact ? 'p-3' : 'p-4')}>
      <div className="flex items-center gap-2 mb-3">
        <History className="w-4 h-4 text-blue-400" />
        <h2 className="text-sm font-semibold text-blue-300 uppercase tracking-wider">Precaution Watch</h2>
      </div>

      <div className="space-y-2">
        {entries.map(e => {
          const isHot = e.severity === 'critical' || e.severity === 'extreme'
          const longText = e.mechanism === 'incident' ? (e.description || '') : (e.content || '')
          const isLong = longText.length > 200
          const isExpanded = expanded.has(e.key)
          const shownText = isLong && !isExpanded ? longText.slice(0, 200) + '…' : longText

          return (
            <div
              key={e.key}
              className={clsx(
                'bg-gray-950/50 border border-blue-900/30 rounded-lg p-3 cursor-pointer hover:border-blue-700/50 transition',
                isHot && 'opacity-60'
              )}
              onClick={() => onZoneClick(e.zoneId)}
            >
              <div className="flex items-center justify-between mb-1.5 flex-wrap gap-1">
                <span className="flex items-center gap-1.5 text-[9.5px] font-bold uppercase tracking-wide text-blue-300 bg-blue-950/60 px-1.5 py-0.5 rounded">
                  {e.mechanism === 'incident' ? <Clock className="w-3 h-3" /> : <BookOpen className="w-3 h-3" />}
                  {e.mechanism === 'incident' ? 'Incident Pattern Intelligence — vector similarity search' : 'Compliance RAG — regulation match'}
                </span>
                <span className="text-[10px] text-gray-500 whitespace-nowrap">
                  active since {new Date(e.activeSince).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>

              <div className="text-xs font-bold text-gray-200 mb-1">{e.zoneName}</div>

              {e.mechanism === 'incident' ? (
                <>
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className={clsx(
                      // Deliberately nowhere near the app's severity palette (red/orange/
                      // yellow, see index.css's .severity-critical etc.) — a precaution
                      // must never be color-confusable with a live alert.
                      'text-[9px] font-bold uppercase px-1.5 py-0.5 rounded',
                      e.matchType === 'incident' ? 'bg-indigo-900/40 text-indigo-300' : 'bg-slate-700/50 text-slate-300'
                    )}>
                      {e.matchType === 'incident' ? 'Incident' : 'Near-miss — caught before harm'}
                    </span>
                    <span className="text-[10px] text-gray-500">{e.date} · {e.zoneName}</span>
                  </div>
                  <p className="text-xs text-gray-300 leading-relaxed">
                    {shownText}
                    {isLong && (
                      <button onClick={(ev) => { ev.stopPropagation(); toggleExpand(e.key) }} className="text-blue-400 hover:text-blue-300 ml-1 font-semibold">
                        {isExpanded ? 'view less' : 'view more'}
                      </button>
                    )}
                  </p>
                  {e.rootCause && <p className="text-[10px] text-gray-500 mt-1">Root cause: {e.rootCause}</p>}
                  {e.reportedBy && !e.rootCause && <p className="text-[10px] text-gray-500 mt-1">Reported by: {e.reportedBy}</p>}
                </>
              ) : (
                <>
                  <div className="text-[10px] text-gray-500 mb-1">{e.source} — {e.clauseRef}</div>
                  <p className="text-xs text-gray-300 leading-relaxed">
                    {shownText}
                    {isLong && (
                      <button onClick={(ev) => { ev.stopPropagation(); toggleExpand(e.key) }} className="text-blue-400 hover:text-blue-300 ml-1 font-semibold">
                        {isExpanded ? 'view less' : 'view more'}
                      </button>
                    )}
                  </p>
                </>
              )}

              <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-gray-800/60 gap-2">
                <span className="text-[10px] font-bold text-blue-300 whitespace-nowrap">{similarityTier(e.distance)} similarity</span>
                {/* Repeated per-card, not just once in the shared footer below — a user
                    who only scrolls to or acts on one card must still see this caveat. */}
                <span className="text-[9px] text-gray-600 text-right">not a likelihood of recurrence</span>
              </div>
            </div>
          )
        })}
      </div>

      <p className="text-[9px] text-gray-600 mt-3 pt-2 border-t border-gray-800 leading-relaxed">
        Text similarity to historical record — not a likelihood of recurrence. Matched against a small seeded reference
        set (3 incidents + 4 near-misses across 4 of 6 zones) — not a trained model, not a prediction.
      </p>
    </div>
  )
}
