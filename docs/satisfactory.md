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
   call, not something this connector can resolve on its own. This blocker is
   specific to the `.sav`-parsing half (`SatisfactorySource`) — `DocsSource`
   (below) needs no third-party parser at all and carries no such issue.
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
- Trains, rail networks, vehicle paths, drone ports, blueprint interiors.
- The "Welcome to Graphs" teaching notebook — see
  `.session/2026-08-12-satisfactory-source.md` for the planned arc, now that
  `Docs.json` enrichment (below) exists to build it on.
- Bundling any Coffee Stain game assets or extracted content in this repo —
  applies to both connectors.
- Resource-node identity (which ore, what purity) — see
  [Docs.json Enrichment — Known Issues](#known-issues-1) below. Not resolvable
  from either data source this repo reads.

---

## Docs.json Enrichment (2026-08-12)

A second connector, `DocsSource` (`sources/docs_source.py`), reads
Satisfactory's shipped game-data dump and loads the **logical layer** — item
classes, recipes, buildable metadata, schematics — then joins it to the
physical layer above via a `RUNS_RECIPE` edge sourced from the save. Built in
this repo (not a separate companion repo, despite the original session spec's
locked decision to keep it separate) — see
[Decisions Made This Session](#decisions-made-this-session) in
`.session/2026-08-12-docs-enrichment.md` for why. No third-party dependency:
the file is plain UTF-16 JSON with a handful of UE-struct-encoded string
fields, parsed with `re` from the standard library.

### Quick Start

```bash
# .env — no new pip extra needed
SATISFACTORY_DOCS_PATH=/path/to/CommunityResources/Docs   # dir, or a direct
                                                            # en-US.json path

# One-time schema addition (already folded into satisfactory_constraints.cypher)
# — Recipe.className and Schematic.className uniqueness constraints.

# Import (after config-satisfactory.yaml has already been run at least once —
# recipe_ingredients/recipe_products MATCH onto :Item nodes it creates, and
# the final job MATCHes onto its :Actor nodes)
uv run python main.py --config config-docs.yaml --debug

# After it finishes — item secondary labels + displayName denormalisation
# paste the "Logical-layer enrichment" section of
# cypher/satisfactory_postimport.cypher into Neo4j Browser
```

Finding the Docs folder:
- **Steam:** `<install>\CommunityResources\Docs\`
- **Epic:** `<install>\CommunityResources\Docs\`

The folder holds one file per locale (`en-US.json`, `de.json`, ...). Older
game versions shipped a single `Docs.json` — `DocsSource` resolves either
filename if given the directory, or accepts a direct path to the file.
**The file is UTF-16 with a BOM** — `DocsSource` opens it with
`encoding="utf-16"`; the default encoding fails or produces garbage.

### What Gets Extracted

Eight `extract` values against `DocsSource`, plus one new extract
(`machine_recipes`) added to the existing `SatisfactorySource` for the
save-side half of the join. Real row counts against the real game data file
(`en-US.json`, current game version) — see Live Test Run below for how these
differ from the original session spec's estimates, which were written from
memory/community docs for an unknown older game version.

| # | `extract` | Source | Rows (real) | Keys |
|---|---|---|---|---|
| 1 | `items` | Docs | 195 | `className, displayName, description, form, category, stackSize, sinkPoints, energyValue` |
| 2 | `buildables` | Docs | 539 | `className, displayName, description, powerConsumption, powerConsumptionExponent, manufacturingSpeed` |
| 3 | `recipes` | Docs | 317 | `className, displayName, durationSeconds, isAlternate` |
| 4 | `recipe_ingredients` | Docs | 665 | `recipeClassName, itemClassName, amount` |
| 5 | `recipe_products` | Docs | 354 | `recipeClassName, itemClassName, amount` |
| 6 | `recipe_machines` | Docs | 444 | `recipeClassName, buildableClassName` |
| 7 | `schematics` | Docs | 574 | `className, displayName, tier, type` |
| 8 | `schematic_unlocks` | Docs | 1016 | `schematicClassName, recipeClassName` |
| 9 | `machine_recipes` | Save (`SatisfactorySource`) | 459 | `instanceName, recipeClassName, clockSpeed` |

`recipes`/`recipe_ingredients`/`recipe_machines` exclude ~550 of the 872 raw
`FGRecipe` entries — building-construction and customisation recipes
(`mProducedIn` is empty or only `BP_BuildGun_C`/`FGBuildGun`), which have no
place in a recipe graph about *making things*, not *building things*.
`isAlternate` is `mDisplayName.startswith("Alternate:")` — confirmed 1:1
against the `Recipe_Alternate_*` classname-prefix convention on the real
file (110/110 agree).

### Graph model additions

**Node labels added:** `:Recipe`, `:Schematic`. **`:Item` gets one secondary
label from** `{RawResource, Ingot, Part, Fluid, Ammo, Equipment, Consumable}`
(`Fluid` can co-occur with `RawResource` — Crude Oil and Water are both).

**Relationship types added:** `CONSUMES` (`Recipe`→`Item`, `{amount}`),
`PRODUCES` (`Recipe`→`Item`, `{amount}`), `PRODUCIBLE_IN` (`Recipe`→`Class`),
`UNLOCKS` (`Schematic`→`Recipe`), `RUNS_RECIPE` (`Actor`→`Recipe`,
`{clockSpeed}` — **the** physical/logical join edge, sourced from
`mCurrentRecipe`/`mCurrentPotential` on each manufacturer instance in the
save).

**`buildables` enriches existing `:Class` nodes** (matched by `shortName`,
which the physical-layer `classes` extract already sets — no new `:Class`
identity scheme needed) rather than creating a separate label. A buildable
type never actually built in the current save gets a new `:Class` node with
no `typePath` — expected; `class_type_path_unique` only constrains nodes that
*have* the property.

### The join, and what almost broke it

Per the original session spec: the save and Docs.json reference the same
classes in different string shapes, and every join silently returns zero
rows if both sides don't normalise to the same key. Two real breaks were
found and fixed **before** any join Cypher ran, by inspecting the live
Neo4j instance's actual property values rather than trusting either the
session spec or the extractor's own output in isolation:

1. **The session spec's own `parse_item_amounts()` regex didn't work.**
   `[\'"]?` (zero-or-one quote) doesn't consume the real format's *two*
   trailing quote characters back to back — a UE single-quote closing the
   class path immediately followed by the JSON double-quote closing the
   `ItemClass` string value: `...Desc_IronIngot_C'",Amount=3`. Verified
   against all 872 real `FGRecipe` entries (1738 ingredient/product fields)
   before trusting the fix (`['"]*`, zero-or-more) — 0 mismatches.
2. **Pre-existing `:Item.className` was a full save PathName, not a short
   class name** — `SatisfactorySource._extract_inventory_stacks()` (from the
   prior session) had never been exercised against `DocsSource`'s short-name
   convention, because `DocsSource` didn't exist yet. Confirmed via a live
   query (`MATCH (i:Item) RETURN i.className`) before writing any join
   Cypher: all 78 existing values were full paths like
   `/Game/FactoryGame/Resource/Parts/Cement/Desc_Cement.Desc_Cement_C`. Fixed
   two ways: (a) a one-time migration
   (`SET i.className = last(split(i.className, '.'))`) against the live
   instance, confirmed collision-free first (78 distinct in, 78 distinct
   out); (b) `_extract_inventory_stacks()` now applies
   `class_names.normalise_class()` going forward, so future imports don't
   regress it.

`sources/class_names.py` (`normalise_class`, `parse_item_amounts`,
`parse_quoted_class_list`) is shared between both connectors and unit-tested
against real strings pulled from the live file/save
(`tests/test_class_names.py`) rather than the spec's own examples, since the
spec's regex was one of the things found broken.

### Scope change: resource-node identity dropped

The session spec's `resource_node_yields` extract (`ResourceNode` → `YIELDS`
→ `Item`, "resource class + purity on the node instance") **cannot be built
from data this repo has access to.** Verified directly against the real
save: `BP_ResourceNode_C` instances (459 in the test save) carry only
`mResourcesLeft` (a depletion counter); `BP_ResourceDeposit_C` (2,404 hand-
mining deposits) carry only `mResourceDepositTableIndex`, an index into a
static game table present in neither the save nor Docs.json. The game
resolves resource identity from static level data at runtime, not from
anything serialized. `:ResourceNode` and `:EXTRACTS_FROM` — which the
session's target traversal assumed already existed from the physical-layer
import — don't exist either; miners currently fall into `category='other'`
same as every other non-building actor.

Decision (with Paul, since this changes the session's stated acceptance
test): drop the ore-in-ground leg entirely rather than approximate it.
The acceptance traversal now starts from a `Machine` instead of a
`ResourceNode`:

```cypher
MATCH (m1:Machine)-[:SUPPLIES*1..6]->(m2:Machine)-[:RUNS_RECIPE]->(r:Recipe)-[:PRODUCES]->(item:Item)
RETURN m1.displayName, m2.displayName, r.displayName, item.displayName
LIMIT 25
```

A real fix (if ever needed) requires an external static resource-node
position/purity database — the kind of thing community tools like
Satisfactory Calculator maintain — which is a new class of dependency this
repo hasn't taken on and would need its own decision.

---

## Live Test Run — Docs Enrichment (2026-08-12)

Same local Neo4j instance as the save connector's live test, run
immediately after it in the same session.

**Constraints:** `recipe_class_name_unique`, `schematic_class_name_unique`
added to `cypher/satisfactory_constraints.cypher`; all 8 constraints (6
original + 2 new) confirmed via `SHOW CONSTRAINTS`.

**Import — `config-docs.yaml` at `batch_size: 10`, 9 jobs (8 Docs.json +
1 save-side):**

| Node label | Count after import |
|---|---|
| `Item` | 196 (78 pre-existing + 195 from Docs, minus overlap, plus 1 save-only item with no Docs entry) |
| `Recipe` | 317 |
| `Schematic` | 574 |
| `Class` | 671 (was 209 before this import — 539 buildable rows, most never built in this save) |

| Relationship | Extracted rows | Created | Gap, explained |
|---|---|---|---|
| `CONSUMES` | 665 | 665 | — |
| `PRODUCES` | 354 | 354 | — |
| `PRODUCIBLE_IN` | 444 | 291 | 153 rows target `BP_WorkBenchComponent_C`/`BP_WorkshopComponent_C`/`FGBuildableAutomatedWorkBench` — manual-crafting stations, not `FGBuildable*` classes, so they have no `:Class` node from the `buildables` extract. Correct, not a bug. |
| `UNLOCKS` | 1016 | 339 | 677 rows reference building-construction recipes (walls, ramps, vehicles, power switches, ...) — the exact set excluded from `:Recipe` by design (see "What Gets Extracted" above). Correct, not a bug. |
| `RUNS_RECIPE` | 459 | 459 | — |

Per Instruction 8's rule ("a large gap means normalisation is dropping
matches — stop and fix before proceeding"): both gaps were investigated
before moving on, by cross-referencing the missing rows' class names against
what actually exists in the graph, not assumed benign.

**Postimport pass:** 196 `:Item` nodes got exactly one of
`{RawResource, Ammo, Equipment, Consumable, Ingot, Part}` (29/16/17/5/6/123)
plus `Fluid` as an overlay label on 15 of them. 14,809 `Actor.displayName`
properties set from `Class.displayName` (buildable-typed actors only —
non-building actors like creatures/foliage/pickups have no `:Class`
displayName to inherit, hence the sanity-check number below).

**Sanity checks** (Instruction 10):

| Check | Count | Explanation |
|---|---|---|
| Machines with no `RUNS_RECIPE` | 1,780 of 2,239 | Miners/extractors/generators don't have `mCurrentRecipe` (they auto-produce, no recipe selection) — 2,239 − 1,780 = 459, matching `machine_recipes` exactly. |
| Recipes with no `PRODUCES` | 0 | Every production recipe has an output — expected. |
| Actors with no `displayName` | 16,268 of 31,077 | Non-buildable actors (creatures, foliage, resource nodes, pickups, `FGBlueprintProxy`, `FGConveyorChainActor`) have no `:Class.displayName` to inherit — the same `category='other'` set from the save connector's own actor breakdown. |

**Acceptance traversal:** ran successfully — e.g. `Constructor` running
`Alternate: Stitched Iron Plate` feeds forward through belts/splitters to an
`Assembler` producing `Reinforced Iron Plate`. Confirms the physical
(`SUPPLIES`) and logical (`RUNS_RECIPE`→`PRODUCES`) layers connect through a
real multi-hop path in Paul's actual factory.

**In-game spot-check — not yet done.** Needs Paul's own eyes on the game,
not something verifiable from the graph alone. A concrete candidate handed
off for this: `Build_ConstructorMk1_C_2146938608` at world position
`(303800, -170500, 6200)`, graph says `Iron Plate` recipe at 75% clock
(3 Iron Ingot → 2 Iron Plate). Confirming this (or any similarly overclocked
machine) against the in-game UI would close out the literal ground-truth
check this connector has deferred since its first session.

## Known Issues

- **Resource-node identity is unrecoverable from either data source.** See
  "Scope change: resource-node identity dropped" above — this is the
  Docs-enrichment-specific instance of the same "spec assumption didn't
  survive contact with a real save" pattern as the `factory_links` direction
  heuristic in the save connector.
- **`Ingot` vs `Part` is a `displayName`-suffix heuristic**
  (`ENDS WITH 'Ingot'`), not something Docs.json states authoritatively.
  Same caveat class as the `FEEDS` direction heuristic — worth re-checking
  if an item ever gets mislabeled in practice (e.g. a future item legitimately
  named "... Ingot Something").
- **`buildables` includes every `FGBuildable*` native class**, not just
  production machines — walls, foundations, ramps, and other architecture
  pieces get `:Class.displayName`/`.description` set too (they just have
  `null` power/speed). This is intentional (Instruction 9 wants `displayName`
  denormalised onto every built `:Actor`, not only machines) but means
  `buildables` row counts (539) are much higher than the original session
  spec's ~300 estimate — real data, not a bug.
- **Companion-repo decision reversed for this session only.** The spec's
  locked decision to build `DocsSource` in a separate `satisfactory-graph`
  repo was not followed — no such repo exists yet, and Paul chose to keep
  building here since `DocsSource` (unlike the save connector) has no GPL
  dependency to isolate. If a companion repo gets created later, both
  connectors move together, not just this one — see
  `.session/2026-08-12-docs-enrichment.md` Decisions Made.
