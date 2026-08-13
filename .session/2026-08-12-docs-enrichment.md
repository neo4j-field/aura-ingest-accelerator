---
Status: complete
Date: 2026-08-12
Topic: docs-enrichment
---

# Session: Docs.json Enrichment Layer
# satisfactory-graph (companion repo)

---

## Goal

Add a `DocsSource` connector that reads Satisfactory's shipped game-data dump
(`CommunityResources/Docs/en-US.json`) and loads the **logical layer** of the graph — items,
recipes, buildable metadata, and schematics — then join it to the existing **physical layer**
already imported from the save file. The deliverable is the connector, six new extracts, the
class-name normalisation function that makes the join work, a post-import pass that assigns
item-category secondary labels and denormalises display names, and a validation query set
proving the two layers actually connect. Success condition: a single Cypher traversal can
follow iron ore from a specific resource node in the world, through the physical machines that
process it, to the item classes those machines' recipes produce.

---

## Context & Constraints

### The two-layer model — read this before writing any Cypher

The single most important constraint in this session. There are two distinct graphs here and
edges must not cross between them except through the designated join edges.

**Layer 1 — Physical (instances; already imported, do not modify)**

Every node is one specific thing that exists at coordinates in the world. Thousands of them.

```
(:ResourceNode)<-[:EXTRACTS_FROM]-(:Miner:Machine)-[:SUPPLIES]->(:Smelter:Machine)
```

**Layer 2 — Logical (types; this session)**

Every node is a *class*. There is exactly one `Iron Ore` node in the entire graph, one
`Iron Plate` recipe node. Hundreds of them, not thousands.

```
(:Recipe)-[:CONSUMES {amount}]->(:Item)
(:Recipe)-[:PRODUCES {amount}]->(:Item)
(:Recipe)-[:PRODUCIBLE_IN]->(:Class)
(:Schematic)-[:UNLOCKS]->(:Recipe)
```

**The join edges — the entire point of this session**

| Edge | Source | Meaning |
|---|---|---|
| `(:Machine)-[:RUNS_RECIPE]->(:Recipe)` | `mCurrentRecipe` on the machine instance **in the save** | This physical constructor is set to build Iron Plates |
| `(:ResourceNode)-[:YIELDS]->(:Item)` | resource class on the node instance | This specific ore patch produces Iron Ore |
| `(:Actor)-[:INSTANCE_OF]->(:Class)` | already exists | |
| `(:Actor)-[:HOLDS]->(:Item)` | already exists (inventory) | |

**What NOT to build.** Do not create an edge that puts an `:Item` node inside a physical
supply path — e.g. `(:ResourceNode)-[:SUPPLIES]->(:Item)-[:SUPPLIES]->(:Machine)`. It is
tempting because it reads like the story you want to tell, but `:Item` is a type node with one
instance per item class. Wiring it into the physical layer turns `Iron Ore` into a supernode
with tens of thousands of relationships, makes every variable-length traversal route through
it, and destroys the `SUPPLIES` topology built in the previous session. The ore-to-plate story
is told by *traversing both layers via the join edges*, not by flattening them into one.

### Display names are properties, not labels

`Build_ConstructorMk1_C` → `displayName: "Constructor"` as a **property** on the `:Class`
node. Labels are for filtering and index selection; nobody will ever write
`MATCH (n:Constructor)`. Denormalise a copy of `displayName` onto each `:Actor` in the
post-import pass — Bloom, GDS, and the teaching notebook all want it locally available without
a hop.

Item **categories** are legitimate secondary labels, because they are a small closed
vocabulary you genuinely filter on: `:Item:RawResource`, `:Item:Ingot`, `:Item:Part`,
`:Item:Fluid`, `:Item:Ammo`, `:Item:Equipment`, `:Item:Consumable`.

### Locked decisions

- **Never vendor the game data file.** `en-US.json` is Coffee Stain's content. Read it from
  the user's install path via `SATISFACTORY_DOCS_PATH` in `.env`. Do not commit it, do not
  commit a derived extract of it, do not add it to test fixtures. Ship a tiny hand-authored
  fixture with 2 items and 1 recipe for tests instead.
