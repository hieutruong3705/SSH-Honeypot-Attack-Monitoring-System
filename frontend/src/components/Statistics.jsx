const CARDS = [
  { key: 'total',        label: 'Total Attacks',   color: 'text-red-400',    icon: '⚡' },
  { key: 'today',        label: 'Today',            color: 'text-orange-400', icon: '📅' },
  { key: 'top_username', label: 'Top Username',     color: 'text-yellow-400', icon: '👤' },
  { key: 'top_password', label: 'Top Password',     color: 'text-green-400',  icon: '🔑' },
]

export default function Statistics({ stats }) {
  if (!stats) return null
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {CARDS.map(({ key, label, color, icon }) => (
        <div key={key} className="bg-gray-900 rounded-xl p-4 border border-gray-800">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-base">{icon}</span>
            <span className="text-gray-500 text-xs uppercase tracking-wider">{label}</span>
          </div>
          <div className={`text-2xl font-bold font-mono ${color} truncate`}>
            {stats[key] ?? '-'}
          </div>
        </div>
      ))}
    </div>
  )
}
