#!/usr/bin/env python3
"""Collect cross-table concepts from all .concepts.json sidecars in a bundle.

After `convert_source.sh` runs, each concept .md has an optional .concepts.json
sidecar containing the `<CONCEPTS>` array it extracted. This script:
  1. Walks the bundle directory
  2. Collects all .concepts.json files
  3. Merges them into one global list with deduplication
  4. Writes the result to <bundle>/okf-work/all_concepts.json

The list is input to `aggregate_concepts.py` for the merge pass.

Usage:
    python collect_concepts.py <bundle_dir> [--output <file>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Collect cross-table concepts from bundle.")
    ap.add_argument("bundle", help="Path to the bundle root directory.")
    ap.add_argument(
        "--output",
        default=None,
        help="Output file (default: <bundle>/okf-work/all_concepts.json).",
    )
    args = ap.parse_args()

    root = Path(args.bundle).resolve()
    if not root.is_dir():
        sys.stderr.write(f"Not a directory: {root}\n")
        return 2

    out_path = Path(args.output) if args.output else root / "okf-work" / "all_concepts.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Dedup by (kind, sorted tables, title) to avoid exact duplicates across files.
    by_key = {}
    file_count = 0

    for concepts_file in sorted(root.rglob("*.concepts.json")):
        try:
            concepts = json.loads(concepts_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        if not isinstance(concepts, list):
            continue

        file_count += 1
        for c in concepts:
            if not isinstance(c, dict):
                continue
            kind = str(c.get("kind", "")).strip()
            tables = tuple(sorted(str(t) for t in (c.get("tables") or [])))
            title = str(c.get("title", "")).strip().lower()
            body = str(c.get("body", "")).strip()

            if not (kind and tables and title and body):
                continue

            key = (kind, tables, title)
            prev = by_key.get(key)
            # Keep the longer body (more complete).
            if prev is None or len(body) > len(prev.get("body", "")):
                by_key[key] = {
                    "kind": kind,
                    "tables": list(tables),
                    "title": title,
                    "body": body,
                }

    deduped = list(by_key.values())
    with open(out_path, "w") as f:
        json.dump(deduped, f, indent=2, ensure_ascii=False)

    print(f"Collected {file_count} .concepts.json file(s)")
    print(f"Deduped to {len(deduped)} unique concept(s)")
    print(f"Wrote {out_path.relative_to(root.parent) if root.parent in out_path.parents else out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
