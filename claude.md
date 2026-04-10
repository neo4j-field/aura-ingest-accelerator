<!-- AUTO-GENERATED: base + modules[neo4j] -->
<!-- Do not edit above ## Project-Specific -->


---

## Language & Runtime

- **Python ≥ 3.11** (use match statements, `X | Y` union types, `tomllib`, etc. freely)
- **Package manager**: `uv` preferred for running scripts (`uv run python -m ...`); `pip` acceptable
- **Project config**: `pyproject.toml` only — no `setup.py`, no `setup.cfg`
- **Formatter**: `black` (line length 88)
- **Linter**: `ruff` (rules: E, F, W, I, UP, B)
- **Testing**: `pytest` with `pytest-cov`; test files in `tests/`, named `test_*.py`

---

## Dependencies (Core Stack)

| Library | Role |
|---|---|
| `typer` | CLI entry points |
| `rich` | Console output, progress, logging display |

- Always pin with `>=` lower bounds, not `==` exact pins (unless a breaking change requires it)
- Dev extras in `[project.optional-dependencies] dev = [...]` — never in main `dependencies`

---

## CLI Conventions (Typer)

- One `typer.Typer()` app per project, in `main.py`
- Commands should be named for their action (verbs: `run`, `export`, `analyze`, `scan`)
- Use `--debug` flag on all commands; wire it to `logging.setLevel(logging.DEBUG)`
- Use `rich` console for all user-facing output — not bare `print()`
- Register all commands in `pyproject.toml` under `[project.scripts]`
- Emoji status indicators in console output:
  - `✅` success / completion
  - `🔍` discovery / scanning
  - `✨` new discovery / heuristic match
  - `🔗` relationship found
  - `🌿` enrichment
  - ⚠️ warning (via `logger.warning`)
  

Example invocation pattern (always document in README):
```sh
PYTHONPATH=. uv run python -m <package>.main <command> --flag value --debug
```

---

## Logging

- Use `logging.getLogger(__name__)` at module level for all parsers/engines
- Use `logging.getLogger("ClassName")` inside classes
- `--debug` flag sets `logging.DEBUG`; default is `logging.INFO`
- `logger.info()` for significant discoveries and milestones
- `logger.debug()` for AST node walks, column-level detail, fallback logic
- `logger.warning()` for orphaned entries, unresolved references, skipped nodes
- `logger.error()` for parse failures (always include the exception: `f"Failed to parse {file}: {e}"`)
- Never use `print()` for logging — use rich console for user output, logger for diagnostic output

---

## Error Handling

- Never let a single bad record crash the whole run — catch, log, continue
- Log failures at `logger.error()` with context: `f"Failed to process {item}: {e}"`
- Collect and surface skipped/failed items at the end of a run — never silently drop them
- Fallback chains: try clean path first, then defensive fallbacks; log each fallback at `debug` level
- Defensive attribute access on objects with variable structure: prefer `getattr(obj, 'attr', None)` over direct access

---

## File & Directory Structure

```
<project_name>/
├── pyproject.toml
├── README.md
├── ARCHITECTURE.md          # Required for all projects
├── requirements.txt         # Pinned runtime deps (generated)
├── requirements-dev.txt     # Points to pyproject.toml dev extras
├── <package_name>/
│   ├── __init__.py
│   ├── main.py              # CLI entry point (typer app)
├── tests/
├── output/                  # Generated manifests or other exports or results (gitignored)
└── test/data/               # Test fixtures (DDL, CSV, JSON)
```

---

## Documentation Standards

- Every project must have:
  - `README.md` with Quick Start showing all three pipeline stages with example CLI invocations
  - `ARCHITECTURE.md` explaining the design philosophy, data-flow and component responsibilities
- ARCHITECTURE.md must include a component table: Component | Responsibility | Key Logic
- Inline docstrings on all public methods — one-liner minimum, full docstring for complex logic
- Complex fallback logic (e.g., AST node extraction) should have inline `logger.debug()` comments explaining *why* each fallback exists, not just what it does

## Documentation Currency

Claude should treat README.md and ARCHITECTURE.md as live artifacts,
not one-time scaffolding. After any session that produces:

- A working new module or command
- A validated MVP or end-to-end flow
- A significant refactor that changes how components interact
- A new CLI argument, config key, or output format

...Claude should pause before closing the session and ask:

  "We just got X working. Want me to update README.md / ARCHITECTURE.md
   to reflect this before we close out?"

