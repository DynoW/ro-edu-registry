# PLAN v2: ro-edu-registry — canonical dataset + modular frontends

One canonical, community-maintained registry of Romanian education & student-life entities (schools, high schools, robotics clubs, universities, faculties, student associations) with thin, derived outputs: an interactive map, a marketing/outreach CSV. Repo working name: `schools` (a.k.a. `ro-edu-registry`).

---

## 0. Status (Sep 8, 2026)

| Step | State |
| :--- | :--- |
| Scraper (`scripts/scraper.py`) | ✅ Done — 6,254 units, 42 counties → `public/data/schools_raw.json` |
| Geocoder (`scripts/geocoder.py`) | ✅ Done — 5,364/6,254 geocoded; 890 without coords (rural OSM gaps) |
| Enricher (`scripts/enrich_osm.py`) | ✅ Done — coords now 6,218/6,254 (99.4%): 36 exact OSM POI + 844→1,390 village-center fallbacks (marked `coords_precision: village`), 550 centroid-snapped coords corrected, 260 contact links harvested from OSM tags (140 websites, 52 emails). 36 remain (no extractable locality, e.g. „Liceul CONIL") |
| Normalizer (`scripts/normalize.py`) | ✅ Done — 6,254 canonical entities (schema-validated) → `data/entities/schools.json`; rerun-safe (merge-preserves OSM/village enrichments and contributor edits) |
| Exporter (`scripts/export.py`) | ✅ Done — `registry.geojson` (5,364 features), `registry.csv` (6,254 rows), `coverage.json` |
| Frontend (`src/`, Vite + React + **Leaflet**) | ✅ v1 done — hartă cu randare raster/2D (funcționează pe orice browser, **fără nevoie de WebGL**), clustering, filtre pe tip, căutare diacritice-insensibilă, modal contacte, pagini Căutare (listă completă) și /export |
| Deploy | ✅ Public pe GitHub Pages: **https://dynow.github.io/ro-edu-registry/** — CI generează datele din registrul canonic, construiește frontend-ul și publică la fiecare push pe main (`deploy.yml`); validare schemă pe orice PR (`validate.yml`); pagină Căutare funcțională fără WebGL (search.json) |

---

## 1. Core principle: canonical data → derived outputs

```
┌───────────────────────────────────────────────────────┐
│  Canonical data layer  (hand-editable, in git)         │
│  data/entities/*.json   validated by JSON Schema in CI │
└──────────────────────────┬────────────────────────────┘
                           │  npm run export  (local + CI)
        ┌──────────────────┼───────────────────┬─────────────────────┐
        ▼                  ▼                   ▼                     
  registry.geojson    registry.csv       coverage.json         
  (map frontend)      (outreach/doc:     (contribution         
                        județ, denumire,   dashboard)          
                        link, contact)                          
```

Rules:

1. `data/` is the **only** hand-edited source of truth. Everything under `public/data/` is generated — never edited by hand.
2. Every entity has a stable `id` (SIIIR code for schools; slug for others), a `source` provenance field, and an `updated` date.
3. **Exporters** (`export.py`) are pure functions of the canonical data → deterministic, reproducible in CI. Geocoded coordinates are folded into canonical data once, offline (geocoder touches live Nominatim, so it is never run in CI); exporters never call live services.
4. Same dataset powers all repurposings: map, marketing list, future projects — no forks of the data.

---

## 2. Data model (schema v2)

```jsonc
{
  "id": "siiir:12345678",            // or "slug:osut-cluj" for non-school entities
  "kind": "highschool",              // school | highschool | robotics-club |
                                     // university | faculty | student-org
  "name": "Colegiul Național ...",
  "county": "CJ",                    // 2-letter code; join key for county views
  "city": "Cluj-Napoca",
  "addr": "...", "postcode": "...",
  "coords": [23.5914, 46.7704],      // null until geocoded
  "siiir": "12345678",               // schools only; canonical dedupe key
  "stats": { "cand": 320, "rep": 300, "nerep": 20, "last_grade": 8.95 },
  "links": [                         // stable contacts
    { "type": "website",  "value": "https://..." },
    { "type": "email",    "value": "secretariat@...", "verified": false },
    { "type": "phone",    "value": "..." },
    { "type": "facebook", "value": "https://..." }
  ],
  "source": "admitere.edu.ro",       // admitere.edu.ro | osm | manual | contributor
  "updated": "2026-09-08"
}
```

Design decisions:

- `links` = stable contacts (site, email, socials).
- `kind` is a closed enum validated by schema → every new category is a one-line schema change, not a redesign.
- Provenance (`source`, `added_by`) on everything, so bad data is traceable.

---

## 3. Repository layout

```text
schools/
├── data/
│   ├── entities/
│   │   ├── schools.json            # from schools_raw.json via normalize.py, then hand-fixable
│   │   ├── universities.json
│   │   └── clubs-orgs.json         # robotics clubs, student orgs
│   └── schemas/                    # JSON Schema per kind (entity + link)
├── scripts/
│   ├── scraper.py                  # ✅ exists — admitere.edu.ro feeds (42 counties)
│   ├── geocoder.py                 # ⏳ exists, resumable cache
│   ├── normalize.py                # schools_raw.json → data/entities/schools.json
│   ├── enrich_osm.py               # Overpass: website/phone/email tags for mapped schools
│   └── export.py                   # canonical → geojson + csv + coverage
├── public/data/                    # GENERATED ONLY, gitignored (geojson, csv, coverage.json)
├── src/                            # Map frontend (Vite + React + MapLibre, v1 design)
├── .github/
│   ├── ISSUE_TEMPLATE/             # add-entity.md, fix-data.md
│   └── workflows/
│       ├── validate.yml            # JSON Schema validation + export determinism check
│       ├── linkcheck.yml           # weekly dead-link bot → files issues
│       └── refresh.yml             # weekly scraper re-run to catch feed updates
├── CONTRIBUTING.md                 # copy-paste JSON examples, no build knowledge needed
└── PLAN.md
```

---

## 4. Entity sources (colleague's list → concrete sources)

| Entity | Primary source | Notes |
| :--- | :--- | :--- |
| Schools / high schools | ✅ `static.admitere.edu.ro/2026/repartizare/{county}/data/{school,highschool}.json` | 6,254 units; carries candidat/repartizat/nerepartizat stats |
| High-school admission rankings | Same feeds (repartizare results) | Add per-school **ultima medie** → real difficulty ranking per county |
| Universities | Accredited list (edu.ro / ARACIS) + `metaranking.ro` | name, city, site, ranking tier; seed JSON + contributors |
| Robotics clubs | FIRST Romania team lists (FLL/FTC/FRC), RoboChallenge, VEX events | Map teams → host schools where possible |
| Student orgs (tech/antreprenoriat) | OSUT, OSUC, ASII, LSE, LSRS, BEST, AIESEC + university sites | Seed list per university |
| Websites / emails / phones | OSM tags (`enrich_osm.py`), school websites (mailto crawl), SIIR registry | Pattern-derived emails stored `verified: false` |

---

## 5. Derived outputs

| File | Consumer | Format |
| :--- | :--- | :--- |
| `public/data/registry.geojson` | Map frontend | Minified FeatureCollection, all kinds, `kind` per feature |
| `public/data/registry.csv` | Outreach/marketing project | Exactly the colleague's doc: **județ, denumire, link, contact/email** (+kind) |
| `public/data/coverage.json` | Contribution dashboard | Per county: % with coords / website / email |
| Per-county CSVs (optional) | Targeted county campaigns | `public/data/csv/{COUNTY}.csv` |

`scripts/export.py` regenerates all of them in one run. Generated outputs are **not committed** (`public/data/` is gitignored): the Pages build step runs `export.py` from canonical `data/` at deploy time, and `validate.yml` re-runs export and diffs it against a fresh build to catch non-determinism. This avoids committing regenerable files (history bloat) and the commit-plus-CI-regenerate churn/merge-conflict trap — the geojson depends on live Nominatim responses, so two runs never agree byte-for-byte. The geocode cache (`scripts/geocode_cache.json`) stays untracked during runs; it is the resumability mechanism, not a dataset.

---

## 6. Community contributions (GitHub)

- **Data = JSON in `data/`** → contributions are plain PRs; JSON Schema + CI do the reviewing of structure, humans review content. No tooling knowledge required.
- **Issue templates**: "Add missing entity" (kind, județ, name, link), "Fix wrong data" (entity id + correction). The templates collect exactly the fields a maintainer needs to edit the JSON.
- **Link checker bot** (weekly Action): validates every `links[].value` with HTTP checks; dead links open an issue or flip `verified: false`.
- **"Edit this entry" deep link**: every school modal on the map links to a prefilled GitHub issue with the entity id — contribution friction near zero.
- **Coverage dashboard gamifies gaps**: counties with missing emails auto-generate `good-first-issue` labels.
- `CONTRIBUTING.md` documents: how to add an entity, JSON examples, and the "never edit `public/data/`" rule.
- **Licensing**: code MIT; data ODbL or CC BY-SA 4.0 (required anyway for OSM-derived coordinates) with attribution notice in README.

---

## 7. Outreach/modularity guarantees (the "repurposable" requirement)

- A new use case (e.g. SMS campaign, university fair list, a different map) = **one new exporter in `scripts/export.py`**, zero data forks.
- Marketing CSV consumers get `registry.csv` regenerated on every merge — no stale spreadsheets.
- The map and any future frontend are disposable: they only read `public/data/` outputs; the dataset outlives any UI.
- Per-county and per-kind filtering lives in the exporters, so each downstream project gets exactly the columns it needs.

---

## 8. Frontend (v1 map, unchanged in essence)

Vite + React + **Leaflet** + tile-uri raster OSM (randare 2D universală, fără WebGL și fără API key — tile-urile CARTO au început să ceară API key, deci nu mai sunt o opțiune gratuită). $0 static hosting on GitHub Pages. Changes from v1 plan:

- **Kind filter chips**: schools / high schools / universities / clubs / orgs — toggleable layers over the same clustered source.
- **School modal**: contact links (site, email, phone, socials) + "Edit on GitHub" link.
- **`/export` page**: download links to `registry.csv` and per-county CSVs.
- Search stays client-side fuzzy over the loaded GeoJSON; component structure (MapView / SchoolModal / SearchBar) as drafted in v1.

---

## 9. Extra ideas

1. **Ultima medie per school** — scrape per-specialization admission grades from repartizare results; turns the map into a real county-level school ranking, not just candidate counts.
2. **OSM enrichment** — most Romanian schools are mapped POIs; Overpass bulk-pulls `website`, `phone`, `email` tags before any crawling.
3. **Email pattern fallback** — crawl school websites for `mailto:`; guess `secretariat@`/`office@` from domain; store as `verified: false` with MX validation.
4. **Weekly refresh Action** — re-run the scraper on a schedule so the registry tracks the live admitere feeds.
5. **Datasette or static JSON API** — later, if third parties want queryable access; the canonical layer makes this trivial.
6. **Dedupe guard** — merge sources on SIIIR code; fuzzy-name check on manual additions to prevent duplicate entities.
7. **GDPR note in CONTRIBUTING/README** — outreach targets institutional addresses (secretariat@, public institutions = legitimate interest); exclude personal emails from exports.

---

## 10. Roadmap

1. ✅ **Resume geocoder** → complete `schools.geojson` (5,364/6,254 geocoded).
2. ✅ **`normalize.py`** — migrate `schools_raw.json` → `data/entities/schools.json` under schema v2; the geocoder folds resolved coordinates back into canonical data (offline) so exports stay deterministic.
3. ✅ **`export.py` + `registry.csv`** — delivers the colleague's doc format immediately; unblocks the outreach/marketing project.
4. ✅ **Frontend v1** — map with kind filters, search, contact modal + /export page.
5. **Seed datasets** — `universities.json`, `clubs-orgs.json` (research pass + community refinement).
6. **Contribution infra** — ⏳ partial: `validate.yml` ✅, REPO_URL wired ✅; rămân issue templates, `linkcheck.yml`, CONTRIBUTING.md, licențe MIT/ODbL.
7. **Coverage dashboard**.
8. **Ranking enrichment** — ultima medie per school/specialization.
