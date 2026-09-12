"""Phase 2 geocoder: converts schools_raw.json to coordinate-enriched GeoJSON.

Geocodes each school against the OpenStreetMap Nominatim API with a 1 request/second
pace, a local on-disk cache (resumable across runs), a three-step fallback
chain (full query, address-only, name+county), and Romania-restricted results.

Input:  public/data/schools_raw.json
Output: public/data/schools.geojson (minified FeatureCollection)
Cache:  scripts/geocode_cache.json
"""

import json
import os
import time
import urllib.parse

import httpx

from counties import COUNTY_NAMES


class RateLimited(RuntimeError):
    """Nominatim kept returning 429 after exhausting backoff retries."""


class RateLimiter:
    """Ensures at most one request per `interval` seconds."""

    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self._last = 0.0

    def wait(self) -> None:
        elapsed = time.monotonic() - self._last
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        self._last = time.monotonic()

CACHE_FILE = "scripts/geocode_cache.json"
RAW_FILE = "public/data/schools_raw.json"
OUTPUT_FILE = "public/data/schools.geojson"


def load_cache() -> dict:
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print(f"WARNING: {CACHE_FILE} is corrupt; starting with an empty cache", flush=True)
        return {}


def save_cache(cache: dict) -> None:
    tmp = CACHE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)
    os.replace(tmp, CACHE_FILE)


def build_query(s: dict) -> tuple[str, list[str]]:
    county = COUNTY_NAMES.get(s["county"], s["county"])
    addr = f"{s['addr']} {s['postcode']}".strip() if s.get("postcode") else s["addr"]
    name = s["name"].replace("„", "").replace("”", "").replace('"', "")
    query = f"{s['name']}, {addr}, {county}, Romania"
    fallbacks = [
        f"{addr}, {county}, Romania",
        f"{name}, {county}, Romania",
    ]
    return query, fallbacks


def geocode(client: httpx.Client, rate_limiter: RateLimiter, query: str, max_retries: int = 3):
    encoded = urllib.parse.quote(query)
    url = f"https://nominatim.openstreetmap.org/search?q={encoded}&format=json&limit=1&countrycodes=ro"
    for attempt in range(max_retries):
        rate_limiter.wait()
        resp = client.get(url)
        if resp.status_code == 429:
            wait = 60 * (2 ** attempt)
            print(f"Rate limited; backing off {wait}s ({query[:60]}...)", flush=True)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        data = resp.json()
        if data:
            return [float(data[0]["lon"]), float(data[0]["lat"])]
        return None
    raise RateLimited(f"Still rate limited after {max_retries} attempts for {query!r}")


def run_geocoder():
    cache = load_cache()
    with open(RAW_FILE, "r", encoding="utf-8") as f:
        schools = json.load(f)

    client = httpx.Client(headers={"User-Agent": "FastMapRoSchools/1.0"}, timeout=15.0)
    rate_limiter = RateLimiter(interval=1.0)
    features = []
    total = len(schools)
    consecutive_rate_limited = 0
    MAX_CONSECUTIVE_429 = 3

    for idx, s in enumerate(schools):
        query, fallbacks = build_query(s)

        if query not in cache:
            try:
                coords = geocode(client, rate_limiter, query)
                for fallback in fallbacks:
                    if coords is not None:
                        break
                    coords = geocode(client, rate_limiter, fallback)
                cache[query] = coords
                save_cache(cache)  # Atomic write: a crash loses at most the in-flight lookup
            except RateLimited as e:
                consecutive_rate_limited += 1
                print(f"Rate limited for {query!r} ({consecutive_rate_limited}/{MAX_CONSECUTIVE_429} consecutive)", flush=True)
                if consecutive_rate_limited >= MAX_CONSECUTIVE_429:
                    raise SystemExit(
                        "Aborting: Nominatim is rate-limiting every request. "
                        "All progress is saved in the cache; rerun later."
                    ) from e
            except Exception as e:
                consecutive_rate_limited = 0
                # Transient errors are not cached so the next run retries them
                print(f"Geocoding error for {query!r}: {e}", flush=True)
            else:
                consecutive_rate_limited = 0

        coords = cache.get(query)
        if coords:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": coords
                },
                "properties": s
            })

        if idx % 100 == 0:
            print(f"Progress: {idx}/{total} | geocoded so far: {len(features)}", flush=True)

    save_cache(cache)
    geojson = {"type": "FeatureCollection", "features": features}
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(geojson, f, separators=(',', ':'))
    print(f"Geocoded {len(features)}/{total} schools ({total - len(features)} without coordinates) to {OUTPUT_FILE}", flush=True)


if __name__ == "__main__":
    run_geocoder()
