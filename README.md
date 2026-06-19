# anything-to-okf — Convert Any File Format to Open Knowledge Format

**Transform your documents, data, and code into a beautiful, linked knowledge bundle — no vendor lock-in, pure markdown.**

Convert **any file format** (CSV, PDF, Word, JSON, Markdown, code) into **Open Knowledge Format (OKF)** bundles. Automatically detect and inject cross-table relationships. Iteratively refine, evaluate quality, and incorporate feedback — all in conversation with Claude.

Perfect for:
- 📊 Building knowledge bases from mixed sources
- 🔗 Creating linked data catalogs (sales data, schemas, documentation)
- 🤖 Feeding AI agents structured, portable knowledge
- 📝 Publishing to Obsidian, MkDocs, Hugo, or git
- 🔄 Enriching existing data with AI-powered analysis

---

## 🚀 Quick Start (< 5 minutes)

### 1. Say what you want

```
User: "Convert my sales folder to OKF. I have orders.csv, customers.json, and a schema doc."
```

### 2. Watch it build your bundle

The skill will:
- ✅ Extract content from all formats
- ✅ Auto-detect cross-table relationships (foreign keys, metrics)
- ✅ Bidirectionally inject links (no manual linking needed)
- ✅ Generate `index.md` files for navigation
- ✅ Validate against OKF spec

### 3. Refine interactively

```
User: "Make the orders overview more concise"
User: "Add an Examples section with queries"
User: "Score the bundle"
User: "Add this detail about customer tiers"
```

**No re-extraction needed.** The skill edits generated markdown on the fly.

### 4. Export anywhere

Your bundle is **plain markdown** — portable and ready for:
- Git (version control, diffs, PRs)
- Obsidian / MkDocs / Hugo / Notion
- LLM context (just load the .md files)
- Dataplex (convert to mdcode via kcmd if needed)

---

## ✨ What Makes This Different

| Aspect | knowledge-catalog | anything-to-okf |
|--------|-------------------|-----------------|
| **Input formats** | BigQuery only | Any format (CSV, PDF, JSON, code…) |
| **LLM** | Google Vertex Gemini | Claude (or codex) |
| **Output** | Dataplex mdcode (vendor lock) | OKF markdown (portable) |
| **Refinement** | Interactive REPL | Conversation-driven (Phase 2) |
| **Quality metrics** | Golden-based | Deterministic + extensible (Phase 3) |
| **User feedback** | Proposals → override | JSON feedback fusion (Phase 4) |
| **Architecture** | Full ADK + Dataplex | Pure Python/Bash, runs anywhere |
| **Source re-extraction** | Not needed (Phases 2-4) | Not needed (Phases 2-4) ✅ |

**TL;DR:** Same power as knowledge-catalog's enrichment engine, but format-agnostic, lighter-weight, and conversation-driven inside Claude Code.

---

## 📋 How It Works: 4 Phases

### **Phase 1: Generation** (Automatic)

Extract, deduplicate, and intelligently inject cross-table relationships.

```
Input: CSV + JSON + Markdown
  ↓
extract_concepts.py   → JSON blocks for each source
collect_concepts.py   → Deduplicate across files
aggregate_concepts.py → LLM merge pass (connect fragmented facts)
inject_shared_concepts.py → Bidirectional links
  ↓
Output: OKF bundle with auto-detected relationships
```

**Example:** A CSV with `customer_id` column + a JSON schema + a doc saying "orders.customer_id → customers.id" → the FK appears in **both** orders and customers overviews automatically.

### **Phase 2: Refinement** (Interactive)

Free-text iteration on generated markdown — no source re-extraction.

```
User: "Make orders shorter"
  ↓ (loads current orders.md, calls claude with refinement request)
Output: Refined orders.md (saved)
```

Commands: `"Make X more concise"`, `"Add Examples"`, `"Show history"`, `"Revert"`

### **Phase 3: Evaluation** (Quality Scoring)

