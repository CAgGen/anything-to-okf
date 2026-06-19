#!/usr/bin/env python3
"""Apply user feedback proposals to a bundle, re-generating affected concepts.

Feedback proposals are JSON describing desired changes:
{
  "proposals": [
    {
      "concept_id": "tables/orders",
      "target_section": "# Schema",  // optional: which section to enhance
      "feedback": "Add column meanings inline with the table",
      "priority": "high"
    }
  ]
}

This script:
1. Loads proposals
2. For each concept, prepends proposal as additional context to writer prompt
3. Re-generates the concept .md (via claude CLI with --instructions)
4. Records applied feedback in refine_session.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


class FeedbackApplier:
    """Apply user feedback proposals to bundle concepts."""

    def __init__(self, bundle_root: Path):
        self.bundle_root = bundle_root.resolve()

    @staticmethod
    def load_proposals(proposal_file: Path) -> list[dict]:
        """Load feedback proposals from JSON file."""
        try:
            data = json.loads(proposal_file.read_text(encoding="utf-8"))
            return data.get("proposals", []) if isinstance(data, dict) else []
        except json.JSONDecodeError:
            return []

    def apply_proposal_to_concept(
        self, concept_id: str, proposal: dict, model: str = "claude-opus-4-8"
    ) -> bool:
        """
        Re-generate a concept with feedback as additional context.

        This calls claude CLI with the concept's aggregated content + feedback prompt.
        """
        md_path = self.bundle_root / f"{concept_id}.md"
        if not md_path.exists():
            print(f"Concept not found: {concept_id}")
            return False

        current_content = md_path.read_text(encoding="utf-8")
        feedback_text = proposal.get("feedback", "")
        target_section = proposal.get("target_section", "")

        # Build the refinement prompt.
        prompt = f"""You are refining an existing OKF concept markdown.

EXISTING CONTENT:
{current_content}

USER FEEDBACK REQUEST:
{feedback_text}

{f'Target section: {target_section}' if target_section else '(Apply to the whole document)'}

Instructions:
- Preserve all existing content (do not remove or shorten)
- Apply the user's feedback as an enhancement or clarification
- Ground only in what the existing content states; do NOT invent new facts
- Maintain OKF frontmatter as-is (do NOT change type, title, etc.)

Output ONLY the refined markdown (frontmatter + body). No explanation.
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
                print(f"Claude call failed: {result.stderr}")
                return False

            refined = result.stdout.strip()
            if refined:
                md_path.write_text(refined + "\n", encoding="utf-8")
                print(f"✓ Applied feedback to {concept_id}")
                return True
        except subprocess.TimeoutExpired:
            print(f"Claude call timed out for {concept_id}")
        except FileNotFoundError:
            print("claude CLI not found on PATH")

        return False

    def apply_all(
        self, proposal_file: Path, model: str = "claude-opus-4-8"
    ) -> int:
        """Load proposals and apply all to affected concepts."""
        proposals = self.load_proposals(proposal_file)
        if not proposals:
            print(f"No proposals found in {proposal_file}")
            return 1

        applied = 0
        for proposal in proposals:
            concept_id = proposal.get("concept_id", "").strip()
            if not concept_id:
                continue
            if self.apply_proposal_to_concept(concept_id, proposal, model):
                applied += 1

        print(f"\nApplied {applied}/{len(proposals)} proposals")
        return 0 if applied > 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply feedback proposals to bundle.")
    ap.add_argument("bundle", help="Bundle root directory")
    ap.add_argument("--proposals", required=True, help="Feedback proposals JSON file")
    ap.add_argument(
        "--model",
        default="claude-opus-4-8",
        help="Claude model to use",
    )
    args = ap.parse_args()

    bundle = Path(args.bundle).resolve()
    proposals_file = Path(args.proposals).resolve()

    if not bundle.is_dir():
        sys.stderr.write(f"Not a directory: {bundle}\n")
        return 2

    if not proposals_file.exists():
        sys.stderr.write(f"Proposals file not found: {proposals_file}\n")
        return 2

    applier = FeedbackApplier(bundle)
    return applier.apply_all(proposals_file, args.model)


if __name__ == "__main__":
    raise SystemExit(main())
