# Topological Features Testing

This document explains how to test the topological analysis features of the IFC to Neo4j Knowledge Graph project.

## Overview

The topological features testing suite validates the functionality of the topological analysis components, which convert IFC geometry to topological entities and extract spatial relationships between building elements. The tests verify:

1. **Conversion**: IFC elements to TopologicPy entities
2. **Relationship Extraction**: Adjacency, containment, and space boundaries
3. **Connectivity Graph**: Generation of the full connectivity graph
4. **Path Finding**: Finding paths between building elements
5. **Database Mapping**: Correct mapping of topological relationships to Neo4j
6. **Performance**: Benchmarking the performance of topological operations

## Prerequisites

Before running the tests, make sure the following are installed and configured:

- Python 3.12 with required dependencies (IfcOpenShell, TopologicPy, Neo4j driver)
- Running Neo4j database instance
- Internet connection (for downloading test IFC files if not already available)

## Running the Tests

### Basic Test Execution

To run the topological features tests with the default IFC file (simple building):

```bash
python test_topological_features.py
```

### Specifying a Test File

You can specify which test file to use by providing its name as a command-line argument:

```bash
python test_topological_features.py duplex         # Test with Duplex Apartment model
python test_topological_features.py office         # Test with Office Building model
python test_topological_features.py simple_building # Test with Simple Building model
```

### Test Environment Configuration

By default, the tests connect to Neo4j at `bolt://localhost:7687` with user `neo4j` and password `test1234`. To change these settings, modify the `neo4j_uri`, `neo4j_user`, and `neo4j_password` parameters in the `TopologicalFeaturesTester` constructor.

## Test Descriptions

### 1. IFC to TopologicPy Conversion Test

This test checks the conversion of IFC elements to TopologicPy entities:
- Attempts to convert each building element in the IFC model
- Reports conversion success/failure rates by element type
- Identifies which element types convert successfully and which have issues

### 2. Adjacency Relationship Extraction Test

Tests the extraction of adjacency relationships between building elements:
- Measures the number of adjacency relationships found
- Reports the extraction time
- Validates the correctness of detected adjacencies

### 3. Containment Relationship Extraction Test

Tests the extraction of containment relationships (which elements contain others):
- Counts the total number of containment relationships
- Measures extraction performance
- Validates containment hierarchy

### 4. Space Boundaries Extraction Test

Tests the detection of space boundaries (which elements bound which spaces):
- Counts the number of space boundary relationships
- Measures extraction performance
- Validates boundary detection accuracy

### 5. Connectivity Graph Generation Test

Tests the generation of the complete connectivity graph:
- Measures the total number of connections in the graph
- Breaks down relationships by type
- Evaluates graph generation performance

### 6. Path Finding Test

Tests the ability to find paths between building elements:
- Attempts to find paths between spaces and walls
- Reports success rate and path lengths
- Measures pathfinding performance

### 7. Database Mapping Test

Tests the mapping of topological relationships to the Neo4j database:
- Clears existing topological relationships
- Analyzes building topology
- Imports all relationships into Neo4j
- Reports number of relationships created by type
- Measures mapping performance

### 8. Topological Query Test

Tests running topological queries against the Neo4j database:
- Executes a query to find adjacent elements
- Measures query performance
- Validates query results

## Test Results

After running the tests, a summary of results is displayed showing:

- Overall success/failure
- Total execution time
- Results for each individual test
- Relationship counts by type
- Element conversion rates by type
- Performance metrics for each operation

## Interpreting Results

### Success Criteria

A successful test run should show:

- High conversion rates (>80%) for common element types (walls, slabs, spaces)
- Reasonable number of topological relationships found (dependent on model complexity)
- All operations completing without exceptions
- Consistent relationship counts in the database compared to extracted counts

### Common Issues

If tests fail, check the following:

1. **Conversion failures**: May indicate issues with the IFC model or TopologicPy compatibility
2. **Few or no relationships**: Could indicate issues with geometry processing or tolerance settings
3. **Database errors**: Verify Neo4j connection and permissions
4. **Memory errors**: Large IFC models might require more memory for processing

## Performance Benchmarking

The test suite includes performance measurements for each operation:

- **Extraction time**: How long it takes to extract relationships from the model
- **Mapping time**: How long it takes to import relationships into Neo4j
- **Query time**: How long it takes to execute topological queries

These metrics can be used to optimize the topological analysis pipeline and identify bottlenecks.

## Extending the Tests

To add new tests:

1. Add a new test method to the `TopologicalFeaturesTester` class
2. Include the test in the `run_all_tests` method
3. Update this documentation to reflect the new test

## Conclusion

The topological features testing suite provides comprehensive validation of the topological analysis capabilities of the IFC to Neo4j Knowledge Graph project. By running these tests regularly, you can ensure that the topological functionality works correctly and efficiently across different IFC models. 