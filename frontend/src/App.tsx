import { useState, useEffect, useCallback, useRef } from 'react'
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

type View = 'dashboard' | 'audit' | 'alerts' | 'config'
import TrendChart from './components/TrendChart'
import ComparisonPanel from './components/ComparisonPanel'
import ConfigurationPage from './components/ConfigurationPage'
import DataSourceSelector from './components/DataSourceSelector'
import CompliancePanel from './components/CompliancePanel'
import PendingActions from './components/PendingActions'
import PrecautionWatch from './components/PrecautionWatch'
import AuditPage from './components/AuditPage'
import StatsBar from './components/StatsBar'
import { useMatchHeight } from './hooks/useMatchHeight'

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
  sensors: { id: string; type: string; unit: string }[]
}

export type IncidentMatch = {
  type: 'incident' | 'near_miss'
  id: number
  zone_id: string
  date: string | null
  description: string
  severity?: string
  reported_by?: string
  root_cause?: string
  distance?: number
}

export type ComplianceCitation = {
  source: string
  clause_ref: string
  content: string
  distance?: number
  precaution_eligible?: boolean
}

export type ZoneRisk = {
  zone_id: string
  zone_name: string
  readings: Reading[]
  risk: {
    compound_score: number
    severity: string
    contributing_factors: string[]
    lead_time_minutes: number | null
    agent_outputs?: {
      incident?: { matches: IncidentMatch[]; score: number; retrieval: string } | null
      compliance?: { citations: ComplianceCitation[]; score: number; retrieval: string } | null
    }
  }
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
  const [reportUpgrading, setReportUpgrading] = useState(false)
  const reportRequestIdRef = useRef<string | null>(null)
  const [scenarioActive, setScenarioActive] = useState(false)
  const [scenarioZone, setScenarioZone] = useState('')
  const [trendZone, setTrendZone] = useState('')
  const [demoScenarios, setDemoScenarios] = useState<DemoScenario[]>([])
  const [view, setView] = useState<View>('dashboard')
  const [alertsTab, setAlertsTab] = useState<'alerts' | 'compliance'>('alerts')
  const [workers, setWorkers] = useState<WorkerLocation[]>([])
  const heatmapRef = useRef<HTMLDivElement>(null)
  const heatmapHeight = useMatchHeight(heatmapRef)
  const trendRef = useRef<HTMLDivElement>(null)
  const trendHeight = useMatchHeight(trendRef)

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
        // Guards against the same broadcast landing twice — e.g. React StrictMode
        // briefly holding two WebSocket connections open during dev-mode remount,
        // both delivering the one message — rather than trusting delivery is exactly-once.
        setAlerts(prev => prev.some(a => a.id === data.id) ? prev : [data, ...prev].slice(0, 50))
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
        // Same duplicate-delivery guard as 'alert' above — this is the exact bug that
        // showed two identical "Notify supervisor" cards for one real pending action.
        setPendingActions(prev => prev.some(a => a.id === data.id) ? prev : [data, ...prev])
      }),
      subscribe('action_confirmed', ({ id }: { id: number }) => {
        setPendingActions(prev => prev.filter(a => a.id !== id))
      }),
      subscribe('report_upgraded', ({ request_id, report }: { request_id: string; report: string }) => {
        // The modal already shows the instant fallback report; swap in the AI-generated
        // version if/when it finishes, but only if this is still the report being viewed.
        if (reportRequestIdRef.current === request_id) {
          setReport(report)
          setReportUpgrading(false)
        }
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
    setReportUpgrading(false)
    reportRequestIdRef.current = null
    try {
      const res = await fetch(`${API}/api/report/${zoneId}`, { method: 'POST' })
      const data = await res.json()
      // The backend returns a real (deterministic) report instantly and upgrades it
      // in the background if AI generation succeeds — never block the modal on that.
      setReport(data.report)
      if (data.upgrading && data.request_id) {
        reportRequestIdRef.current = data.request_id
        setReportUpgrading(true)
      }
    } catch {
      setReport('Failed to generate report.')
    }
    setReportLoading(false)
  }, [])

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      <Header connected={connected} scenarioActive={scenarioActive} />

      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <aside className="w-16 bg-gray-900 border-r border-gray-800 flex flex-col items-center py-4 gap-2 shrink-0">
          <button
            onClick={() => setView('dashboard')}
            className={`flex flex-col items-center gap-1 p-2 rounded-lg transition w-12 ${view === 'dashboard' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'}`}
            title="Dashboard"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
            <span className="text-[10px] leading-none">Board</span>
          </button>
          <button
            onClick={() => setView('audit')}
            className={`flex flex-col items-center gap-1 p-2 rounded-lg transition w-12 ${view === 'audit' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'}`}
            title="Audit Trail"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12h6M9 16h6"/></svg>
            <span className="text-[10px] leading-none">Audit</span>
          </button>
          <button
            onClick={() => setView('alerts')}
            className={`flex flex-col items-center gap-1 p-2 rounded-lg transition w-12 ${view === 'alerts' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'}`}
            title="Alert Feed"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>
            <span className="text-[10px] leading-none">Alerts</span>
          </button>
          <button
            onClick={() => setView('config')}
            className={`flex flex-col items-center gap-1 p-2 rounded-lg transition w-12 ${view === 'config' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'}`}
            title="Configuration"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
            <span className="text-[10px] leading-none">Config</span>
          </button>
        </aside>

        {/* Main Content */}
        <div className="flex-1 overflow-auto">
          {view === 'audit' ? (
            <AuditPage zones={zones} apiBase={API} />
          ) : view === 'alerts' ? (
            <div className="h-full overflow-auto p-4 space-y-4">
              <div className="flex justify-center gap-2">
                <button
                  onClick={() => setAlertsTab('alerts')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition ${alertsTab === 'alerts' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
                >
                  Alerts
                </button>
                <button
                  onClick={() => setAlertsTab('compliance')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition ${alertsTab === 'compliance' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
                >
                  Regulatory Compliance
                </button>
              </div>

              {alertsTab === 'alerts' ? (
                <AlertFeed alerts={alerts} />
              ) : (
                <CompliancePanel apiBase={API} />
              )}
            </div>
          ) : view === 'config' ? (
            <ConfigurationPage zones={zones} />
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
          <DataSourceSelector apiBase={API} />
          <ShiftInfo shift={shift} />
        </div>

        {/* Each right-side column's height is pinned in px to its left-side partner's
            *measured* rendered height (useMatchHeight), not CSS Grid stretch — Grid
            only stretches the wrapper to the row's max-content height, it doesn't
            shrink a taller sibling's own content (e.g. a long sensor list) to fit,
            so the shorter card's card would end early and leave a visible gap. */}
        <div className="grid grid-cols-12 gap-4 items-start">
          <div className="col-span-8" ref={heatmapRef}>
            <PlantMap zones={zones} zoneRisks={zoneRisks} workers={workers} onZoneClick={(zoneId) => { setTrendZone(zoneId); openReport(zoneId) }} />
          </div>

          <div className="col-span-4 flex flex-col gap-4 overflow-hidden" style={{ height: heatmapHeight }}>
            <ComparisonPanel zoneRisks={zoneRisks} />
            <PendingActions actions={pendingActions} onConfirm={confirmAction} apiBase={API} />
            <div className="flex-1 min-h-0">
              <SensorFeed zoneRisks={zoneRisks} />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-4 items-start">
          <div className="col-span-8" ref={trendRef}>
            <TrendChart zoneRisks={zoneRisks} selectedZone={trendZone} />
          </div>

          <div className="col-span-4" style={{ height: trendHeight }}>
            <PermitPanel permits={permits} onSuspend={suspendPermit} />
          </div>
        </div>

        <div className="grid grid-cols-12 gap-4">
          <div className="col-span-12">
            <PrecautionWatch zoneRisks={zoneRisks} zones={zones} onZoneClick={(zoneId) => { setTrendZone(zoneId); openReport(zoneId) }} />
          </div>
        </div>
      </main>
      )}
        </div>
      </div>

      {reportZone && view === 'dashboard' && (
        <ReportModal
          zone={zones[reportZone]?.name || reportZone}
          report={report}
          loading={reportLoading}
          upgrading={reportUpgrading}
          onClose={() => setReportZone(null)}
        />
      )}
    </div>
  )
}