- **This lives in the companion repo, not `aura-ingest-accelerator`.** Same reasoning as the
  save connector — keeps the field-org accelerator's dependency graph clean.
- **No third-party docs parser.** Unlike the `.sav` format, this file is plain JSON. The only
  hard part is the string-encoded ingredient arrays, which is ~20 lines of regex. Adding an
  npm-ecosystem dependency for that is not worth it.
- **Same `extract`-per-projection pattern** as `SatisfactorySource`. Same module-level parse
  cache keyed on `(path, mtime_ns, size)`.
- **Recipes are imported in full** — all ~1500, including alternates the player hasn't
  unlocked. The `:Schematic` layer tells you which are unlocked; filtering at ingest would
  throw away the ability to ask "what could I build if I unlocked X."

### Out of scope

- Icons / images (`mSmallIcon` paths point into game assets — not redistributable).
- Building-cost recipes and customisation recipes (filter these out — see Gotchas).
- Power-grid modelling, throughput, or clock-speed math. Properties get imported; simulation
  does not.
- Trains (separate session).
- The teaching notebook (separate session — but this session unblocks it).

### Reference files

- `sources/satisfactory_source.py` — the connector pattern to mirror exactly
- `cypher/satisfactory_postimport.cypher` — extend, don't replace
- Wiki reference: `https://satisfactory.wiki.gg/wiki/Community_resources`

---

## Relevant Specs / Schemas / Examples

### File location and encoding

```
<install>/CommunityResources/Docs/en-US.json
```

Steam: `C:\Program Files (x86)\Steam\steamapps\common\Satisfactory\CommunityResources\Docs\`
Epic: `C:\Program Files\Epic Games\Satisfactory\CommunityResources\Docs\`

The Docs folder holds one file per locale (`en-US.json`, `de.json`, `pt-BR.json`, …). Older
game versions shipped a single `Docs.json` — support both filenames when resolving the path.

**The file is UTF-16 with a BOM.** Open it as `encoding="utf-16"` (which handles the BOM and
byte order automatically). `json.load(open(path))` with default encoding will fail or produce
garbage — this is the single most common way people waste an hour on this file.

```python
import json
with open(docs_path, encoding="utf-16") as f:
    docs = json.load(f)
