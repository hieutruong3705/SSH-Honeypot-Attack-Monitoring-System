import { useState, useEffect } from 'react'
import { ShieldCheck, Play, Loader2, ChevronDown, ChevronRight } from 'lucide-react'

function StatusBadge({ status }) {
  const styles = {
    PASS: 'bg-green-500/80 text-white',
    FAIL: 'bg-red-500/80 text-white',
    WARNING: 'bg-yellow-500/80 text-white',
  }
  return (
    <span className={`px-2 py-0.5 rounded-md text-[10px] uppercase tracking-wider font-medium ${styles[status] || styles.FAIL}`}>
      {status}
    </span>
  )
}

function CheckRow({ check }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border-b border-soft-border last:border-0">
      <div
        className="flex items-center gap-3 px-5 py-3 cursor-pointer hover:bg-soft-border/20 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <button className="text-soft-text hover:text-soft-textHover">
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>
        <span className={`w-2 h-2 rounded-full inline-block ${
          check.status === 'PASS' ? 'bg-green-400' :
          check.status === 'FAIL' ? 'bg-red-400' : 'bg-yellow-400'
        }`} />
        <div className="flex-1 min-w-0">
          <span className="text-xs font-medium text-soft-textHover">{check.name}</span>
        </div>
        {check.cis_id && (
          <span className="text-[10px] text-blue-400 font-mono font-medium bg-blue-500/10 px-1.5 py-0.5 rounded">
            {check.cis_id}
          </span>
        )}
        <span className="text-[10px] text-soft-text font-medium bg-soft-border/50 px-2 py-0.5 rounded-full uppercase tracking-wider">
          {check.category}
        </span>
        <StatusBadge status={check.status} />
        <span className="text-xs text-soft-text font-mono w-10 text-right">{check.score}/{check.weight}</span>
      </div>

      {expanded && (
        <div className="px-5 pb-3 pl-14 space-y-2">
          {check.cis_ref && (
            <div>
              <span className="text-[10px] text-soft-text uppercase tracking-wider">CIS Reference</span>
              <p className="text-xs text-blue-400/80 font-mono mt-0.5">{check.cis_ref}</p>
            </div>
          )}
          <div>
            <span className="text-[10px] text-soft-text uppercase tracking-wider">Detail</span>
            <p className="text-xs text-soft-textHover font-mono mt-0.5 break-all">{check.detail}</p>
          </div>
          {check.status !== 'PASS' && (
            <div>
              <span className="text-[10px] text-soft-text uppercase tracking-wider">Fix</span>
              <p className="text-xs text-soft-text mt-0.5 font-mono">{check.recommendation}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function SystemAudit() {
  const [result, setResult] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)

  const runAudit = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/audit')
      const data = await res.json()
      setResult(data)
      refreshHistory()
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  const refreshHistory = async () => {
    try {
      const res = await fetch('/api/audit/history')
      const data = await res.json()
      setHistory(data)
    } catch (_) {}
  }

  useEffect(() => { refreshHistory() }, [])

  return (
    <div className="space-y-4">
      {/* Header card */}
      <div className="card">
        <div className="px-5 py-4 border-b border-soft-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck size={16} className="text-soft-text" />
            <h2 className="text-sm font-medium text-soft-textHover">System Security Audit</h2>
            <span className="text-[10px] text-blue-400 font-mono bg-blue-500/10 px-1.5 py-0.5 rounded">CIS Benchmark</span>
          </div>
          <button
            onClick={runAudit}
            disabled={loading}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors
              ${loading
                ? 'bg-soft-border text-soft-text cursor-not-allowed'
                : 'bg-soft-border hover:bg-soft-border/80 text-soft-textHover'
              }`}
          >
            {loading
              ? <><Loader2 size={12} className="animate-spin" /> Scanning...</>
              : <><Play size={12} /> Run Audit</>
            }
          </button>
        </div>

        {result && (
          <div className="px-5 py-4">
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              <div className="p-4 rounded-lg bg-soft-bg">
                <p className="text-xs font-medium text-soft-text mb-1">Score</p>
                <p className="text-2xl font-semibold text-soft-textHover">{result.percentage}<span className="text-sm text-soft-text">/100</span></p>
              </div>
              <div className="p-4 rounded-lg bg-soft-bg">
                <p className="text-xs font-medium text-soft-text mb-1">Grade</p>
                <p className={`text-2xl font-semibold ${
                  result.grade === 'A' ? 'text-soft-green' :
                  result.grade === 'B' ? 'text-blue-400' :
                  result.grade === 'C' ? 'text-yellow-400' : 'text-red-400'
                }`}>{result.grade}</p>
              </div>
              <div className="p-4 rounded-lg bg-soft-bg">
                <p className="text-xs font-medium text-soft-text mb-1">Passed</p>
                <p className="text-2xl font-semibold text-green-500">{result.checks.filter(c => c.status === 'PASS').length}</p>
              </div>
              <div className="p-4 rounded-lg bg-soft-bg">
                <p className="text-xs font-medium text-soft-text mb-1">Warning</p>
                <p className="text-2xl font-semibold text-yellow-500">{result.checks.filter(c => c.status === 'WARNING').length}</p>
              </div>
              <div className="p-4 rounded-lg bg-soft-bg">
                <p className="text-xs font-medium text-soft-text mb-1">Failed</p>
                <p className="text-2xl font-semibold text-red-500">{result.checks.filter(c => c.status === 'FAIL').length}</p>
              </div>
            </div>
            <div className="flex items-center justify-between mt-3 text-[10px] text-soft-text">
              <span>Platform: {result.platform}</span>
              <span>Scanned: {result.timestamp}</span>
            </div>
          </div>
        )}

        {!result && !loading && (
          <div className="py-16 flex flex-col items-center justify-center">
            <ShieldCheck size={32} className="text-soft-border mb-3" />
            <p className="text-sm font-medium text-soft-text">Chưa có kết quả</p>
            <p className="text-xs text-soft-text mt-1">Bấm "Run Audit" để quét hệ thống</p>
          </div>
        )}
      </div>

      {/* Checklist */}
      {result && (
        <div className="card">
          <div className="px-5 py-4 border-b border-soft-border flex items-center justify-between">
            <h2 className="text-sm font-medium text-soft-textHover">Checklist</h2>
            <span className="text-[10px] text-soft-text font-medium bg-soft-border/50 px-2 py-0.5 rounded-full uppercase tracking-wider">
              {result.checks.length} checks
            </span>
          </div>
          <div>
            {result.checks.map((c, i) => <CheckRow key={i} check={c} />)}
          </div>
        </div>
      )}

      {/* Scan History */}
      {history.length > 0 && (
        <div className="card">
          <div className="px-5 py-4 border-b border-soft-border flex items-center justify-between">
            <h2 className="text-sm font-medium text-soft-textHover">Scan History</h2>
            <span className="text-[10px] text-soft-text font-medium bg-soft-border/50 px-2 py-0.5 rounded-full uppercase tracking-wider">
              {history.length} scans
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="text-xs text-soft-text bg-soft-bg border-b border-soft-border">
                <tr>
                  <th className="px-5 py-3 font-medium">Time</th>
                  <th className="px-5 py-3 font-medium">Score</th>
                  <th className="px-5 py-3 font-medium">Grade</th>
                  <th className="px-5 py-3 font-medium text-right">Percentage</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-soft-border">
                {history.map((h, i) => (
                  <tr key={i} className="hover:bg-soft-border/30 transition-colors">
                    <td className="px-5 py-3 text-soft-text text-xs">{h.timestamp}</td>
                    <td className="px-5 py-3 text-xs font-mono text-soft-textHover">{h.score}/{h.max_score}</td>
                    <td className="px-5 py-3">
                      <span className={`text-xs font-bold ${
                        h.grade === 'A' ? 'text-green-500' :
                        h.grade === 'B' ? 'text-blue-400' :
                        h.grade === 'C' ? 'text-yellow-400' : 'text-red-400'
                      }`}>{h.grade}</span>
                    </td>
                    <td className="px-5 py-3 text-xs font-mono text-soft-text text-right">{h.percentage}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
