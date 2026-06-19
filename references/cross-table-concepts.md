# Cross-Table Concepts: Automatic Relationship Detection

This document explains Phase 1 of the knowledge-catalog feature replication: **automatic detection, aggregation, and bidirectional injection of cross-table relationships**.

## The Problem It Solves

Imagine you have these sources:

| Source | What it says |
|--------|-------------|
| orders.csv | Columns: order_id, customer_id, status, total_usd, placed_at |
| customers.json | Columns: customer_id, email, tier, created_at |
| schema-doc.md | "orders.customer_id is a foreign key to customers.customer_id" |

**Without cross-table concepts**, the user must:
1. Manually write "See [customers](/customers.md)" in the orders overview
2. Manually write "is referenced by [orders](/orders.md)" in the customers overview
3. Avoid duplication when the same fact appears in multiple sources

**With cross-table concepts**, the system:
1. Extracts the FK from schema-doc.md automatically
2. Injects it into BOTH overviews
3. Deduplicates across sources
4. Connects fragmented facts (one doc says "FK", another says "points to customers")

## How It Works: 4-Step Pipeline

### Step 1: Extraction (in `convert_source.sh`)

When the model writes each concept, it ALSO outputs a `<CONCEPTS>` JSON block containing cross-table facts:

```json
<CONCEPTS>[
  {
    "kind": "join",
    "tables": ["orders", "customers"],
    "title": "Customer Orders FK",
    "body": "orders.customer_id is a foreign key into customers.customer_id"
  },
  {
    "kind": "metric",
    "tables": ["orders", "revenue"],
    "title": "Daily Revenue",
    "body": "total_usd sums daily revenue; aggregated by customer tier"
  }
]</CONCEPTS>
```

Each concept's `.md` file gets a `.concepts.json` sidecar in the same directory.

**Key rules for extraction:**
- Ground ONLY in the source material — no invented relationships
- Extract facts that span 2+ tables (or define a metric/grain across tables)
- `kind` is `join`, `metric`, or `relationship`
- `tables` lists the concepts involved (use their IDs: `tables/orders`, not "Orders Table")
- `body` is 1-3 sentences, including specific keys/formulas verbatim

### Step 2: Collection (`scripts/collect_concepts.py`)

Walks the bundle and collects all `.concepts.json` sidecars into one file:
`okf-work/all_concepts.json`

Applies deterministic deduplication:
- If two concepts have the same `(kind, tables, title)`, keep the longer `body` (more complete)
- Removes exact duplicates across all sources

### Step 3: Aggregation (`scripts/aggregate_concepts.py`)

Runs ONE small LLM call on the deduplicated list to:

**Merge near-duplicates:**
```
Input:
  - [join] tables=[orders, customers] | FK: orders.customer_id points to customers
  - [join] tables=[orders, customers] | Customer FK: customer_id is foreign key
→ Output: [join] tables=[orders, customers] | Customer Orders FK: orders.customer_id is a foreign key...
```

**Connect fragmented facts across documents:**
```
Input:
  - [join] tables=[orders, customers] | FK: defines customer_id as foreign key
  - [join] tables=[orders, customers] | Reference: it points to customers.customer_id
→ Output: [join] tables=[orders, customers] | FK: customer_id is FK to customers.customer_id (1:N relationship)
```

**Drop pure duplicates** (keep the higher-quality one)

Output: `okf-work/aggregated_concepts.json`

### Step 4: Injection (`scripts/inject_shared_concepts.py`)

For each `.md` file in the bundle, builds a `# Cross-references` section:

```markdown
# Cross-references

Cross-table concepts and relationships involving this entity:
- **[join] Customer Orders FK** (involves [customers](/customers.md)): orders.customer_id is a foreign key...
- **[metric] Daily Revenue** (involves [revenue](/revenue.md)): total_usd sums daily revenue by tier...
```

**Bidirectional logic:**
- If a concept mentions table X in its `tables` list, that concept is injected into X's `# Cross-references`
- A FK between `[orders, customers]` appears in BOTH orders and customers overviews
- This holds even if only one source document mentions the relationship

