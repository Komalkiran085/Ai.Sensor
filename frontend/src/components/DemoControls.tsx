import { Play, RotateCcw } from 'lucide-react'

type Props = {
  scenarioActive: boolean
  onTrigger: () => void
  onReset: () => void
}

export default function DemoControls({ scenarioActive, onTrigger, onReset }: Props) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 flex items-center gap-3">
      <span className="text-xs text-gray-400 font-semibold uppercase mr-2">Demo</span>
      {!scenarioActive ? (
        <button
          onClick={onTrigger}
          className="flex items-center gap-1.5 bg-red-600 hover:bg-red-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition"
        >
          <Play className="w-4 h-4" /> Trigger Vizag Scenario
        </button>
      ) : (
        <button
          onClick={onReset}
          className="flex items-center gap-1.5 bg-gray-600 hover:bg-gray-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition"
        >
          <RotateCcw className="w-4 h-4" /> Reset to Normal
        </button>
      )}
    </div>
  )
}
