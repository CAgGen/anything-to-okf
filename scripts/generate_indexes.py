#!/usr/bin/env python3
"""Generate (or regenerate) OKF `index.md` files for every directory in a bundle.

Per the OKF spec (references/okf-spec.md §6), an `index.md` provides
*progressive disclosure*: it lists a directory's contents so a human or agent
can see what is available before opening individual documents.

This is a deterministic post-processing step — run it AFTER all concept docs are
written so each index reflects the final tree. It reads each concept's
frontmatter (`type`, `title`, `description`) and builds:

  * For each concept type, a section heading with bullet links to the concepts.
  * A "Subdirectories" section linking to each child directory's index.

Concept entries are grouped by `type` (e.g. all "BigQuery Table" concepts
together), matching the style of reference OKF bundles. Index files carry no
frontmatter, per the spec.

Usage:
    python generate_indexes.py <bundle_dir>
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("PyYAML is required: pip install pyyaml\n")
    sys.exit(2)

INDEX = "index.md"
RESERVED = {"index.md", "log.md"}
_DELIM = "---"


def read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if not lines or lines[0].strip() != _DELIM:
        return {}
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == _DELIM:
            end = i
            break
    if end is None:
        return {}
    try:
        fm = yaml.safe_load("\n".join(lines[1:end])) or {}
    except yaml.YAMLError:
        return {}
    return fm if isinstance(fm, dict) else {}


def directories(root: Path) -> list[Path]:
    dirs: set[Path] = {root}
    for md in root.rglob("*.md"):
        cur = md.parent
        while True:
            dirs.add(cur)
            if cur == root:
                break
            cur = cur.parent
    return sorted(dirs)


def build_index(directory: Path, dir_desc: dict[Path, str]) -> str | None:
    by_type: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    subdirs: list[tuple[str, str]] = []  # (name, description)

    for child in sorted(directory.iterdir()):
        if child.name == INDEX:
            continue
        if child.is_file() and child.suffix == ".md" and child.name not in RESERVED:
            fm = read_frontmatter(child)
            typ = str(fm.get("type") or "Concepts")
            title = str(fm.get("title") or child.stem)
            desc = str(fm.get("description") or "")
            by_type[typ].append((title, child.name, desc))
        elif child.is_dir():
            subdirs.append((child.name, dir_desc.get(child, "")))

    if not by_type and not subdirs:
        return None

    sections: list[str] = []
    for typ in sorted(by_type):
        lines = [f"# {typ}", ""]
        for title, link, desc in sorted(by_type[typ], key=lambda e: e[0].lower()):
            suffix = f" - {desc}" if desc else ""
            lines.append(f"* [{title}]({link}){suffix}")
        sections.append("\n".join(lines))
    if subdirs:
        lines = ["# Subdirectories", ""]
        for name, desc in sorted(subdirs):
            suffix = f" - {desc}" if desc else ""
            lines.append(f"* [{name}]({name}/{INDEX}){suffix}")
        sections.append("\n".join(lines))

    return "\n\n".join(sections) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate OKF index.md files.")
    ap.add_argument("bundle", help="Path to the bundle root directory.")
    args = ap.parse_args()
    root = Path(args.bundle).resolve()
    if not root.is_dir():
        sys.stderr.write(f"Not a directory: {root}\n")
        return 2

    # Deepest-first so a parent index can describe a child dir from its single
    # concept's description when available.
    dirs = sorted(directories(root), key=lambda p: len(p.parts), reverse=True)
    dir_desc: dict[Path, str] = {}
    written = []
    for d in dirs:
        content = build_index(d, dir_desc)
        if content is None:
            continue
        (d / INDEX).write_text(content, encoding="utf-8")
        written.append(d / INDEX)
        # If this dir holds exactly one concept, lift its description up so the
        # parent's "Subdirectories" entry is meaningful.
        concepts = [
            c
            for c in d.iterdir()
            if c.is_file() and c.suffix == ".md" and c.name not in RESERVED
        ]
        if len(concepts) == 1:
            desc = str(read_frontmatter(concepts[0]).get("description") or "")
            if desc:
                dir_desc[d] = desc

    for p in written:
        print(f"wrote {p.relative_to(root)}")
    print(f"\n{len(written)} index.md file(s) written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