```

### Top-level structure

An array of native-class groupings:

```json
[
  {
    "NativeClass": "Class'/Script/FactoryGame.FGRecipe'",
    "Classes": [ { "ClassName": "Recipe_IronPlate_C", "mDisplayName": "Iron Plate", ... } ]
  },
  {
    "NativeClass": "Class'/Script/FactoryGame.FGItemDescriptor'",
    "Classes": [ { "ClassName": "Desc_IronOre_C", "mDisplayName": "Iron Ore", ... } ]
  }
]
```

Native classes of interest:

| NativeClass contains | Yields |
|---|---|
| `FGRecipe` | recipes |
| `FGItemDescriptor`, `FGItemDescriptorBiomass`, `FGItemDescriptorNuclearFuel`, `FGConsumableDescriptor`, `FGEquipmentDescriptor`, `FGAmmoType*` | items |
| `FGResourceDescriptor` | raw resources (subset of items) |
| `FGBuildingDescriptor`, `FGBuildable*` | buildables |
| `FGSchematic` | unlocks / milestones |

Do not hardcode this list from memory — enumerate the distinct `NativeClass` values from the
actual file first (Instruction 2) and build the mapping from what's there.

### Ingredient parsing — the one genuinely fiddly part

`mIngredients` and `mProduct` are **strings containing a serialised UE struct array**, not
JSON arrays:

```
((ItemClass="/Script/Engine.BlueprintGeneratedClass'/Game/FactoryGame/Resource/Parts/IronIngot/Desc_IronIngot.Desc_IronIngot_C'",Amount=3))
```

Parse approach: strip the outer `((` and `))`, split on `),(`, then per entry regex out the
short class name and the amount.

```python
import re

_ITEM_RE = re.compile(r'ItemClass=.*?[\'"]?([A-Za-z0-9_]+_C)[\'"]?\s*,\s*Amount=(\d+)')

def parse_item_amounts(raw: str) -> list[tuple[str, int]]:
    """Parse an mIngredients / mProduct string into [(className, amount), ...]."""
    if not raw:
        return []
    return [(m.group(1), int(m.group(2))) for m in _ITEM_RE.finditer(raw)]
```

Validate this against the real file before trusting it — quoting style has changed between
game versions and the regex above is written to be tolerant of that, but tolerant is not the
same as correct.

### Gotchas that will silently produce wrong data

1. **Fluid amounts are ×1000.** Recipes involving `RF_LIQUID` or `RF_GAS` items store amounts
   in millilitres. A recipe showing `Amount=30000` of water means 30 m³. Divide by 1000 when
   the item's `mForm` is liquid or gas. This requires items to be imported *before* recipes,
   so the form is known at recipe-parse time. **This is why extract order matters.**
2. **`mManufactoringDuration` is a string**, not a number (and yes, that's the game's
   spelling). `float()` it. Same for several other numeric fields — never assume a JSON
   number.
3. **`mStackSize` is an enum string** (`SS_MEDIUM`, `SS_BIG`, …), not an integer. Either map
   it to the real integer or store the enum verbatim — do not `int()` it.
4. **Filter out non-production recipes.** The `FGRecipe` list includes building-construction
   recipes and customisation/paint recipes. A building recipe has no `mProducedIn`, or lists
   only `BP_BuildGun_C` / `BP_WorkBench_C`. Excluding these is what keeps the recipe graph
   meaningful; including them adds ~500 nodes of noise.
5. **`mForm` values**: `RF_SOLID`, `RF_LIQUID`, `RF_GAS`, `RF_INVALID`.

### Class-name normalisation — the join, and the #1 failure mode

The save file stores full path names. Docs.json uses short class names in `ClassName` and
embeds full paths inside the ingredient strings. Both must normalise to the same key or
**every join edge silently produces zero rows** — no error, no warning, just an empty result.

```
save:   "Persistent_Level:PersistentLevel.Build_ConstructorMk1_C_2147414321"
docs:   "Build_ConstructorMk1_C"
key:    "Build_ConstructorMk1_C"

save recipe ref: ".../Recipe_IronPlate.Recipe_IronPlate_C"
docs:            "Recipe_IronPlate_C"
key:             "Recipe_IronPlate_C"
```

```python
def normalise_class(raw: str) -> str:
    """Reduce any class reference (save path, docs path, bare name) to its short class name."""
    s = raw.strip().strip("'\"")
    s = s.rsplit(".", 1)[-1]        # drop package path
    s = s.rsplit(":", 1)[-1]        # drop level prefix
    s = re.sub(r"_\d+$", "", s)     # drop instance suffix (…_C_2147414321 -> …_C)
    return s
```

Apply this on **both** sides. Write a unit test with one real example of each of the five
shapes above before wiring anything up.

### Extract catalogue

| # | `extract` | Rows | Keys |
|---|---|---|---|
| 1 | `items` | ~180 | `className, displayName, description, form, category, stackSize, sinkPoints, energyValue` |
| 2 | `buildables` | ~300 | `className, displayName, description, powerConsumption, powerConsumptionExponent, manufacturingSpeed` |
| 3 | `recipes` | ~1500 | `className, displayName, durationSeconds, isAlternate, isProduction` |
| 4 | `recipe_ingredients` | ~4000 | `recipeClassName, itemClassName, amount` |
| 5 | `recipe_products` | ~2000 | `recipeClassName, itemClassName, amount` |
| 6 | `recipe_machines` | ~2000 | `recipeClassName, buildableClassName` |
| 7 | `schematics` | ~250 | `className, displayName, tier, type` |
| 8 | `schematic_unlocks` | ~1500 | `schematicClassName, recipeClassName` |

Run order is 1 → 8. Items must land before recipes (fluid conversion depends on `mForm`).

### New constraints

```cypher
CREATE CONSTRAINT recipe_class_name_unique IF NOT EXISTS
  FOR (r:Recipe) REQUIRE r.className IS UNIQUE;

CREATE CONSTRAINT schematic_class_name_unique IF NOT EXISTS
  FOR (s:Schematic) REQUIRE s.className IS UNIQUE;
```

`:Item` and `:Class` constraints already exist from the previous session.

### Representative Cypher — recipe ingredients

```cypher
UNWIND $rows AS row
MATCH (r:Recipe {className: row.recipeClassName})
MATCH (i:Item   {className: row.itemClassName})
MERGE (r)-[c:CONSUMES]->(i)
ON CREATE SET c.amount = row.amount
```

Note `MATCH` on both ends rather than `MERGE`. If either side is missing, the row is silently
skipped — which is what you want during development, but means **you must check the
`relationships_created` count against the input row count** rather than assuming success.

### Two new extracts against the *save* (not Docs.json)

These are the join edges and belong in `SatisfactorySource`, not `DocsSource`:

| `extract` | Keys | Source property |
|---|---|---|
| `machine_recipes` | `instanceName, recipeClassName, clockSpeed` | `mCurrentRecipe`, `mCurrentPotential` |
| `resource_node_yields` | `instanceName, itemClassName, purity` | resource class + purity on the node |

`mCurrentPotential` is the overclock factor — import it, it costs nothing and makes a good
"find the overclocked machines" query later.

### The target traversal — build toward this

This is the acceptance test for the whole session:

```cypher
// Iron ore in the ground -> the machines that process it -> what they make
MATCH (node:ResourceNode)-[:YIELDS]->(ore:Item {displayName: 'Iron Ore'})
MATCH (node)<-[:EXTRACTS_FROM]-(miner:Machine)
MATCH (miner)-[:SUPPLIES*1..6]->(m:Machine)-[:RUNS_RECIPE]->(r:Recipe)-[:PRODUCES]->(out:Item)
RETURN node.instanceName, miner.displayName, m.displayName,
       r.displayName, out.displayName
LIMIT 25
```

If this returns rows against Paul's real save, the session is done.

---

## Instructions

1. **Read** `sources/satisfactory_source.py` in full. `DocsSource` mirrors its structure —
   `EXTRACTS` tuple, `_extract_*` generators, module-level parse cache, lazy file read.

2. **Inspect the real file before writing extracts.** Load `en-US.json` with
   `encoding="utf-16"`, print every distinct `NativeClass` value with its class count, then
   pretty-print one full entry each for a recipe, an item, a resource descriptor, and a
   buildable. **Report this output before continuing** — the field names below are documented
   from community sources and the game's data layout has changed across versions.

3. **Write and unit-test `normalise_class()` and `parse_item_amounts()` first**, in isolation,
   with real strings pulled from step 2. Every join in this session depends on both. Getting
   them wrong produces empty results rather than errors, so they get tests before they get
   callers.

4. **Create** `sources/docs_source.py` with extracts 1–8 from the catalogue. Add
   `SATISFACTORY_DOCS_PATH` to `.env` and `env.sample`. Resolve both `en-US.json` and legacy
   `Docs.json` filenames.

5. **Add** the `docs` branch to `build_source()` and update its `ValueError` message.

6. **Add** `machine_recipes` and `resource_node_yields` extracts to `SatisfactorySource`.

7. **Create** `config-docs.yaml` with jobs in order 1–8, then the two save-side join jobs
   last. `batch_size: 10` initially.

8. **Run constraints, then import.** After each job, compare `relationships_created` against
   the row count. A large gap means the normalisation is dropping matches — stop and fix
   before proceeding rather than importing eight jobs of silent misses.

9. **Extend** `cypher/satisfactory_postimport.cypher`:
   - assign item category secondary labels
   - denormalise `displayName` from `:Class` onto each `:Actor`
   - denormalise `displayName` onto `:Machine` for Bloom/GDS convenience

10. **Validate** with the target traversal above, plus:
    ```cypher
    MATCH (m:Machine) WHERE NOT (m)-[:RUNS_RECIPE]->() RETURN count(m);
    MATCH (r:Recipe)  WHERE NOT (r)-[:PRODUCES]->()    RETURN count(r);
    MATCH (a:Actor)   WHERE a.displayName IS NULL      RETURN count(a);
    ```
    Non-zero counts are expected (unset machines, filtered recipes, actors with no descriptor)
    — but each one needs an explanation, not a shrug.

11. **Spot-check against the game.** Pick one machine Paul can see on screen, confirm the
    graph reports the same recipe, the same inputs, and the same overclock. Row counts will
    not catch a systematically wrong join; this will.

12. **Update** `## Project-Specific` in the standards file with all new labels and
    relationship types, and append a Review Log entry.

---

## Decisions Made This Session

- **Deviated from the "companion repo" locked decision.** No `satisfactory-graph` companion
  repo exists locally or on GitHub (checked `git remote -v`, `gh repo list`, filesystem).
  Surfaced this to Paul before writing any code; he chose to build `DocsSource` in
  `aura-ingest-accelerator` on `feat/satisfactory-source` instead of scaffolding a new repo.
  Rationale accepted: unlike `SatisfactorySource`, `DocsSource` needs no third-party parser
  (Docs.json is plain UTF-16 JSON) — the GPL-3.0 / dependency-graph-cleanliness concern that
  motivated the companion-repo split for the `.sav` connector doesn't apply here. The `.sav`
  connector's own companion-repo question remains open/unaffected by this decision.

- **Dropped `resource_node_yields` and the ore-in-ground leg of the acceptance traversal.**
  Verified directly against the real save that resource class + purity are not recoverable
  from either the save (`BP_ResourceNode_C` only carries `mResourcesLeft`, a depletion
  counter; `BP_ResourceDeposit_C` only carries an index into a static game table present
  nowhere in either data source) or Docs.json. `:ResourceNode`/`:EXTRACTS_FROM`, which the
  spec's target traversal assumed already existed from the physical-layer import, don't exist
  either. Surfaced to Paul with three options before writing any code for this extract; he
  chose to drop the ore-in-ground leg entirely rather than approximate via miner inventory
  contents. The acceptance traversal now starts from `Machine` instead of `ResourceNode` — see
  `docs/satisfactory.md` "Docs.json Enrichment" for the adapted query and what a real fix
  (an external static node-position/purity database) would require.

- **Fixed the session spec's own `parse_item_amounts()` regex** — `[\'"]?` (zero-or-one quote)
  silently matched nothing against the real `mIngredients`/`mProduct` format's two trailing
  quote characters back to back. Caught by validating against all 872 real `FGRecipe` entries
  before trusting it (per Instruction 3), not assumed correct from the spec. Fixed to `['"]*`
  (zero-or-more) in `sources/class_names.py`.

- **Migrated pre-existing `:Item.className` from full save PathNames to short class names.**
  `SatisfactorySource._extract_inventory_stacks()` (prior session) had never been exercised
  against a short-name join convention because `DocsSource` didn't exist yet. Found by querying
  the live instance directly before writing any join Cypher (`MATCH (i:Item) RETURN
  i.className` showed full paths, not the short names `normalise_class()` produces).
  Confirmed collision-free (78 distinct in, 78 distinct out) before running the migration live;
  `_extract_inventory_stacks()` fixed to normalise going forward so future imports don't
  regress it. Not explicitly called for by the session spec, but necessary for every
  `:Item`-touching join edge to work at all.

- **In-game spot-check confirmed (2026-08-13).** Paul checked
  `Build_ConstructorMk1_C_2146938608` in-game against the candidate handed off at session
  close: Iron Plate recipe at 75% clock, matching the graph exactly. Closes out the literal
  ground-truth check both Satisfactory connectors (this one and the `.sav` connector's
  `factory_links` direction heuristic) had deferred since their first sessions.
