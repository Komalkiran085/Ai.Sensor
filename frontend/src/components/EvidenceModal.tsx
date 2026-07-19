import { useEffect, useState } from 'react'
import { X, ShieldCheck, Loader2 } from 'lucide-react'

type Evidence = {
  id: number
  action_id: number
  zone_id: string
  captured_at: string
  sensor_snapshot: { sensor_id: string; sensor_type: string; value: number }[]
  permit_snapshot: any[]
  shift_snapshot: Record<string, any>
  risk_snapshot: { compound_score: number; severity: string; lead_time_minutes: number | null; contributing_factors: string[] }
}

export default function EvidenceModal({ evidenceId, apiBase, onClose }: { evidenceId: number; apiBase: string; onClose: () => void }) {
  const [evidence, setEvidence] = useState<Evidence | null>(null)

  useEffect(() => {
    fetch(`${apiBase}/api/evidence/${evidenceId}`).then(r => r.json()).then(setEvidence).catch(() => {})
  }, [evidenceId, apiBase])

  return (
    <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-8" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-green-400" />
            <h3 className="text-lg font-bold text-white">Preserved Evidence</h3>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white transition">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 overflow-y-auto max-h-[65vh] text-sm">
          {!evidence ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-xs text-gray-500">
                Captured {new Date(evidence.captured_at).toLocaleString()} — zone: {evidence.zone_id.replace(/_/g, ' ')}
              </p>

              <div>
                <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5">Risk at capture</h4>
                <p className="text-gray-300">
                  {(evidence.risk_snapshot.compound_score * 100).toFixed(0)}% — {evidence.risk_snapshot.severity.toUpperCase()}
                  {evidence.risk_snapshot.lead_time_minutes != null && ` · ~${evidence.risk_snapshot.lead_time_minutes} min lead time`}
                </p>
                <div className="flex flex-wrap gap-1 mt-1.5">
                  {evidence.risk_snapshot.contributing_factors.map((f, i) => (
                    <span key={i} className="text-[10px] bg-gray-800 text-gray-300 px-1.5 py-0.5 rounded">{f}</span>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5">Sensor readings</h4>
                <div className="grid grid-cols-2 gap-1.5">
                  {evidence.sensor_snapshot.map((r, i) => (
                    <div key={i} className="bg-gray-800/50 rounded px-2 py-1 text-xs text-gray-300">
                      {r.sensor_id} · {r.sensor_type}: <span className="font-bold">{r.value}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5">Active permits</h4>
                {evidence.permit_snapshot.length === 0 ? (
                  <p className="text-gray-500 text-xs">None active in this zone.</p>
                ) : (
                  evidence.permit_snapshot.map((p, i) => (
                    <p key={i} className="text-xs text-gray-300">{p.permit_id} — {p.work_type?.replace(/_/g, ' ')}</p>
                  ))
                )}
              </div>

              <div>
                <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5">Shift</h4>
                <p className="text-xs text-gray-300">
                  {evidence.shift_snapshot.shift_name}
                  {evidence.shift_snapshot.is_changeover && ' — changeover in progress'}
                  {evidence.shift_snapshot.fatigue_risk && ' — fatigue risk'}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
