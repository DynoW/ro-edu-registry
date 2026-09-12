"""Weekly link checker: validates HTTP links in the canonical registry.

Reads  data/entities/*.json
Writes public/data/linkcheck.json (dead links report) and prints a summary.

Only URL-typed links are checked (email/phone are skipped). A link is dead
if the server answers 4xx/5xx (HEAD first, then GET for servers without HEAD
support) or the connection fails. Redirects are followed; 301/302 chains are
not reported. Exit code is always 0 — CI decides what to do with the report.
"""

import asyncio
import json
from pathlib import Path

import httpx

ENTITIES_DIR = Path("data/entities")
OUT_FILE = Path("public/data/linkcheck.json")

URL_TYPES = {"website", "facebook", "instagram", "youtube", "linkedin", "discord", "tiktok", "other"}

MAX_CONCURRENCY = 8
REQUEST_TIMEOUT = 15.0


def collect_links() -> list[dict]:
    targets = []
    for path in sorted(ENTITIES_DIR.glob("*.json")):
        entities = json.loads(path.read_text(encoding="utf-8"))
        for e in entities:
            for i, link in enumerate(e.get("links", [])):
                value = link.get("value", "")
                if link.get("type") in URL_TYPES and value.startswith("http"):
                    targets.append({
                        "entity": e["id"],
                        "name": e["name"],
                        "type": link["type"],
                        "value": value,
                        "key": f"{path.name}:{e['id']}:{i}",
                    })
    return targets


async def check(client: httpx.AsyncClient, semaphore: asyncio.Semaphore, t: dict) -> dict | None:
    async with semaphore:
        for method in ("HEAD", "GET"):
            try:
                resp = await client.request(method, t["value"], timeout=REQUEST_TIMEOUT, follow_redirects=True)
                if resp.status_code < 400:
                    return None
                last = f"HTTP {resp.status_code}"
            except httpx.HTTPError as e:
                last = f"{type(e).__name__}: {e}"
        return {**t, "error": last}


async def main() -> None:
    targets = collect_links()
    print(f"Checking {len(targets)} links…")
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ro-edu-registry-linkcheck/1.0)"}
    async with httpx.AsyncClient(headers=headers) as client:
        results = await asyncio.gather(*(check(client, semaphore, t) for t in targets))
    dead = [r for r in results if r]
    for r in dead:
        print(f"DEAD [{r['error']}] {r['value']} ({r['entity']}, {r['type']})")
    print(f"{len(dead)}/{len(targets)} dead links")
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(dead, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
