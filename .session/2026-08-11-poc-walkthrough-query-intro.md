---
Status: complete
Date: 2026-08-11
Topic: poc-walkthrough-query-intro
---

# Session: Add Query-Exploration Section to poc_walkthrough.ipynb

## Goal

Add a new section to `poc_walkthrough.ipynb`, inserted after the existing import
steps and before the "Cleanup" step, that teaches customers — many of whom are new
to Cypher and come from a Spark/tabular background — how to write their own
read-only exploratory queries against the data they just imported. This goes one
step beyond the count-only verification query already in the notebook, toward
filtering, one-hop traversal, and aggregation, so customers can start answering
their own questions on a call without repeated hand-holding.

---

## Context & Constraints

### Locked decisions
- Follow the notebook's existing pedagogical pattern exactly: a markdown
  explainer cell immediately before each relevant code cell, GraphAcademy links
  embedded contextually at the point of relevance (not front-loaded), matching
  the style already used in the "5. Indexes and Constraints" section.
- Reuse the emoji/callout conventions already in the notebook: `📚` for training
  links, `⚠️` for warnings, `✅` for success confirmations.
- Target audience: Spark/tabular-background users unfamiliar with graph
  traversal. Analogies to SQL joins/filters are welcome where they clarify, but
  don't front-load jargon.
- Reuse the schema already established earlier in the notebook so every example
  runs against data the customer already has in the graph:
  - `ClientNode {id, name, email, createdAt, updatedAt}`
  - `Supplier {supplierCode, name, location}`
  - `(:ClientNode)-[:INTERACTED_WITH {timestamp}]->(:ClientNode)`
- Scope is read-only exploration only: `MATCH` / `WHERE` / aggregation / basic
  one-hop traversal. No write patterns (already covered) and no GDS
  algorithms/projections (that's a separate track for GDS-track customers).

### Out of scope
- GDS projections or algorithms.
- APOC procedures.
- Any modification to existing cells above this section — insertion only.
- Renumbering existing sections beyond what's needed to fit the new section in.

---

## Relevant Specs / Schemas / Examples

### Existing schema available by this point in the notebook
```
(:ClientNode {id, name, email, createdAt, updatedAt})
(:Supplier {supplierCode, name, location})
(:ClientNode)-[:INTERACTED_WITH {timestamp}]->(:ClientNode)
```

### Existing style reference (from the notebook's Indexes & Constraints section)
```markdown
> 📚 **Want to go deeper on Cypher?** [Cypher Fundamentals](https://graphacademy.neo4j.com/courses/cypher-fundamentals/)
> covers `MERGE`, `MATCH`, `CREATE`, and the `UNWIND` pattern used throughout this
> toolkit — free, 1 hour, no installation required.
```
Match this tone and link-placement style for the new section.

### Illustrative content to adapt (not final copy — refine during the session)
- **Filtering:**
  ```cypher
  MATCH (c:ClientNode)
  WHERE c.email ENDS WITH '@acme.com'
  RETURN c.name, c.email
  LIMIT 25
  ```
- **One-hop traversal:**
  ```cypher
  MATCH (c:ClientNode {id: $client_id})-[:INTERACTED_WITH]->(other:ClientNode)
  RETURN DISTINCT other.name
  ```
- **Aggregation:**
  ```cypher
  MATCH (c:ClientNode)-[:INTERACTED_WITH]->(other:ClientNode)
  RETURN c.name, count(other) AS interaction_count
  ORDER BY interaction_count DESC
  LIMIT 10
  ```
- **`RETURN` vs `RETURN DISTINCT` callout** — flag this explicitly, since fan-out
  traversal producing duplicate rows is a common new-user confusion point.

---

## Instructions

1. Read the current "5. Indexes and Constraints" and "6. Test Import" sections of
   `poc_walkthrough.ipynb` to match heading level (`##`), tone, and callout
   conventions before writing new cells.
2. Insert a new section (e.g. "6a. Exploring Your Data — Basic Queries") between
   the existing test-import verification cell and the "7. Full Import" section,
   containing:
   a. Short framing prose: now that data is imported, here's how to start asking
      questions of it.
   b. A markdown + code cell pair on `MATCH` + `WHERE` filtering, using
      `ClientNode`.
   c. A markdown + code cell pair on one-hop traversal via `INTERACTED_WITH`.
   d. A markdown + code cell pair on basic aggregation (`count`, `ORDER BY`).
   e. A short callout on `RETURN` vs `RETURN DISTINCT`.
3. Embed one GraphAcademy link contextually near the first new concept
   introduced — link forward to Cypher Fundamentals once rather than repeating
   it in every sub-section.
4. Every new code cell must run against data already created earlier in the
   notebook — no new sample data introduced.
5. Do not modify any existing cells above this section.
6. Verify the notebook's JSON stays valid after edits — correct `cell_type`,
   unique `id`, `metadata: {}`, `outputs: []`, `execution_count: null` on new code
   cells.

---

## Decisions Made This Session

- **Constraint surfaced:** the `INTERACTED_WITH` relationship used in the traversal
  and aggregation examples is defined in `config.yaml`'s "Interactions" job, but that
  job is never actually run by the notebook's main walkthrough flow (sections 1–8
  only import `ClientNode` via the hardcoded test/full import cells). A customer
  following the notebook step-by-step would reach the new section 6a with zero
  `INTERACTED_WITH` edges in the graph. Rather than introduce a new write cell
  (out of scope — "no write patterns") or silently swap the example to a
  relationship that doesn't exist either, added a `⚠️` callout in the "One-Hop
  Traversal" markdown cell explaining that these two examples depend on the
  Interactions job and will simply return no rows until it's been run — not an
  error. Also added an empty-result guard (`if sample is None`) around the
  traversal cell since `ClientNode` presence isn't otherwise guaranteed either.
- Inserted new section "6a. Exploring Your Data — Basic Queries" between the
  "Verify in Neo4j" cell (end of section 6) and "## 7. Full Import", as specified.
  8 new cells (4 markdown, 4 code), all with unique ids, `metadata: {}`,
  `outputs: []`, `execution_count: null`. No existing cells modified — diff is
  purely additive (124 insertions, 0 deletions).
- One GraphAcademy link (Cypher Fundamentals) embedded once, in the section's
  intro markdown cell, per the "link forward once" instruction.
