import { Fragment, useEffect, useState, useCallback } from 'react'
import { Download, ChevronDown, ChevronRight, ShieldCheck, Clock, FileSearch } from 'lucide-react'
import clsx from 'clsx'
import { ZoneMeta } from '../App'
import EvidenceModal from './EvidenceModal'

type AuditAction = {
  id: number
  action_type: string
  status: string
  human_confirmed: boolean
  executed_by: string
  executed_at: string | null
  evidence_id: number | null
}

type AuditRow = {
  alert_id: number
  zone_id: string
  zone_name: string
  severity: string
  compound_score: number | null
  lead_time_minutes: number | null
  explanation: string
  contributing_factors: string[]
  permit_id: string
  sent_at: string | null
  action: AuditAction | null
}

const ACTION_LABELS: Record<string, string> = {
  suspend_permit: 'Suspend permit',
  notify_supervisor: 'Notify supervisor',
  evacuate_zone: 'Evacuate zone',
}

const STATUS_STYLE: Record<string, string> = {
  pending_confirmation: 'bg-yellow-900/40 text-yellow-400 border-yellow-700',
  executed: 'bg-green-900/40 text-green-400 border-green-700',
  auto_executed: 'bg-blue-900/40 text-blue-400 border-blue-700',
}

function formatTime(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'medium' })
}

