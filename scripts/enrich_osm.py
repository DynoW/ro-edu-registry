"""OpenStreetMap + village enrichment: fixes missing coords and harvests contact links.

Phase A: per-county Overpass pull of named school objects (cached on disk).
Phase B: match canonical entities (missing coords, or centroid-flagged coords)
         to OSM objects by normalized name + locality -> OSM coords (precision 'building').
Phase C: harvest website/email/phone tags from matched OSM objects into links
         (source: openstreetmap, verified: false).
Phase D: village-level Nominatim fallback for entities still without coords
         (locality extracted from the name) -> precision 'locality'.

Reads/writes the canonical registry in place: data/entities/schools.json
"""

import json
import re
import time
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

import httpx

from geocoder import COUNTY_NAMES, RateLimiter

REGISTRY = Path("data/entities/schools.json")
OVERPASS_CACHE = Path("scripts/overpass_cache")
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
UA = {"User-Agent": "ro-edu-registry/1.0 (github contribution project)"}

CENTROID_MIN_SHARED = 4  # coords shared by >= N entities in a county = county-center fallback
COUNTY_DELAY = 1.5
ACCEPT_RATIO = 0.80
STRICT_RATIO = 0.93  # locality known, candidate has no locality tag
NO_LOCALITY_RATIO = 0.97  # no locality known anywhere
AMBIGUITY_GAP = 0.03

LOCALITY_RE = re.compile(r",\s*(?:SAT|ORAȘ|ORAS|MUNICIPIUL|LOC\.?|COMUNA)\s+([^,]+)$", re.IGNORECASE)
PLACE_TYPES = {"village", "hamlet", "town", "city"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^A-Za-z0-9 ]+", " ", s).upper()
    return re.sub(r"\s+", " ", s).strip()


def extract_locality(name: str) -> tuple[str, str] | None:
    """Returns (raw_locality, normalized_locality) from ', SAT X'-style suffixes."""
    m = LOCALITY_RE.search(name)
    if not m:
        return None
    raw = m.group(1).strip()
    return raw, norm(raw)


GENERIC_TOKENS = {"NR", "NUMARUL", "NUM", "SAT", "ORAS", "ORASUL", "MUNICIPIUL", "MUN",
                  "LOC", "LOCUL", "COMUNA", "SCOALA", "SCOALA", "LICEUL", "COLEGIUL", "ROMANIA"}


def village_candidates(name: str) -> list[tuple[str, str]]:
    """Ordered (raw, normalized) locality guesses: comma marker first, then the
    last two / last one words (common 'LICEUL TEORETIC ... PANCIU' pattern).
    Only used for the village fallback; Nominatim's place-type + county guards
    reject wrong guesses."""
    out = []
    marker = extract_locality(name)
    if marker:
        out.append(marker)
    clean = re.sub(r"[\"„”']", " ", name)
    tokens = clean.split()
    for take in (2, 1):
        if len(tokens) >= take + 2:  # keep at least the school-type words in front
            tail = tokens[-take:]
            if (
                all(t.upper() not in GENERIC_TOKENS and not t.isdigit() for t in tail)
                and (take == 1 and len(tail[0]) >= 3 or any(len(t) >= 4 for t in tail))
            ):
                raw = " ".join(tail)
                if all(n != norm(raw) for _, n in out):
                    out.append((raw, norm(raw)))
    return out


