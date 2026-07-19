import { useState, useEffect, useCallback } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import { Reading } from './lib/readings'
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
import PendingActions from './components/PendingActions'
import AuditPage from './components/AuditPage'
import type { View } from './components/Header'

const WS_URL = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.hostname}:8000/ws`
const API = `http://${window.location.hostname}:8000`

export type Alert = {
  id: number
  zone_id: string
  zone_name: string
  severity: string
  compound_score: number
  lead_time_minutes: number | null
  explanation: string
  contributing_factors: string[]
  permit: any
  sent_at?: string
}

export type ZoneMeta = {
  zone_id: string
  name: string
  hazard_classification: string
  boundary: number[][]
}

export type ZoneRisk = {
  zone_id: string
  zone_name: string
  readings: Reading[]
  risk: { compound_score: number; severity: string; contributing_factors: string[]; lead_time_minutes: number | null }
  shift: any
  permits: any[]
}

export type DemoScenario = {
  id: string
  label: string
  zone_id: string
  description: string
}

export type PendingAction = {
  id: number
  alert_id: number
  zone_id: string
  action_type: string
  status: string
  evidence_id: number | null
}

export type WorkerLocation = {
  worker_id: string
  name: string
  zone_id: string
  role: string
}

export default function App() {
  const { connected, subscribe } = useWebSocket(WS_URL)
  const [zones, setZones] = useState<Record<string, ZoneMeta>>({})
  const [zoneRisks, setZoneRisks] = useState<Record<string, ZoneRisk>>({})
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [permits, setPermits] = useState<any[]>([])
  const [pendingActions, setPendingActions] = useState<PendingAction[]>([])
  const [shift, setShift] = useState<any>(null)
  const [reportZone, setReportZone] = useState<string | null>(null)
  const [report, setReport] = useState<string>('')
  const [reportLoading, setReportLoading] = useState(false)
  const [scenarioActive, setScenarioActive] = useState(false)
  const [scenarioZone, setScenarioZone] = useState('')
  const [trendZone, setTrendZone] = useState('')
  const [demoScenarios, setDemoScenarios] = useState<DemoScenario[]>([])
  const [view, setView] = useState<View>('dashboard')
  const [workers, setWorkers] = useState<WorkerLocation[]>([])

  const playBeep = useCallback((severity: string) => {
    try {
      const ctx = new AudioContext()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.frequency.value = severity === 'extreme' ? 880 : 660
      osc.type = 'square'
      gain.gain.value = 0.15
      osc.start()
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5)
      osc.stop(ctx.currentTime + 0.5)
    } catch {}
  }, [])

  // Subscribe to WebSocket events
  useEffect(() => {
    const unsubs = [
      subscribe('zone_risks', (data: Record<string, ZoneRisk>) => setZoneRisks(data)),
      subscribe('alert', (data: Alert) => {
        setAlerts(prev => [data, ...prev].slice(0, 50))
        if (data.severity === 'critical' || data.severity === 'extreme') {
          playBeep(data.severity)
        }
      }),
      // The pending action hasn't been confirmed yet — buzz again, like a fire panel
      // that keeps sounding until someone acknowledges it rather than chiming once.
      subscribe('action_reminder', ({ severity }: { severity: string }) => {
        playBeep(severity)
      }),
      subscribe('permit_status_changed', ({ permit_id, status }: { permit_id: string; status: string }) => {
        setPermits(prev => prev.map(p => p.permit_id === permit_id ? { ...p, status } : p))
      }),
      subscribe('alert_updated', ({ id, explanation }: { id: number; explanation: string }) => {
        // The alert fired instantly with fast fallback text; this swaps in the real
        // AI-generated explanation once it's ready, without ever blocking the alert itself.
        setAlerts(prev => prev.map(a => a.id === id ? { ...a, explanation } : a))
      }),
      subscribe('action_proposed', (data: PendingAction) => {
        setPendingActions(prev => [data, ...prev])
      }),
      subscribe('action_confirmed', ({ id }: { id: number }) => {
        setPendingActions(prev => prev.filter(a => a.id !== id))
      }),
    ]
    return () => unsubs.forEach(u => u())
  }, [subscribe, playBeep])

  // Fetch initial data
  useEffect(() => {
    fetch(`${API}/api/zones`).then(r => r.json()).then((data: Record<string, ZoneMeta>) => {
      setZones(data)
      const firstZone = Object.keys(data)[0]
      if (firstZone) {
        setScenarioZone(firstZone)
        setTrendZone(firstZone)
      }
    }).catch(() => {})
    fetch(`${API}/api/risks`).then(r => r.json()).then(setZoneRisks).catch(() => {})
    fetch(`${API}/api/permits`).then(r => r.json()).then(setPermits).catch(() => {})
    fetch(`${API}/api/shift`).then(r => r.json()).then(setShift).catch(() => {})
    fetch(`${API}/api/alerts`).then(r => r.json()).then(setAlerts).catch(() => {})
    fetch(`${API}/api/actions/pending`).then(r => r.json()).then(setPendingActions).catch(() => {})
    fetch(`${API}/api/demo/scenarios`).then(r => r.json()).then(setDemoScenarios).catch(() => {})
    fetch(`${API}/api/workers`).then(r => r.json()).then(setWorkers).catch(() => {})
  }, [])

  // Poll shift info
  useEffect(() => {
    const id = setInterval(() => {
      fetch(`${API}/api/shift`).then(r => r.json()).then(setShift).catch(() => {})
    }, 10000)
    return () => clearInterval(id)
  }, [])

  // Poll worker locations — zone-level badge presence, not a live feed, so a short poll is honest
  useEffect(() => {
    const id = setInterval(() => {
      fetch(`${API}/api/workers`).then(r => r.json()).then(setWorkers).catch(() => {})
    }, 5000)
    return () => clearInterval(id)
  }, [])

  const triggerScenario = useCallback(async (zoneId: string) => {
    await fetch(`${API}/api/demo/trigger-scenario/${zoneId}`, { method: 'POST' })
    setScenarioActive(true)
    setScenarioZone(zoneId)
    setTrendZone(zoneId)
  }, [])

  const resetDemo = useCallback(async () => {
    await fetch(`${API}/api/demo/reset`, { method: 'POST' })
    setScenarioActive(false)
    setAlerts([])
    setPendingActions([])
  }, [])

  const suspendPermit = useCallback(async (permitId: string) => {
    await fetch(`${API}/api/permits/${permitId}/suspend`, { method: 'POST' })
    setPermits(prev => prev.map(p => p.permit_id === permitId ? { ...p, status: 'suspended' } : p))
  }, [])

  const confirmAction = useCallback(async (actionId: number) => {
    await fetch(`${API}/api/actions/${actionId}/confirm`, { method: 'POST' })
    setPendingActions(prev => prev.filter(a => a.id !== actionId))
  }, [])

  const openReport = useCallback(async (zoneId: string) => {
    setReportZone(zoneId)
    setReportLoading(true)
    try {
      const res = await fetch(`${API}/api/report/${zoneId}`, { method: 'POST' })
      const data = await res.json()
      setReport(data.report)
    } catch {
      setReport('Failed to generate report.')
    }
    setReportLoading(false)
  }, [])

  return (
    <div className="min-h-screen bg-gray-950">
      <Header connected={connected} scenarioActive={scenarioActive} view={view} onViewChange={setView} />

      {view === 'audit' ? (
        <AuditPage zones={zones} apiBase={API} />
      ) : (
      <main className="max-w-[1600px] mx-auto p-4 space-y-4">
        <StatsBar zoneRisks={zoneRisks} alerts={alerts} permits={permits} />

        <div className="flex gap-4 items-stretch flex-wrap">
          <DemoControls
            zones={Object.values(zones)}
            scenarios={demoScenarios}
            scenarioZone={scenarioZone}
            onZoneChange={setScenarioZone}
            scenarioActive={scenarioActive}
            onTrigger={() => triggerScenario(scenarioZone)}
            onTriggerNamed={(zoneId) => triggerScenario(zoneId)}
            onReset={resetDemo}
          />
          <DataSourceSelector />
          <ShiftInfo shift={shift} />
        </div>

        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-8 space-y-4">
            <PlantMap zones={zones} zoneRisks={zoneRisks} workers={workers} onZoneClick={(zoneId) => { setTrendZone(zoneId); openReport(zoneId) }} />
            <TrendChart zoneRisks={zoneRisks} selectedZone={trendZone} />
          </div>

          <div className="col-span-4 space-y-4">
            <ComparisonPanel zoneRisks={zoneRisks} />
            <PendingActions actions={pendingActions} onConfirm={confirmAction} apiBase={API} />
            <SensorFeed zoneRisks={zoneRisks} />
            <PermitPanel permits={permits} onSuspend={suspendPermit} />
          </div>
        </div>

        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-8">
            <AlertFeed alerts={alerts} />
          </div>
          <div className="col-span-4">
            <CompliancePanel apiBase={API} />
          </div>
        </div>
      </main>
      )}

      {reportZone && view === 'dashboard' && (
        <ReportModal
          zone={zones[reportZone]?.name || reportZone}
          report={report}
          loading={reportLoading}
          onClose={() => setReportZone(null)}
        />
      )}
    </div>
  )
}
