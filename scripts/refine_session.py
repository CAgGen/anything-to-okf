#!/usr/bin/env python3
"""Manage refinement sessions for interactive OKF bundle modification.

A refinement session allows users to iteratively improve a bundle through
free-text requests ("make orders more concise", "add lineage") without
re-extracting sources.

Session state: refine_session.json
- bundle_path: where the bundle is
- original_concepts: pre-refinement bundle content (for rollback/comparison)
- refinement_history: list of {request, timestamp, affected_files}
- context: shared grounding (sources, aggregated concepts, etc.)

Usage:
    python refine_session.py <bundle_dir> init  # Start a new session
    python refine_session.py <bundle_dir> apply <concept_id> <request>
    python refine_session.py <bundle_dir> show  # Show session history
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


class RefinementSession:
    """Manage interactive refinement of an OKF bundle."""

    def __init__(self, bundle_root: Path):
        self.bundle_root = bundle_root.resolve()
        self.session_file = self.bundle_root / "okf-work" / "refine_session.json"
        self.session_data = self._load_session()

    def _load_session(self) -> dict:
        """Load existing session or initialize empty."""
        if self.session_file.exists():
            try:
                return json.loads(self.session_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        return {
            "bundle_path": str(self.bundle_root),
            "created_at": datetime.utcnow().isoformat(),
            "refinement_history": [],
            "original_concepts": [],
        }

    def save_session(self) -> None:
        """Persist session state."""
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.session_file, "w") as f:
            json.dump(self.session_data, f, indent=2, ensure_ascii=False)

    def init(self) -> bool:
        """Initialize a new session, backing up original bundle."""
        if self.session_data.get("refinement_history"):
            print("Session already initialized (found refinement history)")
            return False

        # Snapshot all current .md concepts (pre-refinement state).
        md_files = sorted(
            p for p in self.bundle_root.rglob("*.md")
            if p.name not in ("index.md", "log.md")
        )
        self.session_data["original_concepts"] = {
            str(p.relative_to(self.bundle_root)): p.read_text(encoding="utf-8")
            for p in md_files
        }
        self.save_session()
        print(f"Session initialized: {len(md_files)} concept(s) backed up")
        return True

    def record_refinement(
        self, request: str, affected_files: list[str]
    ) -> None:
        """Log a refinement turn."""
        entry = {
            "request": request,
            "timestamp": datetime.utcnow().isoformat(),
            "affected_files": affected_files,
        }
        self.session_data["refinement_history"].append(entry)
        self.save_session()

    def show_history(self) -> None:
        """Display refinement history."""
        if not self.session_data.get("refinement_history"):
            print("No refinement history yet")
            return
        for i, turn in enumerate(self.session_data["refinement_history"], 1):
            print(f"\nTurn {i}: {turn['timestamp']}")
            print(f"  Request: {turn['request']}")
            print(f"  Modified: {', '.join(turn['affected_files'])}")

    def get_original_concept(self, concept_id: str) -> str | None:
        """Get the pre-refinement content of a concept for comparison."""
        rel_path = f"{concept_id}.md"
        return self.session_data.get("original_concepts", {}).get(rel_path)


def main() -> int:
    ap = argparse.ArgumentParser(description="Manage OKF refinement sessions.")
    ap.add_argument("bundle", help="Bundle root directory")
    ap.add_argument(
        "command",
        choices=["init", "show"],
        help="init: start new session; show: display history",
    )
    args = ap.parse_args()

    bundle = Path(args.bundle).resolve()
    if not bundle.is_dir():
        sys.stderr.write(f"Not a directory: {bundle}\n")
        return 2

    session = RefinementSession(bundle)

    if args.command == "init":
        return 0 if session.init() else 1
    elif args.command == "show":
        session.show_history()
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
