import { Shield, AlertTriangle, Activity, Users } from 'lucide-react'
import { ZoneRisk } from '../App'
import clsx from 'clsx'

export default function StatsBar({ zoneRisks, alerts, permits }: { zoneRisks: Record<string, ZoneRisk>; alerts: any[]; permits: any[] }) {
  const zones = Object.values(zoneRisks)
  const criticalZones = zones.filter(z => z.risk?.severity === 'critical' || z.risk?.severity === 'extreme').length
  const warningZones = zones.filter(z => z.risk?.severity === 'warning').length
  const activePermits = permits.filter(p => p.status === 'active').length
  const maxScore = zones.length > 0 ? Math.max(...zones.map(z => z.risk?.compound_score ?? 0)) : 0

  const stats = [
    {
      label: 'Plant Risk Level',
      value: maxScore >= 0.6 ? 'CRITICAL' : maxScore >= 0.35 ? 'ELEVATED' : 'NORMAL',
      sub: `Score: ${(maxScore * 100).toFixed(0)}%`,
      icon: Shield,
      color: maxScore >= 0.6 ? 'text-red-400' : maxScore >= 0.35 ? 'text-yellow-400' : 'text-green-400',
      bg: maxScore >= 0.6 ? 'bg-red-900/30' : maxScore >= 0.35 ? 'bg-yellow-900/30' : 'bg-green-900/30',
      pulse: maxScore >= 0.6,
    },
    {
      label: 'Active Alerts',
      value: alerts.length.toString(),
      sub: `${criticalZones} critical zones`,
      icon: AlertTriangle,
      color: alerts.length > 0 ? 'text-orange-400' : 'text-gray-400',
      bg: alerts.length > 0 ? 'bg-orange-900/30' : 'bg-gray-800/30',
      pulse: criticalZones > 0,
    },
    {
      label: 'Zone Status',
      value: `${zones.length - criticalZones - warningZones}/${zones.length}`,
      sub: `${warningZones} warning, ${criticalZones} critical`,
      icon: Activity,
      color: criticalZones > 0 ? 'text-red-400' : 'text-green-400',
      bg: criticalZones > 0 ? 'bg-red-900/30' : 'bg-green-900/30',
      pulse: false,
    },
    {
      label: 'Active Permits',
      value: activePermits.toString(),
      sub: `${permits.length - activePermits} suspended`,
      icon: Users,
      color: 'text-blue-400',
      bg: 'bg-blue-900/30',
      pulse: false,
    },
  ]

  return (
    <div className="grid grid-cols-4 gap-3">
      {stats.map(s => (
        <div key={s.label} className={clsx('rounded-xl border border-gray-800 p-3 flex items-center gap-3', s.bg, s.pulse && 'animate-pulse')}>
          <div className={clsx('p-2 rounded-lg bg-gray-900/50', s.color)}>
            <s.icon className="w-5 h-5" />
          </div>
          <div>
            <p className="text-[10px] text-gray-500 uppercase tracking-wider">{s.label}</p>
            <p className={clsx('text-lg font-bold', s.color)}>{s.value}</p>
            <p className="text-[10px] text-gray-500">{s.sub}</p>
          </div>
        </div>
      ))}
    </div>
  )
}
