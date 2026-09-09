"""Phase 4 exporter: canonical registry -> derived outputs (pure function of data/).

Reads:  data/entities/*.json
Writes: public/data/registry.geojson   - map payload (entities with coords only)
        public/data/registry.csv       - outreach list: județ, denumire, mediu, adresă, link, email, telefon, kind
        public/data/coverage.json      - per-county completeness for the contribution dashboard

All outputs are generated; never edit them by hand.
"""

import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

from geocoder import COUNTY_NAMES

ENTITIES_DIR = Path("data/entities")
OUT_DIR = Path("public/data")
GENERATED = date.today().isoformat()


def load_entities() -> list[dict]:
    entities = []
    for path in sorted(ENTITIES_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            entities.extend(json.load(f))
    return entities


def first_link_of(entity: dict, link_type: str) -> str:
    for link in entity.get("links", []):
        if link["type"] == link_type:
            return link["value"]
    return ""


def website_of(entity: dict) -> str:
    for link in entity.get("links", []):
        if link["type"] == "website":
            return link["value"]
    return ""


def export_geojson(entities: list[dict], path: Path) -> int:
    features = []
    for e in entities:
        if not e.get("coords"):
            continue
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": e["coords"]},
            "properties": {
                "id": e["id"],
                "kind": e["kind"],
                "name": e["name"],
                "county": e["county"],
                "env": e.get("env"),
                "addr": e.get("addr"),
                "postcode": e.get("postcode"),
                "cand": e.get("stats", {}).get("cand"),
                "rep": e.get("stats", {}).get("rep"),
                "nerep": e.get("stats", {}).get("nerep"),
                "phone": first_link_of(e, "phone"),
                "website": website_of(e),
                "email": first_link_of(e, "email"),
                "coords_precision": e.get("coords_precision"),
            },
        })
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, separators=(",", ":"))
    return len(features)


def export_csv(entities: list[dict], path: Path) -> None:
    # utf-8-sig so Excel opens diacritics correctly
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["județ", "denumire", "mediu", "adresă", "link", "email", "telefon", "kind"])
        for e in sorted(entities, key=lambda x: (x["county"], x["name"])):
            writer.writerow([
                COUNTY_NAMES.get(e["county"], e["county"]),
                e["name"],
                e.get("env") or "",
                e.get("addr") or "",
                website_of(e),
                first_link_of(e, "email"),
                first_link_of(e, "phone"),
                e["kind"],
            ])


def export_search(entities: list[dict], path: Path) -> int:
    """Lean, coord-free records for the no-WebGL search page."""
    records = [
        {
            "id": e["id"],
            "kind": e["kind"],
            "name": e["name"],
            "county": e["county"],
            "addr": e.get("addr"),
            "postcode": e.get("postcode"),
            "phone": first_link_of(e, "phone"),
            "website": first_link_of(e, "website"),
            "email": first_link_of(e, "email"),
        }
        for e in sorted(entities, key=lambda x: (x["county"], x["name"]))
    ]
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"generated": GENERATED, "entities": records}, f, ensure_ascii=False, separators=(",", ":"))
    return len(records)


def export_coverage(entities: list[dict], path: Path) -> None:
    by_county = defaultdict(list)
    for e in entities:
        by_county[e["county"]].append(e)

    def slice_of(items: list[dict]) -> dict:
        n = len(items)
        pct = lambda k: round(100 * sum(1 for e in items if k(e)) / n) if n else 0
        return {
            "entities": n,
            "coords_pct": pct(lambda e: e.get("coords")),
            "website_pct": pct(lambda e: website_of(e)),
            "email_pct": pct(lambda e: any(l["type"] == "email" for l in e.get("links", []))),
        }

    coverage = {
        "generated": GENERATED,
        "total": slice_of(entities),
        "counties": {c: slice_of(items) for c, items in sorted(by_county.items())},
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(coverage, f, ensure_ascii=False, indent=2)


def main() -> None:
    entities = load_entities()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    n_geo = export_geojson(entities, OUT_DIR / "registry.geojson")
    export_csv(entities, OUT_DIR / "registry.csv")
    n_dir = export_search(entities, OUT_DIR / "search.json")
    export_coverage(entities, OUT_DIR / "coverage.json")

    print(
        f"Exported {len(entities)} entities from {ENTITIES_DIR}:\n"
        f"  registry.geojson: {n_geo} features (skipped {len(entities) - n_geo} without coords)\n"
        f"  registry.csv: {len(entities)} rows\n"
        f"  search.json: {n_dir} records\n"
        f"  coverage.json: {len({e['county'] for e in entities})} counties"
    )


if __name__ == "__main__":
    main()
