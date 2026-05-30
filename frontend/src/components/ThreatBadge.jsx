const STYLES = {
  LOW: 'bg-yellow-900/60 text-yellow-300 border border-yellow-700',
  MEDIUM: 'bg-orange-900/60 text-orange-300 border border-orange-700',
  HIGH: 'bg-red-900/60 text-red-300 border border-red-700',
  CRITICAL: 'bg-purple-900/60 text-purple-300 border border-purple-700 animate-pulse',
}

export default function ThreatBadge({ level }) {
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider ${STYLES[level] || STYLES.LOW}`}>
      {level}
    </span>
  )
}