Metrics dashboard for your bundle.

```
Output:
  Structural Validity: 99/100 ✅
  Concept Coverage: 12 concepts
  Cross-References: 100% (all bidirectional)
  Overall Score: 99/100 ✅
```

Future: Judge-based metrics (hallucination, recall, consistency).

### **Phase 4: Feedback** (User Overrides)

Incorporate domain knowledge without re-extracting.

```json
{
  "proposals": [
    {
      "concept_id": "tables/orders",
      "feedback": "Clarify that total_usd is 0.00 when refunded",
      "priority": "high"
    }
  ]
}
```

The skill re-refines with feedback as additional context. Additive only — never removes existing content.

---

## 🎯 Real-World Example

**Scenario:** You have sales data in three formats. You want a searchable knowledge base.

### Sources:
- `orders.csv` — 5 columns, no docs
- `customers.json` — schema with FK info
- `schema-relationships.md` — documents the 1:N relationship + revenue metric

### Commands:
```
1. User: "Build an OKF bundle from this sales data"
   → Skill Phase 1: generates bundle (12 concepts, cross-table FKs detected)

2. User: "Too verbose, shorten the schema sections"
   → Skill Phase 2: refines (no re-extraction)

3. User: "Score it"
   → Skill Phase 3: "98/100 ✅"

4. User: "Add that the tier affects SLA"
   → Skill Phase 4: updates customer schema with SLA info

5. User: "Export to Obsidian"
   → Skill outputs: ready to drag into Obsidian vault
```

---

## 📊 Feature Breakdown

### Core Capabilities

- ✅ **Format-agnostic**: CSV, JSON, PDF, Word, HTML, Markdown, code, anything
- ✅ **Cross-table concepts**: Auto-detect & bidirectionally inject relationships
- ✅ **Smart deduplication**: LLM merge pass connects fragmented facts
- ✅ **Session-based refinement**: Iterate without re-extracting sources
- ✅ **Quality evaluation**: Structural + coverage + cross-reference metrics
- ✅ **User feedback fusion**: JSON proposals → concept enhancement
- ✅ **Portable output**: Plain markdown, no vendor lock-in
- ✅ **Git-friendly**: Diffs, PRs, version history on OKF bundles

### What It Doesn't Do (By Design)

- ❌ Auto-discover from schema reflection alone (requires sources to state relationships)
- ❌ Infer cardinality beyond what sources state
- ❌ Resolve conflicting facts (picks one, logs it)

---

## 📚 Documentation

Full guides for each phase:

| Document | What It Covers |
|----------|--------|
| **[SKILL.md](SKILL.md)** | Main instructions + complete workflow + all commands |
| **[PHASE_1_SUMMARY.md](PHASE_1_SUMMARY.md)** | Cross-table concepts in depth |
| **[PHASES_2-4_SUMMARY.md](PHASES_2-4_SUMMARY.md)** | Refinement, evaluation, feedback architecture |
| **[references/okf-spec.md](references/okf-spec.md)** | OKF v0.1 format spec (read before planning) |
| **[references/cross-table-concepts.md](references/cross-table-concepts.md)** | Deep dive: extraction, aggregation, injection |
| **[references/format-extraction.md](references/format-extraction.md)** | How to extract from each file type |
| **[references/refinement-evaluation-feedback.md](references/refinement-evaluation-feedback.md)** | Phases 2-4 workflows + command reference |

---

## 🛠️ Architecture

