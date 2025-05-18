# IFC to Neo4j Knowledge Graph

This project converts Industry Foundation Classes (IFC) building models into rich knowledge graphs using Neo4j.

## Features

- Parse IFC files using IfcOpenShell
- Extract topological relationships with TopologicPy
- Create a rich knowledge graph in Neo4j
- Query building data using Cypher
- Visualize building data and relationships

## Installation

### Prerequisites

- Python 3.12
- Neo4j Desktop
- IfcOpenShell
- TopologicPy

### Setup

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Mac/Linux
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Start Neo4j database using Neo4j Desktop

## Project Structure

- `src/ifc_to_graph/` - Core package
  - `parser/` - IFC parsing utilities using IfcOpenShell
  - `topology/` - Topological analysis using TopologicPy
  - `database/` - Neo4j connection and graph operations
  - `utils/` - Helper utilities and tools
  - `cli/` - Command-line interface
- `data/` - Directory for IFC model files
- `tests/` - Unit and integration tests

## Usage

*Coming soon*

## License

*To be determined* 