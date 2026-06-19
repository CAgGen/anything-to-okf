#!/usr/bin/env python3
"""Validate an OKF (Open Knowledge Format) bundle for conformance.

OKF v0.1 conformance (see references/okf-spec.md) is intentionally permissive.
This checker separates HARD errors (a bundle is non-conformant) from soft
warnings (style/quality issues the spec explicitly tolerates).

HARD ERRORS (exit code 1):
  * A non-reserved `.md` file has no parseable YAML frontmatter block.
  * A frontmatter block is missing a non-empty `type` field.
  * An `index.md` / `log.md` carries frontmatter it shouldn't (only the
    bundle-root `index.md` may, and only to declare `okf_version`).

WARNINGS (do not fail the build, but are reported so they can be fixed):
  * Missing recommended frontmatter (title, description, timestamp).
  * Broken cross-links (the spec says consumers MUST tolerate these — they may
    be not-yet-written knowledge — so they are informational only).
  * A directory with concept docs but no index.md (progressive disclosure aid).

Usage:
    python validate_bundle.py <bundle_dir> [--strict]

`--strict` promotes all warnings to errors (useful in CI once a bundle is
meant to be "complete").
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "PyYAML is required: pip install pyyaml (or use the system python "
        "that has it).\n"
    )
    sys.exit(2)

RESERVED = {"index.md", "log.md"}
RECOMMENDED_KEYS = ("title", "description", "timestamp")
_DELIM = "---"
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def parse_frontmatter(text: str):
    """Return (frontmatter_dict_or_None, had_block, error_or_None)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != _DELIM:
        return None, False, None
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == _DELIM:
            end = i
            break
    if end is None:
        return None, True, "unterminated frontmatter block"
    try:
        fm = yaml.safe_load("\n".join(lines[1:end])) or {}
    except yaml.YAMLError as e:
        return None, True, f"invalid YAML in frontmatter: {e}"
    if not isinstance(fm, dict):
        return None, True, "frontmatter is not a YAML mapping"
    return fm, True, None


def resolve_link(target: str, doc: Path, root: Path) -> Path | None:
    """Resolve an internal markdown link to a bundle path, or None if external."""
    t = target.split("#", 1)[0].strip()
    if not t:
        return None
    low = t.lower()
    if low.startswith(("http://", "https://", "mailto:", "ftp://", "data:")):
        return None
    if t.startswith("/"):
        return (root / t.lstrip("/")).resolve()
    return (doc.parent / t).resolve()


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate an OKF bundle.")
    ap.add_argument("bundle", help="Path to the bundle root directory.")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings (missing recommended fields, broken links, "
        "missing indexes) as errors.",
    )
    args = ap.parse_args()

    root = Path(args.bundle).resolve()
    if not root.is_dir():
        sys.stderr.write(f"Not a directory: {root}\n")
        return 2

    errors: list[str] = []
    warnings: list[str] = []
    concept_count = 0
    dirs_with_concepts: set[Path] = set()
    dirs_with_index: set[Path] = set()

    for md in sorted(root.rglob("*.md")):
        rel = md.relative_to(root)
        text = md.read_text(encoding="utf-8", errors="replace")
        is_reserved = md.name in RESERVED
        is_root_index = md.name == "index.md" and md.parent == root

        fm, had_block, err = parse_frontmatter(text)

        if is_reserved:
            dirs_with_index.add(md.parent)
            if had_block and not is_root_index:
                errors.append(
                    f"{rel}: reserved file must not have frontmatter "
                    f"(only the bundle-root index.md may, for okf_version)."
                )
            continue

        # Non-reserved => concept document.
        concept_count += 1
        dirs_with_concepts.add(md.parent)

        if err:
            errors.append(f"{rel}: {err}")
            continue
        if not had_block or fm is None:
            errors.append(f"{rel}: missing YAML frontmatter block.")
            continue
        if not fm.get("type"):
            errors.append(f"{rel}: missing required non-empty 'type' field.")
        for k in RECOMMENDED_KEYS:
            if not fm.get(k):
                warnings.append(f"{rel}: missing recommended '{k}' field.")

        # Broken-link scan (informational).
        body = text.split(_DELIM, 2)[-1] if had_block else text
        for m in _LINK_RE.finditer(body):
            tgt = resolve_link(m.group(1), md, root)
            if tgt is None:
                continue
            if tgt.suffix == "" and tgt.is_dir():
                tgt = tgt / "index.md"
            if not tgt.exists():
                warnings.append(
                    f"{rel}: broken internal link -> {m.group(1)}"
                )

    for d in sorted(dirs_with_concepts - dirs_with_index):
        warnings.append(
            f"{d.relative_to(root) or '.'}/: has concept docs but no index.md."
        )

    if args.strict:
        errors.extend(warnings)
        warnings = []

    print(f"OKF bundle: {root}")
    print(f"  concepts: {concept_count}")
    print(f"  errors:   {len(errors)}")
    print(f"  warnings: {len(warnings)}")
    for w in warnings:
        print(f"  [warn]  {w}")
    for e in errors:
        print(f"  [ERROR] {e}")

    if errors:
        print("\nFAIL: bundle is not OKF-conformant.")
        return 1
    print("\nOK: bundle is OKF-conformant.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
