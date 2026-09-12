import { useEffect, useState } from 'react'
import { MapView } from './components/MapView'
import { SearchPage } from './pages/SearchPage'
import { ExportPage } from './pages/ExportPage'

type Page = 'map' | 'search' | 'export'

const parseHash = (): Page => {
  const h = window.location.hash
  if (h.startsWith('#/cautare')) return 'search'
  if (h.startsWith('#/export')) return 'export'
  return 'map'
}

const NAV: { id: Page; route: string; label: string }[] = [
  { id: 'map', route: '', label: 'Hartă' },
  { id: 'search', route: 'cautare', label: 'Căutare' },
  { id: 'export', route: 'export', label: 'Export' },
]

export default function App() {
  const [page, setPage] = useState<Page>(parseHash)

  useEffect(() => {
    const onHash = () => setPage(parseHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  return (
    <div className="flex h-screen flex-col font-sans">
      <header className="z-30 flex items-center justify-between border-b border-slate-200 bg-white px-4 py-2.5">
        <div className="flex items-baseline gap-2">
          <span className="text-base font-bold text-slate-900">ro-edu-registry</span>
          <span className="hidden text-xs text-slate-400 sm:inline">harta educației din România</span>
        </div>
        <nav className="flex gap-1">
          {NAV.map((n) => (
            <a
              key={n.id}
              href={`#/${n.route}`}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                page === n.id ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'
              }`}
            >
              {n.label}
            </a>
          ))}
        </nav>
      </header>

      <main className="relative min-h-0 flex-1">
        {page === 'map' && <MapView />}
        {page === 'search' && (
          <div className="h-full overflow-y-auto">
            <SearchPage />
          </div>
        )}
        {page === 'export' && (
          <div className="h-full overflow-y-auto">
            <ExportPage />
          </div>
        )}
      </main>
    </div>
  )
}
