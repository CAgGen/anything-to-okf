#!/usr/bin/env python3
"""Inject aggregated cross-table concepts into each concept's .md file.

For each concept, finds all shared concepts that mention it (bidirectional) and
adds them as a new "# Cross-references" section with markdown links to related
concepts.

Usage:
    python inject_shared_concepts.py <bundle_dir> [--input <file>]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def derive_concept_id(md_path: Path, bundle_root: Path) -> str:
    """Convert /path/to/bundle/tables/orders.md -> tables/orders"""
    rel = md_path.relative_to(bundle_root).with_suffix("")
    return str(rel).replace("\\", "/")


def build_cross_reference_section(
    concepts: list[dict], concept_id: str, bundle_root: Path
) -> str | None:
    """Build a markdown # Cross-references section for this concept.

    Returns None if no concepts mention this concept_id.
    Bidirectional: returns all concepts where concept_id is in tables list.
    """
    relevant = [
        c for c in concepts if concept_id in (c.get("tables") or [])
    ]
    if not relevant:
        return None

    lines = ["# Cross-references", "", "Cross-table concepts and relationships involving this entity:"]
    for c in relevant:
        kind = c.get("kind", "")
        title = c.get("title", "unknown")
        body = c.get("body", "")
        tables = c.get("tables", [])

        # Build links to the OTHER tables involved in this concept.
        other_tables = [t for t in tables if t != concept_id]
        links = []
        for t in other_tables:
            # Assume concept IDs map to .md paths: tables/orders -> tables/orders.md
            link_path = f"/{t}.md"
            links.append(f"[{t}]({link_path})")

        if links:
            link_str = ", ".join(links)
            lines.append(f"- **[{kind}] {title}** (involves {link_str}): {body}")
        else:
            lines.append(f"- **[{kind}] {title}**: {body}")

    return "\n".join(lines) + "\n"


def inject_into_file(md_path: Path, section: str) -> bool:
    """Add or replace the Cross-references section in a .md file.

    Appends before any final "# Citations" section if present, otherwise appends
    at the end of the file. Returns True if the file was modified.
    """
    try:
        content = md_path.read_text(encoding="utf-8")
    except OSError:
        return False

    # If a Cross-references section already exists, replace it.
    existing_pattern = r"# Cross-references\n\n.*?(?=\n# |\Z)"
    if re.search(existing_pattern, content, re.S):
        content = re.sub(existing_pattern, section.rstrip(), content, count=1, flags=re.S)
        md_path.write_text(content, encoding="utf-8")
        return True

    # Otherwise, insert before Citations if present, else at end.
    citations_idx = content.find("\n# Citations\n")
    if citations_idx != -1:
        content = content[:citations_idx] + "\n\n" + section + content[citations_idx:]
    else:
        if not content.endswith("\n"):
            content += "\n"
        content += "\n" + section

    md_path.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Inject aggregated cross-table concepts.")
    ap.add_argument("bundle", help="Path to the bundle root directory.")
    ap.add_argument(
        "--input",
        default=None,
        help="Input JSON file (default: <bundle>/okf-work/aggregated_concepts.json).",
    )
    args = ap.parse_args()

    root = Path(args.bundle).resolve()
    in_path = Path(args.input) if args.input else root / "okf-work" / "aggregated_concepts.json"

    if not in_path.exists():
        print(f"No aggregated concepts file: {in_path}")
        print("Skipping injection (run aggregate_concepts.py first)")
        return 0

    try:
        concepts = json.loads(in_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Failed to parse concepts JSON: {e}\n")
        return 2

    if not isinstance(concepts, list):
        sys.stderr.write("Concepts JSON is not an array\n")
        return 2

    # Find all concept .md files (skip index.md and log.md).
    md_files = [
        p for p in root.rglob("*.md")
        if p.name not in ("index.md", "log.md")
    ]

    modified = 0
    for md_path in sorted(md_files):
        concept_id = derive_concept_id(md_path, root)
        section = build_cross_reference_section(concepts, concept_id, root)
        if section:
            if inject_into_file(md_path, section):
                modified += 1
                print(f"  ✓ {concept_id}")

    print(f"\nModified {modified} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
