import ThreatBadge from './ThreatBadge'

const BORDER = {
  LOW: 'border-yellow-700',
  MEDIUM: 'border-orange-600',
  HIGH: 'border-red-600',
  CRITICAL: 'border-purple-500',
}

export default function LiveFeed({ attacks }) {
  return (
    <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-gray-200">Live Attack Feed</h2>
        <span className="text-xs text-gray-500">{attacks.length} entries</span>
      </div>

      <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
        {attacks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-gray-600">
            <svg className="w-10 h-10 mb-3 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            <p className="text-sm">Waiting for attacks...</p>
          </div>
        ) : (
          attacks.map((a, i) => (
            <div
              key={i}
              className={`bg-gray-800/80 rounded-lg p-3 border-l-4 ${BORDER[a.threat_level] || BORDER.LOW} flex items-start justify-between gap-3`}
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-red-400 font-mono text-sm font-medium">{a.ip}</span>
                  <ThreatBadge level={a.threat_level} />
                </div>
                <div className="mt-1.5 text-sm">
                  <span className="text-green-400 font-mono">{a.username}</span>
                  <span className="text-gray-600 mx-1">/</span>
                  <span className="text-yellow-400 font-mono">{a.password}</span>
                </div>
              </div>
              <div className="text-right shrink-0">
                <div className="text-gray-400 text-xs font-mono">
                  {a.timestamp ? a.timestamp.slice(0, 10) : ''}
                </div>
                <div className="text-gray-600 text-xs mt-1">score {a.threat_score}</div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
