#!/usr/bin/env python3
"""Aggregate cross-table concepts: dedup + LLM merge pass to connect facts.

Input: all_concepts.json (from collect_concepts.py)
Output: aggregated_concepts.json

The merge pass runs ONE small LLM call to:
  1. Fold near-duplicates (same fact, slightly different wording)
  2. CONNECT facts that only emerge by combining entries
     (e.g. one doc says "customer_id is FK", another says "it points to customers")
  3. Drop pure duplicates

Usage:
    python aggregate_concepts.py <bundle_dir> [--model <id>]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def run_lm_merge(concepts: list[dict], table_names: list[str], model: str) -> list[dict]:
    """Call LLM to merge and connect concepts intelligently."""
    if len(concepts) <= 1:
        return concepts

    listing = "\n".join(
        f"{i}. [{c['kind']}] tables={c['tables']} | {c['title']}: {c['body']}"
        for i, c in enumerate(concepts)
    )

    prompt = f"""DATASET CONCEPTS: {table_names}

EXTRACTED CROSS-TABLE FACTS (one per line, gathered from separate documents):
{listing}

Consolidate this list:
(a) MERGE entries that state the same fact — keep the most complete wording, union their tables.
(b) CONNECT facts that only emerge by combining entries — e.g., one names a join key and another names the table it joins to — into a single complete fact.
(c) DROP an entry only if it is a pure duplicate.

Do NOT invent any join, key, or formula not present above.
Do NOT add tables outside the DATASET CONCEPTS list.

Return STRICT JSON (no markdown, no prose):
{{"concepts":[{{"kind":"...", "tables":["..."], "title":"...", "body":"..."}}, ...]}}
"""

    try:
        result = subprocess.run(
            ["claude", "-p", "--model", model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            sys.stderr.write(f"LLM call failed: {result.stderr}\n")
            return concepts  # Fallback: return unmerged
        text = result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        sys.stderr.write(f"Failed to call claude: {e}\n")
        return concepts  # Fallback

    # Parse JSON from response.
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        sys.stderr.write("No JSON found in LLM response\n")
        return concepts  # Fallback

    try:
        obj = json.loads(m.group(0))
        merged = obj.get("concepts", []) if isinstance(obj, dict) else []
    except json.JSONDecodeError:
        sys.stderr.write("Failed to parse LLM JSON\n")
        return concepts  # Fallback

    # Validate and normalize merged output.
    out = []
    table_set = set(str(t) for t in table_names)
    for c in merged:
        if not isinstance(c, dict):
            continue
        kind = str(c.get("kind", "")).strip()
        tables = [str(t) for t in (c.get("tables") or []) if str(t) in table_set]
        title = str(c.get("title", "")).strip()
        body = str(c.get("body", "")).strip()
        if kind and tables and title and body:
            out.append({
                "kind": kind,
                "tables": tables,
                "title": title,
                "body": body,
            })

    # If merge returned nothing usable, fallback to original list.
    return out if out else concepts


def main() -> int:
    ap = argparse.ArgumentParser(description="Aggregate cross-table concepts via LLM merge.")
    ap.add_argument("bundle", help="Path to the bundle root directory.")
    ap.add_argument(
        "--model",
        default="claude-opus-4-8",
        help="Claude model to use (default: claude-opus-4-8).",
    )
    ap.add_argument(
        "--input",
        default=None,
        help="Input JSON file (default: <bundle>/okf-work/all_concepts.json).",
    )
    ap.add_argument(
        "--output",
        default=None,
        help="Output file (default: <bundle>/okf-work/aggregated_concepts.json).",
    )
    args = ap.parse_args()

    root = Path(args.bundle).resolve()
    in_path = Path(args.input) if args.input else root / "okf-work" / "all_concepts.json"
    out_path = Path(args.output) if args.output else root / "okf-work" / "aggregated_concepts.json"

    if not in_path.exists():
        sys.stderr.write(f"Input file not found: {in_path}\n")
        return 2

    try:
        concepts = json.loads(in_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Failed to parse input JSON: {e}\n")
        return 2

    if not isinstance(concepts, list):
        sys.stderr.write("Input is not a JSON array\n")
        return 2

    # Extract table names from all concepts.
    table_names = set()
    for c in concepts:
        if isinstance(c, dict):
            table_names.update(str(t) for t in (c.get("tables") or []))
    table_names = sorted(table_names)

    print(f"Input: {len(concepts)} raw concept(s)")
    print(f"Dataset tables: {table_names}")
    print("Running LLM merge pass...")

    merged = run_lm_merge(concepts, table_names, args.model)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    print(f"Output: {len(merged)} aggregated concept(s)")
    print(f"Wrote {out_path.relative_to(root.parent) if root.parent in out_path.parents else out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
