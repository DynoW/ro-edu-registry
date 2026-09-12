"""Compares a fresh scrape (public/data/schools_raw.json) against the canonical
registry (data/entities/schools.json) and reports feed drift.

Writes a Markdown report to public/data/refresh_report.md. Empty report means
the live admitere.edu.ro feeds match the canonical registry.

Run scripts/scraper.py first.
"""

import json
from collections import defaultdict
from pathlib import Path

RAW_FILE = Path("public/data/schools_raw.json")
CANONICAL_FILE = Path("data/entities/schools.json")
REPORT_FILE = Path("public/data/refresh_report.md")


def main() -> None:
    raw = json.loads(RAW_FILE.read_text(encoding="utf-8"))
    canonical = json.loads(CANONICAL_FILE.read_text(encoding="utf-8"))

    raw_by_id = {r["id"]: r for r in raw}
    canon_by_id = {e["siiir"]: e for e in canonical if "siiir" in e}

    added = sorted(set(raw_by_id) - set(canon_by_id))
    removed = sorted(set(canon_by_id) - set(raw_by_id))

    renamed = []
    for uid in set(raw_by_id) & set(canon_by_id):
        if raw_by_id[uid]["name"] != canon_by_id[uid]["name"]:
            renamed.append((uid, canon_by_id[uid]["name"], raw_by_id[uid]["name"]))

    if not (added or removed or renamed):
        REPORT_FILE.unlink(missing_ok=True)  # absent file = "no drift" for CI
        print("No drift: live feeds match the canonical registry.")
        return

    by_county_new = defaultdict(list)
    for uid in added:
        by_county_new[raw_by_id[uid]["county"]].append(raw_by_id[uid]["name"])
    by_county_gone = defaultdict(list)
    for uid in removed:
        by_county_gone[canon_by_id[uid]["county"]].append(canon_by_id[uid]["name"])

    lines = [
        "Weekly feed refresh found drift between admitere.edu.ro and the canonical registry:",
        "",
        f"- **{len(added)} new unit(s)** in the live feeds, missing from the registry",
        f"- **{len(removed)} unit(s)** removed from the live feeds",
        f"- **{len(renamed)} renamed unit(s)**",
        "",
        "The weekly refresh does not touch canonical data automatically.",
        "A maintainer should run `scripts/scraper.py && scripts/normalize.py` locally,",
        "review the diff, and open a PR (coords/links are merge-preserved).",
        "",
    ]
    for county, names in sorted(by_county_new.items()):
        lines.append(f"### New in {county}")
        lines.extend(f"- {n}" for n in names)
        lines.append("")
    for county, names in sorted(by_county_gone.items()):
        lines.append(f"### No longer in feeds: {county}")
        lines.extend(f"- {n}" for n in names)
        lines.append("")
    if renamed:
        lines.append("### Renamed")
        lines.extend(f"- `{uid}`: {old} → {new}" for uid, old, new in renamed)

    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Drift detected: +{len(added)} / -{len(removed)} / ~{len(renamed)} → {REPORT_FILE}")


if __name__ == "__main__":
    main()
