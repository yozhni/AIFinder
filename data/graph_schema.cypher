// AIFinder Neo4j Graph Schema
// Run this in Neo4j Browser or cypher-shell

// ============================================
// INDEXES
// ============================================

// Product indexes
CREATE INDEX product_id IF NOT EXISTS FOR (p:Product) ON (p.id);
CREATE INDEX product_name IF NOT EXISTS FOR (p:Product) ON (p.name);
CREATE INDEX product_category IF NOT EXISTS FOR (p:Product) ON (p.category);
CREATE INDEX product_brand IF NOT EXISTS FOR (p:Product) ON (p.brand);
CREATE INDEX product_price IF NOT EXISTS FOR (p:Product) ON (p.price);

// Category indexes
CREATE INDEX category_name IF NOT EXISTS FOR (c:Category) ON (c.name);

// Application indexes
CREATE INDEX application_name IF NOT EXISTS FOR (a:Application) ON (a.name);

// UseCase indexes
CREATE INDEX usecase_name IF NOT EXISTS FOR (u:UseCase) ON (u.name);

// Workflow indexes
CREATE INDEX workflow_name IF NOT EXISTS FOR (w:Workflow) ON (w.name);

// Property indexes
CREATE INDEX property_name IF NOT EXISTS FOR (pr:Property) ON (pr.name);

// ============================================
// FULL-TEXT INDEXES (for search)
// ============================================

CREATE FULLTEXT INDEX product_fulltext IF NOT EXISTS
FOR (p:Product) ON EACH [p.name, p.specifications, p.application, p.use_case];

// ============================================
// NODE CREATION (run after data sync)
// ============================================

// Create Category nodes
CALL apoc.periodic.iterate(
  "MATCH (p:Product) RETURN DISTINCT p.category AS category",
  "MERGE (c:Category {name: category})",
  {batchSize: 100}
);

// Create Application nodes
CALL apoc.periodic.iterate(
  "MATCH (p:Product) RETURN DISTINCT p.application AS application",
  "MERGE (a:Application {name: application})",
  {batchSize: 100}
);

// Create UseCase nodes
CALL apoc.periodic.iterate(
  "MATCH (p:Product) RETURN DISTINCT p.use_case AS use_case",
  "MERGE (u:UseCase {name: use_case})",
  {batchSize: 100}
);

// Create Workflow nodes
CALL apoc.periodic.iterate(
  "MATCH (p:Product) RETURN DISTINCT p.application AS app_name",
  "MERGE (w:Workflow {name: app_name + ' workflow'})",
  {batchSize: 100}
);

// Create Property nodes
MERGE (ps:Property {name: "sterile", value: true})
MERGE (pn:Property {name: "sterile", value: false})
MERGE (rs:Property {name: "refrigerated", value: true})
MERGE (rn:Property {name: "refrigerated", value: false})
MERGE (ef:Property {name: "endotoxin_free", value: true})
MERGE (en:Property {name: "endotoxin_free", value: false});

// ============================================
// RELATIONSHIP CREATION (run after data sync)
// ============================================

// BELONGS_TO: Product -> Category
MATCH (p:Product), (c:Category {name: p.category})
MERGE (p)-[:BELONGS_TO]->(c);

// HAS_APPLICATION: Product -> Application
MATCH (p:Product), (a:Application {name: p.application})
MERGE (p)-[:HAS_APPLICATION]->(a);

// HAS_USE_CASE: Product -> UseCase
MATCH (p:Product), (u:UseCase {name: p.use_case})
MERGE (p)-[:HAS_USE_CASE]->(u);

// HAS_PROPERTY: Product -> Property
MATCH (p:Product)
WHERE p.sterile = true
MERGE (ps:Property {name: "sterile", value: true})
MERGE (p)-[:HAS_PROPERTY]->(ps);

MATCH (p:Product)
WHERE p.sterile = false
MERGE (pn:Property {name: "sterile", value: false})
MERGE (p)-[:HAS_PROPERTY]->(pn);

MATCH (p:Product)
WHERE p.refrigerated = true
MERGE (rs:Property {name: "refrigerated", value: true})
MERGE (p)-[:HAS_PROPERTY]->(rs);

MATCH (p:Product)
WHERE p.refrigerated = false
MERGE (rn:Property {name: "refrigerated", value: false})
MERGE (p)-[:HAS_PROPERTY]->(rn);

MATCH (p:Product)
WHERE p.endotoxin_free = true
MERGE (ef:Property {name: "endotoxin_free", value: true})
MERGE (p)-[:HAS_PROPERTY]->(ef);

// PART_OF_WORKFLOW: Workflow -> Application
MATCH (w:Workflow), (a:Application)
WHERE w.name = a.name + ' workflow'
MERGE (w)-[:USES_APPLICATION]->(a);

// HAS_USE_CASE: Application -> UseCase
MATCH (a:Application), (u:UseCase)
WHERE a.name CONTAINS CASE
  WHEN u.name CONTAINS 'protein' THEN 'Protein purification'
  WHEN u.name CONTAINS 'cell' THEN 'Cell culture'
  WHEN u.name CONTAINS 'bacteria' THEN 'General laboratory'
  WHEN u.name CONTAINS 'buffer' THEN 'General laboratory'
  WHEN u.name CONTAINS 'centrifug' THEN 'General laboratory'
  WHEN u.name CONTAINS 'PCR' THEN 'Molecular biology'
  WHEN u.name CONTAINS 'clone' THEN 'Molecular biology'
  WHEN u.name CONTAINS 'steril' THEN 'General laboratory'
  WHEN u.name CONTAINS 'weigh' THEN 'General laboratory'
  WHEN u.name CONTAINS 'mix' THEN 'General laboratory'
  WHEN u.name CONTAINS 'shake' THEN 'General laboratory'
  WHEN u.name CONTAINS 'vacuum' THEN 'General laboratory'
  WHEN u.name CONTAINS 'UV' THEN 'General laboratory'
  WHEN u.name CONTAINS 'sanit' THEN 'General laboratory'
  ELSE 'General laboratory'
END
MERGE (a)-[:HAS_USE_CASE]->(u);
