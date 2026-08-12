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

// --- Sanity checks -----------------------------------------------------------
// MATCH (:Machine)-[:SUPPLIES]->(:Machine) RETURN count(*);
// MATCH (m:Machine) WHERE NOT (m)--(:Conveyor) RETURN count(m);  // orphans
