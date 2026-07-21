import { Database } from 'lucide-react'
import { ZoneMeta } from '../App'

const SECURITY_POLICIES = ['None', 'Basic256Sha256', 'Aes128_Sha256_RsaOaep', 'Aes256_Sha256_RsaPss']

export default function ConfigurationPage({ zones }: { zones: Record<string, ZoneMeta> }) {
  const zoneList = Object.values(zones)

  return (
    <div className="max-w-[1200px] mx-auto p-4 space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-gray-200">Configuration</h1>
        <p className="text-xs text-gray-500 mt-1">SCADA/PLC connectivity for pulling live sensor data directly from plant hardware.</p>
      </div>

      {/* ── OPC-UA ───────────────────────────────────────────────── */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 opacity-90">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-start gap-3">
            <Database className="w-5 h-5 text-gray-500 mt-0.5" />
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold text-gray-300">OPC-UA / SCADA Integration</h2>
                <span className="text-[10px] bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded font-semibold">Soon</span>
              </div>
              <p className="text-xs text-gray-500 mt-1 max-w-xl">
                Connects directly to the plant's own SCADA system over OPC-UA — the standard industrial protocol for
                reading live sensor/PLC data — instead of simulated or replayed readings.
              </p>
            </div>
          </div>
        </div>

        <fieldset disabled className="mt-4 space-y-4 opacity-60">
          <div className="grid grid-cols-3 gap-4">
            <label className="block">
              <span className="text-[11px] text-gray-400">Endpoint URL</span>
              <input
                type="text" placeholder="opc.tcp://192.168.1.50:4840"
                className="mt-1 w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-300 placeholder:text-gray-600"
              />
            </label>
            <label className="block">
              <span className="text-[11px] text-gray-400">Security Policy</span>
              <select className="mt-1 w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-300">
                {SECURITY_POLICIES.map(p => <option key={p}>{p}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="text-[11px] text-gray-400">Authentication</span>
              <select className="mt-1 w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-xs text-gray-300">
                <option>Anonymous</option>
                <option>Username &amp; Password</option>
                <option>X.509 Certificate</option>
              </select>
            </label>
          </div>

          <div>
            <span className="text-[11px] text-gray-400">Node ID mapping — example (same pattern for every zone/sensor)</span>
            <div className="mt-1 overflow-x-auto border border-gray-800 rounded">
              <table className="text-xs w-full">
                <thead>
                  <tr className="text-left text-gray-500 bg-gray-800/50">
                    <th className="px-2 py-1 font-medium">Zone</th>
                    <th className="px-2 py-1 font-medium">Sensor</th>
                    <th className="px-2 py-1 font-medium">OPC-UA Node ID</th>
                  </tr>
                </thead>
                <tbody>
                  {(zoneList[0]?.sensors ?? []).slice(0, 3).map(s => (
                    <tr key={s.id} className="border-t border-gray-800">
                      <td className="px-2 py-1 text-gray-400">{zoneList[0].name}</td>
                      <td className="px-2 py-1 text-gray-400 font-mono">{s.id} ({s.type})</td>
                      <td className="px-2 py-1">
                        <input
                          type="text" placeholder={`ns=2;s=${zoneList[0].zone_id}.${s.type}.Value`}
                          className="w-full bg-gray-800 border border-gray-700 rounded px-1.5 py-1 text-gray-300 placeholder:text-gray-600 font-mono"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <button className="px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-800 text-gray-500">Test Connection</button>
        </fieldset>
      </div>
    </div>
  )
}
