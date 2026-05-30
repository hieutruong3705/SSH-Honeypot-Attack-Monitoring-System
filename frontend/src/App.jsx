import { useState, useEffect, useRef, useCallback } from 'react'
import LiveFeed    from './components/LiveFeed'
import Statistics  from './components/Statistics'
import AttackChart from './components/AttackChart'
import SessionFeed from './components/SessionFeed'

const WS_URL = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws`

export default function App() {
  const [attacks,  setAttacks]  = useState([])
  const [stats,    setStats]    = useState(null)
  const [sessions, setSessions] = useState({})   // { [session_id]: sessionObj }
  const [connected, setConnected] = useState(false)
  const wsRef           = useRef(null)
  const reconnectTimer  = useRef(null)

  const refreshStats = useCallback(() => {
    fetch('/api/stats').then(r => r.json()).then(setStats).catch(() => {})
  }, [])

  // ── WebSocket ──────────────────────────────────────────────────────────────

  const connect = useCallback(() => {
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen  = () => { setConnected(true); clearTimeout(reconnectTimer.current) }
    ws.onclose = () => {
      setConnected(false)
      reconnectTimer.current = setTimeout(connect, 3000)
    }

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        handleEvent(msg)
      } catch (_) {}
    }
  }, [])   // eslint-disable-line react-hooks/exhaustive-deps

  function handleEvent(msg) {
    const { type, data } = msg

    if (type === 'attack') {
      setAttacks(prev => [data, ...prev].slice(0, 100))
      refreshStats()
      return
    }

    if (type === 'session_start') {
      setSessions(prev => ({
        ...prev,
        [data.session_id]: { ...data, commands: [], active: true },
      }))
      return
    }

    if (type === 'session_command') {
      setSessions(prev => {
        const s = prev[data.session_id]
        if (!s) return prev
        return {
          ...prev,
          [data.session_id]: {
            ...s,
            threat_score: data.threat_score,
            threat_level: data.threat_level,
            commands: [
              ...s.commands,
              { cmd: data.cmd, score_delta: data.score_delta, timestamp: data.timestamp },
            ],
          },
        }
      })
      return
    }

    if (type === 'session_end') {
      setSessions(prev => ({
        ...prev,
        [data.session_id]: {
          ...prev[data.session_id],
          ...data,
          commands: data.commands
            ? data.commands.map(c => ({ cmd: c.cmd, score_delta: c.score_delta, timestamp: c.time }))
            : prev[data.session_id]?.commands ?? [],
          active: false,
        },
      }))
      refreshStats()
    }
  }

  // ── Bootstrap ──────────────────────────────────────────────────────────────

  useEffect(() => {
    fetch('/api/attacks').then(r => r.json()).then(setAttacks).catch(() => {})
    refreshStats()

    // Load completed sessions from DB
    fetch('/api/sessions').then(r => r.json()).then(rows => {
      const map = {}
      rows.forEach(s => {
        map[s.session_id] = { ...s, commands: [], active: false }
      })
      setSessions(map)
    }).catch(() => {})

    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect, refreshStats])

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-950 text-white">

      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          <h1 className="text-lg font-bold tracking-tight">SSH Honeypot Monitor</h1>
        </div>
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border ${
          connected
            ? 'bg-green-900/40 text-green-300 border-green-800'
            : 'bg-gray-800 text-gray-500 border-gray-700'
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-green-400' : 'bg-gray-600'}`} />
          {connected ? 'Live' : 'Reconnecting...'}
        </div>
      </header>

      {/* Body */}
      <main className="p-4 md:p-6 space-y-4 max-w-screen-2xl mx-auto">
        {/* Row 1 — stats */}
        <Statistics stats={stats} />

        {/* Row 2 — attack feed + charts */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <LiveFeed attacks={attacks} />
          <AttackChart stats={stats} />
        </div>

        {/* Row 3 — shell sessions */}
        <SessionFeed sessions={sessions} />
      </main>
    </div>
  )
}
