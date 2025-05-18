# Topology Module

## Overview

This module provides functionality for analyzing the topological relationships between building elements in IFC models. It uses TopologicPy to create a geometric and topological representation of the IFC model, and provides methods to extract and analyze relationships such as adjacency, containment, and space boundaries.

## Features

- **IFC to TopologicPy Conversion**: Convert IFC elements to corresponding TopologicPy entities (Cells, Faces, Edges, etc.)
- **Adjacency Analysis**: Identify which elements are adjacent to each other
- **Containment Analysis**: Identify which elements contain or are contained by other elements
- **Space Boundary Detection**: Identify the building elements that form the boundaries of spaces
- **Connectivity Analysis**: Generate a comprehensive connectivity graph of the building model
- **Path Finding**: Find paths between elements in the building model

## Usage

```python
from src.ifc_to_graph.parser.ifc_parser import IfcParser
from src.ifc_to_graph.topology.topologic_analyzer import TopologicAnalyzer

# Initialize the IFC parser
ifc_parser = IfcParser("path/to/model.ifc")

# Initialize the topological analyzer
analyzer = TopologicAnalyzer(ifc_parser)

# Convert an IFC element to a topologic entity
element = ifc_parser.get_element_by_id("some_global_id")
topologic_entity = analyzer.convert_ifc_to_topologic(element)

# Get adjacency relationships
adjacency_map = analyzer.get_adjacency_relationships()

# Get containment relationships
containment_map = analyzer.get_containment_relationships()

# Get space boundary relationships
space_boundaries = analyzer.get_space_boundaries()

# Get comprehensive connectivity graph
connectivity_graph = analyzer.get_connectivity_graph()

# Find a path between two elements
path = analyzer.find_path("start_element_id", "end_element_id")

# Perform full topological analysis
analysis_results = analyzer.analyze_building_topology()
```

## Dependencies

This module depends on:
- `ifcopenshell` for working with IFC models
- `numpy` for numerical operations
- `TopologicPy` for topological analysis (optional, will gracefully degrade if not available)

## Implementation Notes

- The module includes caching mechanisms for improved performance with repeated operations
- If TopologicPy is not available, the module will provide warnings and basic functionality
- Tolerances can be adjusted for adjacency and containment detection
- Space boundaries are detected both from explicit IFC relationships and through topological analysis 