// cypher/satisfactory_constraints.cypher
// Run this against the target Aura instance before the first
// config-satisfactory.yaml import. See README.md's Constraints section.

CREATE CONSTRAINT save_id_unique IF NOT EXISTS
  FOR (s:Save) REQUIRE s.saveId IS UNIQUE;

CREATE CONSTRAINT actor_instance_name_unique IF NOT EXISTS
  FOR (a:Actor) REQUIRE a.instanceName IS UNIQUE;

CREATE CONSTRAINT class_type_path_unique IF NOT EXISTS
  FOR (c:Class) REQUIRE c.typePath IS UNIQUE;

CREATE CONSTRAINT level_name_unique IF NOT EXISTS
  FOR (l:Level) REQUIRE l.name IS UNIQUE;

CREATE CONSTRAINT item_class_name_unique IF NOT EXISTS
  FOR (i:Item) REQUIRE i.className IS UNIQUE;

CREATE CONSTRAINT power_circuit_id_unique IF NOT EXISTS
  FOR (p:PowerCircuit) REQUIRE p.circuitId IS UNIQUE;

// --- Logical layer (docs-enrichment session) --------------------------------
// See .session/2026-08-12-docs-enrichment.md. Item already has a constraint
// above — its className values were migrated from full save paths to short
// class names in that session so DocsSource's `items` extract joins onto the
// same nodes instead of creating duplicates.

CREATE CONSTRAINT recipe_class_name_unique IF NOT EXISTS
  FOR (r:Recipe) REQUIRE r.className IS UNIQUE;

CREATE CONSTRAINT schematic_class_name_unique IF NOT EXISTS
  FOR (s:Schematic) REQUIRE s.className IS UNIQUE;

CALL db.awaitIndexes(300);
