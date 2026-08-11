<!-- AUTO-GENERATED: base + modules[neo4j] -->
<!-- Do not edit above ## Project-Specific — run refresh-dev-standards.sh to update -->
<!-- dev-standards: https://github.com/pdrangeid/dev-standards -->

# Claude Standards: Base Python Conventions

This file encodes universal patterns and conventions for all Python projects
in this ecosystem. It is auto-fetched by `setup-project.sh` and `refresh-dev-standards.sh`.

---

## Language & Runtime

- **Python ≥ 3.11** (use match statements, `X | Y` union types, `tomllib`, etc. freely)
- **Project config**: `pyproject.toml` only — no `setup.py`, no `setup.cfg`
- **Formatter**: `black` (line length 88)
- **Linter**: `ruff` (rules: E, F, W, I, UP, B)
- **Testing**: `pytest` with `pytest-cov`; test files in `tests/`, named `test_*.py`

---

## Package Management

- `uv` is the preferred package manager and script runner for all projects
- Always document `uv` invocations first in README and usage docs:
  ```sh
  # Preferred
  uv run python -m <package>.main <command> --debug

  # Fallback (traditional venv activated)
  python -m <package>.main <command> --debug
  ```
- Install dependencies with `uv pip install -e .[dev]` — not bare `pip install`
- Use `uv venv` for environment creation — not `python -m venv`
- `uv run` does not require activating the venv — prefer it for one-off execution
- Legacy projects using `argparse` should migrate to `typer` when next significantly touched

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
  - `⚠️` warning (via `logger.warning`)

Example invocation pattern (always document in README):
```sh
uv run python -m <package>.main <command> --flag value --debug
```

---

## Logging

- Use `logging.getLogger(__name__)` at module level for all modules
- Use `logging.getLogger("ClassName")` inside classes
- `--debug` flag sets `logging.DEBUG`; default is `logging.INFO`
- `logger.info()` for significant discoveries and milestones
- `logger.debug()` for detail-level tracing and fallback logic
- `logger.warning()` for skipped entries, unresolved references, non-fatal issues
- `logger.error()` for failures — always include context: `f"Failed to process {item}: {e}"`
- Never use `print()` for logging — use rich console for user output, logger for diagnostics

---

## Error Handling

- Never let a single bad record crash the whole run — catch, log, continue
- Collect and surface skipped/failed items at the end of a run — never silently drop them
- Fallback chains: try clean path first, then defensive fallbacks; log each fallback at `debug` level
- Defensive attribute access on objects with variable structure:
  prefer `getattr(obj, 'attr', None)` over direct attribute access

---

## File & Directory Structure

```
<project_name>/
├── pyproject.toml
├── README.md
├── ARCHITECTURE.md              # Required for all projects
├── AGENTS.md                    # Auto-generated standards + Project-Specific section
├── CLAUDE.md                    # Bridge stub — `@AGENTS.md` import + Claude Code section
├── requirements.txt             # Pinned runtime deps (generated)
├── requirements-dev.txt         # Points to pyproject.toml dev extras
├── <package_name>/
│   ├── __init__.py
│   └── main.py                  # CLI entry point (typer app)
├── config/
│   └── config.yaml              # Primary project config
├── docs/
│   └── usage_instructions.md
├── tests/
│   └── data/                    # Test fixtures
└── output/                      # Generated artifacts (gitignored)
```

---

## Configuration Conventions

- All project configuration lives in `config/` — never hardcode paths,
  credentials, or environment-specific values in source code
- Credentials exclusively via `.env` (gitignored) — always provide `.env.example`
- A `config.yaml` (or project-named equivalent) is the primary config file,
  loaded at startup via a dedicated `config.py` module
- Never load config inline in business logic — always via `config.py`
- `config.py` is the only module that reads `.env` and YAML —
  everything else receives config as parameters
- Config should be loaded once at startup and passed down —
  not re-read on every function call

---

## Documentation Standards

- Every project must have:
  - `README.md` with Quick Start showing the core workflow with example CLI invocations
  - `ARCHITECTURE.md` explaining design philosophy, data flow, and component responsibilities
