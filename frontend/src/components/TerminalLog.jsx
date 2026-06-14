import { useEffect, useRef } from 'react'

export default function TerminalLog({ entries, connected }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [entries])

  return (
    <div className="card overflow-hidden flex flex-col h-full bg-[#0f172a]">
      <div className="px-4 py-3 border-b border-soft-border flex items-center justify-between bg-soft-bg">
        <h2 className="text-sm font-medium text-soft-textHover">System Log</h2>
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-soft-border"></div>
          <div className="w-2.5 h-2.5 rounded-full bg-soft-border"></div>
          <div className="w-2.5 h-2.5 rounded-full bg-soft-border"></div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 font-mono text-sm">
        {!connected && (
          <div className="text-soft-red mb-2 italic">
            Disconnected from server...
          </div>
        )}
        
        {entries.map(e => {
          let color = 'text-soft-text'
          if (e.kind === 'LOGIN') color = 'text-soft-yellow'
          if (e.kind === 'START') color = 'text-soft-green'
          if (e.kind === 'CMD')   color = 'text-soft-textHover'
          if (e.kind === 'END')   color = 'text-soft-text'

          return (
            <div key={e.id} className="mb-1 leading-relaxed break-all hover:bg-white/5 px-1 rounded transition-colors">
              <span className="text-soft-text/60 mr-3">[{e.time}]</span>
              <span className={`font-semibold mr-2 ${color}`}>[{e.kind}]</span>
              <span className="text-gray-300">{e.text}</span>
            </div>
          )
        })}
        <div ref={bottomRef} className="h-4" />
      </div>
    </div>
  )
}
