import { ShieldAlert } from 'lucide-react'

function Badge({ level }) {
  const styles = {
    LOW: 'bg-soft-border text-soft-text',
    MEDIUM: 'bg-yellow-900/30 text-yellow-500',
    HIGH: 'bg-orange-900/30 text-orange-500',
    CRITICAL: 'bg-red-900/30 text-red-500 font-semibold',
  }
  const cls = styles[level] || styles.LOW
  return (
    <span className={`px-2 py-0.5 rounded-md text-[10px] uppercase tracking-wider ${cls}`}>
      {level || 'LOW'}
    </span>
  )
}

export default function LiveFeed({ attacks }) {
  return (
    <div className="card h-[400px] flex flex-col">
      <div className="px-5 py-4 border-b border-soft-border flex items-center justify-between">
        <h2 className="text-sm font-medium text-soft-textHover">Live Feed</h2>
        <span className="text-xs text-soft-text bg-soft-border/50 px-2 py-1 rounded-md">{attacks.length} events</span>
      </div>

      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="text-xs text-soft-text bg-soft-bg sticky top-0 z-10 border-b border-soft-border shadow-sm">
            <tr>
              <th className="px-5 py-3 font-medium">Time</th>
              <th className="px-5 py-3 font-medium">IP Address</th>
              <th className="px-5 py-3 font-medium">Credentials</th>
              <th className="px-5 py-3 font-medium text-right">Threat</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-soft-border">
            {attacks.length === 0 && (
              <tr>
                <td colSpan="4" className="text-center py-12 text-soft-text text-sm">No activity recorded.</td>
              </tr>
            )}
            {attacks.map((a, i) => (
              <tr key={i} className="hover:bg-soft-border/30 transition-colors">
                <td className="px-5 py-3 text-soft-text text-xs">{a.timestamp}</td>
                <td className="px-5 py-3 font-mono text-soft-textHover text-xs flex items-center gap-2">
                  <span>{a.ip}</span>
                  {a.proxy_type && (
                    <span className="bg-red-500 text-white text-[9px] px-1 rounded font-bold tracking-wider">
                      [{a.proxy_type.toUpperCase()}]
                    </span>
                  )}
                </td>
                <td className="px-5 py-3 text-xs">
                  <span className="text-soft-textHover">{a.username}</span>
                  <span className="text-soft-text mx-1">/</span>
                  <span className="text-soft-text">{a.password}</span>
                </td>
                <td className="px-5 py-3 text-right">
                  <Badge level={a.threat_level} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
