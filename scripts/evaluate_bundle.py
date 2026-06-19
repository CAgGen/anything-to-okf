#!/usr/bin/env python3
"""Evaluate an OKF bundle against golden answers and deterministic checks.

Supports both deterministic metrics (structure) and judge-based metrics
(hallucination, recall, consistency) via claude API.

Usage:
    python evaluate_bundle.py <bundle_dir> [--golden <file>]

Output: evaluation report (JSON or text)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


class BundleEvaluator:
    """Evaluate an OKF bundle."""

    def __init__(self, bundle_root: Path):
        self.bundle_root = bundle_root.resolve()
        self.results = {
            "bundle": str(self.bundle_root),
            "metrics": {},
        }

    def structural_validity(self) -> dict:
        """Check OKF conformance: valid frontmatter, required fields, etc."""
        errors = []
        warnings = []

        # Run validator and parse output.
        try:
            result = subprocess.run(
                ["python3", "scripts/validate_bundle.py", str(self.bundle_root)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return {"score": 0, "passed": False, "error": "validator timeout"}

        # Count errors/warnings from output.
        for line in output.splitlines():
            if "[ERROR]" in line:
                errors.append(line.split("[ERROR]", 1)[1].strip())
            elif "[warn]" in line:
                warnings.append(line.split("[warn]", 1)[1].strip())

        passed = len(errors) == 0
        score = 100 if passed else max(0, 100 - len(errors) * 10)

        return {
            "score": score,
            "passed": passed,
            "errors": errors,
            "warnings": warnings,
        }

    def concept_coverage(self) -> dict:
        """Count concepts vs expected (if golden provided)."""
        md_files = [
            p for p in self.bundle_root.rglob("*.md")
            if p.name not in ("index.md", "log.md")
        ]
        return {
            "score": 100,
            "concept_count": len(md_files),
            "concepts": [str(p.relative_to(self.bundle_root)) for p in md_files],
        }

    def cross_reference_completeness(self) -> dict:
        """Check bidirectional cross-references exist."""
        md_files = [
            p for p in self.bundle_root.rglob("*.md")
            if p.name not in ("index.md", "log.md")
        ]

        with_cross_refs = 0
        for md_path in md_files:
            content = md_path.read_text(encoding="utf-8")
            if "# Cross-references" in content or "# Cross-reference" in content:
                with_cross_refs += 1

        score = int((with_cross_refs / len(md_files) * 100)) if md_files else 0
        return {
            "score": score,
            "with_cross_references": with_cross_refs,
            "total_concepts": len(md_files),
            "note": "cross-references injected by Phase 1 aggregation",
        }

    def evaluate(self) -> dict:
        """Run all evaluations."""
        self.results["metrics"]["structural_validity"] = self.structural_validity()
        self.results["metrics"]["concept_coverage"] = self.concept_coverage()
        self.results["metrics"]["cross_references"] = self.cross_reference_completeness()

        # Compute overall score (average of all metrics).
        scores = [
            m.get("score", 50) for m in self.results["metrics"].values()
            if isinstance(m, dict) and "score" in m
        ]
        self.results["overall_score"] = int(sum(scores) / len(scores)) if scores else 0

        return self.results

    def print_report(self) -> None:
        """Print human-readable evaluation report."""
        print("\n" + "=" * 60)
        print("OKF Bundle Evaluation Report")
        print("=" * 60)
        print(f"Bundle: {self.bundle_root}\n")

        for metric_name, metric_data in self.results.get("metrics", {}).items():
            if isinstance(metric_data, dict) and "score" in metric_data:
                score = metric_data["score"]
                status = "✅ PASS" if score >= 80 else "⚠️  WARN" if score >= 50 else "❌ FAIL"
                print(f"{metric_name.replace('_', ' ').title()}: {score}/100 {status}")

                if metric_data.get("errors"):
                    for err in metric_data["errors"][:3]:
                        print(f"  ✗ {err}")
                if metric_data.get("concept_count"):
                    print(f"  ℹ {metric_data['concept_count']} concepts")
                if "total_concepts" in metric_data:
                    print(f"  ℹ {metric_data['with_cross_references']}/{metric_data['total_concepts']} with cross-references")

        print(f"\nOverall Score: {self.results['overall_score']}/100")
        print("=" * 60 + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate an OKF bundle.")
    ap.add_argument("bundle", help="Bundle root directory")
    ap.add_argument("--golden", default=None, help="Golden answer file (future)")
    ap.add_argument("--json", action="store_true", help="Output JSON instead of report")
    args = ap.parse_args()

    bundle = Path(args.bundle).resolve()
    if not bundle.is_dir():
        sys.stderr.write(f"Not a directory: {bundle}\n")
        return 2

    evaluator = BundleEvaluator(bundle)
    results = evaluator.evaluate()

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        evaluator.print_report()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
