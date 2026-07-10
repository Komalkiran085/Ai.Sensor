import { Alert } from '../App'
import { AlertTriangle, ShieldAlert, Info } from 'lucide-react'
import clsx from 'clsx'

const SEVERITY_ICON: Record<string, typeof AlertTriangle> = {
  extreme: ShieldAlert,
  critical: AlertTriangle,
  warning: Info,
}

export default function AlertFeed({ alerts }: { alerts: Alert[] }) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Alert Feed</h2>
        <span className="text-xs bg-red-900/50 text-red-400 px-2 py-0.5 rounded-full">{alerts.length} alerts</span>
      </div>
      <div className="space-y-2 max-h-[300px] overflow-y-auto">
        {alerts.length === 0 && <p className="text-gray-500 text-sm">No alerts — all clear.</p>}
        {alerts.map((a, i) => {
          const Icon = SEVERITY_ICON[a.severity] || Info
          return (
            <div key={`${a.id}-${i}`} className={clsx('alert-enter p-3 rounded-lg border', {
              'severity-extreme': a.severity === 'extreme',
              'severity-critical': a.severity === 'critical',
              'severity-warning': a.severity === 'warning',
            })}>
              <div className="flex items-start gap-2">
                <Icon className={clsx('w-5 h-5 mt-0.5 flex-shrink-0', {
                  'text-red-400': a.severity === 'extreme',
                  'text-orange-400': a.severity === 'critical',
                  'text-yellow-400': a.severity === 'warning',
                })} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-bold text-gray-100">{a.zone.replace(/_/g, ' ')}</span>
                    <span className="text-xs text-gray-400">Score: {(a.compound_score * 100).toFixed(0)}%</span>
                  </div>
                  <p className="text-xs text-gray-300 leading-relaxed">{a.explanation}</p>
                  {a.contributing_factors?.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {a.contributing_factors.map((f: string, j: number) => (
                        <span key={j} className="text-[10px] bg-gray-700/50 text-gray-300 px-1.5 py-0.5 rounded">{f}</span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
