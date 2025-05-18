# IFC to Neo4j Knowledge Graph: Project Structure

This document provides a detailed overview of the project's file structure, explaining the purpose and organization of each directory and file.

## Root Directory

The root directory contains the following key components:

```
ifc_knowledge_graph/
├── data/                  # Data storage and sample files
├── docs/                  # Documentation
├── src/                   # Source code
├── tests/                 # Test files
├── venv/                  # Virtual environment (not tracked in Git)
├── .git/                  # Git repository data (not tracked in Git)
├── .gitignore             # Git ignore configuration
├── main.py                # Main application entry point
├── direct_connection_test.py # Basic Neo4j connection test
├── neo4j_setup_guide.md   # Guide for setting up Neo4j
├── parse_test.py          # Simple IFC parsing test
├── requirements.txt       # Python dependencies
├── README.md              # Project overview and instructions
├── test_neo4j_manual.py   # Neo4j connector test
└── test_processor_manual.py # IFC to Neo4j processor test
```

## Directory Details

### `data/`

The data directory stores IFC model files and other data used by the application.

```
data/
└── ifc_files/             # IFC model files
    └── Duplex_A_20110907.ifc # Sample IFC file
```

### `docs/`

The docs directory contains all project documentation.

```
docs/
├── file_structure.md      # This document - explaining project structure
└── implementationplan.md  # Implementation phases and tasks
```

### `src/`

The src directory contains all source code for the application, organized in a package structure.

```
src/
└── ifc_to_graph/          # Main package
    ├── __init__.py        # Package initialization
    ├── cli/               # Command-line interface
    │   ├── __init__.py    # CLI module initialization
    │   ├── ifc_parser_cli.py # Parser CLI
    │   └── ifc_to_neo4j_cli.py # Neo4j conversion CLI
    ├── database/          # Neo4j database operations
    │   ├── __init__.py    # Database module initialization
    │   ├── neo4j_connector.py # Neo4j connection management
    │   ├── schema.py      # Database schema definitions
    │   └── ifc_to_graph_mapper.py # IFC to graph mapping logic
    ├── parser/            # IFC file parsing functionality
    │   └── __init__.py    # Parser module initialization
    ├── processor.py       # Main processor for IFC to Neo4j conversion
    ├── topology/          # Topological analysis using TopologicPy
    │   └── __init__.py    # Topology module initialization
    └── utils/             # Helper utilities
        └── __init__.py    # Utils module initialization
```

### `tests/`

The tests directory contains all tests for the application.

```
tests/
├── __init__.py            # Tests package initialization
└── test_parser.py         # Parser unit tests
```

## Module Purposes

### Source Code Modules

1. **`parser/`**: Contains code for parsing IFC files using IfcOpenShell, extracting entities, properties, and relationships.

2. **`topology/`**: Contains code for analyzing topological relationships between building elements using TopologicPy, including adjacency, containment, and connectivity.

3. **`database/`**: Contains code for Neo4j database operations, including:
   - **`neo4j_connector.py`**: Connection management, query execution, and transaction handling
   - **`schema.py`**: Schema definitions including node labels, relationship types, constraints, and indexes
   - **`ifc_to_graph_mapper.py`**: Logic for mapping IFC entities to Neo4j graph elements

4. **`utils/`**: Contains utility functions and helper classes used across the project.

5. **`cli/`**: Contains command-line interface code for running the application from the command line.

6. **`processor.py`**: Coordinates the entire IFC to Neo4j conversion process, using the parser and database modules.

### Test and Utility Files

1. **`main.py`**: Main entry point for the application, providing a command-line interface.

2. **`direct_connection_test.py`**: Tests direct connection to Neo4j using the driver, bypassing custom modules.

3. **`test_neo4j_manual.py`**: Tests the Neo4jConnector and SchemaManager classes.

4. **`test_processor_manual.py`**: Tests the end-to-end IFC to Neo4j conversion process.

5. **`parse_test.py`**: Simple test for IFC file parsing using IfcOpenShell.

6. **`neo4j_setup_guide.md`**: Provides step-by-step instructions for setting up the Neo4j database.

## Documentation Files

1. **`file_structure.md`**: This document - explains the project structure in detail.

2. **`implementationplan.md`**: Details the implementation phases and tasks for the project.

3. **`README.md`**: Gives an overview of the project, installation instructions, and basic usage information.

4. **`neo4j_setup_guide.md`**: Instructions for setting up and connecting to the Neo4j database.

## Configuration Files

1. **`.gitignore`**: Specifies files and directories that Git should ignore, such as the virtual environment and Python cache files.

2. **`requirements.txt`**: Lists all Python package dependencies for the project.

## Development Workflow

The project is structured to support the following development workflow:

1. **Setup**: Follow the Neo4j setup guide to prepare the database environment.

2. **Data Preparation**: Place IFC model files in the `data/ifc_files/` directory.

3. **Model Parsing**: Use the `parser` module to extract information from IFC files.

4. **Topological Analysis**: Use the `topology` module to analyze spatial relationships.

5. **Database Storage**: Use the `database` module to store the extracted information in Neo4j.

6. **Query and Analysis**: Use Neo4j queries (Cypher) to analyze and visualize the building information.

## Future Structure Additions

As the project evolves, the following additions to the structure may be considered:

1. **`examples/`**: Directory for example scripts and notebooks demonstrating usage.

2. **`scripts/`**: Directory for utility scripts for data processing, database setup, etc.

3. **`docs/api/`**: API documentation generated from source code.

4. **`docs/tutorials/`**: Step-by-step tutorials for using the library.

5. **`migrations/`**: Database schema migration scripts.
