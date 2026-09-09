import { useMemo, useState } from 'react'
import { Feature, KIND_META, Kind } from '../types'
import { norm } from '../utils'
import { countyName } from '../counties'

interface Props {
  features: Feature[]
  onSelect: (f: Feature) => void
}

export function SearchBar({ features, onSelect }: Props) {
  const [q, setQ] = useState('')

  const results = useMemo(() => {
    const nq = norm(q)
    if (nq.length < 3) return []
    return features
      .filter(
        (f) =>
          norm(f.properties.name).includes(nq) ||
          norm(f.properties.id).includes(nq) ||
          norm(f.properties.phone).includes(nq),
      )
      .slice(0, 8)
  }, [q, features])

  return (
    <div className="absolute left-4 top-4 z-10 w-80">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Caută școală, liceu, telefon…"
        className="w-full rounded-xl border border-slate-200 bg-white/95 px-4 py-2.5 text-sm shadow-lg outline-none backdrop-blur placeholder:text-slate-400 focus:border-sky-400"
      />
      {results.length > 0 && (
        <ul className="mt-1 max-h-80 overflow-y-auto rounded-xl bg-white/95 shadow-xl backdrop-blur">
          {results.map((f) => {
            const meta = KIND_META[f.properties.kind as Kind]
            return (
              <li key={f.properties.id}>
                <button
                  onClick={() => {
                    onSelect(f)
                    setQ('')
                  }}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-slate-100"
                >
                  <span
                    className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ backgroundColor: meta?.color }}
                  />
                  <span className="min-w-0">
                    <span className="block truncate text-slate-800">{f.properties.name}</span>
                    <span className="block text-xs text-slate-400">
                      {countyName(f.properties.county)}
                    </span>
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
