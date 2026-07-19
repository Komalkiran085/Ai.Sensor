import { useState } from 'react'
import { ShieldAlert, Check, FileSearch } from 'lucide-react'
import { PendingAction } from '../App'
import EvidenceModal from './EvidenceModal'

type Props = {
  actions: PendingAction[]
  onConfirm: (id: number) => void
  apiBase: string
}

const ACTION_LABELS: Record<string, string> = {
  suspend_permit: 'Suspend active permit',
  notify_supervisor: 'Notify supervisor',
  evacuate_zone: 'Evacuate zone',
}

export default function PendingActions({ actions, onConfirm, apiBase }: Props) {
  const [viewingEvidence, setViewingEvidence] = useState<number | null>(null)

  if (actions.length === 0) return null

  return (
    <div className="bg-red-950/40 rounded-xl border border-red-700 p-4">
      <div className="flex items-center gap-2 mb-3">
        <ShieldAlert className="w-4 h-4 text-red-400" />
        <h2 className="text-sm font-semibold text-red-300 uppercase tracking-wider">
          Awaiting your confirmation
        </h2>
      </div>
      <div className="space-y-2">
        {actions.map(a => (
          <div key={a.id} className="flex items-center justify-between bg-gray-900/60 border border-red-800 rounded-lg p-2.5">
            <div>
              <div className="text-xs font-bold text-gray-100">
                {ACTION_LABELS[a.action_type] || a.action_type}
              </div>
              <div className="text-[10px] text-gray-400">{a.zone_id?.replace(/_/g, ' ') ?? 'unknown zone'}</div>
            </div>
            <div className="flex items-center gap-2">
              {a.evidence_id != null && (
                <button
                  onClick={() => setViewingEvidence(a.evidence_id)}
                  title="View preserved evidence"
                  className="flex items-center gap-1 text-[11px] font-bold bg-gray-800 hover:bg-gray-700 text-gray-300 px-2.5 py-1.5 rounded-lg transition"
                >
                  <FileSearch className="w-3.5 h-3.5" />
                </button>
              )}
              <button
                onClick={() => onConfirm(a.id)}
                className="flex items-center gap-1 text-[11px] font-bold bg-red-600 hover:bg-red-700 text-white px-3 py-1.5 rounded-lg transition"
              >
                <Check className="w-3.5 h-3.5" /> Confirm
              </button>
            </div>
          </div>
        ))}
      </div>

      {viewingEvidence != null && (
        <EvidenceModal evidenceId={viewingEvidence} apiBase={apiBase} onClose={() => setViewingEvidence(null)} />
      )}
    </div>
  )
}
