"""Validates every canonical entity file against data/schemas/entity.schema.json.

Runs in CI (validate.yml) and locally before committing registry changes.
"""

import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "data" / "schemas" / "entity.schema.json"
ENTITIES_DIR = ROOT / "data" / "entities"


def main() -> int:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)
    errors = 0
    total = 0
    for path in sorted(ENTITIES_DIR.glob("*.json")):
        entities = json.loads(path.read_text(encoding="utf-8"))
        for i, entity in enumerate(entities):
            total += 1
            for err in validator.iter_errors(entity):
                errors += 1
                print(f"{path.name}[{i}] {entity.get('id', '?')}: {err.message}")
    print(f"Validated {total} entities across {len(list(ENTITIES_DIR.glob('*.json')))} files: {errors} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
