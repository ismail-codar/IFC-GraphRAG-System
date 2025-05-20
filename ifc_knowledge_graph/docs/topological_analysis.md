# Topological Analysis Feature

## Overview

The topological analysis feature in the IFC Knowledge Graph pipeline extracts implicit spatial relationships between building elements based on their geometry. While IFC files contain explicit relationships defined by the BIM authoring tool, many spatial relationships are not explicitly modeled but are implicit in the geometry itself.

This feature uses [TopologicPy](https://github.com/wassimj/topologicpy) to analyze the 3D geometry of building elements and extract these implicit relationships, creating a richer knowledge graph with more sophisticated spatial queries.

## Available Relationship Types

When topological analysis is enabled, the following relationship types are added to the knowledge graph:

1. **ADJACENT** - Identifies elements that are adjacent to each other (share a boundary or are within a specified tolerance). This applies to walls, slabs, spaces, and other building elements.

2. **CONTAINS_TOPOLOGICALLY** - Identifies spatial containment relationships based on actual geometry (e.g., a space fully contains certain elements).

3. **BOUNDED_BY** - Identifies elements that form the boundary of a space (e.g., walls, slabs, roofs that bound a space).

4. **CONNECTS_SPACES** - Identifies elements that connect spaces, such as doors and windows.

These relationships are created with additional properties that provide more detail:

- `relationshipSource`: Set to "topologicalAnalysis" to differentiate from IFC-defined relationships
- `relationshipType`: The type of relationship (e.g., "adjacency", "containment", etc.)
- `distanceTolerance`: The tolerance used for determining relationships
- `containmentType`: For containment relationships (e.g., "full", "partial")
- Additional properties depending on the relationship type

## Using Topological Analysis

### Command-Line Interface

To enable topological analysis when converting an IFC file to Neo4j, use the `--topology` or `-t` flag:

```bash
# Basic usage
python -m ifc_knowledge_graph graph path/to/your/model.ifc --topology

# Full example with other options
python -m ifc_knowledge_graph graph path/to/your/model.ifc --topology --clear --batch-size 200 --parallel
```

### Programmatic Usage

When using the `IfcProcessor` class directly, set the `enable_topological_analysis` parameter to `True`:

```python
from ifc_to_graph.processor import IfcProcessor

processor = IfcProcessor(
    ifc_file_path="path/to/your/model.ifc",
    neo4j_uri="neo4j://localhost:7687",
    neo4j_username="neo4j",
    neo4j_password="password",
    enable_topological_analysis=True
)

stats = processor.process(clear_existing=True)
print(f"Created {stats['topological_relationship_count']} topological relationships")
```

## Example Neo4j Queries Using Topological Relationships

Here are some example Cypher queries that leverage the topological relationships:

### Finding Adjacent Walls

```cypher
MATCH (w1:Element {IFCType: 'IfcWall'})-[r:ADJACENT]->(w2:Element {IFCType: 'IfcWall'})
RETURN w1.Name, w2.Name, r.distanceTolerance
```

### Finding Spaces Connected by Doors

```cypher
MATCH (s1:Element {IFCType: 'IfcSpace'})<-[:CONNECTS_SPACES]-(d:Element {IFCType: 'IfcDoor'})-[:CONNECTS_SPACES]->(s2:Element {IFCType: 'IfcSpace'})
RETURN s1.Name, d.Name, s2.Name
```

### Finding All Elements Contained in a Space

```cypher
MATCH (s:Element {IFCType: 'IfcSpace'})-[:CONTAINS_TOPOLOGICALLY]->(e:Element)
RETURN s.Name, count(e) as ElementCount, collect(e.Name) as ElementNames
```

### Finding All Elements That Form the Boundary of a Space

```cypher
MATCH (s:Element {IFCType: 'IfcSpace'})<-[:BOUNDED_BY]-(e:Element)
RETURN s.Name, count(e) as BoundaryElements, collect(e.IFCType + ': ' + e.Name) as ElementDetails
```

## Performance Considerations

Topological analysis is a computation-intensive process, especially for large IFC models. Here are some considerations:

1. **Processing Time**: Enabling topological analysis significantly increases the processing time, sometimes by 2-5x depending on the model complexity.

2. **Memory Usage**: Analyzing topology requires more memory as it loads and processes geometric data.

3. **Selective Usage**: Consider enabling topological analysis only when needed for specific analysis tasks rather than for all imports.

4. **Parallel Processing**: Using the `--parallel` flag can help speed up the process on multi-core systems.

## Troubleshooting

### Common Issues

1. **Missing TopologicPy**:
   If you see the error "TopologicPy is not available", make sure it's installed:
   ```bash
   pip install topologicpy
   ```

2. **Geometry Processing Errors**:
   Some IFC elements with complex or invalid geometry might cause errors. The system will log these and continue processing other elements.

3. **Empty Results**:
   If no topological relationships are created, check:
   - Your IFC file has 3D geometry (not just 2D)
   - The elements are properly modeled with valid spatial relationships
   - TopologicPy is working correctly

## Limitations

1. **Geometric Accuracy**: Topological analysis depends on the quality of geometry in the IFC file.

2. **Tolerance Settings**: Default tolerance values might need adjustment for different models.

3. **Unsupported Elements**: Some specialized IFC element types may not be processed correctly.

## Future Enhancements

1. **Custom Tolerance Settings**: Add command-line options to control tolerance parameters.

2. **Improved Geometry Processing**: Better handling of complex or invalid geometry.

3. **Additional Relationship Types**: More sophisticated spatial relationships.

4. **Performance Optimizations**: Faster processing of large models. 