- `ARCHITECTURE.md` must include a component table: Component | Responsibility | Key Logic
- Inline docstrings on all public methods — one-liner minimum, full docstring for complex logic
- Complex fallback logic should have inline `logger.debug()` comments explaining
  *why* each fallback exists, not just what it does

---

## Documentation Currency

Claude should treat `README.md` and `ARCHITECTURE.md` as live artifacts,
not one-time scaffolding. After any session that produces:

- A working new module or command
- A validated MVP or end-to-end flow
- A significant refactor that changes how components interact
- A new CLI argument, config key, or output format

...Claude should pause before closing the session and ask:

  "We just got X working. Want me to update README.md / ARCHITECTURE.md
   to reflect this before we close out?"

### What to check when updating
- README Quick Start — does the example command still work as written?
- README Workflow section — does it reflect current pipeline steps?
- ARCHITECTURE.md Data Flow — does the diagram match current reality?
- ARCHITECTURE.md Component table — any new modules to add?
- `docs/usage_instructions.md` — any new flags, args, or config keys?

### What NOT to do
- Don't prompt after every small change — only after validated, working functionality
- Don't rewrite sections that are still accurate
- Don't update docs speculatively for features not yet working
- Don't ask mid-session — wait until the user signals something is working

---

## Session Close Checklist

When a user signals they're done for the session (e.g. "ok that's good for now",
"let's stop here", "committing this"), Claude should quickly check:

1. Were any docs updated to match what was built? If not, offer to do it now.
2. Are there any deferred decisions or known issues worth noting somewhere?
3. Have any new dependencies been added that need updating in `pyproject.toml`?
4. Is there anything that should be committed that hasn't been?

Keep this lightweight — one short prompt, not an interrogation.

---

## Working Conventions (Claude Collaboration)

### Tooling
- **Preferred**: Claude Code (CLI) for active coding sessions — direct filesystem
  access, no upload/download cycle
- **Fallback**: Upload files to chat for review; produce complete ready-to-save
  files in response (not diffs) for any change larger than ~10 lines
- **VSCode** is the primary editor; GitHub for all repos

### Session Continuity
- `AGENTS.md` is the shared contract across sessions — read it at the start of
  every new coding session before touching any code
- If a parallel session produces new conventions, update `AGENTS.md` before
  continuing in other sessions to prevent drift

### GitHub Workflow
- Standard branch-per-feature workflow
- `main` is stable; `develop` is integration; feature branches for all active work
- Update `ARCHITECTURE.md` when module boundaries change significantly —
  don't let it drift from reality
