import { Feature, KIND_META } from '../types'
import { countyName } from '../counties'
import { ISSUE_TEMPLATES, REPO_URL } from '../config'

interface Props {
  feature: Feature
  onClose: () => void
}

export function SchoolModal({ feature, onClose }: Props) {
  const p = feature.properties
  const meta = KIND_META[p.kind]
  const editUrl = REPO_URL
    ? `${REPO_URL}/issues/new?template=${ISSUE_TEMPLATES.fixData}&title=${encodeURIComponent(`Corecție: ${p.name}`)}&siiir=${encodeURIComponent(p.id)}`
    : null

  return (
    <div className="absolute right-4 top-16 z-20 max-h-[calc(100%-5rem)] w-96 overflow-y-auto rounded-2xl border border-slate-100 bg-white/95 p-5 shadow-2xl backdrop-blur">
      <div className="mb-2 flex items-start justify-between gap-2">
        <span className="rounded-full px-2.5 py-0.5 text-xs font-semibold text-white" style={{ backgroundColor: meta?.color }}>
          {countyName(p.county)}
          {p.env ? ` · ${p.env === 'URBAN' ? 'urban' : 'rural'}` : ''}
        </span>
        <button onClick={onClose} className="text-lg leading-none text-slate-400 hover:text-slate-700 hover:cursor-pointer" aria-label="Închide">
          ×
        </button>
      </div>

      <h2 className="text-base font-bold leading-snug text-slate-900">{p.name}</h2>
      {(p.addr || p.postcode) && (
        <p className="mt-1 text-xs text-slate-500">
          {[p.addr, p.postcode].filter(Boolean).join(', ')}
          {(p.coords_precision === 'village' || p.coords_precision === 'centroid') && (
            <span className="ml-1 italic text-slate-400">· locație aproximativă</span>
          )}
        </p>
      )}

      <div className="mt-4 grid grid-cols-3 gap-2 rounded-xl bg-slate-50 p-3 text-center">
        <div>
          <div className="text-[11px] font-semibold uppercase text-slate-400">Candidați</div>
          <div className="text-sm font-bold text-slate-800">{p.cand ?? '—'}</div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase text-slate-400">Repartizați</div>
          <div className="text-sm font-bold text-emerald-600">{p.rep ?? '—'}</div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase text-slate-400">Nerepartizați</div>
          <div className="text-sm font-bold text-rose-500">{p.nerep ?? '—'}</div>
        </div>
      </div>
      {p.cand == null && p.rep == null && p.nerep == null && (
        <p className="mt-1 text-center text-[11px] italic text-slate-400">
          fără date de admitere — unitatea nu participă la repartizare
        </p>
      )}

      <div className="mt-3 flex flex-wrap gap-1.5 text-sm">
        {p.phone && (
          <a href={`tel:${p.phone}`} className="rounded-lg bg-slate-100 px-2 py-1 font-medium text-slate-700 hover:bg-slate-200">
            {p.phone}
          </a>
        )}
        {p.website && (
          <a href={p.website} target="_blank" rel="noreferrer" className="rounded-lg bg-sky-50 px-2 py-1 font-medium text-sky-700 hover:bg-sky-100">
            website
          </a>
        )}
        {p.email && (
          <a href={`mailto:${p.email}`} className="rounded-lg bg-emerald-50 px-2 py-1 font-medium text-emerald-700 hover:bg-emerald-100">
            {p.email}
          </a>
        )}
      </div>

      <div className="mt-3 flex flex-col gap-1.5 text-sm">
        {editUrl && (
          <a href={editUrl} target="_blank" rel="noreferrer" className="text-xs text-slate-500 hover:text-slate-800 hover:underline">
            Date greșite? Editează pe GitHub
          </a>
        )}
      </div>
    </div>
  )
}
