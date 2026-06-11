import { useEffect, useRef } from 'react'

const LINE_STYLE = {
  LOGIN: 'text-cyan-300',
  CMD: 'text-green-300',
  START: 'text-blue-300',
  END: 'text-gray-400',
  SYSTEM: 'text-yellow-300',
}

function TerminalLine({ entry }) {
  return (
    <div className="flex gap-3 whitespace-pre-wrap break-words leading-6">
      <span className="w-[7.5rem] shrink-0 text-gray-500">{entry.time}</span>
      <span className={`w-[4.5rem] shrink-0 font-semibold ${LINE_STYLE[entry.kind] || 'text-gray-300'}`}>
        {entry.kind}
      </span>
      <span className="min-w-0 flex-1 text-gray-200">{entry.text}</span>
    </div>
  )
}

export default function TerminalLog({ entries, connected }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [entries])

  return (
    <div className="bg-black rounded-lg border border-gray-800 overflow-hidden">
      <div className="flex items-center justify-between border-b border-gray-800 bg-gray-950 px-4 py-2">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-red-500" />
            <span className="h-2.5 w-2.5 rounded-full bg-yellow-400" />
            <span className="h-2.5 w-2.5 rounded-full bg-green-500" />
          </div>
          <h2 className="text-sm font-semibold text-gray-200">Terminal Log</h2>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span className={`h-1.5 w-1.5 rounded-full ${connected ? 'bg-green-400' : 'bg-gray-600'}`} />
          <span>{entries.length} lines</span>
        </div>
      </div>

      <div className="h-[360px] overflow-y-auto px-4 py-3 font-mono text-xs md:text-sm">
        {entries.length === 0 ? (
          <div className="flex h-full items-center justify-center text-gray-700">
            waiting for live honeypot events...
          </div>
        ) : (
          <>
            {entries.map((entry) => (
              <TerminalLine key={entry.id} entry={entry} />
            ))}
            <div ref={bottomRef} />
          </>
        )}
      </div>
    </div>
  )
}
