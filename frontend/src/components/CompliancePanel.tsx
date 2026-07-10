import { CheckCircle, AlertCircle, Circle } from 'lucide-react'
import clsx from 'clsx'

const CHECKS = [
  { rule: 'Gas clearance before confined space entry', ref: 'OISD-GDN-237', status: 'fail' },
  { rule: 'Hot work permit proximity check', ref: 'Factory Act Sec 7A', status: 'fail' },
  { rule: 'Shift handover safety briefing', ref: 'DGMS Circular 2023', status: 'warn' },
  { rule: 'Emergency evacuation drill (monthly)', ref: 'OISD-STD-116', status: 'pass' },
  { rule: 'Fire detection system operational', ref: 'OISD-STD-189', status: 'pass' },
  { rule: 'PPE compliance in hazardous zones', ref: 'Factory Act Sec 35', status: 'pass' },
  { rule: 'Gas detector calibration (quarterly)', ref: 'OISD-RP-149', status: 'pass' },
  { rule: 'Simultaneous permit conflict check', ref: 'OISD-GDN-237', status: 'fail' },
]

export default function CompliancePanel() {
  const passed = CHECKS.filter(c => c.status === 'pass').length
  const failed = CHECKS.filter(c => c.status === 'fail').length

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Regulatory Compliance</h2>
        <div className="flex gap-2 text-[10px]">
          <span className="bg-green-900/50 text-green-400 px-2 py-0.5 rounded-full">{passed} passed</span>
          <span className="bg-red-900/50 text-red-400 px-2 py-0.5 rounded-full">{failed} failed</span>
        </div>
      </div>
      <div className="space-y-1.5 max-h-[200px] overflow-y-auto">
        {CHECKS.map((c, i) => (
          <div key={i} className={clsx('flex items-center gap-2 p-1.5 rounded-lg text-xs', {
            'bg-green-900/10': c.status === 'pass',
            'bg-red-900/10': c.status === 'fail',
            'bg-yellow-900/10': c.status === 'warn',
          })}>
            {c.status === 'pass' && <CheckCircle className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />}
            {c.status === 'fail' && <AlertCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />}
            {c.status === 'warn' && <Circle className="w-3.5 h-3.5 text-yellow-500 flex-shrink-0" />}
            <span className="text-gray-300 flex-1">{c.rule}</span>
            <span className="text-[9px] text-gray-600 font-mono">{c.ref}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
