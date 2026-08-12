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

Modular Python ingestion framework for loading data into Neo4j Aura from GCS (CSV),
BigQuery, Databricks Unity Catalog, and Satisfactory `.sav` save files. Core
components: `Neo4jImporter` (batch Cypher execution with retry), `GCSSource` /
`BigQuerySource` / `DatabricksSource` / `SatisfactorySource` (data sources — the
first three stream, the last parses fully into memory), and a config-driven
runner in `main.py` that wires sources, transforms, and Cypher together from a
`config.yaml`-style file.

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

**DatabricksSource — PAT auth, lazy driver import**

`DatabricksSource.__init__` reads `DATABRICKS_SERVER_HOSTNAME` / `DATABRICKS_HTTP_PATH`
/ `DATABRICKS_TOKEN` from `.env` and raises `ValueError` immediately if any are
missing. `databricks.sql` is lazy-imported inside `get_batches()` (same convention
as `boto3` in `GCSSource`) — the `[databricks]` extra (`databricks-sql-connector`)
is never required unless a `databricks` job actually runs. Streams via
`cursor.fetchmany(batch_size)`, converting each row with `row.asDict()`. Validated
end-to-end against `samples.tpch.customer` (Unity Catalog sample data) into a local
Neo4j test instance — connector mechanics confirmed sound; PAT is POC-scope only,
no OAuth/service-principal auth yet.

**SatisfactorySource — one class, seven `extract` projections, full-parse cache**

`SatisfactorySource(save_path, extract)` parses a Satisfactory `.sav` file with the
optional `satisfactory-save` PyPI package (lazy-imported inside `_save()`, same
convention as `boto3`/`databricks.sql`) and yields one of seven named row shapes
selected by `extract`: `save`, `levels`, `classes`, `actors`, `inventory_stacks`,
`factory_links`, `power_links`. `save_path` accepts `${VAR}`-style env-var
references (e.g. `"${SATISFACTORY_SAVE_PATH}"` in `config-satisfactory.yaml`) —
`__init__` calls `load_dotenv()` then `os.path.expandvars()` itself, because this
repo's config loader does plain `yaml.safe_load` with no interpolation of its own.

Parsing is cached at module level, keyed on `(resolved_path, st_mtime_ns,
st_size)`, so all seven jobs against one save file parse the `.sav` exactly once
per process even though each job constructs its own `SatisfactorySource` instance.
Every object's owning actor is derived by string-splitting its save path on the
last `.` (e.g. `...Build_ConstructorMk1_C_123.Output0` → owner
`...Build_ConstructorMk1_C_123`) — components never store an explicit `Owner`
back-reference in this parser version.

Validated end-to-end (extract-only, no live Aura write) against a real ~4.2MB /
~55,000-object save (`FFD_autosave_2.sav`, ~1060 hours played): all seven
extracts ran clean and produced plausible row shapes and counts (31,255 actors,
6,075 factory links, 2,487 power links, 4,124 non-empty inventory stacks, 209
distinct classes). See Known Issues below for what's still unverified.

### Next Steps

- Swap the `"Databricks Table Import"` job in `config.yaml` from the
  `samples.tpch.customer` validation query to the actual customer Unity Catalog
  table/columns once provided — config-only change, no code expected.
- Before running that job past a small test batch, create the real identity-property
  uniqueness constraint for whatever label it merges on (see `README.md`'s
  Constraints section).
- Run `cypher/satisfactory_constraints.cypher`, then `config-satisfactory.yaml`
  with `batch_size: 10` (its current setting), against a real Aura target — this
  session validated the Python-side extracts only, not a live Cypher/Aura round
  trip. Bump `batch_size` to 1000 (500 for `factory_links`) once verified.
- Validate `factory_links` direction against ground truth per the session recipe
  in `.session/2026-08-12-satisfactory-source.md` step 9: pick one machine in
  Paul's save whose real inputs/outputs are known, confirm the graph agrees. The
  direction heuristic (see Known Issues) has not been empirically checked yet.
- GPL-3 licensing decision (see Known Issues) blocks merging this branch past a
  feature branch — do not merge to `develop` or `main` until resolved.

### Known Issues / Tech Debt

- `GCSSource` with `blob.open()` yields inside a `with` block (generator + context
  manager). The stream is closed on generator exhaustion or `.close()`. Callers that
  abandon a partially-consumed generator (e.g. early `next()` preview calls in the
  notebook) should call `.close()` explicitly or use `next()` inside a `try/finally`.
  In practice the GC handles it, but it's worth noting.
