import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell,
} from 'recharts'
import { Map as MapIcon, KeyRound } from 'lucide-react'

const TooltipStyle = {
  backgroundColor: '#18181b',
  border: '1px solid #27272a',
  borderRadius: '6px',
  fontSize: '12px',
  color: '#e5e7eb',
}

export default function AttackChart({ stats }) {
  if (!stats) return null

  const hourData = stats.by_hour || []
  const topIps = stats.top_ips || []
  const topCreds = stats.top_creds || []

  return (
    <div className="flex flex-col gap-6">
      {/* Chart */}
      <div className="card h-[280px] flex flex-col">
        <div className="px-5 py-4 border-b border-soft-border">
          <h2 className="text-sm font-medium text-soft-textHover">Attack Frequency (24h)</h2>
        </div>
        <div className="flex-1 p-4">
          {hourData.length === 0 ? (
            <div className="h-full flex items-center justify-center text-soft-text text-sm">No data recorded</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={hourData} margin={{ top: 10, right: 0, bottom: 0, left: -25 }}>
                <XAxis dataKey="hour" stroke="#3f3f46" tick={{ fill: '#a1a1aa', fontSize: 11 }} tickFormatter={h => `${h}h`} axisLine={false} tickLine={false} />
                <YAxis stroke="#3f3f46" tick={{ fill: '#a1a1aa', fontSize: 11 }} allowDecimals={false} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={TooltipStyle} itemStyle={{ color: '#e5e7eb' }} cursor={{ fill: 'rgba(255, 255, 255, 0.02)' }} />
                <Bar dataKey="cnt" name="Attacks" radius={[2, 2, 0, 0]}>
                  {hourData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.cnt > 50 ? '#0284c7' : '#38bdf8'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Top Stats */}
      <div className="grid grid-cols-1 gap-4">
        {/* Top IPs */}
        <div className="card">
          <div className="px-4 py-3 border-b border-soft-border flex items-center gap-2">
            <MapIcon size={16} className="text-soft-text" />
            <h2 className="text-sm font-medium text-soft-textHover">Top Attacker IPs</h2>
          </div>
          <div className="p-3">
            {topIps.length === 0 ? (
              <p className="text-soft-text text-xs py-4 text-center">No data</p>
            ) : (
              <div className="space-y-1">
                {topIps.map((item, i) => (
                  <div key={i} className="flex items-center justify-between p-2 rounded hover:bg-soft-border/30 transition-colors">
                    <span className="text-soft-textHover font-mono text-xs truncate">{item.ip}</span>
                    <span className="text-soft-text text-[10px] font-mono bg-soft-border/50 px-2 py-0.5 rounded">{item.cnt}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Top Credentials */}
        <div className="card">
          <div className="px-4 py-3 border-b border-soft-border flex items-center gap-2">
            <KeyRound size={16} className="text-soft-text" />
            <h2 className="text-sm font-medium text-soft-textHover">Top Credentials</h2>
          </div>
          <div className="p-3">
            {topCreds.length === 0 ? (
              <p className="text-soft-text text-xs py-4 text-center">No data</p>
            ) : (
              <div className="space-y-1">
                {topCreds.map((item, i) => (
                  <div key={i} className="flex items-center justify-between p-2 rounded hover:bg-soft-border/30 transition-colors">
                    <span className="text-soft-yellow/80 font-mono text-xs truncate">{item.cred}</span>
                    <span className="text-soft-text text-[10px] font-mono bg-soft-border/50 px-2 py-0.5 rounded">{item.cnt}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
