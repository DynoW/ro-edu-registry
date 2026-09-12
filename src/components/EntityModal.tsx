import { Feature, KIND_META, KIND_SINGULAR, isSchoolKind } from '../types'
import { countyName } from '../counties'
import { ISSUE_TEMPLATES, REPO_URL } from '../config'
import { LinkChips, extIdLabel, parentLabel } from './LinkChips'

interface Props {
  feature: Feature
  parentFeature?: Feature
  onSelectParent?: (f: Feature) => void
  onClose: () => void
}

export function EntityModal({ feature, parentFeature, onSelectParent, onClose }: Props) {
  const p = feature.properties
  const meta = KIND_META[p.kind]
  const school = isSchoolKind(p.kind)
  const editUrl = REPO_URL
    ? `${REPO_URL}/issues/new?template=${ISSUE_TEMPLATES.fixData}&title=${encodeURIComponent(`Corecție: ${p.name}`)}&siiir=${encodeURIComponent(p.id)}`
    : null

  return (
    <div className="absolute right-4 top-16 z-20 max-h-[calc(100%-5rem)] w-96 overflow-y-auto rounded-2xl border border-slate-100 bg-white/95 p-5 shadow-2xl backdrop-blur">
      <div className="mb-2 flex items-start justify-between gap-2">
        <span className="rounded-full px-2.5 py-0.5 text-xs font-semibold text-white" style={{ backgroundColor: meta?.color }}>
          {countyName(p.county)}
          {school
            ? p.env
              ? ` · ${p.env === 'URBAN' ? 'urban' : 'rural'}`
              : ''
            : ` · ${KIND_SINGULAR[p.kind]}`}
        </span>
        <button onClick={onClose} className="text-lg leading-none text-slate-400 hover:text-slate-700" aria-label="Închide">
          ×
        </button>
      </div>

      <h2 className="text-base font-bold leading-snug text-slate-900">{p.name}</h2>
      {p.external_ids && Object.keys(p.external_ids).length > 0 && (
        <p className="mt-1 text-xs font-semibold text-slate-700">
          {Object.entries(p.external_ids)
            .map(([k, v]) => `${extIdLabel(k)} #${v}`)
            .join(' · ')}
        </p>
      )}
      {p.parent &&
        (parentFeature && onSelectParent ? (
          <button
            onClick={() => onSelectParent(parentFeature)}
            className="mt-1 block text-left text-xs italic text-sky-700 hover:text-sky-900 hover:underline"
          >
            {parentLabel(p.kind)} {parentFeature.properties.name}
          </button>
        ) : (
          <p className="mt-1 text-xs italic text-slate-500">
            {parentLabel(p.kind)} {parentFeature?.properties.name ?? p.parent.replace(/^(siiir|slug):/, '')}
          </p>
        ))}
      {(p.addr || p.postcode || p.city) && (
        <p className="mt-1 text-xs text-slate-500">
          {[p.addr, p.city, p.postcode].filter(Boolean).join(', ')}
          {(p.coords_precision === 'locality' || p.coords_precision === 'area') && (
            <span className="ml-1 italic text-slate-400">· locație aproximativă</span>
          )}
        </p>
      )}

      {school && (p.cand != null || p.rep != null || p.nerep != null) && (
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
      )}

      <LinkChips links={p.links} />

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
