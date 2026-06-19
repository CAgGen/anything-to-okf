#!/usr/bin/env bash
# Build an OKF bundle WITH cross-table concept aggregation and injection.
#
# This orchestrates the full workflow:
#   1. Extract source content (user responsibility, then call convert_source.sh per concept)
#   2. collect_concepts.py - gather all .concepts.json sidecars
#   3. aggregate_concepts.py - LLM merge pass (smart dedup + connection)
#   4. inject_shared_concepts.py - add cross-references to each .md
#   5. generate_indexes.py - build directory indexes
#   6. validate_bundle.py - check conformance
#
# Assumes: all concept .md files are already generated (via convert_source.sh)
#          and their .concepts.json sidecars exist.
#
# Usage:
#   ./scripts/build_bundle_with_concepts.sh <bundle_dir> [--model <id>] [--strict]
#
set -euo pipefail

BUNDLE=""
MODEL="claude-opus-4-8"
STRICT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model) MODEL="$2"; shift 2;;
    --strict) STRICT="--strict"; shift;;
    *) BUNDLE="$1"; shift;;
  esac
done

[[ -z "$BUNDLE" ]] && { echo "Usage: $0 <bundle_dir> [--model <id>] [--strict]" >&2; exit 1; }
[[ -d "$BUNDLE" ]] || { echo "Not a directory: $BUNDLE" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE="$(cd "$BUNDLE" && pwd)"

echo "========================================"
echo "Building OKF Bundle WITH Concepts"
echo "========================================"
echo "Bundle: $BUNDLE"
echo "Model: $MODEL"
echo

# Step 1: Collect all .concepts.json sidecars.
echo "[1/5] Collecting concepts from sidecars..."
python3 "$SCRIPT_DIR/collect_concepts.py" "$BUNDLE" \
  || { echo "FAILED: collect_concepts.py" >&2; exit 1; }
echo

# Step 2: Aggregate via LLM merge pass.
echo "[2/5] Aggregating concepts (LLM merge pass)..."
python3 "$SCRIPT_DIR/aggregate_concepts.py" "$BUNDLE" --model "$MODEL" \
  || { echo "FAILED: aggregate_concepts.py" >&2; exit 1; }
echo

# Step 3: Inject cross-references back into .md files.
echo "[3/5] Injecting cross-references into concepts..."
python3 "$SCRIPT_DIR/inject_shared_concepts.py" "$BUNDLE" \
  || { echo "FAILED: inject_shared_concepts.py" >&2; exit 1; }
echo

# Step 4: Generate indexes.
echo "[4/5] Generating index.md files..."
python3 "$SCRIPT_DIR/generate_indexes.py" "$BUNDLE" \
  || { echo "FAILED: generate_indexes.py" >&2; exit 1; }
echo

# Step 5: Validate.
echo "[5/5] Validating bundle conformance..."
python3 "$SCRIPT_DIR/validate_bundle.py" "$BUNDLE" $STRICT \
  || { echo "FAILED: validate_bundle.py" >&2; exit 1; }
echo

echo "========================================"
echo "✅ Bundle complete with cross-table concepts"
echo "========================================"
echo "Output: $BUNDLE"
echo "Concepts aggregated at: $BUNDLE/okf-work/aggregated_concepts.json"
