import { Clock, AlertTriangle } from 'lucide-react'

export default function ShiftInfo({ shift }: { shift: any }) {
  if (!shift) return null

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 flex-1">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-blue-400" />
          <span className="text-sm font-semibold text-gray-300">Shift: {shift.shift_name}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400">{shift.minutes_remaining} min remaining</span>
          {shift.changeover_soon && (
            <span className="flex items-center gap-1 text-xs bg-yellow-900/50 text-yellow-400 px-2 py-0.5 rounded-full">
              <AlertTriangle className="w-3 h-3" /> Changeover Soon
            </span>
          )}
          {shift.fatigue_risk && (
            <span className="text-xs bg-orange-900/50 text-orange-400 px-2 py-0.5 rounded-full">Fatigue Risk</span>
          )}
        </div>
      </div>
    </div>
  )
}
