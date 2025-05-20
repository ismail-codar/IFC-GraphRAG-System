# Project File Structure

## Project Structure Update (May 2025)

**Current Status:**
- The pipeline for converting IFC to Neo4j is complete and functional, with proven integration test results.
- Recent integration tests successfully created a knowledge graph with 306 nodes and 2328 relationships.
- The BIMConverse natural language querying system has been implemented and enables users to query the IFC knowledge graphs using conversational language.
- The codebase is now ready for advanced querying, API development, and comprehensive documentation.
- New optimization tools have been added to reduce IFC file sizes and improve processing speed.
- There is a non-critical issue with material node creation that affects material associations but doesn't prevent the core graph from being created.

---

# IFC to Neo4j Knowledge Graph Project Structure

## Root Directory

```
/ifc_knowledge_graph/
├── docs/                       # Documentation files
├── tools/                      # Utility scripts
├── tests/                      # Test cases and fixtures
├── examples/                   # Example scripts and configs
├── ifc_parser/                 # IFC file parsing module
├── topology/                   # Topological analysis module
├── neo4j_connector/            # Neo4j database interaction module
├── bimconverse/                # BIMConverse natural language querying system
├── data/                       # Sample data and resources
├── config/                     # Configuration files
└── notebooks/                  # Jupyter notebooks for demonstrations
```

## Documentation (`/docs/`)

```
/docs/
├── concept.md                  # High-level project concept
├── currentappstatus.md         # Current implementation status
├── implementationplan.md       # Phase-based implementation plan
├── file_structure.md           # This file - project structure
├── database_schema.md          # Neo4j database schema documentation
├── api_reference.md            # API reference documentation
├── usage_examples.md           # Usage examples and tutorials
└── troubleshooting.md          # Common issues and solutions
```

## IFC Parser Module (`/ifc_parser/`)

```
/ifc_parser/
├── __init__.py
├── parser.py                   # Main IFC parsing functionality
├── schema.py                   # IFC schema definitions
├── processor.py                # IFC data processing functions
├── optimizer.py                # Memory and performance optimizations
├── utils.py                    # Utility functions
└── exceptions.py               # Custom exception classes
```

## Topology Module (`/topology/`)

```
/topology/
├── __init__.py
├── analyzer.py                 # Core topology analysis functionality
├── cell_complex.py             # Cell complex representation
├── spatial_relationships.py    # Spatial relationship extraction
├── geometry.py                 # Geometry processing functions
└── utils.py                    # Utility functions
```

## Neo4j Connector Module (`/neo4j_connector/`)

```
/neo4j_connector/
├── __init__.py
├── connector.py                # Database connection management
├── cypher_builder.py           # Cypher query construction
├── batch_importer.py           # Batch import functionality
├── schema_manager.py           # Database schema management
└── utils.py                    # Utility functions
```

## BIMConverse Module (`/bimconverse/`)

```
/bimconverse/
├── __init__.py
├── core.py                     # Core GraphRAG implementation
├── cli.py                      # Command-line interface
├── schema.py                   # Building schema definitions
├── config.py                   # Configuration utilities
├── prompts.py                  # Prompt templates for LLMs
├── retrievers.py               # Custom retrieval strategies
└── formatters.py               # Response formatting utilities
```

## Tests (`/tests/`)

```
/tests/
├── __init__.py
├── unit/                       # Unit tests for all modules
├── integration/                # Integration tests
├── fixtures/                   # Test fixtures and sample data
└── conftest.py                 # PyTest configuration
```

## Tools (`/tools/`)

```
/tools/
├── ifc_optimizer.py            # IFC file size reduction tool
├── batch_processor.py          # Batch processing script
├── graph_statistics.py         # Graph database statistics tool
├── validator.py                # Data validation tool
└── visualization.py            # Visualization utilities
```

## Examples (`/examples/`)

```
/examples/
├── simple_parser.py            # Basic IFC parsing example
├── topology_analysis.py        # Topological analysis example
├── graph_import.py             # Neo4j import example
├── basic_query.py              # Basic querying example
├── bimconverse_example.py      # BIMConverse usage example
└── config_samples/             # Example configuration files
```

## Future Development Plans

1. **Advanced GraphRAG Capabilities:**
   - Implement multi-hop reasoning for complex building queries
   - Create parent-child document retrieval for IFC hierarchies
   - Develop hypothetical question generation for common building queries
   - Add specialized spatial relationship traversal patterns
   - Implement building domain-specific prompt templates

2. **Web Interface and API:**
   - Develop a web-based user interface
   - Create a RESTful API for third-party integration
   - Implement real-time visualization of query results
   - Add user authentication and permission management

3. **Advanced Analytics:**
   - Implement graph algorithms for building analysis
   - Add machine learning for pattern recognition
   - Create reporting and dashboard functionality
   - Develop comparative analysis between building models

4. **Integrations:**
   - Create plugins for BIM software like Revit, ArchiCAD
   - Implement connectors for common data formats
   - Add support for IFC export from the knowledge graph
   - Develop IoT data integration for digital twins
