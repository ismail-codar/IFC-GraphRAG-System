# Graph Quality Analysis

This document provides an overview of the Graph Quality Analysis module, which is part of the IFC to Neo4j Knowledge Graph project. The module helps to validate, clean, and report on the quality of the graph database.

## Overview

The Graph Quality Analyzer is designed to ensure the integrity and quality of the Neo4j graph database generated from IFC files. It provides a set of tools for:

1. **Validation**: Analyzing the graph database to identify inconsistencies, errors, and potential issues
2. **Cleaning**: Automatically fixing detected issues to improve graph quality
3. **Reporting**: Generating comprehensive reports on the graph structure and quality metrics
4. **Statistics**: Collecting and presenting detailed information about the graph schema and content

## Validation Checks

The analyzer performs several types of validation checks:

### Schema Consistency
- Validates node label consistency
- Checks relationship type consistency
- Verifies required property existence (e.g., GlobalId for Element nodes)
- Ensures proper schema structure

### Relationship Integrity
- Checks for dangling relationships
- Identifies invalid relationship types between specific node labels
- Validates relationship cardinality for IFC hierarchy elements

### Orphan Node Detection
- Finds nodes without any relationships
- Reports orphaned nodes by type
- Identifies isolated elements in the graph

### Property Completeness
- Checks for missing required properties
- Verifies property value consistency
- Validates property types and formats

### IFC Reference Integrity
- Checks for duplicate GlobalIds
- Validates the format of GlobalIds
- Ensures proper IFC entity references

### Topological Consistency
- Verifies consistency between different topological relationship types
- Checks bidirectional consistency in containment relationships
- Identifies anomalies in the topological structure

## Data Cleaning

The analyzer provides several cleaning operations to fix detected issues:

### Orphan Node Cleaning
- Removes orphan nodes that aren't needed in the graph
- Preserves important nodes even if orphaned (e.g., Project, Site, Building)

### Relationship Issue Fixing
- Deletes invalid relationships between nodes
- Removes duplicate relationships
- Repairs inconsistent relationship patterns

### Property Issue Fixing
- Adds missing required properties with default values
- Corrects property value types
- Ensures property consistency

### Topological Issue Fixing
- Creates missing inverse relationships
- Makes relationships symmetric where required
- Ensures bidirectional consistency for topological relationships

## Reporting and Statistics

The analyzer generates comprehensive reports on the graph database:

### Graph Quality Metrics
- Overall graph quality score
- Detailed validation scores by category
- List of identified issues and their severity

### Graph Statistics
- Node counts by label
- Relationship counts by type
- Property usage statistics
- Graph density metrics
- Topological relationship metrics

### Schema Statistics
- Node label information
- Relationship type details
- Property key distribution by label
- Constraints and indexes information

## Usage

### Basic Validation

```python
from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector
from src.ifc_to_graph.utils.graph_quality_analyzer import GraphQualityAnalyzer

# Initialize the Neo4j connector
connector = Neo4jConnector(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="your_password"
)

# Create the analyzer
analyzer = GraphQualityAnalyzer(connector)

# Run validation
validation_results = analyzer.validate_graph()
print(f"Overall quality score: {validation_results.get('overall_score', 0)}")
```

### Data Cleaning

```python
# Define cleaning options
clean_options = {
    "remove_orphans": True,
    "fix_relationships": True,
    "fix_properties": True,
    "fix_topological": True
}

# Clean identified issues
cleaning_results = analyzer.clean_graph_issues(clean_options)
print(f"Nodes modified: {cleaning_results.get('nodes_modified', 0)}")
print(f"Relationships modified: {cleaning_results.get('relationships_modified', 0)}")
```

### Generate Report

```python
# Generate comprehensive report
report = analyzer.generate_report(include_details=True)

# Export to JSON file
analyzer.export_report_to_json("graph_quality_report.json")
```

### Get Schema Statistics

```python
# Get detailed schema information
schema_stats = analyzer.get_schema_statistics()

# Access constraint information
if "constraints" in schema_stats:
    for constraint in schema_stats["constraints"]:
        print(constraint)
```

## Integration with IFC Pipeline

The Graph Quality Analyzer is designed to be integrated into the IFC to Neo4j conversion pipeline:

1. **After Conversion**: Run validation after the IFC to Neo4j conversion to identify any issues
2. **Before Analysis**: Clean the graph before performing analytical queries to ensure accurate results
3. **Scheduled Maintenance**: Periodically validate and clean the graph database as part of regular maintenance

## Benefits

Using the Graph Quality Analyzer provides several benefits:

1. **Improved Data Quality**: Ensures the graph database accurately represents the IFC model
2. **Better Query Performance**: Cleaning the graph improves query efficiency
3. **Enhanced Reliability**: Validates relationships and properties for correctness
4. **Comprehensive Reporting**: Provides detailed insights into the graph structure
5. **Automated Maintenance**: Reduces manual effort required to maintain the database

## Conclusion

The Graph Quality Analysis module is an essential component of the IFC to Neo4j Knowledge Graph project, ensuring the quality and integrity of the graph database. By validating, cleaning, and reporting on the graph structure, it provides a robust foundation for further analysis and query operations. 