def overpass_county(county: str) -> list[dict]:
    """Named school objects for one county, cached on disk."""
    OVERPASS_CACHE.mkdir(parents=True, exist_ok=True)
    cache_file = OVERPASS_CACHE / f"RO-{county}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    query = (
        "[out:json][timeout:120];"
        f'area["ISO3166-2"="RO-{county}"]->.a;'
        "("
        'nwr["amenity"="school"]["name"](area.a);'
        'nwr["building"="school"]["name"](area.a);'
        ");"
        "out center;"
    )
    elements = None
    for attempt in range(3):
        url = OVERPASS_URLS[attempt % len(OVERPASS_URLS)]
        try:
            resp = httpx.get(url, params={"data": query}, headers=UA, timeout=180)
            if resp.status_code == 429 or resp.status_code >= 500:
                wait = 30 * (attempt + 1)
                print(f"  Overpass {resp.status_code} from {url} for {county}; backoff {wait}s", flush=True)
                time.sleep(wait)
                continue
            if resp.status_code == 200:
                elements = resp.json().get("elements", [])
                break
            print(f"  Overpass {resp.status_code} from {url} for {county}", flush=True)
        except Exception as e:
            print(f"  Overpass error for {county} via {url}: {e}", flush=True)
            time.sleep(15)
    if elements is None:
        return []  # transient failure: NOT cached, so the next run retries the county

    out = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name", "")
        if not name:
            continue
        if "lat" in el and "lon" in el:
            coords = [el["lon"], el["lat"]]
        elif "center" in el:
            coords = [el["center"]["lon"], el["center"]["lat"]]
        else:
            continue
        out.append({"name": name, "tags": tags, "coords": coords})
    cache_file.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def osm_locality(tags: dict) -> str | None:
    for key in ("addr:city", "addr:town", "addr:village", "addr:hamlet", "addr:suburb", "addr:place", "is_in:city"):
        if tags.get(key):
            return norm(tags[key])
    return None


def links_from_tags(tags: dict) -> list[dict]:
    links = []
    for key, ltype in (("website", "website"), ("contact:website", "website"),
                       ("email", "email"), ("contact:email", "email"),
                       ("phone", "phone"), ("contact:phone", "phone")):
        for value in (tags.get(key) or "").split(";"):
            value = value.strip()
            if value and all((l["type"], l["value"]) != (ltype, value) for l in links):
                links.append({"type": ltype, "value": value, "source": "openstreetmap", "verified": False})
    return links


def match(e_norm: str, e_loc: str | None, candidates: list[dict]) -> dict | None:
    """Best OSM candidate above the confidence thresholds, or None if ambiguous."""
    eligible = []
    for c in candidates:
        c_norm, c_loc = c["norm"], c["loc"]
        r = SequenceMatcher(None, e_norm, c_norm).ratio()
        if e_loc:
            loc_match = c_loc == e_loc or e_loc in c_norm or (c_loc is not None and c_loc in e_norm)
            ok = (loc_match and r >= ACCEPT_RATIO) or (c_loc is None and r >= STRICT_RATIO)
        else:
            ok = r >= NO_LOCALITY_RATIO
        if ok:
            eligible.append((r, c))
    if not eligible:
        return None
    eligible.sort(key=lambda t: t[0], reverse=True)
    top_r, top = eligible[0]
    if len(eligible) > 1 and top_r - eligible[1][0] < AMBIGUITY_GAP and top_r < 1.0:
        return None
    return top


def village_geocode(client: httpx.Client, limiter: RateLimiter, locality_raw: str, county: str, cache: dict) -> tuple | None:
    county_name = COUNTY_NAMES.get(county, county)
    key = f"village-structured: {locality_raw}, {county_name}"
    if key in cache:
        return cache[key]
    result = None
    try:
        limiter.wait()
        resp = client.get(NOMINATIM_URL, params={
            "city": locality_raw, "county": county_name, "country": "Romania",
            "format": "json", "limit": 3,
        })
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  Nominatim error for {locality_raw!r}/{county}: {e}", flush=True)
        return None
    for hit in data:
        if norm(county_name) not in norm(hit.get("display_name", "")):
            continue
        if hit.get("class") == "place" and hit.get("type") in PLACE_TYPES:
            result = [float(hit["lon"]), float(hit["lat"])]
            break
        if hit.get("class") == "boundary" and hit.get("type") == "administrative":
            # Commune/city boundary named like the village -> bbox centroid
            bb = [float(v) for v in hit.get("boundingbox", [])]
            if len(bb) == 4:
                result = [(bb[2] + bb[3]) / 2, (bb[0] + bb[1]) / 2]
                break
    cache[key] = result
    return result


