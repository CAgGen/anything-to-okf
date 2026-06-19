#!/usr/bin/env bash
# Convert ONE extracted source into a single OKF concept document by delegating
# the writing to an LLM CLI — `claude` and/or `codex`.
#
# This is the engine that satisfies "convert via claude and codex": the
# orchestrating agent does the planning (which concepts exist, the tree, the
# `type` of each), then calls this script once per concept to do the grounded
# prose-writing. Keeping the write in a subprocess lets you fan out, pick an
# engine per concept, or get two independent drafts to reconcile.
#
# The source you pass in MUST already be plain text / markdown (extract office
# formats, PDFs, etc. first — see references/format-extraction.md). The model is
# told to ground STRICTLY in that text and not invent facts.
#
# Usage:
#   convert_source.sh --source <extracted.txt> --out <concept.md> \
#       --type "<TYPE>" [--title "<TITLE>"] [--id <concept-id>] \
#       [--resource <uri>] [--engine claude|codex|both|auto] [--model <id>] \
#       [--instructions "<extra grounding notes>"]
#
# Engines:
#   auto   (default) use claude if present, else codex.
#   claude use the `claude` CLI (claude -p).
#   codex  use the `codex` CLI (codex exec).
#   both   produce TWO drafts: <out>.claude.md and <out>.codex.md, plus a
#          merge-prompt note. The orchestrating agent then reconciles them into
#          <out> (best-of-both: union of grounded facts, one clean structure).
#
# Output: the concept markdown is written to --out (frontmatter + body), with
# any stray ``` code fences the model may wrap around the whole doc stripped.
set -euo pipefail

SOURCE="" OUT="" TYPE="" TITLE="" CID="" RESOURCE="" ENGINE="auto" MODEL="" EXTRA=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source) SOURCE="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    --type) TYPE="$2"; shift 2;;
    --title) TITLE="$2"; shift 2;;
    --id) CID="$2"; shift 2;;
    --resource) RESOURCE="$2"; shift 2;;
    --engine) ENGINE="$2"; shift 2;;
    --model) MODEL="$2"; shift 2;;
    --instructions) EXTRA="$2"; shift 2;;
    *) echo "Unknown arg: $1" >&2; exit 2;;
  esac
done

[[ -z "$SOURCE" || -z "$OUT" || -z "$TYPE" ]] && {
  echo "Required: --source, --out, --type" >&2; exit 2; }
[[ -f "$SOURCE" ]] || { echo "Source not found: $SOURCE" >&2; exit 2; }

TODAY="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
[[ -z "$TITLE" ]] && TITLE="$(basename "${CID:-$OUT}" .md)"

# Build the conversion prompt. The rules mirror the OKF spec + the grounding
# discipline of a knowledge-enrichment writer: faithful, structured, no padding.
read -r -d '' PROMPT <<EOF || true
You convert source material into ONE Open Knowledge Format (OKF) concept document.

OKF concept = a single UTF-8 markdown file with two parts:
1. A YAML frontmatter block delimited by --- on its own line, then a closing ---.
2. A markdown body.

Frontmatter to emit (quote any value containing a colon or special chars):
  type: ${TYPE}            # REQUIRED, keep exactly this value
  title: ${TITLE}
  description: <one-sentence summary of this concept>
  $( [[ -n "$RESOURCE" ]] && echo "resource: ${RESOURCE}" )
  tags: [<3-6 short lowercase tags grounded in the content>]
  timestamp: ${TODAY}

Body rules:
- Ground STRICTLY in the SOURCE below. Do NOT invent facts, owners, schemas,
  metrics, or relationships that the source does not state. If the source is
  thin, the body is short — never pad with plausible-sounding generalities.
