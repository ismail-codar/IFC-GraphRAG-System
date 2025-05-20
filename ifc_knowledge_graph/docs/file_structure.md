# Project File Structure

## Project Structure Update (May 2023)

**Current Status:**
- The pipeline for converting IFC to Neo4j is complete and functional, with proven integration test results.
- Recent integration tests successfully created a knowledge graph with 306 nodes and 2328 relationships.
- The BIMConverse natural language querying system has been implemented and enables users to query the IFC knowledge graphs using conversational language.
- Phase 1 of codebase refactoring has been completed, focusing on reorganizing the test structure and removing redundant files.
- There is a known issue with material node creation that affects material associations but doesn't prevent the core graph from being created.
- Phase 2 of refactoring is in progress, focusing on fixing bugs and standardizing code patterns.

---

# IFC to Neo4j Knowledge Graph Project Structure

## Actual Directory Structure

```
/ifc_knowledge_graph/
├── src/                       # Core source code
│   └── ifc_to_graph/          # IFC to graph pipeline
│       ├── __init__.py
│       ├── processor.py       # Main orchestrator
│       ├── parser/            # IFC parsing
│       ├── topology/          # Topological analysis
│       ├── database/          # Neo4j interaction
│       ├── utils/             # Utilities
│       └── cli/               # Command line interfaces
├── bimconverse/               # BIMConverse RAG system
│   ├── __init__.py
│   ├── core.py                # Core RAG functionality
│   ├── cli.py                 # Command-line interface
│   ├── prompts.py             # Prompt templates
│   └── retrievers.py          # Retrieval strategies
├── tests/                     # Consolidated tests
│   ├── __init__.py
│   ├── unit/                  # Unit tests
│   │   ├── __init__.py
│   │   ├── test_ifc_parser.py
│   │   └── test_neo4j_connector.py
│   └── integration/           # Integration tests
│       ├── __init__.py
│       ├── test_integration.py
│       ├── test_core.py
│       ├── test_multihop.py
│       ├── test_graph_quality.py
│       └── test_topological_features.py
├── tools/                     # Utility scripts
├── examples/                  # Example scripts
├── data/                      # Sample data
├── docs/                      # Documentation
├── visualizations/            # Visualization outputs
├── performance_reports/       # Performance data
├── output/                    # Output files
├── main.py                    # Main entry point
├── requirements.txt           # Dependencies
├── config.json                # Configuration
└── README.md                  # Project overview
```

## Documentation (`/docs/`)

```
/docs/
├── concept.md                 # High-level project concept
├── currentappstatus.md        # Current implementation status
├── implementationplan.md      # Phase-based implementation plan
├── file_structure.md          # This file - project structure
├── database_schema.md         # Neo4j database schema documentation
├── graphrag.md                # GraphRAG implementation details
└── other documentation files
```

## IFC to Graph Module (`/src/ifc_to_graph/`)

### Parser (`/src/ifc_to_graph/parser/`)

```
/parser/
├── __init__.py
├── ifc_parser.py              # Main IFC parsing functionality
└── domain_enrichment.py       # Domain-specific enrichment
```

### Topology (`/src/ifc_to_graph/topology/`)

```
/topology/
├── __init__.py
├── topologic_analyzer.py      # Core topology analysis
└── README.md                  # Topology documentation
```

### Database (`/src/ifc_to_graph/database/`)

```
/database/
├── __init__.py
├── neo4j_connector.py         # Database connection management
├── schema.py                  # Schema definitions
├── ifc_to_graph_mapper.py     # Maps IFC data to graph
├── topologic_to_graph_mapper.py # Maps topology to graph
├── performance_monitor.py     # Tracks database operations
└── query_optimizer.py         # Query optimization
```

### Utils (`/src/ifc_to_graph/utils/`)

```
/utils/
├── __init__.py
├── parallel_processor.py      # Parallel processing utilities
└── graph_quality_analyzer.py  # Graph quality analysis
```

### CLI (`/src/ifc_to_graph/cli/`)

```
/cli/
├── __init__.py
├── ifc_parser_cli.py          # IFC parsing CLI
└── ifc_to_neo4j_cli.py        # Neo4j conversion CLI
```

## BIMConverse Module (`/bimconverse/`)

```
/bimconverse/
├── __init__.py
├── core.py                    # Core GraphRAG implementation
├── cli.py                     # Command-line interface
├── prompts.py                 # Prompt templates for LLMs
└── retrievers.py              # Custom retrieval strategies
```

## Tests (`/tests/`)

```
/tests/
├── __init__.py
├── unit/                      # Unit tests
│   ├── __init__.py
│   ├── test_ifc_parser.py     # Tests for IFC parser
│   └── test_neo4j_connector.py # Tests for Neo4j connector
└── integration/               # Integration tests
    ├── __init__.py
    ├── test_integration.py    # End-to-end tests
    ├── test_core.py           # BIMConverse core tests
    ├── test_multihop.py       # Multi-hop reasoning tests
    ├── test_graph_quality.py  # Graph quality tests
    └── test_topological_features.py # Topology tests
```

## Tools (`/tools/`)

```
/tools/
├── ifc_optimize.py            # IFC file size reduction
└── optimize_all_ifcs.py       # Batch processing
```

## Examples (`/examples/`)

```
/examples/
├── domain_enrichment_example.py # Domain enrichment example
└── other example files
```

## Future Development Plans

1. **Complete Phase 2 of Refactoring:**
   - Fix material node creation bug
   - Consolidate duplicate functionality
   - Standardize imports throughout the codebase
   - Improve code quality and maintainability
   
2. **Advanced GraphRAG Capabilities:**
   - Implement multi-hop reasoning for complex building queries
   - Create parent-child document retrieval for IFC hierarchies
   - Develop hypothetical question generation for common building queries
   - Add specialized spatial relationship traversal patterns
   - Implement building domain-specific prompt templates

3. **Web Interface and API:**
   - Develop a web-based user interface
   - Create a RESTful API for third-party integration
   - Implement real-time visualization of query results
   - Add user authentication and permission management

4. **Advanced Analytics:**
   - Implement graph algorithms for building analysis
   - Add machine learning for pattern recognition
   - Create reporting and dashboard functionality
   - Develop comparative analysis between building models

5. **Integrations:**
   - Create plugins for BIM software like Revit, ArchiCAD
   - Implement connectors for common data formats
   - Add support for IFC export from the knowledge graph
   - Develop IoT data integration for digital twins
