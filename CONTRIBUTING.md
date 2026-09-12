# Contributing to ro-edu-registry

Thank you for helping build the registry of Romanian education entities! 🎓

You do **not** need any build tooling knowledge. Contributions are plain JSON
edits or GitHub issues — CI validates everything automatically.

## The one rule

> `data/entities/*.json` is the **only** hand-edited data.
> Everything under `public/data/` is generated — never edit it, never commit it.

## Two ways to contribute

### 1. Open an issue (easiest)

- [Report wrong data](https://github.com/DynoW/ro-edu-registry/issues/new?template=fix-data.yml) — include the entity `id` if you can (shown in the map modal).
- [Add a missing entity](https://github.com/DynoW/ro-edu-registry/issues/new?template=add-entity.yml) — fill in what you know; a maintainer will do the JSON.

### 2. Send a pull request

1. Fork the repo (or create a branch).
2. Edit the relevant file in `data/entities/` — see examples below.
3. Run `python3 scripts/format_entities.py` (or `pnpm format:data`) — it puts fields in the canonical order CI expects. No dependencies needed.
4. Open a PR. CI validates the schema and the field order automatically. That's it.

If you want to check locally before pushing: `python3 scripts/validate.py`
(needs `pip install jsonschema`) or `pnpm export` to see the derived outputs.

## JSON examples

The full field reference per entity kind (required vs optional, what each
field means) lives in [docs/FIELDS.md](docs/FIELDS.md).

### Fix a wrong value

Find the entity by `id` (schools: `siiir:<code>`, others: `slug:<name>`) and
edit the field — e.g. fix a website:

```json
{
  "id": "siiir:1234567890",
  "links": [
    { "type": "website", "value": "https://cnlv.ro", "source": "manual", "verified": true }
  ]
}
```

`links` entries support these types: `website`, `facebook`, `instagram`,
`youtube`, `linkedin`, `discord`, `whatsapp`, `tiktok`, `email`, `phone`,
`other`. Optional fields: `label`, `source` (provenance, e.g. `manual`),
`verified` (set `true` only if you personally confirmed the link works). Use
`other` + `label` for anything rarer (X/Twitter, FTC Scout profile, blog…).

### Add a new entity (non-school)

Create/edit an entry in the matching file — `universities.json` or
`clubs-orgs.json` — following this shape:

```json
{
  "id": "slug:robotix-cluj",
  "kind": "robotics-club",
  "name": "Robotix Club Cluj",
  "county": "CJ",
  "city": "Cluj-Napoca",
  "coords": [23.5914, 46.7704],
  "coords_precision": "address",
  "links": [
    { "type": "website", "value": "https://robotix.ro", "source": "manual", "verified": true }
  ],
  "source": "manual",
  "added_by": "your-github-username",
  "updated": "2026-09-09"
}
```

Field notes:

| Field | Rules |
| :--- | :--- |
| `id` | `slug:<short-slug>` for non-schools, `siiir:<10-digit code>` for schools. Never reuse or change an existing id. |
| `kind` | One of: `school`, `highschool`, `robotics-club`, `university`, `faculty`, `student-org` |
| `parent` | Id of the parent entity when one exists — the university for a `faculty`, the host school for a club (optional) |
| `county` | 2-letter county code (`AB`, `AR`, …, `B` for Bucharest) |
| `coords` | `[lon, lat]` in WGS84 — optional; omit if unknown, `null` also works |
| `coords_precision` | How `coords` were found: `building` (exact OpenStreetMap object) > `address` (geocoded from name/address) > `locality` (village/city center) > `area` (coarse). Omit when unsure — `address` is the safe default for coordinates you looked up yourself. |
| `source` | Where the data came from: `manual`, `openstreetmap`, `admitere.edu.ro`, or the institution's own site |
| `added_by` | Your GitHub username — credit for the contribution (optional) |
| `updated` | Today's date, `YYYY-MM-DD` |

### Credit

Git history is the authoritative record — every PR keeps its author. For
entities added via issues (where a maintainer types the JSON), set
`added_by` to the GitHub username of the person who reported it, so the
credit lives next to the data. Omit the field for pipeline-generated entries
(`source: admitere.edu.ro`).

Tip: to find `[lon, lat]` for any address, open
[openstreetmap.org](https://www.openstreetmap.org), search it, right-click →
*"Copy coordinates"* (order is `lat, lon` — flip it for JSON: `[lon, lat]`).

### Add a school

Schools already number 6,254 and come from official feeds. If one is truly
missing, open an [add-entity issue](https://github.com/DynoW/ro-edu-registry/issues/new?template=add-entity.yml)
with its SIIIR code (findable on [admitere.edu.ro](https://static.admitere.edu.ro/2026/repartizare/B/index.html) in "Școli" section) so the pipeline can pick it up properly.

## Data quality guidelines

- Keep names exactly as the institution writes them (diacritics included).
- One entity per physical unit; don't merge campuses or dedupe by hand.
- Don't change `id`s — they are stable keys used by the map, CSV exports and
  issue deep-links.
- Never edit generated files (`public/data/`) or the geocode/Overpass caches.

## Privacy

This registry publishes **institutional** contact data only: official school
websites, secretariat emails, public phone numbers — information that public
institutions must publish by law. Do **not** add personal data of private
individuals (e.g. a teacher's personal phone). Such entries will be removed.
The outreach CSV is intended for institutional communication (legitimate
interest); personal emails are excluded from exports.

## Development setup

```bash
pnpm install     # Node 22+, pnpm 10
pnpm dev         # map frontend at localhost:5173
pnpm export      # regenerate public/data/ (Python 3.12, no deps needed)
pnpm build       # typecheck + production build
```

The frontend only reads generated files in `public/data/` — if the map looks
empty locally, run `pnpm export` first.
