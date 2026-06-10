import ThreatBadge from './ThreatBadge'

const CMD_COLOR = (delta) => {
  if (delta >= 20) return 'text-red-400'
  if (delta >= 10) return 'text-orange-400'
  if (delta > 0) return 'text-yellow-300'
  return 'text-gray-300'
}

function SessionCard({ session }) {
  const isActive = session.active
  const hasCmds = session.commands && session.commands.length > 0

  return (
    <div className={`rounded-lg border bg-gray-800/60 ${isActive ? 'border-green-700' : 'border-gray-700'
      }`}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700/60">
        <div className="flex items-center gap-2 min-w-0">
          {isActive && (
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse shrink-0" />
          )}
          <span className="text-red-400 font-mono text-sm font-medium">{session.ip}</span>
          <span className="text-gray-500 text-xs font-mono">{session.username}</span>
          <ThreatBadge level={session.threat_level} />
        </div>
        <div className="text-right shrink-0 ml-2">
          <div className="text-gray-500 text-xs">
            {isActive ? (
              <span className="text-green-400 font-medium">● LIVE</span>
            ) : (
              `${session.duration_seconds ?? 0}s`
            )}
          </div>
          <div className="text-gray-600 text-xs">score {session.threat_score}</div>
        </div>
      </div>

      {/* Command stream */}
      <div className="px-3 py-2 space-y-0.5 max-h-40 overflow-y-auto font-mono text-xs">
        {!hasCmds && (
          <span className="text-gray-600">no commands yet</span>
        )}
        {session.commands?.map((c, i) => (
          <div key={i} className="flex items-start gap-1.5">
            <span className="text-gray-600 shrink-0">$</span>
            <span className={`flex-1 break-all ${CMD_COLOR(c.score_delta ?? c.score_delta)}`}>
              {c.cmd}
            </span>
            {(c.score_delta > 0) && (
              <span className="text-gray-600 shrink-0 ml-1">+{c.score_delta}</span>
            )}
          </div>
        ))}
        {isActive && (
          <div className="flex items-center gap-1.5 text-gray-500">
            <span>$</span>
            <span className="animate-pulse">▌</span>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-3 py-1.5 border-t border-gray-700/40 flex justify-between text-xs text-gray-600">
        <span>{session.session_id}</span>
        <span>{session.login_time?.slice(0, 19)}</span>
      </div>
    </div>
  )
}

export default function SessionFeed({ sessions }) {
  const all = Object.values(sessions).sort((a, b) =>
    a.login_time < b.login_time ? 1 : -1
  )
  const active = all.filter(s => s.active)
  const done = all.filter(s => !s.active)

  return (
    <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-gray-200">Shell Sessions</h2>
        <div className="flex items-center gap-3 text-xs">
          {active.length > 0 && (
            <span className="text-green-400 flex items-center gap-1">
              <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
              {active.length} live
            </span>
          )}
          <span className="text-gray-600">{all.length} total</span>
        </div>
      </div>

      {all.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-gray-600">
          <svg className="w-8 h-8 mb-2 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <p className="text-sm">No shell sessions yet</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 max-h-[560px] overflow-y-auto pr-1">
          {active.map(s => <SessionCard key={s.session_id} session={s} />)}
          {done.map(s => <SessionCard key={s.session_id} session={s} />)}
        </div>
      )}
    </div>
  )
}
