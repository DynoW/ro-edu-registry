# Entity fields by kind

The JSON Schema (`data/schemas/entity.schema.json`) is deliberately
kind-agnostic — it validates structure for every entity. This document is the
practical contract: which fields each kind uses, and which are optional.

Legend: **✅ required** · **🔶 optional** · **➖ not used** (schema rejects
unknown fields — `additionalProperties: false`).

## Field matrix

| Field | school / highschool | university | faculty | robotics-club / student-org |
| :--- | :--- | :--- | :--- | :--- |
| `id` | ✅ `siiir:<10-digit code>` | ✅ `slug:<slug>` | ✅ `slug:<slug>` | ✅ `slug:<slug>` |
| `kind` | ✅ `school` or `highschool` | ✅ `university` | ✅ `faculty` | ✅ `robotics-club` / `student-org` |
| `name` | ✅ official name | ✅ | ✅ | ✅ |
| `county` | ✅ 2-letter code | ✅ | ✅ | ✅ |
| `source` | ✅ `admitere.edu.ro` | ✅ own domain (e.g. `upb.ro`) | ✅ own domain / `openstreetmap` | ✅ `manual` |
| `updated` | ✅ `YYYY-MM-DD` | ✅ | ✅ | ✅ |
| `siiir` | ✅ 10-digit unit code | ➖ | ➖ | ➖ |
| `stats` | 🔶 `{cand, rep, nerep}` | ➖ | ➖ | ➖ |
| `env` | 🔶 `URBAN` / `RURAL` / `null` | ➖ | ➖ | ➖ |
| `parent` | ➖ | ➖ | 🔶 expected: university id | 🔶 host school / university id |
| `external_ids` | ➖ | 🔶 | ➖ | 🔶 program ids, e.g. `{"ftc": 32744}` |
| `city` | ➖ (address covers it) | 🔶 | 🔶 | 🔶 |
| `addr` | 🔶 (pipeline) | 🔶 | 🔶 | 🔶 |
| `postcode` | 🔶 | 🔶 | 🔶 | 🔶 |
| `coords` | 🔶 `[lon, lat]` | 🔶 | 🔶 | 🔶 |
| `coords_precision` | 🔶 only with `coords` | 🔶 | 🔶 | 🔶 |
| `links` | 🔶 phone, website, email | 🔶 website, socials, admissions | 🔶 website | 🔶 website, socials |
| `added_by` | ➖ pipeline-generated | 🔶 | 🔶 | 🔶 |

## Field notes

### `id`
Stable key used by the map, CSV exports and issue deep-links. Never reuse or
change an existing id. Schools use their SIIIR unit code; everything else uses
a readable slug (`slug:upb-energetica`, `slug:neurox-cuza`).

### `stats` (schools only)
Admission counts from `admitere.edu.ro`: candidates (`cand`), assigned
(`rep`), unassigned (`nerep`). **`null` means "no data"** — the unit had no
8th-grade cohort in this repartizare cycle — and is distinct from a real `0`.

### `env` (schools only)
`URBAN` / `RURAL` from the admitere feed. `null` when the feed doesn't say.

### `parent`
Id of the entity this one belongs to or is hosted by:
- `faculty` → the university (`"parent": "slug:upb"`)
- `robotics-club` → the host school, when known (`"parent": "siiir:4061102576"`)
- `student-org` → the university it operates at

Omit for top-level entities (schools, universities).

### `external_ids`
Identifiers in external programs/systems, as an open object of lowercase
program slug → id: `{"ftc": 32744}` for a FIRST Tech Challenge team, `{"fll":
123}` for FIRST LEGO League, `{"vex": "12345A"}` for VEX. Used for dedupe and for exporters that group by program.

### `coords` + `coords_precision`
`coords` is `[lon, lat]` (WGS84). When present, `coords_precision` says how it
was obtained, best to coarsest:

| Value | Meaning |
| :--- | :--- |
| `building` | exact OpenStreetMap object (building/POI) |
| `address` | geocoded from name/address — the default when the field is absent |
| `locality` | center of the village/city |
| `area` | centroid of a large OpenStreetMap area (campus polygon) or shared fallback point — least precise |

Entities without `coords` don't appear on the map but stay in search and CSV.

### `links`
Array of contact links. Sub-fields:

| Sub-field | Status | Notes |
| :--- | :--- | :--- |
| `type` | ✅ | one of `website`, `facebook`, `instagram`, `youtube`, `linkedin`, `discord`, `whatsapp`, `tiktok`, `email`, `phone`, `other` |
| `value` | ✅ | URL, email address or phone number |
| `label` | 🔶 | display label, mainly for `other` (e.g. `"FTC Scout — profil echipă"`, `"Admitere licență"`) |
| `source` | 🔶 | provenance: `openstreetmap`, `manual`, the institution's own site, … |
| `verified` | 🔶 | `true` only if a human confirmed the link belongs to this institution. Automated harvests (e.g. from OpenStreetMap) are always `false` |

### `added_by`
GitHub username of the person who reported/added the entity — credit for
issue-based contributions. Git history is the authoritative record for PR
contributions; omit for pipeline-generated schools.
