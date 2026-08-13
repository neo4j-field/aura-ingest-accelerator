// cypher/satisfactory_postimport.cypher
// Run this against the target Aura instance after every config-satisfactory.yaml
// job has completed. Assigns semantic labels from the `category` property set
// during the Actors import, then materialises the collapsed machine-to-machine
// SUPPLIES edge from the raw FEEDS chain.
//
// FEEDS direction comes from a name/index heuristic in
// sources/satisfactory_source.py (_extract_factory_links) — see AGENTS.md
// Known Issues. If SUPPLIES comes out empty or backwards, that heuristic is
// the first place to check before touching this query.

// --- Semantic labels -------------------------------------------------------

MATCH (a:Actor) WHERE a.category = 'building' SET a:Building;
MATCH (a:Actor) WHERE a.category = 'machine'  SET a:Building, a:Machine;
MATCH (a:Actor) WHERE a.category = 'conveyor' SET a:Building, a:Conveyor;
MATCH (a:Actor) WHERE a.category = 'pipe'     SET a:Building, a:Pipe;

// --- Belt collapsing — the derived edge -------------------------------------
// The bound of 250 is a guess at the longest belt run in a real factory.
// Tune against your own save; if this query is slow or blows the heap, the
// fallback is an iterative one-hop-at-a-time collapse rather than a longer bound.

MATCH path = (a:Machine)-[:FEEDS*1..250]->(b:Machine)
WHERE all(n IN nodes(path)[1..-1] WHERE n:Conveyor OR n:Pipe)
MERGE (a)-[r:SUPPLIES]->(b)
ON CREATE SET r.hops = length(path);

// =============================================================================
// Logical-layer enrichment (docs-enrichment session, 2026-08-12)
// =============================================================================
// See .session/2026-08-12-docs-enrichment.md for the two-layer model this
// completes. Run this section (and everything above) after both
// config-satisfactory.yaml AND config-docs.yaml have completed.

// --- Item secondary labels ---------------------------------------------------
// category comes from which Docs.json native class an item was extracted
// from (see sources/docs_source.py _ITEM_NATIVE_CLASSES); form is the game's
// own RF_SOLID/RF_LIQUID/RF_GAS/RF_INVALID. Fluid is assigned from form and
// can co-occur with RawResource (Crude Oil, Water are both). Ingot vs Part is
// a displayName heuristic ("ends with Ingot") — Docs.json carries no
// authoritative ingot/part distinction; same caveat class as the FEEDS
// direction heuristic above, documented in AGENTS.md Known Issues.

MATCH (i:Item) WHERE i.category IN ['resource', 'biomass'] SET i:RawResource;
MATCH (i:Item) WHERE i.form IN ['RF_LIQUID', 'RF_GAS']     SET i:Fluid;
MATCH (i:Item) WHERE i.category = 'ammo'                   SET i:Ammo;
MATCH (i:Item) WHERE i.category = 'equipment'               SET i:Equipment;
MATCH (i:Item) WHERE i.category = 'consumable'               SET i:Consumable;
MATCH (i:Item) WHERE i.category = 'item' AND i.displayName ENDS WITH 'Ingot' SET i:Ingot;
MATCH (i:Item)
WHERE NOT i:RawResource AND NOT i:Ammo AND NOT i:Equipment
  AND NOT i:Consumable AND NOT i:Ingot
SET i:Part;

// --- Denormalised display names ----------------------------------------------
// Class.displayName is set by the "Buildables" job in config-docs.yaml
// (architecture pieces and machines alike). Copy it onto every Actor so
// Bloom/GDS/the teaching notebook can show a human name without a hop.
// Machine gets it twice (once via the generic Actor copy below, since every
// Machine is also an Actor) — this second statement exists only so the
// intent ("Machine needs this for Bloom convenience") isn't buried inside
// the broader Actor pass.

MATCH (a:Actor)-[:INSTANCE_OF]->(c:Class)
WHERE c.displayName IS NOT NULL AND c.displayName <> ''
SET a.displayName = c.displayName;

MATCH (m:Machine)-[:INSTANCE_OF]->(c:Class)
WHERE c.displayName IS NOT NULL AND c.displayName <> ''
SET m.displayName = c.displayName;

// --- Sanity checks -----------------------------------------------------------
// MATCH (:Machine)-[:SUPPLIES]->(:Machine) RETURN count(*);
// MATCH (m:Machine) WHERE NOT (m)--(:Conveyor) RETURN count(m);  // orphans
// MATCH (m:Machine) WHERE NOT (m)-[:RUNS_RECIPE]->() RETURN count(m);
// MATCH (r:Recipe)  WHERE NOT (r)-[:PRODUCES]->()    RETURN count(r);
// MATCH (a:Actor)   WHERE a.displayName IS NULL      RETURN count(a);
