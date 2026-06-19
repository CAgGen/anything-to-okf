---
name: anything-to-okf
description: >-
  Convert files of ANY format — PDF, Word/.docx, PowerPoint/.pptx,
  Excel/.xlsx/.csv, HTML, Markdown, JSON/YAML, source code, plain text, images —
  into an Open Knowledge Format (OKF) bundle: a directory of markdown files with
  YAML frontmatter, cross-links, and index.md files, conformant to OKF v0.1. The
  actual concept-writing is delegated to the `claude` and `codex` CLIs. Use this
  skill whenever the user wants to turn documents, datasets, a folder of mixed
  files, a knowledge base, a spec, or an export into OKF, an "OKF bundle", a
  "knowledge bundle", or "Open Knowledge Format" — even if they just say
  "convert these to OKF" or "build a knowledge bundle from this folder". Do NOT
  use the Python enrichment agent from the knowledge-catalog repo; this skill is
  the standalone, CLI-driven path.
---

# Anything → OKF

Turn arbitrary source files into a conformant **Open Knowledge Format (OKF)**
bundle. OKF is just a directory of markdown files with YAML frontmatter, joined
by markdown cross-links and `index.md` listings — readable by humans, parseable
by agents, diffable in git. The full rules are in
[references/okf-spec.md](references/okf-spec.md); read that before planning.

The defining idea of this skill: **you plan, the CLIs write.** You (the
orchestrating agent) do the reasoning that needs judgment — extracting content,
deciding what the concepts are, naming and grouping them, choosing each `type`.
The grounded prose-writing of each concept is delegated to the `claude` and/or
`codex` CLIs via [scripts/convert_source.sh](scripts/convert_source.sh). The
deterministic mechanics — index generation and conformance checking — are
scripts, not LLM calls.

## When to use this

Any request to produce OKF / a "knowledge bundle" / "Open Knowledge Format" from
files or a folder: a pile of PDFs, a Word/Excel/PowerPoint export, a docs site,
a schema dump, a codebase, a Notion/Obsidian export, a single spec, etc. If the
input is a BigQuery dataset and the user specifically wants the reference Python
enrichment agent, that's a different tool — this skill is the standalone path.

## Workflow: Full Pipeline (with Cross-Table Concepts)

