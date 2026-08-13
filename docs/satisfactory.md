# Satisfactory Save-Game Connector

Not part of the customer-facing POC kit — this is an internal/demo connector kept
out of `README.md` and `ARCHITECTURE.md` on purpose. It reads a [Satisfactory](https://www.satisfactorygame.com/)
`.sav` file and loads it into Neo4j Aura as a graph, using the exact same
`BaseSource` / `Neo4jImporter` / `config.yaml` pipeline as every other source in
this repo. It exists because a Satisfactory save genuinely *is* a graph on disk
(buildings own connection components that reference the connection they're
paired with on another building — belts and power lines are literally adjacency
lists) — which makes it a good teaching artifact. See the "Welcome to Graphs"
notebook idea in `.session/2026-08-12-satisfactory-source.md` for where this is
headed.

**Do not merge this connector's branch to `develop` or `main` until the two
blockers below are resolved.** See the PR: https://github.com/neo4j-field/aura-ingest-accelerator/pull/1

---

## Blockers

1. **GPL-3.0 licensing.** The parser this connector depends on
   (`satisfactory-save`, and its only real alternative) is GPL-3.0 licensed.
   This repo's own license is currently unset (commented out in
   `pyproject.toml`) and the project is intended for public distribution.
   Keeping `satisfactory-save` behind the optional `[satisfactory]` extra
   (same pattern as `[hmac]`'s `boto3`) means the accelerator neither bundles
   nor links GPL code by default — but the license decision itself is a human
   call, not something this connector can resolve on its own.
2. ~~`factory_links` direction is unvalidated.~~ **Structurally validated
   2026-08-12** — see [Live Test Run](#live-test-run-2026-08-12) below. Not a
   literal in-game eyeball check (the session's original instruction #9), but
   class-level topology checks that would have caught a systematically wrong
   heuristic did not find one.

---

## Quick Start

```bash
uv pip install -e .[satisfactory]

# .env
SATISFACTORY_SAVE_PATH=/path/to/YourSave.sav
NEO4J_URI=neo4j://127.0.0.1:7687   # or neo4j+s://... for Aura
NEO4J_USER=neo4j
NEO4J_PASSWORD=...

# One-time schema setup — run against the target instance
cat cypher/satisfactory_constraints.cypher | # paste into Neo4j Browser, or:
uv run python -c "from neo4j import GraphDatabase; ..." # see below for a scripted runner

# Import (no "run" subcommand — main.py is a single-command Typer app)
uv run python main.py --config config-satisfactory.yaml --debug

# After the import finishes — semantic labels + collapsed SUPPLIES edge
# paste cypher/satisfactory_postimport.cypher into Neo4j Browser
```

There's no built-in `.cypher` file runner in this repo (constraints/postimport
scripts are meant for Neo4j Browser or `cypher-shell`). If scripting it, split
on `;` after stripping full-line `//` comments and run each statement in its
own `session.run()` call — see the "Live Test Run" section below for exactly
what was used to validate this connector.

Finding your save file:
- **Windows:** `%LOCALAPPDATA%\FactoryGame\Saved\SaveGames\<steam-id>\`
- **Linux (WSL, Windows install):** `/mnt/c/Users/<you>/AppData/Local/FactoryGame/Saved/SaveGames/<steam-id>/`
- **Linux (Steam Proton):** `~/.steam/steam/steamapps/compatdata/526870/pfx/drive_c/users/steamuser/AppData/Local/FactoryGame/Saved/SaveGames/<steam-id>/`

`SatisfactorySource` expands `${VAR}`-style references in `save_path` itself
(via `os.path.expandvars`, after calling `load_dotenv()`) — this repo's config
loader does plain `yaml.safe_load` with no interpolation of its own, so
`config-satisfactory.yaml` writes `save_path: "${SATISFACTORY_SAVE_PATH}"` and
the connector resolves it at construction time.

---

## What Gets Extracted

One `SatisfactorySource(save_path, extract)` class, seven `extract` values —
each is a separate `config-satisfactory.yaml` job, run in this dependency
order (nodes before edges):

| # | `extract` | Row shape | Emits |
|---|---|---|---|
| 1 | `save` | `saveId, sessionName, playDurationSeconds, saveVersion, buildVersion, savedAtEpochMillis` | 1 row |
| 2 | `levels` | `saveId, levelName, isPersistent` | ~10^1–10^3 rows (world-partition sublevels) |
| 3 | `classes` | `typePath, shortName, category` | every distinct class in the save |
| 4 | `actors` | `instanceName, typePath, levelName, category, posX/Y/Z, rotX/Y/Z/W, scaleX/Y/Z` | every actor (not component) |
| 5 | `inventory_stacks` | `ownerInstanceName, itemClass, slotIndex, count` | non-empty inventory slots only |
| 6 | `factory_links` | `fromInstanceName, toInstanceName, kind` (`conveyor`\|`pipe`) | one row per directed belt/pipe hop |
| 7 | `power_links` | `instanceName, circuitId` | one row per actor on a power circuit |

The whole `.sav` file is parsed once and cached at module level, keyed on
`(resolved_path, st_mtime_ns, st_size)` — all seven jobs against the same file
share one parse, because cross-references (belt endpoints, power circuits)
can't be resolved without the full object graph in memory. This is a
deliberate deviation from every other source in this repo, which streams with
memory proportional to `batch_size`. See [Known Issues](#known-issues) below.

### Graph model

**Node labels:** `:Save`, `:Level`, `:Class`, `:Actor` (base label on every
save object), `:Building` (also `:Actor`), `:Machine` (also `:Building`),
`:Conveyor` (also `:Building`), `:Pipe` (also `:Building`), `:Item`,
`:PowerCircuit`.

**Relationship types:** `HAS_LEVEL` (`Save`→`Level`), `CONTAINS`
(`Level`→`Actor`), `INSTANCE_OF` (`Actor`→`Class`), `FEEDS` (`Actor`→`Actor`,
raw per-hop belt/pipe chain), `SUPPLIES` (`Machine`→`Machine`, derived
post-import, belts/pipes collapsed out), `ON_CIRCUIT` (`Actor`→`PowerCircuit`),
`HOLDS` (`Actor`→`Item`).

`:Actor` gets a `category` property (`building`, `machine`, `conveyor`,
`pipe`, `power`, `player`, `other`) derived from the class short name — see
`_category_for()` in `sources/satisfactory_source.py`. `cypher/satisfactory_postimport.cypher`
turns that property into real labels and materialises `SUPPLIES` by collapsing
any `FEEDS` chain that passes only through `:Conveyor`/`:Pipe` nodes.

### The non-obvious part: `factory_links` direction

Buildings don't reference each other directly. The chain is:

```
Building A
  └── owns FGFactoryConnectionComponent "…Build_ConstructorMk1_C_123.Output0"
        └── mConnectedComponent -> "…Build_ConveyorBeltMk3_C_456.ConnectionAny0"
                                     └── owned by Building B (or another belt)
```

The original session spec (written before any real save had been inspected)
assumed a `mDirection` property existed on the connection component. **It
doesn't** — verified directly against a real save (`FFD_autosave_2.sav`, 
~55,000 objects): the only property present on
`FGFactoryConnectionComponent` / `FGPipeConnectionComponent` is
`mConnectedComponent`. Direction is instead read from the component's own
path segment name:

- `Output*` → authoritative source (building side)
- `Input*` → authoritative sink (building side)
- `ConveyorAny*`, `PipelineConnection*`, `SnapOnly*`, `Connection*` (ambiguous
  belt/pipe endpoints) → index-parity guess: trailing digit `0` = inbound,
  `>=1` = outbound

Implementation: `_extract_factory_links()` in `sources/satisfactory_source.py`.
Only components classified "outbound" emit a row (pointing at their partner),
which naturally produces exactly one `FEEDS` row per physical connection with
no separate dedup pass needed.

An actor's owning component (and a component's owning actor) is never an
explicit field in this parser version — it's derived by string-splitting the
save path on the last `.` (e.g. `...Build_ConstructorMk1_C_123.Output0` →
owner `...Build_ConstructorMk1_C_123`).

---

## Live Test Run (2026-08-12)

Full end-to-end validation against a real save and a real (local) Neo4j
instance — the first live run since the connector was built.

**Setup:** `FFD_autosave_2.sav` (~4.2MB, ~1060 hours played, ~54,978 save
objects), local Neo4j (`neo4j://127.0.0.1:7687`), `aura-ingest-accelerator`
`.venv` on WSL2.

**Two things fixed to make the run possible:**
- `.env`'s `SATISFACTORY_SAVE_PATH` was Windows-style
  (`%LOCALAPPDATA%\...`, missing the `SaveGames` path segment) — doesn't
  resolve under WSL. Fixed to the real `/mnt/c/...` path.
- `config-satisfactory.yaml`'s header comment said
  `uv run python main.py run --config ...` — `main.py` is a single-command
  Typer app, so `run` as a literal subcommand argument fails
  (`Got unexpected extra argument (run)`). Corrected to
  `uv run python main.py --config ...`.

**Constraints:** All 6 from `cypher/satisfactory_constraints.cypher` created
successfully (`SHOW CONSTRAINTS` confirmed).

**Import — batch_size 10 (first pass), then production batch_size (1000,
500 for factory_links) against a cleared DB:** Both runs produced byte-identical
final counts, confirming batch size has no effect on correctness:

| Node label | Count |
|---|---|
| `Actor` | 31,077 |
| `Level` | 3,337 |
| `Class` | 209 |
| `Item` | 78 |
| `PowerCircuit` | 35 |
| `Save` | 1 |

| Relationship | Count |
|---|---|
| `CONTAINS` | 31,077 |
| `INSTANCE_OF` | 31,077 |
| `HAS_LEVEL` | 3,337 |
| `FEEDS` | 6,075 |
| `ON_CIRCUIT` | 2,408 |
| `HOLDS` | 1,708 |

**Production-batch-size timing (localhost, no network latency — expect
substantially slower against a real Aura endpoint):** 7.37s wall clock,
~532MB peak RSS for the whole process (parse + import). Well under the "low
single-digit GB" estimate in the original session spec for this save's size
(~55K objects is mid-size — a late-game 10^6-object save will be considerably
heavier).

**Post-import pass** (`cypher/satisfactory_postimport.cypher`): labels
assigned (4,717 `Building`, 4,478 `Machine`, 5,992 `Conveyor`, 2,866 `Pipe`),
1,785 `SUPPLIES` edges materialized. Hop-count histogram peaks sharply at 2
(1,530 edges — one belt segment between two machines) with a long tail down
to a handful of 100+-hop backbone runs — the shape you'd expect from real
belt-run lengths, not noise.

**Direction heuristic — structural validation:**

| Building class | n | FEEDS out | FEEDS in | Expected |
|---|---|---|---|---|
| `Build_MinerMk1` | 1 | 1 | 0 | Miners only produce — 0 in is correct |
| `Build_MinerMk2` | 25 | 24 | 0 | Same (1 miner unconnected/idle) |
| `Build_SmelterMk1` | 138 | 138 | 137 | ~1:1 in/out — 1 ore in, 1 ingot out |
| `Build_ConstructorMk1` | 180 | 179 | 178 | ~1:1 in/out — 1 recipe in, 1 out |

If the direction heuristic were systematically reversed, miners would show
`FEEDS` edges flowing *into* them (nonsensical — they have no input
connection at all) instead of 0. They don't. This is not the literal
ground-truth check the original session instructions called for (picking one
machine in Paul's own game and eyeballing its real inputs/outputs), but it's
strong evidence the heuristic is directionally sound for the common
building↔belt case, which is the majority of the graph.

**Not yet done:** the literal in-game eyeball check against one specific
machine. **No live check against an actual Aura instance** (only local
Neo4j) — expect materially different timing due to network round-trips per
batch; consider raising `batch_size` further or increasing
`Neo4jImporter`'s `max_retries` (default 0) for a real Aura run.

---

## Known Issues

- **Deliberate non-streaming.** Every other source in this repo streams —
  memory proportional to `batch_size`, not input size.
  `SatisfactorySource` can't: a save's cross-references can't be resolved
  without the full object graph in memory first. Accepted tradeoff, not an
  oversight. If it becomes a real problem on very large saves, the fix is a
  pre-flatten step (save → NDJSON on disk → existing file-based source), not
  an attempt to stream the parser.
- **`satisfactory-save` writes parser diagnostics straight to process
  stdout**, not through Python's `logging` module — `logging.disable()` does
  not silence it (`[W] Unknown struct name "VehiclePathBlockReference"...`,
  malformed `mSpawnData` on `BP_CreatureSpawner` objects). Noisy but
  non-fatal; expect it on every parse.
- **Duplicate `instanceName` rows in the `actors` extract.** Observed 178
  duplicates out of 31,255 extracted rows against the real test save (mostly
  `BP_CreatureSpawner` and resource-node actors like `BP_Crystal*`) —
  `allSaveObjects()` appears to surface some actors from more than one
  internal pool. Harmless: the `MERGE` on `instanceName` correctly collapses
  them to one node, which is exactly why the actual `Actor` node count
  (31,077) is lower than the extracted row count (31,255).
- **"Machine" category is literal, not gameplay-accurate.** The rule (`Build_*`
  owning ≥1 factory connection → `machine`) labels `Build_StorageContainerMk1_C`,
  `Build_ConveyorPole_C`, `Build_ConveyorPoleWall_C`, etc. as `:Machine` because
  they own `Output`/`Input`/pass-through connection components — correct per
  the literal spec, not correct per "does this building produce something."
  In practice, conveyor poles end up with zero `FEEDS` edges at all (they're
  topologically isolated — 814 of the 2,239 `:Machine` nodes in the test save
  have no `Conveyor`/`Pipe` neighbor, and poles account for the majority of
  those), so this doesn't corrupt the `SUPPLIES` collapse — it just means
  "machine" isn't a reliable filter for "thing with a recipe" if this ever
  feeds a teaching notebook.
- **GPL-3.0.** See Blockers above.
- **No macOS/aarch64 wheels.** `satisfactory-save` publishes wheels for
  `manylinux_2_27+ x86_64` and `win_amd64` only — other platforms fall back
  to the sdist and need a C++ toolchain.

---

## Out of Scope

- Writing back to `.sav` files — read-only, always.
- `Docs.json` enrichment (recipe I/O, power draw, real item display names) —
  phase 2, separate connector, requires reading from the user's game install.
- Trains, rail networks, vehicle paths, drone ports, blueprint interiors.
- The "Welcome to Graphs" teaching notebook — see
  `.session/2026-08-12-satisfactory-source.md` for the planned arc once
  `Docs.json` enrichment exists.
- Bundling any Coffee Stain game assets or extracted content in this repo.
