# Phase 2-4: Refinement, Evaluation, Feedback

After Phase 1 (cross-table concepts), users can iterate on their bundles through three interactive flows.

## Phase 2: Refinement — Free-Text Iteration

**Scenario:** Bundle is generated, but user wants changes without re-extracting sources.

**In the Claude conversation:**

User: *"Make the orders overview more concise, focus on just the key columns"*

Claude (skill):
1. Reads current `tables/orders.md`
2. Calls claude with the current markdown + refinement request
3. Claude rewrites the section, keeping metadata intact
4. Writes new content back to `tables/orders.md`
5. Records change in `refine_session.json`

**Multi-turn example:**

```
User: "Shorten the orders overview"
Claude: (modifies, saves)

User: "Now add an 'Examples' section with sample queries"
Claude: (reads modified file, adds section, saves)

User: "Show me what changed"
Claude: (diff against original, or run `refine_session.py show`)
```

**Commands in chat:**

- "Make [concept] more concise" → refinement
- "Add a [section] to [concept]" → refinement
- "Show me the change history" → `python3 scripts/refine_session.py show`
- "Revert [concept] to original" → read from session backup, restore

**No re-extraction:** Sources stay as-is; only generated markdown is edited.

---

## Phase 3: Evaluation — Quality Metrics

**Scenario:** User wants to know if the bundle is good.

**In the Claude conversation:**

User: *"Score this bundle for me"*

Claude (skill):
1. Runs `python3 scripts/evaluate_bundle.py <bundle>`
2. Checks:
   - **Structural Validity:** All concepts have valid frontmatter, required fields
   - **Concept Coverage:** Count of concepts generated
   - **Cross-Reference Completeness:** % of concepts with `# Cross-references`
3. Displays scorecard:
   ```
   Structural Validity: 95/100 ✅
   Concept Coverage: 12 concepts
   Cross References: 100% (12/12 with bidirectional links)
   Overall Score: 95/100 ✅
   ```

**Advanced (future):** Golden-based metrics

If user provides golden answers (expected concepts, facts, terms), Claude can run:
- **Concept Recall:** Did we generate the expected concepts?
- **Hallucination Check:** Are there invented facts?
- **Consistency:** Do concept definitions agree?

**Commands in chat:**

- "Evaluate the bundle" → run evaluator, show report
- "Score with [golden file]" → run with golden-based metrics
- "What's the hallucination score?" → judge-based quality metric

---

## Phase 4: Feedback — User Overrides

**Scenario:** User wants to steer generation with their own context/requirements.

**Feedback format (JSON):**

Create a file `my_feedback.json`:

```json
{
  "proposals": [
    {
      "concept_id": "tables/orders",
      "target_section": "# Schema",
      "feedback": "The total_usd column should also mention that it's reset to 0.00 when refunded",
      "priority": "high"
    },
    {
      "concept_id": "tables/customers",
      "feedback": "Add notes about the tier field: free/plus/pro determines SLA and feature access",
      "priority": "medium"
    },
    {
      "concept_id": "tables/orders",
      "target_section": "# Examples",
      "feedback": "Include a query that joins orders and customers to show the FK relationship",
      "priority": "low"
    }
  ]
}
```

**In the Claude conversation:**

User: *"I have some feedback to improve the bundle"* (uploads feedback.json)

Claude (skill):
1. Reads proposals
2. For each affected concept:
   - Loads current markdown
   - Calls claude with feedback as additional context
   - Rewrites concept to incorporate feedback
   - Saves new version
3. Records applied feedback

**Result:** Concepts are re-generated with user guidance, without re-extracting sources.

**Commands in chat:**

- "Apply this feedback to the bundle" (user provides JSON)
- "Can you add [detail] to [concept]?" → Claude creates a proposal and applies it
- "The schema is missing [info]" → Claude infers and applies feedback

---

## Workflow: Putting It Together

### Complete user journey:

```
1. User: "Convert my sales data to OKF"
   → Skill: runs Phase 1 (extract, aggregate, inject)
   
2. User: "The orders overview is too long"
   → Skill: Phase 2 refinement (rewrite inline)
   
3. User: "Score the bundle"
   → Skill: Phase 3 evaluation (95/100 ✅)
   
4. User: "The customer_id column meaning is unclear"
   → Skill: Phase 4 feedback (updates schema, re-runs writer)
   
5. User: "Final score?"
   → Skill: Phase 3 re-evaluation (98/100 ✅)
   
6. User: "Done, publish it"
   → Skill: outputs final bundle (ready for git/Dataplex/etc.)
```

### Commands available in the skill:

| What you want | Command | Tool |
|---|---|---|
| Build initial bundle | (upload sources) | Phase 1: convert + aggregate + inject |
| Iterate on content | "Make X more concise" | Phase 2: refine_session.py |
| Check quality | "Score the bundle" | Phase 3: evaluate_bundle.py |
| Incorporate feedback | "Add this detail to Y" | Phase 4: apply_feedback.py |
| See history | "Show change history" | Phase 2: refine_session.py show |
| Compare versions | "Diff against original" | Phase 2: session backup |

---

## Implementation Notes

### Refinement (`Phase 2`)

- Saves `refine_session.json` to track all changes
- Backs up original concepts for rollback/diff
- Each user request = one turn in history
- No concept re-generation; purely markdown editing

### Evaluation (`Phase 3`)

- Deterministic metrics (structure, coverage) always run
- Judge-based metrics (hallucination, consistency) optional (require claude)
- Outputs both JSON (for automation) and human-readable report
- Extensible: add golden-based metrics later

### Feedback (`Phase 4`)

- User describes desired changes in JSON proposal format
- Each proposal targets a concept_id + optional section
- Claude refines concept with feedback as "ground truth context"
- Feedback is ADDITIVE: never removes existing content

---

## Skill Integration

These three phases are not separate tools — they're part of the **continuous dialogue** when using the anything-to-okf skill:

```
User → Skill (Phase 1) → Bundle
User → Skill (Phase 2) → Refined Bundle
User → Skill (Phase 3) → Evaluation Report
User → Skill (Phase 4) → Feedback-Enhanced Bundle
```

The skill maintains session state, guides the user through iterations, and presents results conversationally.
