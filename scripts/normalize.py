"""Phase 3 normalizer: merges scraped records and geocoded coordinates into
the canonical registry (data/entities/schools.json, schema v2).

Reads:
  public/data/schools_raw.json   - scraped admitere.edu.ro records
  public/data/schools.geojson    - geocoder output (coords keyed by raw id)
Writes:
  data/entities/schools.json     - canonical entities, one per line (git-friendly diffs)

The canonical file is the hand-editable source of truth; everything under
public/data/ is generated from it by export.py.
"""

import json
import re
from datetime import date
from pathlib import Path

RAW_FILE = Path("public/data/schools_raw.json")
GEO_FILE = Path("public/data/schools.geojson")
OUT_FILE = Path("data/entities/schools.json")
UPDATED = date.today().isoformat()

KINDS = {"school", "highschool", "robotics-club", "university", "faculty", "student-org"}
SIIIR_RE = re.compile(r"^\d{10}$")
COUNTY_RE = re.compile(r"^[A-Z]{1,2}$")
NON_DIGIT_RE = re.compile(r"\D")
NO_ADDR_RE = re.compile(r"\bnu\s+are\b", re.I)


def clean_addr(addr: str | None) -> str | None:
    """Feed junk like 'nu are 349' / 'principală nu are' → None / 'Principală'."""
    if not addr:
        return None
    cleaned = re.sub(r"\s+", " ", NO_ADDR_RE.sub(" ", addr)).strip(" ,;-")
    if not cleaned or re.fullmatch(r"\d+[a-z]?", cleaned, re.I):
        return None  # nothing left, or a bare house number without a street
    return cleaned


def phone_digits(value: str) -> str:
    """Normalize RO phone formats: 0213149311 / +40213149311 / 40213149311 all → 213149311."""
    d = NON_DIGIT_RE.sub("", value)
    if d.startswith("40") and len(d) >= 11:
        d = d[2:]
    return d[1:] if d.startswith("0") else d


def load_coords() -> dict:
    with open(GEO_FILE, encoding="utf-8") as f:
        geo = json.load(f)
    return {feat["properties"]["id"]: feat["geometry"]["coordinates"] for feat in geo["features"]}


def to_entity(raw: dict, coords) -> dict:
    links = [{"type": "phone", "value": raw["tel"]}] if raw.get("tel") else []
    entity = {
        "id": f"siiir:{raw['id']}",
        "kind": raw["kind"],
        "name": raw["name"],
        "county": raw["county"],
        "env": raw.get("env") or None,
        "addr": clean_addr(raw.get("addr")),
        "postcode": raw.get("postcode") or None,
        "coords": coords,
    }
    if coords is not None:
        entity["coords_precision"] = "address"  # geocoder output is name/address-level; enrich_osm upgrades it
    entity.update({
        "siiir": raw["id"],
        "stats": {
            "cand": raw.get("cand"),
            "rep": raw.get("rep"),
            "nerep": raw.get("nerep"),
        },
        "links": links,
        "source": "admitere.edu.ro",
        "updated": UPDATED,
    })
    return entity


def validate(entities: list[dict]) -> None:
    ids = set()
    for e in entities:
        if not SIIIR_RE.match(e["siiir"]):
            raise ValueError(f"{e['id']}: bad SIIIR code {e['siiir']!r}")
        if e["id"] in ids:
            raise ValueError(f"duplicate id: {e['id']}")
        ids.add(e["id"])
        for field in ("kind", "name", "county", "source", "updated"):
            if not e[field]:
                raise ValueError(f"{e['id']}: missing required field {field!r}")
        if e["kind"] not in KINDS:
            raise ValueError(f"{e['id']}: unknown kind {e['kind']!r}")
        if not COUNTY_RE.match(e["county"]):
            raise ValueError(f"{e['id']}: bad county code {e['county']!r}")
        if e["coords"] is not None and (
            not isinstance(e["coords"], list)
            or len(e["coords"]) != 2
            or not all(isinstance(v, (int, float)) for v in e["coords"])
        ):
            raise ValueError(f"{e['id']}: bad coords {e['coords']!r}")


def write_entities(path: Path, entities: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("[\n")
        f.write(",\n".join(json.dumps(e, ensure_ascii=False) for e in entities))
        f.write("\n]\n")


def load_existing(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return {e["id"]: e for e in json.load(f)}
    except FileNotFoundError:
        return {}


STICKY_PRECISIONS = {"building", "locality", "area"}  # deliberate overrides that survive reruns


def _insert_precision(entity: dict, precision: str) -> dict:
    """Place coords_precision right after coords to keep the canonical key order."""
    out = {}
    for k, v in entity.items():
        if k == "coords_precision":
            continue  # replaced by the sticky value at the coords position
        out[k] = v
        if k == "coords":
            out["coords_precision"] = precision
    if "coords_precision" not in out:
        out["coords_precision"] = precision
    return out


def merge_existing(new: dict, old: dict | None) -> dict:
    """Pipeline data wins by default; hand/enricher edits (coords via OpenStreetMap or
    village geocodes, extra links) are preserved on reruns."""
    if not old:
        return new
    # Absent coords_precision in pre-2026-09 records means "address" (the default)
    if old.get("coords") and "coords_precision" not in old:
        old = {**old, "coords_precision": "address"}
    sticky = None
    if new["coords"] is None and old.get("coords"):
        # Fresh pipeline run found no coordinates: keep the existing ones (hand
        # geocodes or output of a previous run) instead of wiping them.
        new["coords"] = old["coords"]
        sticky = old["coords_precision"]
    elif old.get("coords_precision") in STICKY_PRECISIONS and old.get("coords"):
        new["coords"] = old["coords"]
        sticky = old["coords_precision"]
    elif old.get("coords_precision") and "coords_precision" not in new:
        sticky = old["coords_precision"]
    if sticky:
        new = _insert_precision(new, sticky)
    have = {(l["type"], l["value"]) for l in new["links"]}
    have_phone_digits = {phone_digits(l["value"]) for l in new["links"] if l["type"] == "phone"}
    for link in old.get("links", []):
        if (link["type"], link["value"]) in have:
            continue
        if link["type"] == "phone" and phone_digits(link["value"]) in have_phone_digits:
            continue  # same number, different format (e.g. 0213149311 vs +40213149311)
        new["links"].append(link)
        have.add((link["type"], link["value"]))
        if link["type"] == "phone":
            have_phone_digits.add(phone_digits(link["value"]))
    unchanged = {k: v for k, v in new.items() if k != "updated"} == {k: v for k, v in old.items() if k != "updated"}
    if unchanged:
        new["updated"] = old["updated"]
    return new


def main() -> None:
    with open(RAW_FILE, encoding="utf-8") as f:
        raw_records = json.load(f)
    coords_by_id = load_coords()
    existing = load_existing(OUT_FILE)

    entities = []
    for r in raw_records:
        e = to_entity(r, coords_by_id.get(r["id"]))
        entities.append(merge_existing(e, existing.get(e["id"])))
    entities.sort(key=lambda e: (e["county"], e["name"]))
    validate(entities)

    write_entities(OUT_FILE, entities)

    with_coords = sum(1 for e in entities if e["coords"] is not None)
    with_phone = sum(1 for e in entities if e["links"])
    highschools = sum(1 for e in entities if e["kind"] == "highschool")
    print(
        f"Wrote {len(entities)} canonical entities ({highschools} high schools) to {OUT_FILE}\n"
        f"  coords: {with_coords} | phone: {with_phone} | unresolved ids: {len(raw_records) - len(entities)}"
    )


if __name__ == "__main__":
    main()
