import { useEffect, useState } from 'react'
import { Coverage } from '../types'
import { REPO_URL, dataUrl } from '../config'

const EXPORTS = [
  { file: 'registry.csv', label: 'registry.csv', desc: 'Listă de outreach: județ, denumire, mediu, adresă, link, email, telefon, kind (format Excel-friendly).' },
  { file: 'registry.geojson', label: 'registry.geojson', desc: 'GeoJSON cu toate entitățile geocalibrate — pentru hărți și alte aplicații.' },
  { file: 'coverage.json', label: 'coverage.json', desc: 'Completitudinea datelor per județ (dashboard contribuții).' },
]

export function ExportPage() {
  const [coverage, setCoverage] = useState<Coverage | null>(null)

  useEffect(() => {
    fetch(dataUrl('coverage.json'))
      .then((r) => r.json())
      .then(setCoverage)
      .catch(() => {})
  }, [])

  const t = coverage?.total

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold text-slate-900">Export date</h1>
      <p className="mt-1 text-sm text-slate-500">
        Toate fișierele sunt generate automat din registrul canonic și se regenerează la fiecare update.
      </p>

      {t && (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: 'Entități', value: t.entities.toLocaleString('ro-RO') },
            { label: 'Cu coordonate', value: `${t.coords_pct}%` },
            { label: 'Cu website', value: `${t.website_pct}%` },
            { label: 'Cu email', value: `${t.email_pct}%` },
          ].map((s) => (
            <div key={s.label} className="rounded-xl bg-slate-50 p-3 text-center">
              <div className="text-lg font-bold text-slate-800">{s.value}</div>
              <div className="text-[11px] font-semibold uppercase text-slate-400">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      <ul className="mt-6 space-y-2">
        {EXPORTS.map((x) => (
          <li key={x.file} className="flex items-center justify-between gap-4 rounded-xl border border-slate-100 bg-white p-4 shadow-sm">
            <div>
              <div className="text-sm font-semibold text-slate-800">{x.label}</div>
              <div className="text-xs text-slate-400">{x.desc}</div>
            </div>
            <a
              href={dataUrl(x.file)}
              download
              className="shrink-0 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700"
            >
              Descarcă
            </a>
          </li>
        ))}
      </ul>

      <p className="mt-6 text-xs text-slate-400">
        Licență date: ODbL 1.0 — registrul include date derivate din OpenStreetMap (© contribuitorii
        OpenStreetMap), ceea ce impune ODbL pentru tot pachetul de date, inclusiv registry.csv și
        coverage.json; vezi{' '}
        <a
          href={`${REPO_URL}/blob/main/LICENSE-DATA`}
          className="underline decoration-slate-300 underline-offset-2 hover:text-slate-600"
        >
          LICENSE-DATA
        </a>{' '}
        pentru nota de atribuire. Contactele sunt adrese instituționale publice; fișierele nu conțin
        date cu caracter personal.
      </p>
    </div>
  )
}