- Prefer STRUCTURE over prose: headings (##), lists, tables, fenced code blocks.
  Structure helps both human readers and agent retrieval.
- Capture the MEANING of things, not just names: define key fields/columns/terms
  with their role, and quote specific values, formulas, and qualifiers verbatim.
- Conventional headings to use when applicable: "# Schema" (columns/fields),
  "# Examples" (usage), "# Citations" (external sources backing claims).
- Put external sources the body relies on under a final "# Citations" heading,
  numbered, as [n] [Title](URL). Keep source URLs verbatim; never fabricate one.
- You may reference sibling concepts with bundle-relative links like
  [name](/path/to/other.md) when the source implies a relationship.
${EXTRA:+
Extra grounding notes from the orchestrator:
${EXTRA}
}

CROSS-TABLE FACTS (optional):
After the body, extract any CROSS-TABLE facts this source explicitly states —
facts that connect two or more concepts/tables, or define a metric/grain/
source-of-truth spanning multiple concepts. Emit them as a <CONCEPTS> JSON block
(see below). If the source states no cross-table facts, output <CONCEPTS>[]</CONCEPTS>.

Each cross-table fact is:
  {
    "kind": "join|metric|relationship",
    "tables": ["concept_id_1", "concept_id_2"],
    "title": "short name of the relationship",
    "body": "1-3 sentences describing the fact, including specific keys/formulas"
  }

Example (if the source describes an orders-customers FK):
  <CONCEPTS>[
    {
      "kind": "join",
      "tables": ["orders", "customers"],
      "title": "Customer Orders FK",
      "body": "orders.customer_id is a foreign key into customers.id, establishing a 1:N relationship"
    }
  ]</CONCEPTS>

Rules for <CONCEPTS>:
- Extract ONLY facts the source explicitly states. Do NOT invent joins, keys, or formulas.
- Use the canonical concept IDs (e.g., 'tables/orders', not 'Orders Table').
- If you do not find any cross-table facts, output <CONCEPTS>[]</CONCEPTS>.
- This block MUST come after the body. Output nothing after </CONCEPTS>.

OUTPUT: emit ONLY:
  (1) The concept markdown (--- frontmatter block + body)
  (2) Followed by the <CONCEPTS>...</CONCEPTS> block

No preamble, no explanation, no surrounding code fences.

SOURCE (filename: $(basename "$SOURCE")):
$(cat "$SOURCE")
EOF

run_claude() {
  local out="$1"; local args=(-p)
  [[ -n "$MODEL" ]] && args+=(--model "$MODEL")
  printf '%s' "$PROMPT" | claude "${args[@]}" >"$out"
}

run_codex() {
  local out="$1"; local args=(exec)
  [[ -n "$MODEL" ]] && args+=(--model "$MODEL")
  # codex exec reads the prompt as a positional arg; pass it explicitly.
  codex "${args[@]}" "$PROMPT" >"$out"
}

# Strip a single outer ```...``` fence if the model wrapped the whole doc, and
# drop any leading prose before the first frontmatter delimiter. Also extract
# <CONCEPTS> block to a .concepts.json sidecar.
clean() {
  local f="$1"
  python3 - "$f" <<'PY'
import re, sys, json
p = sys.argv[1]
t = open(p, encoding="utf-8", errors="replace").read().strip()
m = re.match(r"^```[a-zA-Z]*\s*\n(.*)\n```$", t, re.S)
if m:
    t = m.group(1).strip()
# If the model emitted leading chatter before the frontmatter, cut to the
# first line that is exactly '---'.
if not t.startswith("---"):
    j = t.find("\n---\n")
    if j != -1:
        t = t[j + 1:].strip()
# Extract <CONCEPTS> block if present.
concepts = []
m = re.search(r"<CONCEPTS>(.*?)</CONCEPTS>", t, re.S)
if m:
    try:
        arr = json.loads(m.group(1).strip() or "[]")
        concepts = arr if isinstance(arr, list) else []
    except (ValueError, json.JSONDecodeError):
        pass
    # Remove the <CONCEPTS> block from the markdown.
    t = re.sub(r"<CONCEPTS>.*?</CONCEPTS>", "", t, flags=re.S).strip()
# Write the cleaned markdown (no concepts block).
open(p, "w", encoding="utf-8").write(t + "\n")
# Write concepts to a sidecar .concepts.json if any were found.
if concepts:
    concepts_path = p.replace(".md", ".concepts.json")
    with open(concepts_path, "w") as cf:
        json.dump(concepts, cf, indent=2, ensure_ascii=False)
PY
}

have() { command -v "$1" >/dev/null 2>&1; }

case "$ENGINE" in
  auto)
    if have claude; then ENGINE=claude
    elif have codex; then ENGINE=codex
    else echo "Neither claude nor codex is installed." >&2; exit 3; fi
    ;;
esac

case "$ENGINE" in
  claude)
    have claude || { echo "claude CLI not found." >&2; exit 3; }
    run_claude "$OUT"; clean "$OUT"
    echo "wrote $OUT (engine: claude)"
    ;;
  codex)
    have codex || { echo "codex CLI not found." >&2; exit 3; }
    run_codex "$OUT"; clean "$OUT"
    echo "wrote $OUT (engine: codex)"
    ;;
  both)
    have claude || { echo "claude CLI not found (needed for --engine both)." >&2; exit 3; }
    have codex  || { echo "codex CLI not found (needed for --engine both)." >&2; exit 3; }
    run_claude "${OUT}.claude.md"; clean "${OUT}.claude.md"
    run_codex  "${OUT}.codex.md";  clean "${OUT}.codex.md"
    echo "wrote ${OUT}.claude.md and ${OUT}.codex.md (engine: both)"
    echo "MERGE: read both drafts and reconcile into ${OUT} — take the union of"
    echo "grounded facts, keep ONE clean structure, drop anything not in the source."
    ;;
  *)
    echo "Unknown engine: $ENGINE" >&2; exit 2;;
esac