The skill now automatically detects and injects *cross-table relationships* — facts
that connect multiple concepts (e.g., a foreign key defined in one concept's docs,
but also injected into the related concept's overview). No manual link-building needed.

### 1. Discover and classify inputs

List the input file(s) or directory. Classify each by extension/MIME. If given a
URL or an archive, fetch/extract first. Create a scratch workspace:
`mkdir -p <bundle>/.okf-work` (extracted text lands here; it is not part of the
bundle).

### 2. Extract clean content per source

Turn every source into faithful text/markdown — see
[references/format-extraction.md](references/format-extraction.md) for the method
per format (office formats use the bundled `pdf`/`docx`/`pptx`/`xlsx` skills;
text/code/json are read directly; html via pandoc/WebFetch; images described
visually). Write each source's extracted text to
`<bundle>/.okf-work/<slug>.src.txt`.

The cardinal rule of extraction is **fidelity**: preserve exact column names,
types, enum values, formulas, IDs, and numbers; keep tables as tables and code
as code; never invent to fill a gap. Everything downstream inherits this
grounding (or this hallucination), so get it right here.

### 3. Plan the bundle (the enumeration step)

Before writing anything, decide the concept set and the tree. This is the step
that makes the bundle coherent rather than a flat dump:

- **One concept = one unit of knowledge.** A table, a dataset, an API endpoint,
  a metric, a business process/playbook, a glossary term, a source document, a
  code module. A single rich source often yields several concepts; several
  near-identical sources often collapse into one.
- **Canonicalize and dedupe.** If two sources describe the same thing under
  different names/acronyms, make ONE concept and mention the alternate names in
  the body — don't emit duplicates. Pick the most fully-spelled, kebab-case
  concept id.
- **Choose a directory structure** that mirrors how the knowledge groups
  (e.g. `tables/`, `datasets/`, `references/`, `playbooks/`). The layout is free;
  pick what aids navigation.
- **Assign each concept a `type`** — a short, self-explanatory, reused-across-
  like-concepts value (`BigQuery Table`, `API Endpoint`, `Metric`, `Playbook`,
  `Glossary Term`, `Document`, `Source File`, …). The index groups by `type`, so
  consistency matters.
- **Decide each concept's primary source(s)** so the writer is grounded in the
  right slice of extracted text.

Write this plan down (a short list of `concept-id → type → source file(s)`)
before generating.

### 4. Convert each concept via claude / codex (with concept extraction)

For each planned concept, call the dispatch script with its extracted source and
chosen metadata. The script builds an OKF-aware, grounding-disciplined prompt that
ALSO asks the model to extract any **cross-table facts** from the source (foreign
keys, metrics, relationships), writing both the concept `.md` AND a `.concepts.json` sidecar:

```bash
scripts/convert_source.sh \
  --source <bundle>/.okf-work/<slug>.src.txt \
  --out    <bundle>/<dir>/<concept-id>.md \
  --type   "BigQuery Table" \
  --title  "Customer Orders" \
  --id     tables/orders \
  --resource "https://.../tables/orders" \
  --engine auto \
  --instructions "Relate to /tables/customers.md via customer_id."
```

**Engine selection (`--engine`):**

- `auto` *(default)* — use `claude` if installed, else `codex`. Safe default.
- `claude` — force the `claude` CLI.
- `codex` — force the `codex` CLI.
- `both` — get **two independent drafts** (`<out>.claude.md` and
  `<out>.codex.md`). Then YOU reconcile them into the final `<out>`: take the
  union of *grounded* facts, keep one clean structure, and drop anything neither
  source supports. Use `both` for high-value or ambiguous concepts where a
  second model's pass is worth the extra cost/time.

> `codex` may not be installed on every machine. `auto` and `claude` work with
> just the `claude` CLI; `codex`/`both` require `codex` on PATH (the script
> errors clearly if it's missing). You can also write a concept directly by hand
> for trivial cases — but routing through the script is the intended path and is
> what keeps grounding consistent across a large bundle.

You can fan out: run several `convert_source.sh` calls in parallel for
independent concepts. After generation, skim each concept for grounding (no
invented facts) and good structure; re-run with richer `--instructions` if a
concept came out thin or off.

### 5. Aggregate cross-table concepts (AUTOMATED)

After all concepts are generated, run the aggregation pipeline:

```bash
./scripts/build_bundle_with_concepts.sh <bundle> [--model <id>]
```

Or manually, step by step:

```bash
# (1) Collect all .concepts.json sidecars into one list
python3 scripts/collect_concepts.py <bundle>

# (2) Run ONE smart LLM pass to merge/connect concepts
python3 scripts/aggregate_concepts.py <bundle> --model claude-opus-4-8

# (3) Inject cross-references back into each concept's .md
python3 scripts/inject_shared_concepts.py <bundle>
```

**What happens:**

- Each `.concepts.json` sidecar contains facts the model extracted (FK, metrics, relationships)
- `collect_concepts.py` deduplicates them across all concepts
- `aggregate_concepts.py` runs an LLM merge pass that:
  - Folds near-duplicates (same fact, different wording)
  - **Connects facts across documents** — e.g., if one concept says "customer_id is FK" and another says "it points to customers", this pass merges them into one complete fact
  - Drops pure duplicates
- `inject_shared_concepts.py` adds a `# Cross-references` section to each concept, listing all relationships that involve it (bidirectionally)

**Bidirectional linkage:** A foreign-key relationship between orders and customers is automatically added to BOTH the orders and customers overviews, even if only one source document mentions it.

**No manual linking needed** — the system infers relationships from the sources and distributes them intelligently.

### 6. Generate indexes (deterministic)

Done automatically by `build_bundle_with_concepts.sh`, but can be run standalone:

```bash
python3 scripts/generate_indexes.py <bundle>
```

This writes an `index.md` in every directory, grouping concepts by `type` and
listing subdirectories — the progressive-disclosure layer. Run it AFTER all
concepts exist so it reflects the final tree. Don't hand-write indexes.

### 7. Validate (deterministic)

Done automatically by `build_bundle_with_concepts.sh`, but can be run standalone:

```bash
python3 scripts/validate_bundle.py <bundle>
```

Fix every hard `[ERROR]` (missing/unparseable frontmatter, missing `type`,
stray frontmatter in `index.md`). `[warn]` items (missing recommended fields,
broken links, missing index) are spec-tolerated — address them when it improves
the bundle, but they don't block conformance. Use `--strict` only when the user
wants a "complete" bundle with no soft issues.

### 8. Clean up and report

Bundle is ready. Report: path, concept count, cross-table relationships detected,
validation status.

---

## After the Initial Generation: Continuous Refinement (Phase 2+)

Once Phase 1 completes, the user has a working OKF bundle. But it may not be perfect yet.
The skill now supports interactive improvement **without re-extracting sources**:

### Phase 2: Refinement — Free-text iteration

**In the chat:** User says anything like:

- "Make the orders overview more concise"
- "Add an Examples section with sample queries"
- "Clarify what customer_id means"

**Skill does:**
1. Loads the current concept `.md`
2. Sends it + user request to Claude for refinement
3. Rewrites just that section (keeps metadata, other sections intact)
4. Records the change in `refine_session.json`

**No source re-extraction.** The aggregated concepts stay the same;
only the generated markdown is edited. Supports unlimited iteration rounds.

**Commands:** Ask for any change to any concept; the skill tracks history.

### Phase 3: Evaluation — Quality scoring

**In the chat:** User says:

- "Score this bundle"
- "How good is it?"
- "Evaluate the concepts"

**Skill does:**
1. Runs `python3 scripts/evaluate_bundle.py <bundle>`
2. Reports:
   - **Structural Validity** (99/100): all YAML is valid, required fields present
   - **Concept Coverage** (12 concepts): how many you have
   - **Cross-Reference Completeness** (100%): bidirectional links present
   - **Overall Score** (99/100)

**Future:** Golden-based metrics (hallucination check, concept recall, consistency).

**Commands:** Ask for a score; skill reports back with a scorecard.

### Phase 4: Feedback — User proposals

**In the chat:** User provides feedback in JSON format or describes it naturally:

- "Add this detail to the schema section"
- "The lineage is missing [info]"
- (or upload a `feedback.json` with detailed proposals)

**Skill does:**
1. Reads feedback proposals
2. For each affected concept:
   - Loads current markdown
   - Calls Claude with feedback as additional context
   - Rewrites to incorporate feedback
   - Saves new version
3. Reports what changed

**Feedback is ADDITIVE:** Never removes or overwrites existing content;
only enhances based on user input.

**Commands:** Describe what to improve; skill refines the concepts.

---

## Complete Example Journey

```
User: "Convert my sales.csv, customers.json, and schema-doc.md to OKF"
→ Skill runs Phase 1: generates bundle with cross-table concepts
→ Bundle: 12 concepts, bidirectional FK links, all validated ✅

User: "The orders overview is too wordy"
→ Skill runs Phase 2: rewrites that concept, records change
→ Updated orders.md (shorter, clearer)

User: "Score it"
→ Skill runs Phase 3: evaluation report
→ Structural Validity: 99/100, Cross-References: 100%, Overall: 98/100

User: "Add info about cascade delete on the customer FK"
→ Skill runs Phase 4: feedback → updates schema section
→ orders.md now includes cascade semantics

User: "Final score?"
→ Skill re-evaluates: Overall 100/100 ✅

User: "Done! Export it"
→ Skill outputs final bundle (ready for version control, Obsidian, Hugo, etc.)
```

---

## Key Properties

**Phase 1 (Generation):** Extracts sources → generates concepts → aggregates relationships
**Phase 2 (Refinement):** Free-text iteration on generated markdown (no re-extraction)
**Phase 3 (Evaluation):** Quality metrics (structural + future: judge-based)
**Phase 4 (Feedback):** User-provided context → concept re-refinement

All four phases are part of ONE continuous dialogue in the skill, not separate tools.

## Grounding and quality rules (these make or break the output)

The whole value of an OKF bundle is that it is *trustworthy* — an agent or human
should be able to rely on it without re-reading the sources. So:

- **Never invent.** Every statement in a concept must trace to its source. If
  the source doesn't say it, it doesn't go in. Thin source → short concept;
  that's correct, not a failure. Padding with plausible generalities is the
  worst outcome.
- **Capture meaning, not just names.** Define what each column/field/term *is*
  and its role — don't list a bare `name: type`. Quote specific values,
  qualifiers ("null when there's no accepted answer"), enum meanings, and
  formulas verbatim.
- **Prefer structure.** Tables, lists, fenced code, and conventional headings
  (`# Schema`, `# Examples`, `# Citations`) beat prose for retrieval.
- **Keep provenance.** Record source URLs/filenames as `resource` and/or
  numbered `# Citations`. Keep real links verbatim; drop dead local-path links.

## Files in this skill

**Reference docs:**
- [references/okf-spec.md](references/okf-spec.md) — condensed OKF v0.1 rules.
  Read before planning.
- [references/format-extraction.md](references/format-extraction.md) — how to
  extract clean content from each input format. Read in step 2.

**Core conversion:**
- [scripts/convert_source.sh](scripts/convert_source.sh) — convert one source
  to one concept via `claude`/`codex`. Also extracts `<CONCEPTS>` JSON block
  to a `.concepts.json` sidecar (step 4).

**Cross-table concepts (Phase 1):**
- [scripts/collect_concepts.py](scripts/collect_concepts.py) — gather all
  `.concepts.json` sidecars and deduplicate (step 5.1).
- [scripts/aggregate_concepts.py](scripts/aggregate_concepts.py) — run ONE
  smart LLM merge pass to connect and fold cross-table facts (step 5.2).
- [scripts/inject_shared_concepts.py](scripts/inject_shared_concepts.py) —
  add `# Cross-references` sections to each concept, linking related concepts
  bidirectionally (step 5.3).
- [scripts/build_bundle_with_concepts.sh](scripts/build_bundle_with_concepts.sh) —
  orchestrate the full pipeline (steps 5-7 in one go).

**Refinement, Evaluation, Feedback (Phase 2-4):**
- [scripts/refine_session.py](scripts/refine_session.py) — manage refinement
  session state (`refine_session.json`), track change history, support rollback
  (Phase 2).
- [scripts/evaluate_bundle.py](scripts/evaluate_bundle.py) — run quality metrics
  (structural validity, concept coverage, cross-reference completeness); extensible
  for judge-based checks (Phase 3).
- [scripts/apply_feedback.py](scripts/apply_feedback.py) — load user feedback
  proposals (JSON format) and re-refine affected concepts via Claude (Phase 4).

**Index and validation:**
- [scripts/generate_indexes.py](scripts/generate_indexes.py) — generate all
  `index.md` files (step 6).
- [scripts/validate_bundle.py](scripts/validate_bundle.py) — check OKF
  conformance (step 7).