### What to check when updating:
- README Quick Start — does the example command still work as written?
- README Workflow section — does it reflect current pipeline steps?
- ARCHITECTURE.md Data Flow — does the diagram match current reality?
- ARCHITECTURE.md Component table — any new modules to add?
- docs/usage_instructions.md — any new flags, args, or config keys?

### What NOT to do:
- Don't prompt after every small change — only after validated, working functionality
- Don't rewrite sections that are still accurate
- Don't update docs speculatively for features not yet working
- Don't ask mid-session — wait until the user signals something is working

---

## Session Close Checklist

When a user signals they're done for the session (e.g. "ok that's good for now",
"let's stop here", "committing this"), Claude should quickly check:

1. Were any docs updated to match what was built? If not, offer to do it now.
2. Are there any known bugs or deferred decisions worth logging to a Lesson node?
3. Have we added any modules that should be added to requirements.txt or requirements-dev.txt or pyproject.toml
4. Is there anything that should be committed that hasn't been?

Keep this lightweight — one short prompt, not an interrogation.

---

## Working Conventions (Claude Collaboration)

### Tooling
- **Preferred**: Claude Code (CLI) for active coding sessions — direct filesystem access, no upload/download cycle
- **Fallback**: Upload files to this chat for review/analysis; produce complete ready-to-save files in response
- **VSCode** is the primary editor; GitHub for all repos
- Always produce complete files, not diff-style patches, for any change larger than ~10 lines

### Testing Environment
- Never hardcode connection details — always use the profiles system in a relevant yaml file in /config

### Session Continuity
- This `claude.md` is the shared contract across sessions — reference it at the start of any new coding session
- If a parallel session  produces new conventions, update this file before continuing in other sessions

### GitHub Workflow
- Standard branch-per-feature workflow assumed
- `main` / `master` is stable; feature branches for all active work
- Update `ARCHITECTURE.md` when module boundaries change significantly — don't let it drift from reality

---

## Configuration Conventions

- All project configuration lives in `config/` — never hardcode paths, 
  credentials, or environment-specific values in source code
- Credentials exclusively via `.env` (gitignored) — always provide `.env.example`
- A `config.yaml` (or project-named equivalent) is the primary config file,
  loaded at startup via a dedicated `config.py` module (if required)
- Never load config inline in business logic — always via a dedicated `config.py`
- `config.py` is the only module that reads `.env` and YAML — 
  everything else receives config as parameters
- Config should be loaded once at startup and passed down — 
  not re-read on every function call
---

## What NOT to Do (Base Rules)

**All analyzers / datasource-graph-analyzer:**

- Don't use `print()` — use logger or rich console
- Don't hardcode paths, credentials, or environment values in source code
- Don't re-read config on every function call — load once at startup# Claude Module: Neo4j / Graph Standards

Cypher generation conventions, MERGE patterns, CALL {} rules, APOC conventions,
and constraint management for all projects that write to or read from Neo4j.

---

## Cypher Generation Standards

- All MERGE statements must be **idempotent** — use `MERGE`, never `CREATE` for nodes that may already exist
- Property setting pattern:
  ```cypher
  WITH $session_timestamp AS now
  MERGE (n:Label {id: 'uid_value'})
  ON CREATE SET n.name = 'name', n.createdEpochMillis = now, n.createdDatetime = datetime(now)
  ON MATCH SET n.modifiedEpochMillis = now, n.modifiedDatetime = datetime(now)
  SET n.property = 'value';
  ```
- Timestamps: use `datetime('ISO8601_STRING')` format, UTC by default
- Session timestamp passed into exporter at construction time — never generated mid-export
- Use `IF NOT EXISTS` on all `CREATE CONSTRAINT` and `CREATE INDEX` statements
- Use `ON CREATE SET` / `ON MATCH SET` to separate immutable and updateable fields
- Always use `WITH` between `MERGE` → `MATCH` transitions to preserve scope
- When using multiple `WITH` clauses inside a subquery, carry forward all required
  external variables through every transition
- Semicolon-separate multi-statement blocks — variables do not carry between them
- All nodes should contain `createdEpochMillis` and `createdDatetime`; on update also
  `modifiedEpochMillis` and `modifiedDatetime` — omit only when a downstream importer
  handles timestamp assignment (e.g., manifest-style Cypher output)
- Use `IS NULL` instead of `exists(n.prop)` — `exists()` is deprecated in Neo4j 5.x
- If `"parameterized": false` is present in the request, use literal values instead of
  `$parameters` — enables compatibility with Neo4j Browser and schema illustration.
  Default is parameterized unless explicitly disabled.
- Never MERGE on nullable or optional properties — use a reduced stable key set in the
  MERGE predicate; apply optional/nullable fields via `SET` after the MERGE
