import { useState, useEffect, useRef } from 'react'
import { Crosshair, Play, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'

const SCENARIOS = [
  {
    id: 'brute_force',
    name: 'Brute Force Attack',
    desc: '20 login attempts liên tiếp với credential phổ biến',
  },
  {
    id: 'botnet',
    name: 'Botnet Dropper',
    desc: 'Login → wget malware → chmod +x → execute → crontab',
  },
  {
    id: 'recon',
    name: 'Credential Harvester',
    desc: 'Login → thu thập hệ thống → đọc /etc/shadow, SSH keys',
  },
]

function StatusBadge({ state }) {
  if (state === 'running')
    return <span className="px-2 py-0.5 rounded-md text-[10px] uppercase tracking-wider bg-yellow-900/30 text-yellow-500">Running</span>
  if (state === 'done')
    return <span className="px-2 py-0.5 rounded-md text-[10px] uppercase tracking-wider bg-soft-border text-soft-green">Done</span>
  if (state === 'error')
    return <span className="px-2 py-0.5 rounded-md text-[10px] uppercase tracking-wider bg-red-900/30 text-red-500">Error</span>
  return <span className="px-2 py-0.5 rounded-md text-[10px] uppercase tracking-wider bg-soft-border text-soft-text">Idle</span>
}

export default function AttackSimulator() {
  const [statuses, setStatuses] = useState({})
  const pollRefs = useRef({})

  const launch = async (id) => {
    try {
      const res = await fetch(`/api/simulate/${id}`, { method: 'POST' })
      const data = await res.json()
      if (data.status === 'started') {
        setStatuses(prev => ({ ...prev, [id]: { state: 'running', progress: 0, total: 1, step: 'Starting...' } }))
        startPolling(id)
      }
    } catch (e) { console.error(e) }
  }

  const startPolling = (id) => {
    if (pollRefs.current[id]) clearInterval(pollRefs.current[id])
    pollRefs.current[id] = setInterval(async () => {
      try {
        const res = await fetch(`/api/simulate/${id}/status`)
        const data = await res.json()
        setStatuses(prev => ({ ...prev, [id]: data }))
        if (data.state === 'done' || data.state === 'error') {
          clearInterval(pollRefs.current[id])
          delete pollRefs.current[id]
        }
      } catch (_) {}
    }, 500)
  }

  useEffect(() => {
    return () => Object.values(pollRefs.current).forEach(clearInterval)
  }, [])

  return (
    <div className="card flex flex-col">
      <div className="px-5 py-4 border-b border-soft-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Crosshair size={16} className="text-soft-text" />
          <h2 className="text-sm font-medium text-soft-textHover">Attack Simulator</h2>
        </div>
        <span className="text-[10px] text-soft-text font-medium bg-soft-border/50 px-2 py-0.5 rounded-full uppercase tracking-wider">
          {SCENARIOS.length} scenarios
        </span>
      </div>

      <div className="divide-y divide-soft-border">
        {SCENARIOS.map(s => {
          const st = statuses[s.id] || { state: 'idle' }
          const isRunning = st.state === 'running'
          const progress = st.total > 0 ? Math.round((st.progress / st.total) * 100) : 0

          return (
            <div key={s.id} className="px-5 py-4 hover:bg-soft-border/20 transition-colors">
              <div className="flex items-center justify-between mb-2">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-soft-textHover">{s.name}</span>
                    <StatusBadge state={st.state} />
                  </div>
                  <p className="text-xs text-soft-text">{s.desc}</p>
                </div>

                <button
                  onClick={() => launch(s.id)}
                  disabled={isRunning}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors
                    ${isRunning
                      ? 'bg-soft-border text-soft-text cursor-not-allowed'
                      : 'bg-soft-border hover:bg-soft-border/80 text-soft-textHover'
                    }`}
                >
                  {isRunning
                    ? <><Loader2 size={12} className="animate-spin" /> Running</>
                    : <><Play size={12} /> Launch</>
                  }
                </button>
              </div>

              {isRunning && (
                <div className="mt-2 space-y-1.5">
                  <div className="w-full bg-soft-border rounded-full h-1 overflow-hidden">
                    <div className="h-full bg-soft-textHover rounded-full transition-all duration-300" style={{ width: `${progress}%` }} />
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-soft-text font-mono">
                    <span className="truncate">{st.step}</span>
                    <span>{st.progress}/{st.total}</span>
                  </div>
                </div>
              )}

              {st.state === 'done' && (
                <div className="flex items-center gap-1.5 mt-2 text-[10px] text-soft-text">
                  <CheckCircle size={10} className="text-soft-green" />
                  <span>Completed — xem kết quả ở tab Overview</span>
                </div>
              )}

              {st.state === 'error' && (
                <div className="flex items-center gap-1.5 mt-2 text-[10px] text-red-400">
                  <AlertCircle size={10} />
                  <span>{st.step || 'Connection failed'}</span>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
