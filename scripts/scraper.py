"""Phase 1 scraper: pulls school assignment stats for all 42 counties.

Sources (per county):
  - static.admitere.edu.ro/2026/repartizare/{county}/data/school.json
    -> units with 8th-grade cohorts: candidate/assigned/unassigned stats
  - static.admitere.edu.ro/2026/repartizare/{county}/data/highschool.json
    -> all high schools (adds units without graduating cohorts)

The county HTML pages render tables client-side from these JSON endpoints,
so we consume them directly. Records from both feeds are merged by school
code, tagged with `kind` ("school" / "highschool"), strings are cleaned and
6-digit postal codes embedded in addresses are separated into `postcode`.

Output: public/data/schools_raw.json
"""

import asyncio
import json
import os
import re

import httpx

COUNTIES = [
    "B", "AB", "AR", "AG", "BC", "BH", "BN", "BT", "BV", "BR", "BZ", "CS", "CL",
    "CJ", "CT", "CV", "DB", "DJ", "GL", "GR", "GJ", "HR", "HD", "IL", "IS", "IF",
    "MM", "MH", "MS", "NT", "OT", "PH", "SM", "SJ", "SB", "SV", "TR", "TM", "TL",
    "VS", "VL", "VN"
]

BASE_URL = "https://static.admitere.edu.ro/2026/repartizare/{county}/data/{feed}.json"
FEEDS = ("school", "highschool")

OUTPUT_FILE = "public/data/schools_raw.json"

MAX_CONCURRENCY = 8
MAX_RETRIES = 3
REQUEST_TIMEOUT = 20.0

POSTCODE_RE = re.compile(r"^(?P<addr>.*?)[\s,;]+(?P<postal>\d{6})\s*$")


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip() if text else ""


def split_postcode(addr: str) -> tuple[str, str]:
    match = POSTCODE_RE.match(addr)
    if match:
        return clean(match.group("addr")), match.group("postal")
    return addr, ""


def parse_stat(value) -> int | None:
    """Feed records lacking a stats field did not participate in repartizare
    (no 8th-grade cohort) — None means "no data", distinct from a real 0."""
    return int(value) if value is not None else None


def normalize_school(raw: dict, county: str, kind: str) -> dict:
    addr, postcode = split_postcode(clean(raw.get("a", "")))
    return {
        "id": clean(raw.get("c", "")) or clean(raw.get("lc", "")),
        "name": clean(raw.get("n", "")) or clean(raw.get("l", "")),
        "cand": parse_stat(raw.get("noc")),
        "rep": parse_stat(raw.get("nocr")),
        "nerep": parse_stat(raw.get("nocnr")),
        "type": clean(raw.get("t", "")),
        "env": clean(raw.get("m", "")),  # URBAN / RURAL
        "addr": addr,
        "postcode": postcode,
        "tel": clean(raw.get("p", "")),
        "county": clean(raw.get("j", "")) or county,
        "kind": kind,
    }


async def fetch_feed(client: httpx.AsyncClient, url: str) -> list[dict] | None:
    """Returns the record list, [] on 404, or None after exhausting retries."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = await client.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 404:
                print(f"Missing data: {url}")
                return []
            if resp.status_code != 200:
                raise httpx.HTTPStatusError(f"HTTP {resp.status_code}", request=resp.request, response=resp)

            records = resp.json()
            if not isinstance(records, list):
                raise ValueError("Unexpected payload: expected a JSON list")
            return records
        except Exception as e:
            print(f"Error fetching {url} (attempt {attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(2.0 * attempt)
    return None


async def fetch_county(client: httpx.AsyncClient, semaphore: asyncio.Semaphore, county: str) -> list[dict]:
    async with semaphore:
        school_records = await fetch_feed(client, BASE_URL.format(county=county, feed="school"))
        highschool_records = await fetch_feed(client, BASE_URL.format(county=county, feed="highschool"))
        if school_records is None or highschool_records is None:
            print(
                f"{county}: incomplete fetch "
                f"(school feed: {'ok' if school_records is not None else 'FAILED'}, "
                f"highschool feed: {'ok' if highschool_records is not None else 'FAILED'}) — county skipped"
            )
            return []

    # Highschool codes let us tag matching school-feed records as highschools
    highschool_codes = {clean(r.get("lc", "")) for r in highschool_records or []}

    merged = []
    seen_ids = set()
    for r in school_records or []:
        kind = "highschool" if clean(r.get("c", "")) in highschool_codes else "school"
        item = normalize_school(r, county, kind)
        merged.append(item)
        seen_ids.add(item["id"])
    for r in highschool_records or []:
        item = normalize_school(r, county, "highschool")
        if item["id"] in seen_ids:
            continue
        merged.append(item)
        seen_ids.add(item["id"])

    print(f"{county}: {len(school_records or [])} units + {len(highschool_records or [])} high schools -> {len(merged)} merged")
    return merged


async def main():
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ro-schools-map/1.0)"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        tasks = [fetch_county(client, semaphore, c) for c in COUNTIES]
        results = await asyncio.gather(*tasks)

    flat_list = [item for sublist in results for item in sublist]
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(flat_list, f, ensure_ascii=False, indent=2)

    highschools = sum(1 for item in flat_list if item["kind"] == "highschool")
    failed = [c for c, r in zip(COUNTIES, results) if not r]
    print(f"Scraped {len(flat_list)} units ({highschools} high schools, {len(flat_list) - highschools} other) across {len(COUNTIES) - len(failed)}/{len(COUNTIES)} counties -> {OUTPUT_FILE}")
    if failed:
        print(f"Counties with no data: {', '.join(failed)}")


if __name__ == "__main__":
    asyncio.run(main())