export default function AuditPage({ zones, apiBase }: { zones: Record<string, ZoneMeta>; apiBase: string }) {
  const [rows, setRows] = useState<AuditRow[]>([])
  const [loading, setLoading] = useState(true)
  const [zoneFilter, setZoneFilter] = useState('')
  const [severityFilter, setSeverityFilter] = useState('')
  const [expanded, setExpanded] = useState<number | null>(null)
  const [viewingEvidence, setViewingEvidence] = useState<number | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    const params = new URLSearchParams()
    if (zoneFilter) params.set('zone_id', zoneFilter)
    if (severityFilter) params.set('severity', severityFilter)
    fetch(`${apiBase}/api/audit?${params.toString()}`)
      .then(r => r.json())
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false))
  }, [apiBase, zoneFilter, severityFilter])

  useEffect(() => { load() }, [load])

  const exportCsv = useCallback(() => {
    const header = ['Time', 'Zone', 'Severity', 'Score', 'Lead time (min)', 'Action', 'Status', 'Human confirmed', 'Confirmed by', 'Confirmed at', 'Permit', 'Explanation']
    const lines = rows.map(r => [
      formatTime(r.sent_at),
      r.zone_name,
      r.severity,
      r.compound_score != null ? (r.compound_score * 100).toFixed(0) + '%' : '',
      r.lead_time_minutes ?? '',
      r.action ? (ACTION_LABELS[r.action.action_type] ?? r.action.action_type) : '',
      r.action?.status ?? '',
      r.action ? (r.action.human_confirmed ? 'yes' : 'no') : '',
      r.action?.executed_by ?? '',
      formatTime(r.action?.executed_at ?? null),
      r.permit_id,
      r.explanation.replace(/"/g, '""'),
    ])
    const csv = [header, ...lines].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `safetyai-audit-${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }, [rows])

  return (
    <div className="max-w-[1600px] mx-auto p-4 space-y-4">
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
        <div className="flex items-center justify-between mb-1">
          <div>
            <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Audit Trail</h2>
            <p className="text-xs text-gray-500 mt-1">
              Every alert fired and every action taken in response — who confirmed it, and when. This is the record for a regulatory or internal review.
            </p>
          </div>
          <button
            onClick={exportCsv}
            disabled={rows.length === 0}
            className="flex items-center gap-1.5 bg-gray-800 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed text-gray-200 text-sm font-medium px-3 py-2 rounded-lg transition"
          >
            <Download className="w-4 h-4" /> Export CSV
          </button>
        </div>

        <div className="flex items-center gap-3 mt-3">
          <select
            value={zoneFilter}
            onChange={e => setZoneFilter(e.target.value)}
            className="bg-gray-800 text-gray-200 text-sm rounded-lg px-2 py-1.5 border border-gray-700 focus:outline-none focus:border-blue-500"
          >
            <option value="">All zones</option>
            {Object.values(zones).map(z => (
              <option key={z.zone_id} value={z.zone_id}>{z.name}</option>
            ))}
          </select>
          <select
            value={severityFilter}
            onChange={e => setSeverityFilter(e.target.value)}
            className="bg-gray-800 text-gray-200 text-sm rounded-lg px-2 py-1.5 border border-gray-700 focus:outline-none focus:border-blue-500"
          >
            <option value="">All severities</option>
            <option value="warning">Warning</option>
            <option value="critical">Critical</option>
            <option value="extreme">Extreme</option>
          </select>
          <span className="text-xs text-gray-500">{rows.length} record{rows.length === 1 ? '' : 's'}</span>
        </div>
      </div>

      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        {loading ? (
          <p className="text-gray-500 text-sm p-6 text-center">Loading audit trail…</p>
        ) : rows.length === 0 ? (
          <p className="text-gray-500 text-sm p-6 text-center">No alerts recorded yet for this filter.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-950/60 text-gray-500 text-xs uppercase tracking-wider">
              <tr>
                <th className="text-left font-medium px-4 py-2 w-8"></th>
                <th className="text-left font-medium px-4 py-2">Time</th>
                <th className="text-left font-medium px-4 py-2">Zone</th>
                <th className="text-left font-medium px-4 py-2">Severity</th>
                <th className="text-left font-medium px-4 py-2">Score</th>
                <th className="text-left font-medium px-4 py-2">Action</th>
                <th className="text-left font-medium px-4 py-2">Confirmed by</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <Fragment key={r.alert_id}>
                  <tr
                    key={r.alert_id}
                    onClick={() => setExpanded(expanded === r.alert_id ? null : r.alert_id)}
                    className={clsx('border-t border-gray-800 cursor-pointer hover:bg-gray-800/40 transition', {
                      'bg-red-950/20': r.severity === 'extreme',
                      'bg-orange-950/20': r.severity === 'critical',
                      'bg-yellow-950/10': r.severity === 'warning',
                    })}
                  >
                    <td className="px-4 py-2.5 text-gray-500">
                      {expanded === r.alert_id ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    </td>
                    <td className="px-4 py-2.5 text-gray-400 whitespace-nowrap">
                      <div className="flex items-center gap-1.5"><Clock className="w-3.5 h-3.5" />{formatTime(r.sent_at)}</div>
                    </td>
                    <td className="px-4 py-2.5 text-gray-200 font-medium">{r.zone_name}</td>
                    <td className="px-4 py-2.5">
                      <span className={clsx('text-[10px] font-bold px-2 py-0.5 rounded-full uppercase', {
                        'bg-red-500/20 text-red-400': r.severity === 'extreme',
                        'bg-orange-500/20 text-orange-400': r.severity === 'critical',
                        'bg-yellow-500/20 text-yellow-400': r.severity === 'warning',
                      })}>{r.severity}</span>
                    </td>
                    <td className="px-4 py-2.5 text-gray-300 tabular-nums">
                      {r.compound_score != null ? `${(r.compound_score * 100).toFixed(0)}%` : '—'}
                    </td>
                    <td className="px-4 py-2.5">
                      {r.action ? (
                        <span className={clsx('text-[10px] font-bold px-2 py-0.5 rounded-full border', STATUS_STYLE[r.action.status] ?? 'bg-gray-800 text-gray-400 border-gray-700')}>
                          {ACTION_LABELS[r.action.action_type] ?? r.action.action_type} · {r.action.status.replace(/_/g, ' ')}
                        </span>
                      ) : (
                        <span className="text-gray-600 text-xs">no action proposed</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-gray-400 text-xs">
                      {r.action?.human_confirmed ? (
                        <span className="flex items-center gap-1"><ShieldCheck className="w-3.5 h-3.5 text-green-500" /> {r.action.executed_by || '—'}</span>
                      ) : r.action ? 'awaiting confirmation' : '—'}
                    </td>
                  </tr>
                  {expanded === r.alert_id && (
                    <tr className="border-t border-gray-800/60 bg-gray-950/40">
                      <td></td>
                      <td colSpan={6} className="px-4 py-3 text-xs text-gray-300 space-y-2">
                        <p className="leading-relaxed">{r.explanation}</p>
                        {r.contributing_factors?.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {r.contributing_factors.map((f, i) => (
                              <span key={i} className="bg-gray-800 text-gray-300 px-1.5 py-0.5 rounded text-[10px]">{f}</span>
                            ))}
                          </div>
                        )}
                        {r.permit_id && <p className="text-gray-500">Permit: {r.permit_id}</p>}
                        {r.action?.executed_at && (
                          <p className="text-gray-500">Executed at: {formatTime(r.action.executed_at)}</p>
                        )}
                        {r.action?.evidence_id != null && (
                          <button
                            onClick={(e) => { e.stopPropagation(); setViewingEvidence(r.action!.evidence_id) }}
                            className="flex items-center gap-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 px-2.5 py-1.5 rounded-lg text-[11px] font-bold transition"
                          >
                            <FileSearch className="w-3.5 h-3.5" /> View preserved evidence
                          </button>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {viewingEvidence != null && (
        <EvidenceModal evidenceId={viewingEvidence} apiBase={apiBase} onClose={() => setViewingEvidence(null)} />
      )}
    </div>
  )
}
