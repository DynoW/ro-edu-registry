import { useEffect, useMemo, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet.markercluster'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import { Feature, KIND_META, Kind } from '../types'
import { dataUrl, REPO_URL } from '../config'
import { KindFilter } from './KindFilter'
import { SearchBar } from './SearchBar'
import { EntityModal } from './EntityModal'

const CENTER: [number, number] = [45.9432, 24.9668]

const makeMarker = (f: Feature, onSelect: (f: Feature) => void) => {
  const [lon, lat] = f.geometry.coordinates
  const marker = L.circleMarker([lat, lon], {
    radius: 6,
    weight: 1.5,
    color: '#ffffff',
    fillColor: KIND_META[f.properties.kind]?.color ?? '#94a3b8',
    fillOpacity: 1,
  })
  marker.on('click', () => onSelect(f))
  return marker
}

const clusterIcon = (cluster: L.MarkerCluster): L.DivIcon => {
  const n = cluster.getChildCount()
  const size = n < 20 ? 18 : n < 100 ? 24 : 30
  const color = n < 20 ? '#0284c7' : n < 100 ? '#0369a1' : '#075985'
  return L.divIcon({
    html: `<span style="display:flex;align-items:center;justify-content:center;width:${size}px;height:${size}px;border-radius:9999px;background:${color};color:#fff;font-size:12px;font-weight:700;border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.3)">${n}</span>`,
    className: 'cluster-icon-wrap',
    iconSize: [size, size],
  })
}

export function MapView() {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const clusterRef = useRef<L.MarkerClusterGroup | null>(null)
  const [features, setFeatures] = useState<Feature[]>([])
  const [active, setActive] = useState<Set<Kind>>(new Set())
  const [selected, setSelected] = useState<Feature | null>(null)

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return
    const map = L.map(containerRef.current, {
      center: CENTER,
      zoom: 7,
      preferCanvas: true,
      zoomControl: false,
    })
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors',
    }).addTo(map)
    L.control.zoom({ position: 'bottomright' }).addTo(map)

    const group = L.markerClusterGroup({
      chunkedLoading: true,
      maxClusterRadius: 45,
      iconCreateFunction: clusterIcon,
    })
    clusterRef.current = group
    map.addLayer(group)
    mapRef.current = map

    const onResize = () => map.invalidateSize()
    window.addEventListener('resize', onResize)
    requestAnimationFrame(() => map.invalidateSize())

    return () => {
      window.removeEventListener('resize', onResize)
      map.remove()
      mapRef.current = null
      clusterRef.current = null
    }
  }, [])

  useEffect(() => {
    fetch(dataUrl('registry.geojson'))
      .then((r) => r.json())
      .then((fc) => {
        const feats = fc.features as Feature[]
        setFeatures(feats)
        setActive(new Set(feats.map((f) => f.properties.kind)))
      })
      .catch(() => {})
  }, [])

  const filteredFeatures = useMemo(
    () => features.filter((f) => active.has(f.properties.kind)),
    [features, active],
  )

  useEffect(() => {
    const group = clusterRef.current
    if (!group) return
    group.clearLayers()
    group.addLayers(filteredFeatures.map((f) => makeMarker(f, setSelected)))
  }, [filteredFeatures])

  const counts = useMemo(() => {
    const c: Record<string, number> = {}
    for (const f of features) c[f.properties.kind] = (c[f.properties.kind] ?? 0) + 1
    return c
  }, [features])

  const featureById = useMemo(
    () => new Map(features.map((f) => [f.properties.id, f])),
    [features],
  )

  const parentFeature = selected?.properties.parent
    ? featureById.get(selected.properties.parent)
    : undefined

  const toggleKind = (k: Kind) => {
    setActive((prev) => {
      const next = new Set(prev)
      if (next.has(k)) next.delete(k)
      else next.add(k)
      return next
    })
  }

  const focusFeature = (f: Feature) => {
    const [lon, lat] = f.geometry.coordinates
    mapRef.current?.flyTo([lat, lon], 14.5, { duration: 0.9 })
    setSelected(f)
  }

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="absolute inset-0 z-0" />

      <SearchBar features={features} onSelect={focusFeature} />

      <KindFilter counts={counts} active={active} onToggle={toggleKind} />

      <div className="absolute bottom-4 left-4 z-[500] rounded-lg bg-white/90 px-3 py-1.5 text-xs text-slate-600 shadow backdrop-blur">
        {features.length.toLocaleString('ro-RO')} entități · sursă:{' '}
        <a href="https://admitere.edu.ro" target="_blank" rel="noreferrer" className="font-medium text-slate-700 hover:text-slate-900 hover:underline">
          admitere.edu.ro
        </a>{' '}
        +{' '}
        <a href={`${REPO_URL}/graphs/contributors`} target="_blank" rel="noreferrer" className="font-medium text-slate-700 hover:text-slate-900 hover:underline">
          contribuitori
        </a>
      </div>

      {selected && (
        <EntityModal
          feature={selected}
          parentFeature={parentFeature}
          onSelectParent={focusFeature}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  )
}