- Claude Code commits freely on feature/* and develop branches
- Merge to main is always a deliberate human action — never ask
  Claude Code to merge or push to main
- Use --no-ff merges to preserve branch history
- Tag main after merging a completed feature or version
- Claude Code should always commit before ending a session

---

## What NOT to Do (Base Rules)

- **Don't** use `print()` — use logger or rich console
- **Don't** hardcode paths, credentials, or environment values in source code
- **Don't** re-read config on every function call — load once at startup
- **Don't** produce diff-style patches for changes — always produce complete files
- **Don't** let `README.md` or `ARCHITECTURE.md` drift from what the code actually does

---

## Session Management

### The `.session/` Directory

Every project contains a `.session/` directory for structured Claude Code session files.
This is the bridge between architecture/planning sessions (Claude web) and
implementation sessions (Claude Code).

```
.session/
├── _template.md                  # canonical template — do not edit, copy to create sessions
├── specs/                        # durable, promoted decisions (always tracked)
│   └── [topic]-baseline.md       # locked architectural decisions, schemas, contracts
└── YYYY-MM-DD-[topic].md         # active or archived session files (tracked)
```

### Starting a Claude Code Session

At the start of every session, before touching any code:

1. Read `AGENTS.md` (always)
2. Check for a session file: `ls .session/` — if a dated `.md` file exists and is `Status: active`, read it
3. Read any `specs/` files referenced in the session file
4. Confirm your understanding of the **Goal** and **Constraints** before proceeding

If no session file exists, ask the user if there's a session to load or proceed with
their in-chat instructions.

### During a Session

- Append decisions, discoveries, and deviations to `## Decisions Made This Session`
- If a constraint or out-of-scope boundary is hit, surface it explicitly rather than silently working around it
- Do not modify `_template.md` — copy it, rename it, then edit the copy

### Closing a Session

When the user signals the session is complete:

1. Update `Status:` to `complete` in the session file
2. Identify any decisions that should be promoted to `specs/` or `AGENTS.md`
3. Offer to move durable decisions to the right location
4. **Update `AGENTS.md`:**
   - Append a one-paragraph entry to the **Review Log** covering what was built,
     what changed, and any bugs fixed
   - Update **Next Steps** to reflect current state — remove completed items,
     add newly unblocked ones
   - Update **Technical Debt** if new deferred items were identified
5. Follow the standard Session Close Checklist (docs, deps, commit)
6. if the  `### Review Log` section of `AGENTS.md` exceeds 10 entries, archive all but the 5 most recent to `/CHANGELOG.md` (append, don't overwrite), then remove the archived entries from `AGENTS.md`

> `AGENTS.md` must be updated in the same commit as the session file closure.
> It is the living contract read at the start of every future session — if it
> drifts, every subsequent session starts with stale context.

### Authoring Workflow

Session files are typically drafted in Claude web and dropped into `.session/` before
a Claude Code session begins. The standard handoff:

1. Claude web session → produces `.session/YYYY-MM-DD-topic.md`
2. File dropped into repo
3. Claude Code session: `"Read .session/2025-04-24-topic.md and proceed"`

This keeps planning and implementation cleanly separated while maintaining a full
decision audit trail in version control.# Claude Module: Neo4j / Graph Standards

Cypher generation conventions, MERGE patterns, CALL {} rules, APOC conventions,
and constraint management for all projects that write to or read from Neo4j.

---

## Shared Neo4j Library — lifeos-neo4j

All lifeos projects that require a Neo4j connection must import from
`lifeos-neo4j` rather than implementing their own connection management.
This is the single source of truth for driver creation, profile loading,
capability detection, and ConnectionContext.

### Adding the dependency

In `pyproject.toml`:
```toml
[project]
dependencies = [
    "lifeos-neo4j @ file://../../packages/lifeos-neo4j",
    # adjust relative path based on project location
]
```

For projects outside the lifeos monorepo structure, use an absolute path
or a git reference once lifeos-neo4j is published:
```toml
"lifeos-neo4j @ git+https://github.com/pdrangeid/lifeos-neo4j@main"
```

### Public API
```python
from lifeos_neo4j.connection import (
    get_driver,           # raw Driver for simple cases
    get_context,          # ConnectionContext — preferred for most use
    get_default_kg_context,   # reads schemata.default_kg_profile
    get_default_meta_context, # reads schemata.default_meta_profile
)
from lifeos_neo4j.capability_detector import detect_capabilities, CapabilityProfile
from lifeos_neo4j.profiles import load_profiles
```

### ConnectionContext

Prefer `get_context()` over `get_driver()` — it carries `driver`,
`database`, and `profile_name` together so callers don't have to
track them separately:
```python
ctx = get_context("lifeos-kg", config_path)

# Capability detection is explicit and optional — not forced at construction
ctx.capabilities = detect_capabilities(ctx.driver, ctx.database)

# Use in session
with ctx.driver.session(database=ctx.database) as session:
    ...
```

### close_driver_after pattern

Any function that accepts an optional ConnectionContext must follow
this pattern — never close a context you didn't create:
```python
def my_operation(ctx: ConnectionContext | None = None) -> None:
    close_ctx_after = ctx is None
    if ctx is None:
        ctx = get_context("lifeos-kg", config_path)
    try:
        with ctx.driver.session(database=ctx.database) as session:
            ...
    finally:
        if close_ctx_after:
            ctx.driver.close()
```

### Integration testing

All projects using lifeos-neo4j follow the same integration test convention:

- Config: `~/.lifeos/test-profiles.yaml` — machine-local, never committed
- Credentials: `.env` in project root — `NEO4J_USER_TEST_NEO4J` / `NEO4J_PASSWORD_TEST_NEO4J`
- Skip condition: test skips gracefully if config or credentials absent
- `conftest.py` must call `load_dotenv()` before collection to ensure
  env vars are available at skipif evaluation time
```python
# tests/conftest.py
from dotenv import load_dotenv
load_dotenv()
```

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
- All string values escaped via `_escape()` — never f-string raw user data directly into Cypher
- Timestamps: use `datetime('ISO8601_STRING')` format, UTC by default
- Ensure consistant timestamps (by generating in python when practical - or top of cypher if inline) avoid generated transactionally (unless context demands granularity)
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
- **Don't** implement your own `get_driver()` or profile loader — import from lifeos-neo4j
- **Don't** hardcode Neo4j URIs or credentials anywhere — always profiles + .env
- **Don't** call `detect_capabilities()` inside `get_context()` — capability
  detection is explicit, callers opt in
- **Don't** close a ConnectionContext you didn't create
- **Don't** share sessions across major operations — one session per logical unit of work
- **Don't** store `ConnectionContext` as a module-level global — 
  construct at CLI parse time and pass down

---

## Project-Specific

> This section is maintained by the AI Assistant during coding sessions.

### Overview

Modular Python ingestion framework for loading data into Neo4j Aura from GCS (CSV)
and BigQuery. Core components: `Neo4jImporter` (batch Cypher execution with retry),
`GCSSource` / `BigQuerySource` (streaming data sources), and a config-driven runner
in `main.py` that wires sources, transforms, and Cypher together from `config.yaml`.

### Key Patterns

**GCSSource — two auth paths, zero code difference at call sites**

`GCSSource.__init__` reads `GCP_HMAC_ACCESS_KEY` / `GCP_HMAC_SECRET_KEY` from `.env`
via dotenv and selects the auth path automatically:

- **ADC (default):** uses `google-cloud-storage` `blob.open("r", newline="")` — true
  streaming, memory proportional to `batch_size` not file size.
- **HMAC / S3-interoperability:** uses `boto3` S3 client pointed at
  `https://storage.googleapis.com` with `s3v4` signing, wrapping the `StreamingBody`
  in `codecs.getreader("utf-8")` for a text stream. Install with
  `pip install aura-ingest-accelerator[hmac]`. `boto3` is lazy-imported inside the
  `if` branch — it is never required unless HMAC keys are present.

Both paths expose a `self._open_stream` context-manager callable consumed identically
in `get_batches()`. Supplying only one HMAC key raises `ValueError` immediately.

**Batch import pattern**

`Neo4jImporter.run_import()` drives `source.get_batches(batch_size)` and executes
each batch via `UNWIND $rows AS row`. Transient Neo4j errors (Aura scaling events)
are retried with exponential backoff up to `max_retries` (default 0 — fails immediately
so Cypher errors surface without delay; set to 3 for production imports where Aura
scaling events are possible).

**Transform pipeline**

Optional `transform_fn(row) -> dict | None` is applied per-row before the batch is
sent. Returning `None` skips the row. Transform functions are registered by name in
`TRANSFORMS` in `main.py` and referenced by the `transform` key in `config.yaml`.

### Known Issues / Tech Debt

- `GCSSource` with `blob.open()` yields inside a `with` block (generator + context
  manager). The stream is closed on generator exhaustion or `.close()`. Callers that
  abandon a partially-consumed generator (e.g. early `next()` preview calls in the
  notebook) should call `.close()` explicitly or use `next()` inside a `try/finally`.
  In practice the GC handles it, but it's worth noting.

### Review Log

**2026-05-03** — Public release preparation: added `PyYAML` to `pyproject.toml` and `poc_walkthrough.ipynb`; refactored `main.py` to use `typer` for CLI and `rich` for logging; removed root logging config from `importer.py`; created `ARCHITECTURE.md` as required by standards; updated `README.md` and walkthrough to prioritize `CREATE CONSTRAINT` over `CREATE INDEX` for identity properties; verified `uv` usage patterns across documentation.

**2026-04-28** — Added AI-assisted connector onboarding: created `.session/add-connector.md`
(fully pre-filled with real `BaseSource` signature, `build_source()` registration pattern,
`config.yaml` schema, and a worked skeleton modeled on `BigQuerySource`); added `## AI Session
Files` section to `.ai-standards.md` pointing agents at the session file; appended a "Using AI to Add
a New Connector" section to `poc_walkthrough.ipynb` with workflow steps, tool-specific tips
for The AI Coding Agent / Copilot / Codex, and a common-failures table. No source files modified.
