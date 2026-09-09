import { KINDS, Kind } from '../types'

interface Props {
  counts: Record<string, number>
  active: Set<Kind>
  onToggle: (k: Kind) => void
}

export function KindFilter({ counts, active, onToggle }: Props) {
  return (
    <div className="pointer-events-none absolute inset-x-0 top-4 z-10 flex justify-center px-4">
      <div className="pointer-events-auto flex max-w-full flex-wrap justify-center gap-1.5 rounded-xl bg-white/90 p-2 shadow-lg backdrop-blur">
        {KINDS.map((k) => {
          const n = counts[k.id] ?? 0
          const isEnabled = active.has(k.id)
          return (
            <button
              key={k.id}
              onClick={() => onToggle(k.id)}
              disabled={n === 0}
              title={n === 0 ? 'Momentan fără date' : k.label}
              className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition ${
                isEnabled
                  ? 'bg-slate-900 text-white'
                  : n === 0
                    ? 'cursor-not-allowed bg-slate-100 text-slate-300'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: isEnabled ? k.color : '#cbd5e1' }}
              />
              {k.label} ({n})
            </button>
          )
        })}
      </div>
    </div>
  )
}
