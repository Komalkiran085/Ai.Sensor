import { ZoneRisk } from '../App'
import { ShieldX, ShieldCheck, ArrowRight } from 'lucide-react'
import clsx from 'clsx'

export default function ComparisonPanel({ zoneRisks }: { zoneRisks: Record<string, ZoneRisk> }) {
  // Find the highest-risk zone
  const zones = Object.values(zoneRisks)
  const hotZone = zones.reduce((max, z) => (z.risk?.compound_score ?? 0) > (max?.risk?.compound_score ?? 0) ? z : max, zones[0])

  if (!hotZone) return null

  const co = hotZone.reading?.co_ppm ?? 0
  const singleSensorAlert = co >= 50
  const compoundAlert = (hotZone.risk?.compound_score ?? 0) >= 0.35
  const compoundSeverity = hotZone.risk?.severity ?? 'normal'
  const hasPermit = (hotZone.permits?.length ?? 0) > 0

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
      <h2 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">
        Single Sensor vs Compound Detection
      </h2>

      <div className="grid grid-cols-2 gap-3">
        {/* Traditional single sensor */}
        <div className={clsx(
          'p-3 rounded-lg border-2 text-center',
          singleSensorAlert ? 'border-red-500 bg-red-900/20' : 'border-green-600 bg-green-900/20'
        )}>
          <div className="flex items-center justify-center gap-2 mb-2">
            {singleSensorAlert ? (
              <ShieldX className="w-5 h-5 text-red-400" />
            ) : (
              <ShieldCheck className="w-5 h-5 text-green-400" />
            )}
            <span className="text-xs font-bold text-gray-300">Traditional System</span>
          </div>
          <div className={clsx('text-2xl font-black', singleSensorAlert ? 'text-red-400' : 'text-green-400')}>
            {singleSensorAlert ? 'ALARM' : 'NO ALARM'}
          </div>
          <p className="text-[10px] text-gray-500 mt-1">
            CO: {co.toFixed(1)} ppm {!singleSensorAlert && '< 50 ppm threshold'}
          </p>
          <p className="text-[10px] text-gray-600 mt-1">Checks gas sensor only</p>
        </div>

        {/* Compound AI detection */}
        <div className={clsx(
          'p-3 rounded-lg border-2 text-center',
          compoundAlert ? 'border-red-500 bg-red-900/20' : 'border-green-600 bg-green-900/20',
          compoundAlert && 'animate-pulse'
        )}>
          <div className="flex items-center justify-center gap-2 mb-2">
            {compoundAlert ? (
              <ShieldX className="w-5 h-5 text-red-400" />
            ) : (
              <ShieldCheck className="w-5 h-5 text-green-400" />
            )}
            <span className="text-xs font-bold text-gray-300">SafetyAI Compound</span>
          </div>
          <div className={clsx('text-2xl font-black', {
            'text-red-400': compoundSeverity === 'extreme' || compoundSeverity === 'critical',
            'text-yellow-400': compoundSeverity === 'warning',
            'text-green-400': compoundSeverity === 'normal',
          })}>
            {compoundAlert ? compoundSeverity.toUpperCase() : 'SAFE'}
          </div>
          <p className="text-[10px] text-gray-500 mt-1">
            Score: {((hotZone.risk?.compound_score ?? 0) * 100).toFixed(0)}% — {hotZone.zone.replace(/_/g, ' ')}
          </p>
          <p className="text-[10px] text-gray-600 mt-1">
            Gas + Permit + Shift combined
          </p>
        </div>
      </div>

      {/* The insight */}
      {compoundAlert && !singleSensorAlert && (
        <div className="mt-3 bg-yellow-900/20 border border-yellow-700 rounded-lg p-2 flex items-start gap-2">
          <ArrowRight className="w-4 h-4 text-yellow-400 mt-0.5 flex-shrink-0" />
          <p className="text-[11px] text-yellow-300 leading-relaxed">
            <strong>False Negative Prevented:</strong> A traditional single-sensor system would show NO alarm at {co.toFixed(1)} ppm CO.
            SafetyAI detected danger by combining gas readings{hasPermit ? ', active work permit' : ''}, and shift patterns — catching a risk that single-sensor monitoring completely misses.
          </p>
        </div>
      )}
    </div>
  )
}
