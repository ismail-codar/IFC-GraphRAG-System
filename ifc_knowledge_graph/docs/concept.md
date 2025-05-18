Below is an **MVP-focused design brief** that removes the supplemental/optional libraries you flagged.
Everything else remains intact so the coding agent still has a complete roadmap.

---

## 1  | Project Vision

Topic	Description
Goal	Convert any Industry Foundation Classes (IFC) model into a rich, domain-aware knowledge graph stored in Neo4j. The 
        graph  must capture both:
        • Explicit information (entities, attributes, IFC-defined relationships) and
        • Implicit spatial/topological relationships (adjacency, containment, connectivity, ordered material layers).
Why	    Graph form simplifies complex BIM queries ("find all rooms that can be reached without passing through fire doors", 
        "list exterior walls with insulation > 10 cm") and serves as a backbone for FM dashboards, energy analysis, BIM↔GIS integration, etc.
Scope	• Architectural + basic structural disciplines in IFC 2x3/4
        • Walls, windows, doors, rooms, furniture, materials as first-class nodes
        • Geometry sufficient for adjacency & containment, not for full-fidelity rendering                                                                                                                     |


---

## 2  | High-Level Pipeline

```
IFC file → IfcOpenShell → explicit data
                        + geometry
                        ↓
                      TopologicPy → implicit relationships
                        ↓
                Mapping / Dedup layer
                        ↓
             Neo4j (via neo4j-driver)
                        ↓
               Neo4j Desktop instance
```

---

## 3  | Key Libraries & Their Roles (MVP)

| Library                                       | Stability | Role in Pipeline                                     | Notes                                    |
| --------------------------------------------- | --------- | ---------------------------------------------------- | ---------------------------------------- |
| **IfcOpenShell**                              | Mature    | Parse IFC entities, attributes, and geometry handles | Core extractor.                          |
| **TopologicPy**                               | Active    | Compute adjacency, containment, connectivity         | Sole geometry/topology engine for MVP.   |
| **neo4j-driver**                              | Mature    | Batch-load nodes & relationships; manage constraints | Connects to Neo4j Desktop during development. |
| **Logging & CLI** (built-in)                  | Stable    | Progress bars, error logs, CLI entry points          | Use Python `logging` and click/argparse. |

> **Deferred**: any additional geometry libs, mesh kernels, typed data classes, or voxel/boolean packages are out-of-scope for MVP and can be revisited post-release.

---

## 4  | Conceptual Data Model (LPG)

4 | Conceptual Data Model (LPG)
4.1 Node Types & Principal Properties
Node label	Mandatory props	Optional props	Notes
Room	GlobalId, OID, Name, Level	GrossArea, Height, Volume	Aggregates Space & Zone where needed.
Wall	GlobalId, OID, Name, Level, IsExternal	Length, Height, Width, TypeMark	Distinguish curtain walls via IsLoadBearing = false + subtype.
Door / Window	GlobalId, OID, Name, Level	RoughHeight, RoughWidth, FrameWidth	HostedBy relationship to Wall.
Material	OID, MaterialName, Function	—	Layers handled via :HasLayer edge.
Furniture	GlobalId, Name, Level	—	Optional for first release.

4.2 Relationship Types
Relationship	Direction	Key attributes	Source
:ContainedIn	Element → Room	—	IFC: IfcRelContainedInSpatialStructure
:HostedBy	Door/Window → Wall	—	IFC: IfcRelVoidsElement
:Access	Room ↔ Room	accessType (Door/Window/Stair/Direct)	Derived via door adjacency algorithm
:IsConnected	Wall ↔ Wall	—	TopologicPy edge adjacency
:HasLayer	Wall → Material	order (int)	Custom layer-ordering algorithm
:IsFacing	Material → Room	orientation (Interior/Exterior)	Optional; needs clarity ⚠️


---

## 5  | Workflow Stages & Deliverables (re-scoped)

| Stage                         | Core Tasks                                   | Deliverable                 |
| ----------------------------- | -------------------------------------------- | --------------------------- |
| **S-1** Environment Bootstrap | Pip/Poetry project, CI, pre-commit           | Repo skeleton               |
| **S-2** IFC Extraction        | Entity & attribute stream via IfcOpenShell   | `ifc_parser/reader.py`      |
| **S-3** Topology Analysis     | Adjacency / containment via TopologicPy only | `topology/relationships.py` |
| **S-4** Mapping & Buffering   | Merge explicit + implicit data; deduplicate  | `mapping/mapper.py`         |
| **S-5** Neo4j Ingestion       | Connection to Neo4j Desktop, batched loads   | `graph_loader/load.py`      |
| **S-6** Validation            | Completeness + integrity tests (pytest)      | `tests/`                    |
| **S-7** Docs & Samples        | Dev guide, data-model sheet, demo IFC        | `docs/`                     |

---

## 6  | Known Unknowns / Research Spikes (updated)

| Topic ⚠️                           | Why It Matters                                               | Action                                                     |
| ---------------------------------- | ------------------------------------------------------------ | ---------------------------------------------------------- |
| **TopologicPy scalability**        | Sole geometry engine now — must handle large models alone.   | Benchmark on 200k+-entity IFC.                             |
| **Wall-layer orientation logic**   | Relies on geometry vectors from TopologicPy only.            | Prototype & document algorithm; confirm with sample walls. |
| **Neo4j Desktop performance**      | Local Neo4j Desktop may have different performance characteristics. | Test with various batch sizes and connection settings.     |
| **Property-set flattening policy** | Decide which Psets become node props.                        | Get stakeholder sign-off.                                  |

---

## 7  | Quality & Governance


Data Integrity Rules

GlobalId is unique per node label.

Every Door/Window has exactly one Host Wall; raise error otherwise.

No Room may be isolated: enforce ≥ 1 Access edge or log.

Testing Standards

Unit tests for geometry helpers (≥ 90 % branch coverage).

Integration tests ingest a small demo IFC and assert node/edge counts.

Documentation

Data-model sheet (Google Sheet / markdown) reflecting every node/edge label & property.

Runbook for operations: environment variables, Neo4j Desktop setup, graph reset, incremental re-import.



---

## 8  | Next Steps Checklist (MVP)

1. Confirm hardware & performance targets.
2. Set up Neo4j Desktop with an empty database instance.
3. Prototype end-to-end flow on one 10 MB IFC; capture timings.
4. Configure Neo4j driver connection pool with Neo4j Desktop Bolt URI.
5. Finalize wall-layer ordering algorithm with TopologicPy only.
6. Lock property-set inclusion list.
7. Publish data-model sheet for approval.

---

*End of MVP design brief.*
