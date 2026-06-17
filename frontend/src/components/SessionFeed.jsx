import { useState, useMemo } from 'react'
import { TerminalSquare, ChevronDown, ChevronRight } from 'lucide-react'

function classifySession(commands) {
  if (!commands || commands.length === 0) return null
  const tactics = new Set()
  commands.forEach(c => {
    if (c.mitre_id) {
      // Map known technique IDs to tactics
      const id = c.mitre_id
      if (['T1105', 'T1095'].includes(id)) tactics.add('C2')
      if (['T1222.002', 'T1070', 'T1027'].includes(id)) tactics.add('Evasion')
      if (['T1053.003', 'T1098'].includes(id)) tactics.add('Persistence')
      if (['T1003', 'T1110', 'T1110.002'].includes(id)) tactics.add('CredAccess')
      if (['T1082', 'T1046', 'T1057'].includes(id)) tactics.add('Discovery')
      if (['T1059.004', 'T1059.006', 'T1059.001'].includes(id)) tactics.add('Execution')
      if (['T1548'].includes(id)) tactics.add('PrivEsc')
    }
  })

  if (tactics.has('C2') && tactics.has('Evasion') && tactics.has('Persistence'))
    return 'BOTNET DROPPER'
  if (tactics.has('C2') && tactics.has('Evasion'))
    return 'MALWARE DEPLOYER'
  if (tactics.has('CredAccess') && tactics.has('Discovery'))
    return 'RECON & STEAL'
  if (tactics.has('CredAccess'))
    return 'CREDENTIAL HARVESTER'
  if (tactics.has('Persistence'))
    return 'PERSISTENCE INSTALLER'
  if (tactics.has('Discovery'))
    return 'RECON SCOUT'
  return null
}

const CLASS_COLORS = {
  'BOTNET DROPPER':        'bg-red-500/80 text-white',
  'MALWARE DEPLOYER':      'bg-orange-500/80 text-white',
  'CREDENTIAL HARVESTER':  'bg-yellow-500/80 text-white',
  'RECON & STEAL':         'bg-purple-500/80 text-white',
  'PERSISTENCE INSTALLER': 'bg-pink-500/80 text-white',
  'RECON SCOUT':           'bg-soft-border text-soft-textHover',
}

function SessionCard({ session }) {
  const [expanded, setExpanded] = useState(session.active)
  const isActive = session.active
  const hasCmds = session.commands && session.commands.length > 0
  const isCritical = session.threat_level === 'CRITICAL'

  const label = useMemo(() => classifySession(session.commands), [session.commands])

  return (
    <div className={`card overflow-hidden transition-colors ${isCritical ? 'border-red-500 shadow-[0_0_15px_rgba(239,68,68,0.3)]' : ''}`}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-soft-border/30 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <button className="text-soft-text hover:text-soft-textHover">
            {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </button>

          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="text-soft-textHover font-medium text-sm flex flex-wrap items-center gap-2">
                {session.ip}
                {session.proxy_type && (
                  <span className="bg-red-500 text-white text-[9px] px-1 rounded font-bold tracking-wider">
                    [{session.proxy_type.toUpperCase()}]
                  </span>
                )}
                {session.client_tool && (
                  <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold tracking-wider ${
                    session.client_tool.includes('BOTNET') || session.client_tool.includes('SCANNER')
                    ? 'bg-red-500/80 text-white'
                    : 'bg-purple-500/80 text-white'
                  }`}>
                    {session.client_tool}
                  </span>
                )}
                {label && (
                  <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold tracking-wider ${CLASS_COLORS[label] || 'bg-soft-border text-soft-text'}`}>
                    {label}
                  </span>
                )}
              </span>
              {isActive && (
                <span className="w-2 h-2 rounded-full bg-soft-green animate-pulse"></span>
              )}
            </div>
            <span className="text-soft-text text-xs">user: {session.username}</span>
          </div>
        </div>

        <div className="text-right">
          <div className="text-xs font-medium">
            {isActive ? (
              <span className="text-soft-green">Active</span>
            ) : (
              <span className="text-soft-text">{session.duration_seconds ?? 0}s</span>
            )}
          </div>
          <div className={`text-[10px] mt-0.5 ${isCritical ? 'text-red-500 font-bold' : 'text-soft-text'}`}>
            {session.threat_level} (Score: {session.threat_score})
          </div>
        </div>
      </div>

      {/* Expanded Terminal View */}
      {expanded && (
        <div className="border-t border-soft-border bg-[#0f172a]">
          <div className="px-4 py-3 space-y-1.5 max-h-60 overflow-y-auto font-mono text-xs">
            {!hasCmds && (
              <span className="text-soft-text italic">Waiting for commands...</span>
            )}
            {session.commands?.map((c, i) => (
              <div key={i} className="flex items-start gap-2 text-soft-textHover py-0.5">
                <span className="text-soft-text shrink-0 select-none">$</span>
                <span className="flex-1 break-all">{c.cmd}</span>
                {c.mitre_id && (
                  <span className="shrink-0 text-[9px] px-1.5 py-0.5 rounded bg-blue-900/50 text-blue-300 font-bold">
                    {c.mitre_id}
                  </span>
                )}
              </div>
            ))}
            {isActive && (
              <div className="flex items-center gap-2 text-soft-textHover py-0.5">
                <span className="select-none">$</span>
                <span className="animate-pulse bg-soft-text w-1.5 h-3.5 inline-block"></span>
              </div>
            )}
          </div>
          <div className="px-4 py-2 border-t border-soft-border flex justify-between items-center text-[10px] text-soft-text bg-soft-bg">
            <div className="flex gap-4">
              <span>ID: {session.session_id}</span>
              {session.fingerprint && (
                <span className="text-purple-400/70" title="SSH Fingerprint">
                  FP: {session.fingerprint}
                </span>
              )}
            </div>
            <span>{session.login_time?.slice(0, 19)}</span>
          </div>
        </div>
      )}
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
    <div>
      {all.length === 0 ? (
        <div className="card flex flex-col items-center justify-center py-16 text-soft-text">
          <TerminalSquare size={32} className="mb-3 opacity-50" />
          <p className="text-sm font-medium">No active sessions</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {active.map(s => <SessionCard key={s.session_id} session={s} />)}
          {done.map(s => <SessionCard key={s.session_id} session={s} />)}
        </div>
      )}
    </div>
  )
}
