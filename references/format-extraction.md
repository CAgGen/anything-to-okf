# Extracting clean content from any input format

The conversion engine (`scripts/convert_source.sh` → claude/codex) only reasons
well over **plain text or markdown**. So the first job is always: turn each
source file into faithful text/markdown, preserving structure (headings, tables,
lists, code) and capturing real values — without inventing anything.

Pick the lightest reliable method per format. The goal is fidelity, not
prettiness: a table in the source should survive as a markdown table; a column
list should survive as a list; numbers and identifiers must be exact.

## Office documents → use the bundled Anthropic skills

These formats have dedicated skills already available in this environment. Use
them to read/extract; do not hand-roll parsers.

| Format            | Extension(s)        | Use skill        |
|-------------------|---------------------|------------------|
| Word              | `.docx`             | `docx`           |
| PowerPoint        | `.pptx`             | `pptx`           |
| Excel / CSV / TSV | `.xlsx .xlsm .csv .tsv` | `xlsx`       |
| PDF               | `.pdf`              | `pdf`            |

For `.pdf` that is scanned (image-only), the `pdf` skill covers OCR. For
spreadsheets, capture sheet names, headers, and representative rows/values — each
sheet (or logical table) is usually its own concept.

## Already-textual formats → read directly

| Format              | Extension(s)                          | Handling |
|---------------------|---------------------------------------|----------|
| Markdown            | `.md .markdown`                       | Read as-is; it may already be near-OKF (just needs frontmatter + structure). |
| Plain text          | `.txt .rst .org`                      | Read directly. |
| Structured data     | `.json .yaml .yml .toml .xml`         | Read; summarize the schema/shape and key entries. A config or schema file often maps to one concept describing it. |
| Delimited           | `.csv .tsv`                           | Small files: read directly. Large: use the `xlsx` skill. |
| Source code         | `.py .ts .js .go .java .sql .sh ...`  | Read the file(s); describe purpose, public interface, key types/functions, and how it's used. A module/package usually maps to one concept. |
| Notebooks           | `.ipynb`                              | Read cells + outputs (Read tool renders these). |

## HTML and web pages

- Local `.html`/`.htm`: convert to markdown. If `pandoc` is available,
  `pandoc -f html -t gfm file.html` is reliable; otherwise read and extract the
  main content, dropping nav/boilerplate.
- A URL the user provides: fetch it (WebFetch), keep the title and main content,
  and record the URL as the concept's `resource` and/or a `# Citations` entry.

## Images and diagrams

- `.png .jpg .jpeg .gif .webp`: the Read tool shows images visually — describe
  the meaningful content (text, diagram structure, data in a chart) faithfully.
  Don't guess at illegible details.

## Archives / directories

- `.zip .tar .tgz`: extract first, then treat the contents as a directory of
  inputs.
- A directory of mixed files: process each file, and let the directory structure
  inform the bundle's structure when it's meaningful.

## Extraction discipline (applies to every format)

- **Faithful over fluent.** Preserve exact column names, types, enum values,
  formulas, IDs, dates, and numbers. When unsure, quote rather than paraphrase.
- **Keep structure.** Tables → markdown tables. Field lists → lists. Code →
  fenced blocks. Headings → headings. Structure is what makes the result useful
  to downstream agents.
- **Keep provenance.** Note the source filename/URL — it becomes the concept's
  `resource` and/or a `# Citations` entry so claims are traceable.
- **Don't fill gaps.** If the source doesn't state an owner, SLA, lineage, or
  meaning, leave it out. Never invent to make a concept look complete.

## Where extraction output goes

Write each source's extracted text to a scratch file (e.g.
`.okf-work/<concept-id>.src.txt`), then pass it to `convert_source.sh --source`.
This keeps the grounding input explicit and reproducible, and lets you re-run a
single concept's conversion without re-extracting.