## Prompt Design: Why This Works

### For the writer (in `convert_source.sh`)

The `<CONCEPTS>` extraction happens in the SAME call that writes the overview, so:
- The model has full context (not a separate extraction pass)
- It's grounded in the same source material
- No network round-trip overhead

### For the aggregator (in `aggregate_concepts.py`)

The LLM sees a compact list (not full documents), so:
- The call is fast and cheap (one Flash call)
- It can reason about connections ("join key" + "table name" = complete FK)
- It stays on-topic (no risk of drifting into unrelated facts)

### For injection (in `inject_shared_concepts.py`)

Pure deterministic logic — no LLM required:
- Bidirectional: just filter `table_name in concept['tables']`
- Idempotent: adding the section twice produces the same result
- Safe: only ADDS content, never modifies existing markdown

## What It CAN Do

✅ Detect and inject foreign keys (child → parent, and reverse)
✅ Inject metrics that span multiple tables
✅ Handle fragmented facts (one doc says the key, another says the target)
✅ Bidirectional relationships (FK appears in both table overviews)
✅ Deduplication (same fact stated 3 ways → one clean statement)
✅ Work without BigQuery schema discovery (user provides the table list)

## What It CANNOT Do

❌ Auto-discover table relationships without being told they exist in source material
❌ Infer unmapped schemas (columns must be named in sources)
❌ Detect implicit cardinality beyond what the source states
❌ Handle conflicting facts (if two sources contradict, the aggregator picks one)

## Common Pitfalls

**Pitfall 1: Overstating relationships**
```
❌ BAD: "probably has a cascade delete because it's a customer FK"
✅ OK: "orders.customer_id is a foreign key to customers.customer_id"
```
Ground in what the sources EXPLICITLY state.

**Pitfall 2: Invented concept IDs**
```
❌ BAD: tables: ["Customer Record", "Order Entry"]
✅ OK: tables: ["customers", "orders"]
```
Use the actual file-based concept IDs (`tables/orders` → `orders`).

**Pitfall 3: Forgetting bidirectionality**
```
The FK relationship WILL appear in both directions.
If you write "orders has parent customers", don't also manually write "customers has children orders"
→ the system handles both.
```

## Customization

### Control the LLM model

```bash
python3 scripts/aggregate_concepts.py <bundle> --model claude-opus-4-8
```

### Custom concept extraction prompt

Edit the `<CONCEPTS>` block in `scripts/convert_source.sh` to ask for different `kind` values
(e.g., add `"lineage"` if your domains often document data pipelines).

### Skip aggregation

If you want to keep fragmented facts as-is (no merge pass), skip `aggregate_concepts.py`:

```bash
python3 scripts/collect_concepts.py <bundle>
python3 scripts/inject_shared_concepts.py <bundle>
# Skipped the merge pass; all individual facts are injected
```

(Not recommended unless the sources are very clean.)

## Example: Real-World Flow

**Sources:**
- `orders.csv` (5 columns, no schema doc)
- `customers.json` (4 columns, with FK info)
- `schema-relationships.md` (documents the 1:N relationship + revenue metric)

**Output:**

1. **convert_source.sh** writes:
   - `tables/orders.md` (no Cross-references yet; CSV had no FK info)
   - `tables/orders.concepts.json` → `[]` (empty; CSV has no cross-table facts)
   - `tables/customers.md` (no Cross-references yet)
   - `tables/customers.concepts.json` → `[{kind:"join", tables:["orders","customers"], ...}]`

2. **collect_concepts.py** merges:
   - `all_concepts.json` → one FK concept (from customers sidecar)

3. **aggregate_concepts.py** (no-op if only one concept):
   - `aggregated_concepts.json` → same FK concept

4. **inject_shared_concepts.py**:
   - `tables/orders.md` ← adds "# Cross-references" (because FK mentions orders)
   - `tables/customers.md` ← adds "# Cross-references" (because FK mentions customers)

**Result:** Both tables now link to each other, even though only the customers JSON explicitly mentioned the relationship.
