import { useEffect, useState } from 'react'
import { CheckCircle, AlertCircle, HelpCircle } from 'lucide-react'
import clsx from 'clsx'

type ComplianceCheck = {
  rule: string
  ref: string
  status: 'pass' | 'fail' | 'unmonitored'
  detail: string
}

type ComplianceResponse = {
  checks: ComplianceCheck[]
  passed: number
  failed: number
  unmonitored: number
}

export default function CompliancePanel({ apiBase }: { apiBase: string }) {
  const [data, setData] = useState<ComplianceResponse | null>(null)

  useEffect(() => {
    const load = () => fetch(`${apiBase}/api/compliance`).then(r => r.json()).then(setData).catch(() => {})
    load()
    const id = setInterval(load, 15000)
    return () => clearInterval(id)
  }, [apiBase])

  if (!data) {
    return (
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Regulatory Compliance</h2>
        <p className="text-gray-500 text-sm mt-3">Loading live compliance status…</p>
      </div>
    )
  }

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Regulatory Compliance</h2>
        <div className="flex gap-2 text-[10px]">
          <span className="bg-green-900/50 text-green-400 px-2 py-0.5 rounded-full">{data.passed} passed</span>
          <span className="bg-red-900/50 text-red-400 px-2 py-0.5 rounded-full">{data.failed} failed</span>
          <span className="bg-gray-800 text-gray-400 px-2 py-0.5 rounded-full">{data.unmonitored} unmonitored</span>
        </div>
      </div>
      <div className="space-y-1.5 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 160px)' }}>
        {data.checks.map((c, i) => (
          <div
            key={i}
            title={c.detail}
            className={clsx('flex items-center gap-2 p-1.5 rounded-lg text-xs', {
              'bg-green-900/10': c.status === 'pass',
              'bg-red-900/10': c.status === 'fail',
              'bg-gray-800/30': c.status === 'unmonitored',
            })}
          >
            {c.status === 'pass' && <CheckCircle className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />}
            {c.status === 'fail' && <AlertCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />}
            {c.status === 'unmonitored' && <HelpCircle className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />}
            <span className={clsx('flex-1', c.status === 'unmonitored' ? 'text-gray-500' : 'text-gray-300')}>{c.rule}</span>
            <span className="text-[9px] text-gray-600 font-mono flex-shrink-0">{c.ref}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
