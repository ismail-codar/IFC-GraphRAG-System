# TopologicPy

![TopologicPy Logo](https://topologic.app/wp-content/uploads/2023/02/topologicpy-logo-no-loop.gif)

## Overview

TopologicPy is an open-source Python 3 implementation of Topologic, a powerful spatial modeling and analysis software library that revolutionizes architectural design and analysis. It enables the creation of hierarchical and topological information-rich 3D representations that offer unprecedented flexibility and control in the design process. TopologicPy integrates geometry, topology, information, and artificial intelligence to enhance Building Information Models (BIM) with Building Intelligence Models.

## Key Features

### Advanced Spatial Modeling
- **Non-Manifold Topology (NMT)**: Uses cutting-edge C++-based NMT core technology (Open CASCADE)
- **Defeaturing**: Simplifies geometry by removing small or unnecessary details while maintaining topological consistency
- **Encoded Meshing**: Uses base elements to build 3D information-encoded models that match exact specifications

### Mixed Dimensionality Support
- **Lines**: Represent columns and beams
- **Surfaces**: Represent walls and slabs
- **Volumes**: Represent solids
- **Non-building entities**: Can efficiently attach to the structure (e.g., structural loads)

### Graph-Based Analysis
- Integrates with Graph Machine Learning (GML)
- Intelligent algorithms for graph and node classification
- Classifies building typologies
- Predicts associations and completes missing information in building models

### Data Connectivity
- Industry-standard methods for data transport including:
  - IFC (Industry Foundation Classes)
  - OBJ
  - BREP
  - HBJSON
  - CSV
- Cloud-based serialization through services like Speckle

### Compatibility
- Open interface through command-line and scripts
- Visual data flow programming (VDFP) plugins for popular BIM software
- Cloud-based interfaces through Streamlit

## Installation

TopologicPy can be easily installed using pip:

```
pip install topologicpy --upgrade
```

### Prerequisites

TopologicPy depends on Python 3.12 or earlier (but not 3.13 yet). The following dependencies will be installed automatically:

- numpy >= 1.24.0
- scipy >= 1.10.0
- plotly >= 5.11.0
- ifcopenshell >=0.7.9
- ipfshttpclient >= 0.7.0
- web3 >=5.30.0
- openstudio >= 3.4.0
- topologic_core >= 6.0.6
- lbt-ladybug >= 0.25.161
- lbt-honeybee >= 0.6.12
- honeybee-energy >= 1.91.49
- json >= 2.0.9
- py2neo >= 2021.2.3
- pyvisgraph >= 0.2.1
- specklepy >= 2.7.6
- pandas >= 1.4.2
- dgl >= 0.8.2

## Getting Started

1. Create a virtual environment with Python 3.12 (recommended as IfcOpenShell doesn't support Python 3.13 yet):
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install TopologicPy:
   ```
   pip install topologicpy --upgrade
   ```

3. Import and use in your Python script:
   ```python
   import topologicpy
   # Start using the API
   ```

## IFC to Neo4j Knowledge Graph Conversion

TopologicPy is an excellent tool for converting IFC (Industry Foundation Classes) models into Neo4j knowledge graphs. This process involves:

1. **Loading IFC Models**: Import IFC files using IfcOpenShell
2. **Topological Analysis**: Analyze the spatial relationships and connectivity between building elements
3. **Graph Construction**: Create a graph representation with entities as nodes and relationships as edges
4. **Semantic Enrichment**: Attach semantic information from IFC to the graph
5. **Neo4j Export**: Export the graph to Neo4j using the Neo4j driver

### Example Workflow

```python
import topologicpy
import ifcopenshell
from neo4j import GraphDatabase

# Load IFC model
ifc_file = ifcopenshell.open("building_model.ifc")

# Extract building topology
cell_complex = topologicpy.BRepParser.ByIFC(ifc_file)

# Create graph representation
graph = topologicpy.Graph.ByTopology(cell_complex)

# Connect to Neo4j
driver = GraphDatabase.driver("neo4j://localhost:7687", auth=("neo4j", "password"))

# Export graph to Neo4j (simplified example)
with driver.session() as session:
    # Create nodes for each space
    for cell in topologicpy.Topology.Cells(cell_complex):
        properties = topologicpy.Dictionary.ByKeysValues(
            ["guid", "name", "type"],
            [cell.Guid(), cell.Name(), "Space"]
        )
        
        session.run(
            "CREATE (s:Space {guid: $guid, name: $name, type: $type})",
            guid=properties["guid"], 
            name=properties["name"], 
            type=properties["type"]
        )
    
    # Create relationships based on adjacency
    for edge in topologicpy.Graph.Edges(graph):
        start_vertex, end_vertex = topologicpy.Edge.Vertices(edge)
        start_cell = topologicpy.Vertex.CellContents(start_vertex)[0]
        end_cell = topologicpy.Vertex.CellContents(end_vertex)[0]
        
        session.run(
            """
            MATCH (a:Space {guid: $start_guid})
            MATCH (b:Space {guid: $end_guid})
            CREATE (a)-[:ADJACENT_TO]->(b)
            """,
            start_guid=start_cell.Guid(),
            end_guid=end_cell.Guid()
        )

driver.close()
```

## Key Classes for IFC-to-Neo4j Conversion

- **Topology**: Base class that all topology elements inherit from
- **Cell**: Represents a 3D spatial unit (like a room)
- **CellComplex**: Collection of cells with defined relationships
- **Edge**: Represents connections between vertices
- **Face**: Represents surfaces (like walls, floors)
- **Graph**: Creates and manipulates graph structures from topological models
- **Vertex**: Represents points in space (like corners)
- **Wire**: Represents connected edges (like outlines)
- **Dictionary**: Handles attributes and properties of topological entities

## Benefits for BIM-to-Graph Conversion

- **Topological Accuracy**: Maintains precise spatial relationships
- **Lightweight Representation**: Reduces complexity while preserving essential relationships
- **Semantic Enrichment**: Preserves and enhances building information
- **Analysis Ready**: Prepared for various graph algorithms and machine learning
- **Interoperability**: Bridges different platforms and data formats

## Resources and Documentation

- API Documentation: [https://topologicpy.readthedocs.io](https://topologicpy.readthedocs.io)
- GitHub Repository: [https://github.com/wassimj/topologicpy](https://github.com/wassimj/topologicpy)
- Official Website: [https://topologic.app](https://topologic.app)

## License

TopologicPy is released under the AGPLv3 license, offering open-source freedom while ensuring derivative works remain open.

- TopologicPy: © 2024 Wassim Jabi
- Topologic: © 2024 Cardiff University and UCL 