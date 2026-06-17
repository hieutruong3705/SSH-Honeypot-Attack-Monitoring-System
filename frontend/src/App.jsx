import { useState, useEffect, useRef, useCallback } from 'react'
import { Server, Activity, TerminalSquare } from 'lucide-react'
import LiveFeed       from './components/LiveFeed'
import Statistics     from './components/Statistics'
import AttackChart    from './components/AttackChart'
import SessionFeed    from './components/SessionFeed'
import TerminalLog    from './components/TerminalLog'
import AttackMap      from './components/AttackMap'
import MalwareCaptures from './components/MalwareCaptures'

const WS_URL = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws`
const MAX_TERMINAL_LINES = 200

const formatClock = (value) => {
  if (!value) return new Date().toLocaleTimeString('en-GB', { hour12: false })
  const normalized = value.includes('T') ? value : value.replace(' ', 'T')
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return value.slice(11, 19) || value.slice(0, 19)
  return date.toLocaleTimeString('en-GB', { hour12: false })
}

const makeLogEntry = (kind, text, timestamp, stableId = null) => ({
  id: stableId || `${Date.now()}-${Math.random().toString(16).slice(2)}`,
  kind,
  time: formatClock(timestamp),
  timestamp: timestamp || '',
  text,
})

const toSortableTime = (value) => {
  if (!value) return 0
  const normalized = value.includes('T') ? value : value.replace(' ', 'T')
  const time = new Date(normalized).getTime()
  return Number.isNaN(time) ? 0 : time
}

const buildTerminalHistory = (attackRows, sessionRows) => {
  const entries = []

  attackRows.forEach((a, index) => {
    entries.push(makeLogEntry(
      'LOGIN',
      `${a.ip || '-'} | ${a.username || '-'}/${a.password || '-'} | score ${a.threat_score ?? 0}`,
      a.timestamp,
      `attack-${a.id ?? index}`,
    ))
  })

  sessionRows.forEach((s, sessionIndex) => {
    entries.push(makeLogEntry(
      'START',
      `${s.ip || '-'} | ${s.username || '-'} | session ${s.session_id || '-'}`,
      s.login_time,
      `session-${s.session_id || sessionIndex}-start`,
    ))

    ;(s.commands || []).forEach((c, commandIndex) => {
      entries.push(makeLogEntry(
        'CMD',
        `${s.ip || '-'} | ${c.cmd || c.command || ''}`,
        c.timestamp || c.time,
        `session-${s.session_id || sessionIndex}-cmd-${commandIndex}`,
      ))
    })

    entries.push(makeLogEntry(
      'END',
      `${s.ip || '-'} | session ${s.session_id || '-'} closed`,
      s.end_time || s.login_time,
      `session-${s.session_id || sessionIndex}-end`,
    ))
  })

  return entries
    .sort((a, b) => toSortableTime(a.timestamp) - toSortableTime(b.timestamp))
    .slice(-MAX_TERMINAL_LINES)
}

export default function App() {
  const [attacks,  setAttacks]  = useState([])
  const [stats,    setStats]    = useState(null)
  const [sessions, setSessions] = useState({})
  const [terminalEntries, setTerminalEntries] = useState([])
  const [connected, setConnected] = useState(false)

  // Clean UI state
  const [activeTab, setActiveTab] = useState('overview') // 'overview', 'terminal', 'sessions'

  const wsRef           = useRef(null)
  const reconnectTimer  = useRef(null)

  const refreshStats = useCallback(() => {
    fetch('/api/stats').then(r => r.json()).then(setStats).catch(() => {})
  }, [])

  const pushTerminal = useCallback((entry) => {
    setTerminalEntries(prev => [...prev, entry].slice(-MAX_TERMINAL_LINES))
  }, [])

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
  }, [])

  function handleEvent(msg) {
    const { type, data } = msg

    if (type === 'attack') {
      setAttacks(prev => [data, ...prev].slice(0, 100))
      pushTerminal(makeLogEntry('LOGIN', `${data.ip} | ${data.username}/${data.password} | score ${data.threat_score ?? 0}`, data.timestamp))
      refreshStats()
      return
    }

    if (type === 'session_start') {
      setSessions(prev => ({
        ...prev,
        [data.session_id]: { ...data, commands: [], active: true },
      }))
      pushTerminal(makeLogEntry('START', `${data.ip} | ${data.username} | session ${data.session_id}`, data.login_time))
      return
    }

    if (type === 'ip_location_update') {
      const locationPatch = {
        proxy_type: data.proxy_type || null,
        country: data.country || null,
        city: data.city || null,
        lat: data.lat ?? null,
        lon: data.lon ?? null,
      }

      setAttacks(prev => prev.map(a =>
        a.ip === data.ip ? { ...a, ...locationPatch } : a
      ))

      setSessions(prev => {
        const next = {}
        Object.entries(prev).forEach(([sessionId, session]) => {
          next[sessionId] = session.ip === data.ip
            ? { ...session, ...locationPatch }
            : session
        })
        return next
      })
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
              { cmd: data.cmd, score_delta: data.score_delta, timestamp: data.timestamp,
                mitre_id: data.mitre_id, technique: data.technique },
            ],
          },
        }
      })
      // Cáº­p nháº­t máº£ng attacks (Live Feed) Ä‘á»ƒ nÃ³ Ä‘á»•i mÃ u Threat Level
      setAttacks(prev => prev.map(a =>
        (a.ip === data.ip) // Map theo IP vÃ¬ attack object ko cÃ³ session_id
          ? { ...a, threat_score: data.threat_score, threat_level: data.threat_level }
          : a
      ))
      pushTerminal(makeLogEntry('CMD', `${data.ip} | ${data.cmd}`, data.timestamp))
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
      pushTerminal(makeLogEntry('END', `${data.ip} | session ${data.session_id} closed`, data.login_time))
      refreshStats()
    }
  }

  useEffect(() => {
    let cancelled = false

    const attacksRequest = fetch('/api/attacks')
      .then(r => r.json())
      .catch(() => [])

    const sessionsRequest = fetch('/api/sessions')
      .then(r => r.json())
      .catch(() => [])

    attacksRequest.then(rows => {
      if (!cancelled) setAttacks(rows)
    })
    refreshStats()

    sessionsRequest.then(rows => {
      if (cancelled) return
      const map = {}
      rows.forEach(s => {
        map[s.session_id] = { ...s, active: false }
      })
      setSessions(map)
    })

    Promise.all([attacksRequest, sessionsRequest]).then(([attackRows, sessionRows]) => {
      if (!cancelled) {
        setTerminalEntries(buildTerminalHistory(attackRows, sessionRows))
      }
    })

    connect()
    return () => {
      cancelled = true
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect, refreshStats])

  return (
    <div className="min-h-screen bg-soft-bg text-soft-text flex flex-col">
      {/* Clean Navbar */}
      <header className="header-nav px-6 py-3 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="bg-soft-border p-1.5 rounded-md">
            <Server size={18} className="text-soft-textHover" />
          </div>
          <h1 className="text-sm font-semibold tracking-wide text-soft-textHover">
            Honeypot Dashboard
          </h1>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1 bg-soft-card p-1 rounded-lg border border-soft-border text-sm font-medium">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-3 py-1.5 rounded-md transition-colors ${activeTab === 'overview' ? 'bg-soft-border text-soft-textHover' : 'hover:text-soft-textHover'}`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('sessions')}
            className={`px-3 py-1.5 rounded-md transition-colors ${activeTab === 'sessions' ? 'bg-soft-border text-soft-textHover' : 'hover:text-soft-textHover'}`}
          >
            Sessions
          </button>
          <button
            onClick={() => setActiveTab('terminal')}
            className={`px-3 py-1.5 rounded-md transition-colors ${activeTab === 'terminal' ? 'bg-soft-border text-soft-textHover' : 'hover:text-soft-textHover'}`}
          >
            System Log
          </button>
        </div>

        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${connected ? 'bg-soft-green' : 'bg-soft-red'}`}></div>
          <span className="text-xs">{connected ? 'Connected' : 'Offline'}</span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-4 md:p-8 max-w-6xl mx-auto w-full space-y-6">

        {activeTab === 'overview' && (
          <div className="space-y-6 animate-in fade-in duration-300">
            <Statistics stats={stats} />
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 space-y-6">
                <AttackMap />
                <LiveFeed attacks={attacks} />
              </div>
              <div className="lg:col-span-1">
                <AttackChart stats={stats} />
              </div>
            </div>
            <MalwareCaptures />
          </div>
        )}

        {activeTab === 'sessions' && (
          <div className="animate-in fade-in duration-300">
            <div className="flex items-center gap-2 mb-4">
              <TerminalSquare size={18} className="text-soft-textHover" />
              <h2 className="text-sm font-medium text-soft-textHover">Interactive Shell Sessions</h2>
            </div>
            <SessionFeed sessions={sessions} />
          </div>
        )}

        {activeTab === 'terminal' && (
          <div className="animate-in fade-in duration-300 h-[70vh]">
            <TerminalLog entries={terminalEntries} connected={connected} />
          </div>
        )}




      </main>
    </div>
  )
}
