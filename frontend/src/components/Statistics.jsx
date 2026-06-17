import { Shield, Target, UserX, KeyRound } from 'lucide-react'

export default function Statistics({ stats }) {
  if (!stats) return null

  const items = [
    { label: 'Total Attacks', value: stats.total || 0, icon: Target, trend: 'All Time' },
    { label: 'Attacks Today', value: stats.today || 0, icon: Shield, trend: 'Today' },
    { label: 'Top Username', value: stats.top_username || '-', icon: UserX, trend: 'Most Targeted' },
    { label: 'Top Password', value: stats.top_password || '-', icon: KeyRound, trend: 'Most Guessed' },
  ]

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {items.map((it, i) => {
        const Icon = it.icon
        return (
          <div key={i} className="card p-5 hover:bg-soft-border/30 transition-colors">
            <div className="flex items-center justify-between mb-4">
              <Icon size={18} className="text-soft-text" />
              <span className="text-[10px] text-soft-text font-medium bg-soft-border/50 px-2 py-0.5 rounded-full uppercase tracking-wider">
                {it.trend}
              </span>
            </div>
            <div>
              <p className="text-xl md:text-2xl font-semibold text-soft-textHover mb-1 truncate">
                {it.value}
              </p>
              <p className="text-xs font-medium text-soft-text">{it.label}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
