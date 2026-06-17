const STYLES = {
  LOW: 'bg-green-900/30 text-green-400 border-green-800/50 shadow-[0_0_10px_rgba(0,255,0,0.1)]',
  MEDIUM: 'bg-yellow-900/40 text-yellow-400 border-yellow-700/50 shadow-[0_0_10px_rgba(255,255,0,0.1)]',
  HIGH: 'bg-orange-900/50 text-orange-400 border-orange-700/50 shadow-[0_0_10px_rgba(255,165,0,0.2)]',
  CRITICAL: 'bg-cyber-neonRed/20 text-cyber-neonRed border-cyber-neonRed/50 animate-pulse shadow-[0_0_15px_rgba(255,42,42,0.3)]',
}

export default function ThreatBadge({ level, score }) {
  const safeLevel = level || 'LOW'
  const style = STYLES[safeLevel] || STYLES.LOW

  return (
    <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-xs font-bold uppercase tracking-wider ${style}`}>
      <span>{safeLevel}</span>
      {score !== undefined && (
        <span className="opacity-70 border-l border-current pl-1.5 ml-0.5 font-mono">
          {score}
        </span>
      )}
    </div>
  )
}
