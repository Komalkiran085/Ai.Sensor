import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import { ZoneRisk } from '../App'
import { getReading } from '../lib/readings'

type DataPoint = { time: string; co: number; h2s: number; methane: number; score: number }

export default function TrendChart({ zoneRisks, selectedZone }: { zoneRisks: Record<string, ZoneRisk>; selectedZone: string }) {
  const [history, setHistory] = useState<DataPoint[]>([])

  useEffect(() => {
    const data = zoneRisks[selectedZone]
    if (!data) return

    setHistory(prev => {
      const point: DataPoint = {
        time: new Date().toLocaleTimeString('en-US', { hour12: false, minute: '2-digit', second: '2-digit' }),
        co: getReading(data.readings, 'co_ppm') ?? 0,
        h2s: getReading(data.readings, 'h2s_ppm') ?? 0,
        methane: getReading(data.readings, 'methane_ppm') ?? 0,
        score: (data.risk?.compound_score ?? 0) * 100,
      }
      return [...prev.slice(-60), point]
    })
  }, [zoneRisks, selectedZone])

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
          Trend — {selectedZone.replace(/_/g, ' ')}
        </h2>
        <div className="flex gap-3 text-[10px]">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" /> CO (ppm)</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-purple-500" /> H2S (ppm)</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-cyan-500" /> Risk %</span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={history}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey="time" tick={{ fontSize: 9, fill: '#64748b' }} interval="preserveStartEnd" />
          <YAxis tick={{ fontSize: 9, fill: '#64748b' }} domain={[0, 'auto']} />
          <Tooltip
            contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', fontSize: '11px' }}
            labelStyle={{ color: '#94a3b8' }}
          />
          <ReferenceLine y={35} stroke="#eab308" strokeDasharray="5 5" label={{ value: 'CO Warning', fontSize: 9, fill: '#eab308' }} />
          <ReferenceLine y={50} stroke="#ef4444" strokeDasharray="5 5" label={{ value: 'CO Critical', fontSize: 9, fill: '#ef4444' }} />
          <Line type="monotone" dataKey="co" stroke="#ef4444" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="h2s" stroke="#a855f7" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="score" stroke="#06b6d4" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
