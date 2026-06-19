# OKF v0.1 — the rules you need to produce a conformant bundle

This is a condensed, production-focused digest of the Open Knowledge Format
(OKF) v0.1 specification. It contains everything needed to *write* a conformant
bundle. Read it before planning a conversion.

## What a bundle is

A **bundle** is a directory tree of UTF-8 markdown files. The directory layout
is yours to choose — organize concepts however the knowledge naturally groups.

```
bundle/
├── index.md            # progressive-disclosure listing (auto-generated)
├── log.md              # optional update history
├── <concept>.md        # a concept at the root
└── <subdir>/
    ├── index.md
    └── <concept>.md
```

- **Concept** = one markdown file = one unit of knowledge (a table, an API, a
  metric, a playbook, a glossary term, a document, …).
- **Concept ID** = the file path minus `.md` (e.g. `tables/orders.md` →
  `tables/orders`). IDs/segments are kebab-case, `[A-Za-z0-9_][A-Za-z0-9_.-]*`.
- **Reserved filenames** (never use for a concept): `index.md`, `log.md`.

## Concept document = frontmatter + body

```markdown
---
type: BigQuery Table                 # REQUIRED — the only hard requirement
title: Customer Orders               # recommended
description: One row per completed order across all channels.   # recommended
resource: https://.../tables/orders  # optional canonical URI of the asset
tags: [sales, orders, revenue]       # optional
timestamp: 2026-05-28T14:30:00Z      # optional ISO-8601 last-modified
# ...any additional producer-defined keys are allowed
---

# Schema

| Column        | Type      | Description                          |
|---------------|-----------|--------------------------------------|
| `order_id`    | STRING    | Globally unique order identifier.    |
| `customer_id` | STRING    | FK into [customers](/tables/customers.md). |

# Citations

[1] [BigQuery table schema](https://.../tables/orders)
```

### Frontmatter fields

- **`type`** (REQUIRED, non-empty): a short, self-explanatory kind, e.g.
  `BigQuery Table`, `API Endpoint`, `Metric`, `Playbook`, `Reference`,
  `Glossary Term`, `Document`, `Source File`. Not centrally registered — pick a
  descriptive value and reuse it consistently across like concepts (the index
  groups by `type`).
- **`title`**: human display name. Falls back to the filename if omitted.
- **`description`**: one sentence. Used in index listings and search snippets.
- **`resource`**: canonical URI of the underlying asset. Omit for abstract
  concepts that aren't bound to a physical resource.
- **`tags`**: YAML list of short lowercase strings.
- **`timestamp`**: ISO-8601 datetime of last meaningful change.
- Any extra keys are allowed and SHOULD be preserved when round-tripping.

> YAML safety: wrap any `description`/`title`/value that contains a colon,
> `#`, quotes, or starts with a special character in double quotes, or the YAML
> parser will choke.

### Body

Standard markdown. Favor **structure** (headings, lists, tables, fenced code)
over freeform prose — structure aids both human reading and agent retrieval.
There are no required sections. Conventional headings:

| Heading       | Use for                                          |
|---------------|--------------------------------------------------|
| `# Schema`    | An asset's columns/fields, structured.           |
| `# Examples`  | Concrete usage, usually fenced code blocks.       |
| `# Citations` | External sources backing claims (numbered).      |

## Cross-linking

Concepts link to each other with normal markdown links. The relationship type
is conveyed by the surrounding prose, not the link.

- **Bundle-relative (preferred):** begins with `/`, resolved from the bundle
  root — `[customers](/tables/customers.md)`. Stable when files move within a
  subdirectory.
- **Relative:** `[neighbor](./other.md)`.
- Broken links are explicitly tolerated by consumers (they may represent
  not-yet-written knowledge), but avoid creating them on purpose.

## Index files (§6)

`index.md` may appear in any directory. It has **no frontmatter** (exception:
the bundle-root `index.md` may carry a single `okf_version: "0.1"` key). Body is
sections of bullet links, one section per group:

```markdown
# BigQuery Table

* [Orders](orders.md) - One row per completed order.
* [Customers](customers.md) - One row per customer.

# Subdirectories

* [datasets](datasets/index.md) - All sales datasets.
```

Generate indexes with `scripts/generate_indexes.py` rather than by hand.

## Log files (§7, optional)

`log.md` records change history, newest first, grouped by ISO date:

```markdown
# Update Log

## 2026-05-22
* **Creation**: Added [Orders](/tables/orders.md).
```

## Citations (§8)

When the body makes claims from external material, list them under a final
`# Citations` heading, numbered, as `[n] [Title](URL)`. Links may be absolute
URLs, bundle-relative paths, or paths into a `references/` subtree that mirrors
external material as first-class concepts.

## Conformance (§9) — what the validator enforces

A bundle is conformant if:

1. Every non-reserved `.md` has a parseable YAML frontmatter block.
2. Every frontmatter block has a non-empty `type`.
3. `index.md` / `log.md` follow their structure (no stray frontmatter).

Everything else is soft guidance. Consumers MUST NOT reject a bundle for
missing optional fields, unknown `type` values, extra keys, broken links, or
missing indexes. `scripts/validate_bundle.py` reports hard errors vs warnings on
exactly this basis.
