import { useState, useEffect, useCallback } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import PlantMap from './components/PlantMap'
import SensorFeed from './components/SensorFeed'
import AlertFeed from './components/AlertFeed'
import PermitPanel from './components/PermitPanel'
import ShiftInfo from './components/ShiftInfo'
import DemoControls from './components/DemoControls'
import ReportModal from './components/ReportModal'
import Header from './components/Header'
import StatsBar from './components/StatsBar'
import TrendChart from './components/TrendChart'
import ComparisonPanel from './components/ComparisonPanel'
import DataSourceSelector from './components/DataSourceSelector'
import CompliancePanel from './components/CompliancePanel'

const WS_URL = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.hostname}:8000/ws`
const API = `http://${window.location.hostname}:8000`

export type Alert = {
  id: number
  zone: string
  severity: string
  compound_score: number
  explanation: string
  contributing_factors: string[]
  permit: any
  reading: any
}

export type ZoneRisk = {
  zone: string
  reading: any
  risk: { compound_score: number; severity: string; contributing_factors: string[] }
  shift: any
  permits: any[]
}

export default function App() {
  const { connected, subscribe } = useWebSocket(WS_URL)
  const [zoneRisks, setZoneRisks] = useState<Record<string, ZoneRisk>>({})
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [permits, setPermits] = useState<any[]>([])
  const [shift, setShift] = useState<any>(null)
  const [reportZone, setReportZone] = useState<string | null>(null)
  const [report, setReport] = useState<string>('')
  const [reportLoading, setReportLoading] = useState(false)
  const [scenarioActive, setScenarioActive] = useState(false)
  const [trendZone, setTrendZone] = useState('BATTERY_3')

  // Subscribe to WebSocket events
  useEffect(() => {
    const unsubs = [
      subscribe('zone_risks', (data: Record<string, ZoneRisk>) => setZoneRisks(data)),
      subscribe('alert', (data: Alert) => {
        setAlerts(prev => [data, ...prev].slice(0, 50))
        // Play alarm sound for critical/extreme alerts
        if (data.severity === 'critical' || data.severity === 'extreme') {
          try {
            const ctx = new AudioContext()
            const osc = ctx.createOscillator()
            const gain = ctx.createGain()
            osc.connect(gain)
            gain.connect(ctx.destination)
            osc.frequency.value = data.severity === 'extreme' ? 880 : 660
            osc.type = 'square'
            gain.gain.value = 0.15
            osc.start()
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5)
            osc.stop(ctx.currentTime + 0.5)
          } catch {}
        }
      }),
      subscribe('permit_suspended', ({ permit_id }: { permit_id: string }) => {
        setPermits(prev => prev.map(p => p.permit_id === permit_id ? { ...p, status: 'suspended' } : p))
      }),
    ]
    return () => unsubs.forEach(u => u())
  }, [subscribe])

  // Fetch initial data
  useEffect(() => {
    fetch(`${API}/api/permits`).then(r => r.json()).then(setPermits).catch(() => {})
    fetch(`${API}/api/shift`).then(r => r.json()).then(setShift).catch(() => {})
    fetch(`${API}/api/alerts`).then(r => r.json()).then(setAlerts).catch(() => {})
  }, [])

  // Poll shift info
  useEffect(() => {
    const id = setInterval(() => {
      fetch(`${API}/api/shift`).then(r => r.json()).then(setShift).catch(() => {})
    }, 10000)
    return () => clearInterval(id)
  }, [])

  const triggerVizag = useCallback(async () => {
    await fetch(`${API}/api/demo/trigger-vizag`, { method: 'POST' })
    setScenarioActive(true)
  }, [])

  const resetDemo = useCallback(async () => {
    await fetch(`${API}/api/demo/reset`, { method: 'POST' })
    setScenarioActive(false)
    setAlerts([])
  }, [])

  const suspendPermit = useCallback(async (permitId: string) => {
    await fetch(`${API}/api/permits/${permitId}/suspend`, { method: 'POST' })
    setPermits(prev => prev.map(p => p.permit_id === permitId ? { ...p, status: 'suspended' } : p))
  }, [])

  const openReport = useCallback(async (zone: string) => {
    setReportZone(zone)
    setReportLoading(true)
    try {
      const res = await fetch(`${API}/api/report/${zone}`, { method: 'POST' })
      const data = await res.json()
      setReport(data.report)
    } catch {
      setReport('Failed to generate report.')
    }
    setReportLoading(false)
  }, [])

  return (
    <div className="min-h-screen bg-gray-950">
      <Header connected={connected} scenarioActive={scenarioActive} />

      <main className="max-w-[1600px] mx-auto p-4 space-y-4">
        {/* Stats overview */}
        <StatsBar zoneRisks={zoneRisks} alerts={alerts} permits={permits} />

        {/* Top row: Demo controls + Data Source + Shift */}
        <div className="flex gap-4 items-stretch">
          <DemoControls
            scenarioActive={scenarioActive}
            onTrigger={triggerVizag}
            onReset={resetDemo}
          />
          <DataSourceSelector />
          <ShiftInfo shift={shift} />
        </div>

        {/* Main grid */}
        <div className="grid grid-cols-12 gap-4">
          {/* Plant map - 8 cols */}
          <div className="col-span-8 space-y-4">
            <PlantMap zoneRisks={zoneRisks} onZoneClick={(zone) => { setTrendZone(zone); openReport(zone); }} />
            <TrendChart zoneRisks={zoneRisks} selectedZone={trendZone} />
          </div>

          {/* Right sidebar - 4 cols */}
          <div className="col-span-4 space-y-4">
            <ComparisonPanel zoneRisks={zoneRisks} />
            <SensorFeed zoneRisks={zoneRisks} />
            <PermitPanel permits={permits} onSuspend={suspendPermit} />
          </div>
        </div>

        {/* Bottom row */}
        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-8">
            <AlertFeed alerts={alerts} />
          </div>
          <div className="col-span-4">
            <CompliancePanel />
          </div>
        </div>
      </main>

      {reportZone && (
        <ReportModal
          zone={reportZone}
          report={report}
          loading={reportLoading}
          onClose={() => setReportZone(null)}
        />
      )}
    </div>
  )
}
