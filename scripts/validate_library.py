#!/usr/bin/env python3
"""Validate every library item against its per-type JSON Schema.

For each library/<type>/*.json, validate against schemas/<type>.schema.json.
Exits non-zero on the first failure (with a readable message). Run in CI on
every PR and locally before cutting a release tag.

Usage: python scripts/validate_library.py
Requires: jsonschema  (pip install jsonschema)
"""
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "library"
SCHEMAS = ROOT / "schemas"


def main() -> int:
    errors = 0
    checked = 0
    for type_dir in sorted(p for p in LIB.iterdir() if p.is_dir()):
        schema_path = SCHEMAS / f"{type_dir.name}.schema.json"
        if not schema_path.exists():
            print(f"::error::no schema for type '{type_dir.name}' ({schema_path})")
            errors += 1
            continue
        validator = Draft202012Validator(json.loads(schema_path.read_text()))
        for f in sorted(type_dir.glob("*.json")):
            checked += 1
            try:
                doc = json.loads(f.read_text())
            except json.JSONDecodeError as e:
                print(f"::error file={f}::invalid JSON: {e}")
                errors += 1
                continue
            for v in sorted(validator.iter_errors(doc), key=lambda e: e.path):
                loc = "/".join(str(p) for p in v.path) or "(root)"
                print(f"::error file={f}::{loc}: {v.message}")
                errors += 1

    if errors:
        print(f"\nFAILED: {errors} schema error(s) across {checked} files.")
        return 1
    print(f"OK: {checked} library items valid against their schemas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
