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
└── requirements.txt       # Python dependencies
└── README.md              # Project overview and instructions
```

## Directory Details

### `data/`

The data directory stores IFC model files and other data used by the application.

```
data/
└── ifc_files/             # IFC model files
    └── .gitkeep           # Placeholder to ensure directory is tracked in Git
```

### `docs/`

The docs directory contains all project documentation.

```
docs/
├── concept.md             # Project concept and design brief
├── file_structure.md      # This document - explaining project structure
├── implementationplan.md  # Implementation phases and tasks
└── topologicpy.md         # Documentation about TopologicPy library
```

### `src/`

The src directory contains all source code for the application, organized in a package structure.

```
src/
└── ifc_to_graph/          # Main package
    ├── __init__.py        # Package initialization
    ├── cli/               # Command-line interface
    │   └── __init__.py    # CLI module initialization
    ├── database/          # Neo4j database operations
    │   └── __init__.py    # Database module initialization
    ├── parser/            # IFC file parsing functionality
    │   └── __init__.py    # Parser module initialization
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
└── test_neo4j_connection.py # Neo4j connection testing
```

## Module Purposes

### Source Code Modules

1. **`parser/`**: Contains code for parsing IFC files using IfcOpenShell, extracting entities, properties, and relationships.

2. **`topology/`**: Contains code for analyzing topological relationships between building elements using TopologicPy, including adjacency, containment, and connectivity.

3. **`database/`**: Contains code for Neo4j database operations, including connection management, query execution, and transaction handling.

4. **`utils/`**: Contains utility functions and helper classes used across the project.

5. **`cli/`**: Contains command-line interface code for running the application from the command line.

### Test Modules

1. **`test_neo4j_connection.py`**: Tests the connection to the Neo4j database and sets up initial constraints and indexes.

## File Descriptions

### Documentation Files

1. **`concept.md`**: Outlines the project vision, requirements, and technical approach.

2. **`implementationplan.md`**: Details the implementation phases and tasks for the project.

3. **`topologicpy.md`**: Provides information about the TopologicPy library, its features, and usage.

4. **`README.md`**: Gives an overview of the project, installation instructions, and basic usage information.

5. **`file_structure.md`**: This document - explains the project structure in detail.

### Configuration Files

1. **`.gitignore`**: Specifies files and directories that Git should ignore, such as the virtual environment and Python cache files.

2. **`requirements.txt`**: Lists all Python package dependencies for the project.

## Development Workflow

The project is structured to support the following development workflow:

1. **Data Preparation**: Place IFC model files in the `data/ifc_files/` directory.

2. **Model Parsing**: Use the `parser` module to extract information from IFC files.

3. **Topological Analysis**: Use the `topology` module to analyze spatial relationships.

4. **Database Storage**: Use the `database` module to store the extracted information in Neo4j.

5. **Query and Analysis**: Use Neo4j queries (Cypher) to analyze and visualize the building information.

## Future Structure Additions

As the project evolves, the following additions to the structure may be considered:

1. **`examples/`**: Directory for example scripts and notebooks demonstrating usage.

2. **`scripts/`**: Directory for utility scripts for data processing, database setup, etc.

3. **`docs/api/`**: API documentation generated from source code.

4. **`docs/tutorials/`**: Step-by-step tutorials for using the library.

5. **`migrations/`**: Database schema migration scripts.
