# IFC GraphRAG System Implementation: A Phased Approach

This is a three-phase MVP implementation plan to transform an IFC file into a functional BIM assistant on your local machine. Each phase includes specific actions and verification steps to ensure successful completion.

## Phase 1: IFC to Graph Conversion
**Goal:** Convert IFC files to Labeled Property Graph (LPG) format

**Implementation Steps:**
1. Clone the Git repo: https://github.com/sgracia-itainnova/IFC-graph and create an IFCGraphRepo.md documentation file
2. Set up Python environment: Create a fresh Python venv → pip install -r requirements.txt
3. Test the converter with a small model: python convert.py MyHouse.ifc --out ./lpg-export (replace with the repo's actual CLI command)
4. Verify output format - the script should generate either:
   * Cypher import scripts, or
   * CSV/GraphML files with a README describing node and relationship organization

**Success Criteria:** ✔ Files named like nodes_Wall.csv, relationships_ADJACENT_TO.csv (or a single import.cypher) are generated without terminal errors

## Phase 2: Graph Database Configuration
**Goal:** Load the LPG data into a local Neo4j instance

**Implementation Steps:**
1. Install Neo4j Desktop 5.x (which includes APOC library)
2. Create a new database named "bim-mvp" with default Bolt port 7687
3. Copy the generated CSV or Cypher files into the database's import/ folder (path shown in Desktop)
4. Import the data:
   * For CSV files: Use the built-in "neo4j-admin database import full" wizard or APOC's apoc.load.csv calls
   * For Cypher scripts: Open Neo4j Browser and run :source import/import.cypher
5. Create a uniqueness constraint on IFC GUIDs: CREATE CONSTRAINT n10 IF NOT EXISTS FOR (e:IfcElement) REQUIRE e.guid IS UNIQUE;

**Success Criteria:** ✔ A sanity query MATCH () RETURN count(*) shows non-zero node count, and MATCH (r:Room) RETURN count(r) returns the expected number

## Phase 3: Conversational Interface Setup
**Goal:** Implement a query interface with NeoConverse SPA (Single Page Application)

**Implementation Steps:**
1. Clone the NeoConverse (or "NeoConvOS") repository
2. Configure environment: cp .env.template .env and set:
   * NEO4J_URI=bolt://localhost:7687
   * NEO4J_USER=neo4j / NEO4J_PASSWORD=<your-pw>
   * OPENAI_API_KEY=<your-key>
   * Model name (e.g. gpt-4o-mini)
3. Install dependencies and run: npm install (or yarn/pnpm) → npm run dev
4. Test the application at http://localhost:3000 with a query:
   * "How many walls are in the model?" → observe Cypher query and results

**Success Criteria:** ✔ Correct answer appears (e.g., "There are 214 walls in this model") with visible Cypher snippet. Follow-up queries like "How many are fire-rated?" also work

## Future Enhancements (Post-MVP)
| Enhancement | Benefit | Implementation Location |
|-------------|---------|-------------------------|
| Adjacency/topology enrichment | Adds derived relations (:ADJACENT_TO, :ENCLOSES) missing in pure IFC exports | Integrate TopologicPy before Phase 1 |
| Schema JSON & few-shot examples | Improves LLM accuracy on domain terms | NeoConverse settings panel |
| Materialized graph projections | Speeds up heavy multi-hop queries | Neo4j APOC or GDS after Phase 2 |
| MEP/structural classes | Unlocks richer queries (load paths, duct runs) | Extend the converter repository |

**TL;DR:** IFC → (Python) converter → CSV/Cypher → Neo4j Desktop → NeoConverse chat UI – three phases, one afternoon, MVP done.

Let me know if you'd like more detail on any specific step (e.g., using Docker instead of Desktop, or automating imports).