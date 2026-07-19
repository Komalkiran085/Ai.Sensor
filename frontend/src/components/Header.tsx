import { Shield, Wifi, WifiOff, AlertTriangle, LayoutDashboard, ClipboardList } from 'lucide-react'
import clsx from 'clsx'

export type View = 'dashboard' | 'audit'

type Props = {
  connected: boolean
  scenarioActive: boolean
  view: View
  onViewChange: (view: View) => void
}

export default function Header({ connected, scenarioActive, view, onViewChange }: Props) {
  return (
    <header className="bg-gray-900 border-b border-gray-800 px-6 py-3">
      <div className="max-w-[1600px] mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="w-8 h-8 text-blue-400" />
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">SafetyAI</h1>
            <p className="text-xs text-gray-400">Industrial Safety Command Centre</p>
          </div>
        </div>

        <nav className="flex items-center gap-1 bg-gray-950/60 border border-gray-800 rounded-lg p-1">
          <button
            onClick={() => onViewChange('dashboard')}
            className={clsx('flex items-center gap-1.5 text-sm font-medium px-3 py-1.5 rounded-md transition', {
              'bg-blue-600 text-white': view === 'dashboard',
              'text-gray-400 hover:text-gray-200': view !== 'dashboard',
            })}
          >
            <LayoutDashboard className="w-3.5 h-3.5" /> Dashboard
          </button>
          <button
            onClick={() => onViewChange('audit')}
            className={clsx('flex items-center gap-1.5 text-sm font-medium px-3 py-1.5 rounded-md transition', {
              'bg-blue-600 text-white': view === 'audit',
              'text-gray-400 hover:text-gray-200': view !== 'audit',
            })}
          >
            <ClipboardList className="w-3.5 h-3.5" /> Audit Trail
          </button>
        </nav>

        <div className="flex items-center gap-4">
          {scenarioActive && (
            <div className="flex items-center gap-2 bg-red-900/50 border border-red-500 px-3 py-1 rounded-full animate-pulse">
              <AlertTriangle className="w-4 h-4 text-red-400" />
              <span className="text-sm font-medium text-red-300">SCENARIO ACTIVE</span>
            </div>
          )}

          <div className="flex items-center gap-2">
            {connected ? (
              <>
                <Wifi className="w-4 h-4 text-green-400" />
                <span className="text-xs text-green-400">LIVE</span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-red-400" />
                <span className="text-xs text-red-400">DISCONNECTED</span>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
