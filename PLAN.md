# PLAN — remaining work for ro-edu-registry

---

## 1. Data seeding (continuing)

<!-- - **Universities** — expand beyond UPB from the accredited list (edu.ro / ARACIS) + `metaranking.ro`: UBB, Unibuc, ASE, UMF, UPT, UAIC… name, city, own-domain `source`, website + socials.
- **Faculties** — per university from its official faculties page; wire `parent` to the university; geocode buildings from OSM POIs where mapped (pattern proven with UPB). -->
- **Geocode the 37 coord-less entities** — done 2026-09-12: 36 geocoded (OSM POI / Nominatim / village-level, see `coords_precision`) + `slug:upb-inginerie-industriala-robotica` manually pinned to UPB corp CD. Remaining: `siiir:0662102247` (ȘG Valea Spinelului, Năsăud — school not in OSM/Nominatim; Str. George Coșbuc 184 has no house data → needs an OSM addition or a surveyed address). Bonus: fixed CNGC Năsăud, which was geocoded ~35 km off; `normalize.py` now also keeps existing coords when a rerun geocodes nothing.
<!-- - **Robotics clubs** — FIRST Romania team lists (FLL/FTC/FRC), RoboChallenge, VEX events; map teams to host schools via `parent`, store team numbers in `external_ids` (e.g. `{"ftc": 32744}`).
- **Student orgs** — seed lists per university: OSUT, OSUC, ASII, LSE, LSRS, BEST, AIESEC + university sites; `parent` = university. -->

<!-- ## 2. Admission ranking enrichment

- Scrape per-specialization admission grades from the repartizare results → **ultima medie** per school.
- Add `last_grade` to `stats` (schema + scraper + normalizer) → enables a real county-level school difficulty ranking (UI or exporter). -->

## 3. Contact enrichment

- **Email pattern fallback**: crawl school websites for `mailto:`; guess `secretariat@`/`office@`/`contact@` from the site domain; store as `verified: false` with MX validation. (OSM tag harvesting is already done.)

## 4. Coverage dashboard

- **Gamify gaps**: weekly workflow auto-labels `good-first-issue` on counties missing emails/links.

## 5. Guardrails

- **Fuzzy-name dedupe check** on manual additions (merge on SIIIR code already exists in `normalize.py`); warn when a new entity's name is near-identical to an existing one in the same county.

## 6. Later / optional

- **Datasette or static JSON API** if third parties want queryable access — the canonical layer makes this trivial.