- The notebook's main walkthrough (sections 1–8) only ever imports `ClientNode`
  (via `NODE_CYPHER`) — it never runs the "Interactions" job from `config.yaml`,
  so the `INTERACTED_WITH` relationship is never populated by following the
  notebook top to bottom. The "6a. Exploring Your Data" section's traversal/
  aggregation examples depend on that relationship and are guarded with a `⚠️`
  callout + empty-result check rather than silently failing. If a future session
  wires the Interactions job into the main walkthrough (or the Appendix), this
  callout should be revisited/removed.
- **`SatisfactorySource` deliberately breaks the streaming contract every other
  source in this repo follows.** A save's cross-references (belt endpoints,
  power circuits) can't be resolved without the full object graph in memory
  first, so `get_batches()` parses everything before yielding anything. A
  large late-game save (10^5–10^6 objects) will occupy low single-digit GB of
  RAM during parse. This is an accepted, deliberate deviation, not an
  oversight — see `.session/2026-08-12-satisfactory-source.md`. If it becomes
  a real problem, the fix is a pre-flatten step (save → NDJSON on disk →
  existing file-based source), not an attempt to stream the parser.
- **`FGFactoryConnectionComponent` / `FGPipeConnectionComponent` have no
  `mDirection` property** — the session spec assumed one would exist and it
  doesn't (verified against a real save; the only property present is
  `mConnectedComponent`). `_extract_factory_links()` instead infers direction
  from the component's own path segment name: `Output*`/`Input*` on buildings
  are authoritative; ambiguous belt/pipe endpoints (`ConveyorAny*`,
  `PipelineConnection*`, `SnapOnly*`, `Connection*`) fall back to an
  index-parity guess (trailing digit `0` = inbound, `>=1` = outbound). This
  heuristic is **unvalidated against ground truth** — do this before trusting
  `FEEDS`/`SUPPLIES` direction for anything: pick one machine in-game whose
  real inputs/outputs are known and confirm the graph agrees.
- `satisfactory-save` writes some parser diagnostics (`[W] Unknown struct
  name "VehiclePathBlockReference"...`, malformed `mSpawnData` on
  `BP_CreatureSpawner` objects) directly to the process's stdout, not through
  Python's `logging` module — `logging.disable()` does not silence it. Noisy
  but non-fatal; expect it on every parse. Worth revisiting if it ever
  pollutes a script's stdout-based output contract.
- `satisfactory-save` and its only viable alternative are both **GPL-3.0**
  licensed; `aura-ingest-accelerator`'s own license line is currently
  commented out in `pyproject.toml` and the project is intended for public
  distribution. The `[satisfactory]` extra keeps this an opt-in dependency
  (same pattern as `[hmac]`'s `boto3`), which is a materially weaker coupling
  than vendoring — but it is Paul's call, not the agent's. **Do not merge this
  connector past a feature branch until the repo's license is decided.** If
  the answer comes back unfavorable, the fallback is a separate companion
  repo, not shipping it here.
- `satisfactory-save` publishes wheels for `manylinux_2_27+ x86_64` and
  `win_amd64` only — no macOS or aarch64 wheels. Those platforms fall back to
  the sdist and need a C++ toolchain; this affects anyone demoing from Apple
  Silicon.
- The "machine" vs "building" category split follows the session's literal
  rule (`Build_*` owning ≥1 factory connection → machine) rather than any
  gameplay notion of "produces something." On a real save this labels
  `Build_StorageContainerMk1_C` and `Build_ConveyorPole_C` as `machine`
  because they own `Output`/`Input` connection components — correct per spec,
  but worth flagging if it reads oddly in the teaching notebook later.

### Node Labels & Relationship Types — Satisfactory Connector

Per the Neo4j module's Relationship Type Governance rules — introduced by
`sources/satisfactory_source.py` / `config-satisfactory.yaml` /
`cypher/satisfactory_postimport.cypher`:

**Node labels:** `:Save`, `:Level`, `:Class`, `:Actor` (base label on every save
object), `:Building` (also `:Actor`), `:Machine` (also `:Building`), `:Conveyor`
(also `:Building`), `:Pipe` (also `:Building`), `:Item`, `:PowerCircuit`.

**Relationship types:** `HAS_LEVEL` (`Save`→`Level`), `CONTAINS` (`Level`→`Actor`),
`INSTANCE_OF` (`Actor`→`Class`), `FEEDS` (`Actor`→`Actor`, raw per-hop belt/pipe
chain — direction unvalidated, see Known Issues), `SUPPLIES` (`Machine`→`Machine`,
derived post-import, belts/pipes collapsed out), `ON_CIRCUIT` (`Actor`→`PowerCircuit`),
`HOLDS` (`Actor`→`Item`).

### Review Log

**2026-08-12** — Added Satisfactory save-game connector: `sources/satisfactory_source.py`
(`SatisfactorySource`, one class / seven `extract` projections — `save`, `levels`,
`classes`, `actors`, `inventory_stacks`, `factory_links`, `power_links` — lazy-imports
`satisfactory_save`, module-level parse cache keyed on path/mtime/size), registered in
`build_source()` in `main.py`, `[satisfactory]` extra added to `pyproject.toml`,
`SATISFACTORY_SAVE_PATH` documented in `env.sample`, `config-satisfactory.yaml` created
with all seven jobs at `batch_size: 10`, and `cypher/satisfactory_constraints.cypher` /
`cypher/satisfactory_postimport.cypher` created (uniqueness constraints; semantic-label
assignment + collapsed `SUPPLIES` edge). Before writing any extract, inspected a real save
(`FFD_autosave_2.sav`, ~55,000 objects) directly with the installed `satisfactory-save`
0.11.0 library — this caught a spec assumption that didn't hold (no `mDirection` property
on connection components; direction is name/index-encoded instead) and confirmed every
other field name used. All seven extracts smoke-tested clean against that real save
(Python-side only — no live Aura write this session, no Neo4j credentials configured).
Two things are explicitly unresolved and block merging past this feature branch: the
`factory_links` direction heuristic needs ground-truth validation against Paul's own
factory, and the parser's GPL-3.0 license needs a decision against this repo's own
(currently unset) license before any public-facing merge. See Known Issues above.

