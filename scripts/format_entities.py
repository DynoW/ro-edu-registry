"""Canonical formatter for data/entities/*.json.

Enforces the field order defined by data/schemas/entity.schema.json (top-level
properties, plus the nested `stats` and `links` item orders) and the
one-entity-per-line layout used across the registry. Idempotent: running it
twice changes nothing.

Usage:
  python3 scripts/format_entities.py           # rewrite files in place
  python3 scripts/format_entities.py --check   # exit 1 if any file would change (CI)
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILE = ROOT / "data" / "schemas" / "entity.schema.json"
ENTITIES_DIR = ROOT / "data" / "entities"


def orders_from_schema() -> dict[str, list[str]]:
    """Field orders keyed by context: '' = entity, otherwise a nested key
    (e.g. 'stats', 'links') whose item order comes from the schema too."""
    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    props = schema["properties"]
    orders = {"": list(props)}
    for key in ("stats", "links"):
        nested = props[key].get("properties") or props[key].get("items", {}).get("properties")
        if nested:
            orders[key] = list(nested)
    return orders


ORDERS = orders_from_schema()


def order_keys(obj: dict, order: list[str]) -> dict:
    out = {k: obj[k] for k in order if k in obj}
    for k in obj:  # tolerate fields not yet in the canonical order
        if k not in out:
            out[k] = obj[k]
    return out


def format_entity(e: dict) -> dict:
    e = order_keys(e, ORDERS[""])
    for key, order in ORDERS.items():
        if key and isinstance(e.get(key), dict):
            e[key] = order_keys(e[key], order)
        elif key and isinstance(e.get(key), list):
            e[key] = [order_keys(item, order) if isinstance(item, dict) else item for item in e[key]]
    return e


def serialize(entities: list) -> str:
    return "[\n" + ",\n".join(json.dumps(e, ensure_ascii=False) for e in entities) + "\n]\n"


def main() -> int:
    check = "--check" in sys.argv[1:]
    changed = []
    total = 0
    for path in sorted(ENTITIES_DIR.glob("*.json")):
        original = path.read_text(encoding="utf-8")
        entities = json.loads(original)  # doubles as a JSON syntax check
        total += len(entities)
        formatted = serialize([format_entity(e) for e in entities])
        if formatted != original:
            changed.append(path)
            if not check:
                path.write_text(formatted, encoding="utf-8")

    if check:
        if changed:
            print("Files not in canonical format (fix with: python3 scripts/format_entities.py):")
            for p in changed:
                print(f"  {p}")
            return 1
        print(f"Format check passed: {total} entities in {ENTITIES_DIR}")
        return 0

    for p in changed:
        print(f"formatted {p}")
    print(f"Done: {total} entities across {len(sorted(ENTITIES_DIR.glob('*.json')))} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