def main() -> None:
    with open(REGISTRY, encoding="utf-8") as f:
        entities = json.load(f)

    # --- Phase A: flag centroid-snapped coords (identical fallback coords within a county)
    coord_counts = Counter(
        (e["county"], round(e["coords"][0], 6), round(e["coords"][1], 6))
        for e in entities if e["coords"]
    )
    for e in entities:
        if e["coords"] and e.get("coords_precision") in (None, "address"):
            key = (e["county"], round(e["coords"][0], 6), round(e["coords"][1], 6))
            if coord_counts[key] >= CENTROID_MIN_SHARED:
                e["coords_precision"] = "area"

    # --- Phase A2: pull OSM candidates for all counties
    candidates_by_county = {}
    counties = sorted({e["county"] for e in entities})
    for i, county in enumerate(counties, 1):
        raw = overpass_county(county)
        for c in raw:
            c["norm"] = norm(c["name"])
            c["loc"] = osm_locality(c["tags"])
        candidates_by_county[county] = [c for c in raw if c["norm"]]
        print(f"Overpass {i}/{len(counties)} {county}: {len(candidates_by_county[county])} named schools", flush=True)
        time.sleep(COUNTY_DELAY)

    # --- Phase B + C: coords fix + link harvest
    fixed_poi, centroid_fixed, links_added = 0, 0, 0
    for e in entities:
        cands = candidates_by_county.get(e["county"], [])
        if not cands:
            continue
        loc = extract_locality(e["name"])
        e_loc = loc[1] if loc else None
        m = match(norm(e["name"]), e_loc, cands)
        if not m:
            continue
        if not e["coords"]:
            e["coords"] = m["coords"]
            e["coords_precision"] = "building"
            fixed_poi += 1
        elif e.get("coords_precision") == "area":
            e["coords"] = m["coords"]
            e["coords_precision"] = "building"
            centroid_fixed += 1
        have = {(l["type"], l["value"]) for l in e["links"]}
        for link in links_from_tags(m["tags"]):
            if (link["type"], link["value"]) not in have:
                e["links"].append(link)
                have.add((link["type"], link["value"]))
                links_added += 1

    # --- Phase D: village-level Nominatim fallback
    limiter = RateLimiter(interval=1.0)
    try:
        with open("scripts/geocode_cache.json", encoding="utf-8") as f:
            vcache = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        vcache = {}
    fixed_village = 0
    remaining = [
        e for e in entities
        if (not e["coords"] or e.get("coords_precision") == "area") and village_candidates(e["name"])
    ]
    print(f"Village fallback for {len(remaining)} entities...", flush=True)
    with httpx.Client(headers=UA, timeout=15.0, follow_redirects=True) as client:
        for i, e in enumerate(remaining, 1):
            for raw_loc, _ in village_candidates(e["name"]):
                coords = village_geocode(client, limiter, raw_loc, e["county"], vcache)
                if coords:
                    e["coords"] = coords
                    e["coords_precision"] = "locality"
                    fixed_village += 1
                    break
            if i % 50 == 0:
                print(f"  village pass {i}/{len(remaining)} (fixed so far: {fixed_village})", flush=True)
                with open("scripts/geocode_cache.json", "w", encoding="utf-8") as f:
                    json.dump(vcache, f, ensure_ascii=False)
    with open("scripts/geocode_cache.json", "w", encoding="utf-8") as f:
        json.dump(vcache, f, ensure_ascii=False)

    # --- Write canonical back (same one-entity-per-line format as normalize.py)
    for e in entities:
        e.setdefault("updated", __import__("datetime").date.today().isoformat())
    with open(REGISTRY, "w", encoding="utf-8") as f:
        f.write("[\n")
        f.write(",\n".join(json.dumps(e, ensure_ascii=False) for e in entities))
        f.write("\n]\n")

    with_coords = sum(1 for e in entities if e["coords"])
    print(
        f"Enrichment done:\n"
        f"  coords via OSM: {fixed_poi} | centroid coords replaced: {centroid_fixed} | village fallback: {fixed_village}\n"
        f"  links added from OSM: {links_added}\n"
        f"  entities with coords: {with_coords}/{len(entities)} ({round(100 * with_coords / len(entities))}%)\n"
        f"  still missing: {len(entities) - with_coords}"
    )


if __name__ == "__main__":
    main()