```
scripts/
├── convert_source.sh           # Convert one source to one concept (+ extract concepts)
├── collect_concepts.py         # Deduplicate .concepts.json sidecars
├── aggregate_concepts.py       # LLM merge pass (connect facts)
├── inject_shared_concepts.py   # Bidirectional relationship injection
├── build_bundle_with_concepts.sh # One-shot orchestration (Phase 1)
├── refine_session.py           # Session state management (Phase 2)
├── evaluate_bundle.py          # Quality metrics (Phase 3)
├── apply_feedback.py           # User proposals fusion (Phase 4)
├── generate_indexes.py         # Auto-generate index.md files
└── validate_bundle.py          # Check OKF conformance

references/
├── okf-spec.md                 # OKF v0.1 specification
├── cross-table-concepts.md     # Phase 1 deep dive
├── format-extraction.md        # Format-specific extraction
└── refinement-evaluation-feedback.md # Phases 2-4 guide

evals/
├── evals.json                  # Test cases + assertions
└── fixtures/                   # Test data (CSV, JSON, Markdown)
```

---

## 💡 Use Cases

### **1. Data Catalog Enrichment**
Convert your data warehouse metadata + documentation into a searchable, linked OKF bundle.

**Input:** BigQuery schema dump + Looker docs + internal runbooks  
**Output:** Unified catalog (git-backed, agent-readable)

### **2. API/SDK Documentation**
Auto-generate API docs that link to schema, examples, and integration guides.

**Input:** OpenAPI spec + code samples + error docs  
**Output:** Linked knowledge bundle

### **3. Product Knowledge Base**
Turn product specs, customer FAQs, and design docs into a coherent knowledge graph.

**Input:** Feature specs + FAQ markdown + design PDFs  
**Output:** Internal wiki (Obsidian/MkDocs-ready)

### **4. Code-as-Knowledge**
Document your codebase structure, dependencies, and cross-module relationships.

**Input:** Source code + architecture docs + dependency graph  
**Output:** Navigable code knowledge base

---

## 🚀 Getting Started

### Installation

This is a Claude Code **skill**. No installation needed — just use it in Claude Code:

1. Copy `.claude/skills/anything-to-okf/` into your Claude Code skills directory
2. Or reference it from this repo: `https://github.com/<user>/anything-to-okf`

### First Run

```
Open Claude Code
Say: "Convert my docs/sales folder to OKF"
Skill runs Phase 1 → You get a bundle
Continue in chat:
  • "Make the orders concept shorter"
  • "Score the bundle"
  • "Add this detail..."
```

### View the Bundle

```bash
# After skill generates the bundle
cd <bundle-output-dir>
ls -la  # See .md files
cat tables/orders.md  # Read a concept
```

---

## 📖 What Is OKF?

**Open Knowledge Format** is a vendor-neutral markdown+YAML standard for knowledge bundles.

Key properties:
- **Human-readable:** Just markdown files in a directory
- **Agent-readable:** YAML frontmatter + standardized cross-links
- **Portable:** No lock-in, works with git/Obsidian/MkDocs/etc.
- **Minimal spec:** Only requires `type` field — everything else optional

Read [okf-spec.md](references/okf-spec.md) for details.

---

## 🤝 Contributing

Found a bug? Want to add a feature? Contributions welcome!

1. Fork this repo
2. Make your changes in a branch
3. Submit a PR with a clear description

Areas where help is welcome:
- Additional file format extractors (Avro, Protobuf, SQLAlchemy models)
- Judge-based metrics for Phase 3 (hallucination detection)
- Golden-based evaluation framework
- Integration with other knowledge platforms

---

## 📄 License

MIT License — see [LICENSE](LICENSE) file.

---

## 💬 Questions?

- Read the [documentation](#-documentation) for detailed guides
- Check [evals/evals.json](evals/evals.json) for example test cases
- Open an issue on GitHub

---

## 🎓 Learn More

- **[Open Knowledge Format v0.1 Spec](references/okf-spec.md)** — The full spec (short read)
- **[knowledge-catalog](https://github.com/GoogleCloudPlatform/knowledge-catalog)** — The inspiration (Google's agent for Dataplex)
- **[Claude API](https://claude.ai/code)** — Build your own skills

---

**Built with ❤️ for knowledge workers, data engineers, and AI enthusiasts.**

Made to complement knowledge-catalog with a lighter, format-agnostic alternative for anyone building portable knowledge bundles.