**2026-08-11** — Closed session `poc-walkthrough-query-intro`: added a new
"6a. Exploring Your Data — Basic Queries" section to `poc_walkthrough.ipynb`,
inserted between the Test Import verification cell and "7. Full Import" (8 new
cells: filtering with `MATCH`/`WHERE`, one-hop traversal via `INTERACTED_WITH`,
aggregation with `count`/`ORDER BY`, and a `RETURN` vs `RETURN DISTINCT` callout;
one GraphAcademy Cypher Fundamentals link embedded once). No existing cells
modified — diff is purely additive. Surfaced and documented a pre-existing gap
(see Known Issues above): the notebook's main flow never populates
`INTERACTED_WITH`, so the new traversal/aggregation examples return empty
results until the customer runs the "Interactions" job from `config.yaml`
themselves. `README.md` Quickstart updated to mention the new exploration step.

**2026-08-11** — Added Databricks Unity Catalog connector: `sources/databricks_source.py`
(`DatabricksSource`, PAT auth via `.env`, lazy-imports `databricks.sql`), registered in
`build_source()` in `main.py`, `[databricks]` extra added to `pyproject.toml`, and
`DATABRICKS_*` vars documented in `env.sample`. Validated end-to-end against a local
Neo4j test server using the Unity Catalog `samples.tpch.customer` sample table:
constraint creation, batched import (20 rows/2 batches), and node-count verification
all passed. `config.yaml` updated with the validated query/cypher; swapping in the
real customer table is deferred to a future session. `README.md` and `ARCHITECTURE.md`
updated to document the new source.

**2026-05-03** — Public release preparation: added `PyYAML` to `pyproject.toml` and `poc_walkthrough.ipynb`; refactored `main.py` to use `typer` for CLI and `rich` for logging; removed root logging config from `importer.py`; created `ARCHITECTURE.md` as required by standards; updated `README.md` and walkthrough to prioritize `CREATE CONSTRAINT` over `CREATE INDEX` for identity properties; verified `uv` usage patterns across documentation.

**2026-04-28** — Added AI-assisted connector onboarding: created `.session/add-connector.md`
(fully pre-filled with real `BaseSource` signature, `build_source()` registration pattern,
`config.yaml` schema, and a worked skeleton modeled on `BigQuerySource`); added `## AI Session
Files` section to `.ai-standards.md` pointing agents at the session file; appended a "Using AI to Add
a New Connector" section to `poc_walkthrough.ipynb` with workflow steps, tool-specific tips
for The AI Coding Agent / Copilot / Codex, and a common-failures table. No source files modified.
