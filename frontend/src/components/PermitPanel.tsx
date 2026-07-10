import { HardHat, Ban } from 'lucide-react'
import clsx from 'clsx'

type Props = {
  permits: any[]
  onSuspend: (id: string) => void
}

export default function PermitPanel({ permits, onSuspend }: Props) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
      <h2 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">Active Permits</h2>
      <div className="space-y-2">
        {permits.length === 0 && <p className="text-gray-500 text-sm">No active permits.</p>}
        {permits.map(p => (
          <div key={p.permit_id} className={clsx('p-2 rounded-lg border flex items-center justify-between', {
            'bg-gray-800/50 border-gray-700': p.status === 'active',
            'bg-red-900/20 border-red-800': p.status === 'suspended',
          })}>
            <div className="flex items-center gap-2">
              <HardHat className={clsx('w-4 h-4', p.status === 'suspended' ? 'text-red-400' : 'text-blue-400')} />
              <div>
                <div className="text-xs font-bold text-gray-200">{p.permit_id}</div>
                <div className="text-[10px] text-gray-400">{p.worker_name} • {p.work_type?.replace(/_/g, ' ')} • {p.zone?.replace(/_/g, ' ')}</div>
              </div>
            </div>
            {p.status === 'active' ? (
              <button
                onClick={() => onSuspend(p.permit_id)}
                className="text-[10px] bg-red-600 hover:bg-red-700 text-white px-2 py-1 rounded flex items-center gap-1 transition"
              >
                <Ban className="w-3 h-3" /> Suspend
              </button>
            ) : (
              <span className="text-[10px] text-red-400 font-bold">SUSPENDED</span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
