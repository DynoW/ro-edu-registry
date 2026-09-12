import { useEffect, useMemo, useState } from 'react'
import { KIND_META, KINDS, Kind, KIND_SINGULAR, LinkRef, isSchoolKind } from '../types'
import { countyName, COUNTY_NAMES } from '../counties'
import { norm } from '../utils'
import { dataUrl } from '../config'
import { LinkChips, parentLabel } from '../components/LinkChips'

interface SearchEntry {
  id: string
  kind: Kind
  name: string
  county: string
  parent?: string
  external_ids?: Record<string, string | number>
  addr?: string | null
  postcode?: string | null
  phone?: string
  links?: LinkRef[]
}

const PAGE = 200

export function SearchPage() {
  const [entries, setEntries] = useState<SearchEntry[] | null>(null)
  const [q, setQ] = useState('')
  const [county, setCounty] = useState('')
  const [kinds, setKinds] = useState<Set<Kind>>(new Set())
  const [visible, setVisible] = useState(PAGE)

  useEffect(() => {
    fetch(dataUrl('search.json'))
      .then((r) => r.json())
      .then((d) => {
        setEntries(d.entities ?? [])
        setKinds(new Set((d.entities ?? []).map((e: SearchEntry) => e.kind)))
      })
      .catch(() => setEntries([]))
  }, [])

  const kindCounts = useMemo(() => {
    const c: Record<string, number> = {}
    for (const e of entries ?? []) c[e.kind] = (c[e.kind] ?? 0) + 1
    return c
  }, [entries])

  const filtered = useMemo(() => {
    const nq = norm(q)
    const ids = (e: SearchEntry) => Object.values(e.external_ids ?? {}).map(String).join(' ')
    return (entries ?? []).filter(
      (e) =>
        kinds.has(e.kind) &&
        (!county || e.county === county) &&
        (nq.length < 2 ||
          norm(e.name).includes(nq) ||
          norm(e.id).includes(nq) ||
          norm(e.phone ?? '').includes(nq) ||
          norm(ids(e)).includes(nq) ||
          norm(e.addr ?? '').includes(nq)),
    )
  }, [entries, q, county, kinds])

  const toggleKind = (k: Kind) => {
    setKinds((prev) => {
      const next = new Set(prev)
      if (next.has(k)) next.delete(k)
      else next.add(k)
      return next
    })
    setVisible(PAGE)
  }

  const nameById = useMemo(
    () => new Map((entries ?? []).map((e) => [e.id, e.name])),
    [entries],
  )

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8">
      <h1 className="text-2xl font-bold text-slate-900">Căutare</h1>
      <p className="mt-1 text-sm text-slate-500">
        Toate entitățile din registru, căutabile și fără hartă.
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        <input
          value={q}
          onChange={(e) => {
            setQ(e.target.value)
            setVisible(PAGE)
          }}
          placeholder="Caută nume, adresă, telefon…"
          className="min-w-56 flex-1 rounded-xl border border-slate-200 px-4 py-2.5 text-sm outline-none focus:border-sky-400"
        />
        <select
          value={county}
          onChange={(e) => {
            setCounty(e.target.value)
            setVisible(PAGE)
          }}
          className="rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-sky-400"
        >
          <option value="">Toate județele</option>
          {Object.entries(COUNTY_NAMES).map(([code, name]) => (
            <option key={code} value={code}>
              {name}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {KINDS.map((k) => {
          const n = kindCounts[k.id] ?? 0
          const on = kinds.has(k.id)
          return (
            <button
              key={k.id}
              onClick={() => toggleKind(k.id)}
              disabled={n === 0}
              className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition ${
                on
                  ? 'bg-slate-900 text-white'
                  : n === 0
                    ? 'cursor-not-allowed bg-slate-100 text-slate-300'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: on ? k.color : '#cbd5e1' }} />
              {k.label} ({n})
            </button>
          )
        })}
      </div>

      {entries !== null && filtered.length === 0 && (
        <div className="mt-6 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-500">
          Nicio potrivire pentru filtrele curente.
        </div>
      )}

      <p className="mt-4 text-xs text-slate-400">
        {filtered.length.toLocaleString('ro-RO')} rezultate
        {filtered.length > visible && ` — afișate ${visible} (mai sunt ${filtered.length - visible})`}
      </p>

      <ul className="mt-2 space-y-2">
        {filtered.slice(0, visible).map((e) => {
          const meta = KIND_META[e.kind]
          return (
            <li key={e.id} className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="text-sm font-semibold text-slate-800">{e.name}</span>
                <span className="rounded-full px-2 py-0.5 text-[11px] font-semibold text-white" style={{ backgroundColor: meta?.color }}>
                  {isSchoolKind(e.kind) ? countyName(e.county) : `${countyName(e.county)} · ${KIND_SINGULAR[e.kind]}`}
                </span>
              </div>
              {e.parent && (
                <div className="mt-0.5 text-xs italic text-slate-500">
                  {parentLabel(e.kind)} {nameById.get(e.parent) ?? e.parent.replace(/^(siiir|slug):/, '')}
                </div>
              )}
              {(e.addr || e.postcode) && (
                <div className="mt-0.5 text-xs text-slate-400">{[e.addr, e.postcode].filter(Boolean).join(', ')}</div>
              )}
              <LinkChips links={e.links} />
            </li>
          )
        })}
      </ul>

      {filtered.length > visible && (
        <button
          onClick={() => setVisible((v) => v + PAGE)}
          className="mt-4 w-full rounded-xl border border-slate-200 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Afișează încă {Math.min(PAGE, filtered.length - visible)}
        </button>
      )}
    </div>
  )
}
