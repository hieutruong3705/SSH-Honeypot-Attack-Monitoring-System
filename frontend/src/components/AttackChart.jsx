import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell,
} from 'recharts'

const IP_COLORS = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6']

const TooltipStyle = {
  backgroundColor: '#1f2937',
  border: '1px solid #374151',
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
    <div className="space-y-4">
      {/* Attacks by hour */}
      <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
        <h2 className="text-base font-semibold text-gray-200 mb-4">Attacks by Hour (Today)</h2>
        {hourData.length === 0 ? (
          <div className="h-36 flex items-center justify-center text-gray-600 text-sm">No data yet</div>
        ) : (
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={hourData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <XAxis dataKey="hour" stroke="#4b5563" tick={{ fill: '#9ca3af', fontSize: 11 }} tickFormatter={h => `${h}h`} />
              <YAxis stroke="#4b5563" tick={{ fill: '#9ca3af', fontSize: 11 }} allowDecimals={false} />
              <Tooltip contentStyle={TooltipStyle} cursor={{ fill: '#1f2937' }} />
              <Bar dataKey="cnt" name="Attacks" fill="#ef4444" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Top IPs + Top Credentials side by side */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <h2 className="text-sm font-semibold text-gray-200 mb-3">Top Attacker IPs</h2>
          {topIps.length === 0 ? (
            <p className="text-gray-600 text-xs py-4 text-center">No data</p>
          ) : (
            <div className="space-y-2">
              {topIps.map((item, i) => (
                <div key={i} className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span style={{ color: IP_COLORS[i] }} className="text-xs font-bold">#{i + 1}</span>
                    <span className="text-red-400 font-mono text-xs truncate">{item.ip}</span>
                  </div>
                  <span className="text-gray-400 text-xs shrink-0 font-mono">{item.cnt}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <h2 className="text-sm font-semibold text-gray-200 mb-3">Top Credentials</h2>
          {topCreds.length === 0 ? (
            <p className="text-gray-600 text-xs py-4 text-center">No data</p>
          ) : (
            <div className="space-y-2">
              {topCreds.map((item, i) => (
                <div key={i} className="flex items-center justify-between gap-2">
                  <span className="text-yellow-400 font-mono text-xs truncate">{item.cred}</span>
                  <span className="text-gray-400 text-xs shrink-0 font-mono">{item.cnt}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