- When setting string properties, do not use Python-style triple quotes (`"""`).
  Escape line breaks using `\n` within a standard quoted string.
- Never use bare `print()` — always wrap Cypher output in triple backticks.
  Do not add explanation or preamble unless asked.

---

## CALL {} Subquery Rules

- Never use `CALL () {}` at the top level — embed inside a parent query or eliminate entirely
- Use `CALL () {}` only when variable continuity across semicolons is genuinely required
- Pass external variables explicitly in the call signature: `CALL (var1, var2) { ... }`
- Semicolons are not allowed inside a `CALL () {}` block
- After `CALL () {procedure} YIELD ...`, you must `RETURN` yielded variables before `ORDER BY`
- Never place a `WITH` clause immediately after a semicolon outside a `CALL {}` block —
  this throws a syntax error. Always restart as a valid standalone query or use `WITH *`

---

## Relationship Type Governance

- Never invent new relationship types ad hoc — define them explicitly before use
- Relationship type names: `SCREAMING_SNAKE_CASE`, verb-phrase describing direction
  (e.g. `HAS_COLUMN`, `BELONGS_TO`, `LEARNED_DURING`)
- Document all relationship types used by this project in `## Project-Specific`
- Document all node labels used by this project in `## Project-Specific`

---

## APOC Conventions

### Date Math
- `apoc.date.add` requires epochMillis input — convert native `date()` types first
  using `datetime().epochMillis` before passing to any APOC date math
- Supported units: `ms`, `s`, `m`, `h`, `d` — weeks and months are **not** supported
- On Aura, native date types must be explicitly converted before any APOC date operation

### Export Strategy
- Use `stream: true` with a null file path for all APOC exports — Python captures
  the stream via the driver and writes locally
- This pattern works across local, Docker, and Aura — no server filesystem dependency
- Use `format: plain` to avoid `:begin` / `:commit` markers that break import scripts
- Always prepend `CREATE CONSTRAINT UNIQUE_IMPORT_NAME IF NOT EXISTS` before import data
- Always append `CALL db.awaitIndexes(300)` after all schema statements
- When splitting multi-statement Cypher for import, never use simple `split(';')` —
  use regex to avoid false splits inside string literals:
  ```python
  re.split(r';(?=\s*($|\n|--|//))', data)
  ```

### Dynamic Queries
- Cypher does not support inline label parameterization — use `apoc.cypher.run()`
  with string interpolation for dynamic label queries:
  ```cypher
  CALL apoc.cypher.run("MATCH (n:" + label + ") RETURN n", {}) YIELD value
  ```
- Before dynamic label loops: `COLLECT(DISTINCT label)` then `UNWIND` — prevents
  scanning the same label multiple times and eliminates downstream duplicates
- Always carry outer loop variables through every `WITH` clause inside nested
  `apoc.cypher.run()` calls — scope is not inherited automatically
- When `CALL apoc.cypher.run(...) YIELD value` returns aliased fields, access them
  via the outermost alias: `WITH value.bar AS myBar` — not `record.get('value.myBar')`

### Data Structures
- Dynamic property names are not supported in literal maps — use `apoc.map.fromPairs()`
  with alternating key-value pairs:
  ```cypher
  apoc.map.fromPairs([key1, val1, key2, val2])
  ```
- Maps cannot be stored directly as node properties — encode as JSON strings and
  parse at runtime:
  ```cypher
  apoc.convert.fromJsonMap(n.property_types)
  ```

---

## What NOT to Do (Neo4j)

- **Don't** use `CREATE` for nodes that may already exist — always `MERGE`
- **Don't** f-string user data directly into Cypher — always use `_escape()`
- **Don't** generate timestamps inside loops — pass session timestamp at construction time
- **Don't** run constraint files out of order — `01_constraints.cypher` must always run first
- **Don't** use `CALL () {}` at the top level of a query
- **Don't** place a `WITH` clause immediately after a semicolon outside a `CALL {}` block
- **Don't** MERGE on nullable properties — use a reduced stable key set
- **Don't** use `exists(n.prop)` — use `n.prop IS NULL` / `n.prop IS NOT NULL`
- **Don't** store maps as node properties — encode as JSON strings
- **Don't** add new relationship types or node labels without documenting them in `## Project-Specific`

---

## Project-Specific

> This section is maintained by Claude during coding sessions.

### Overview
_To be filled in during first Claude Code session._

### Key Patterns
_Document project-specific conventions, quirks, and decisions here._

### Known Issues / Tech Debt
_Track known bugs and deferred work here._
