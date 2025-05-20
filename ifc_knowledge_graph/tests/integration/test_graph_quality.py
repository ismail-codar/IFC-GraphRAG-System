"""
Test Graph Quality

This script evaluates the quality of the IFC knowledge graph by checking:
1. Connectivity
2. Property completeness
3. Relationship consistency
"""

import os
import sys
import logging
import json

# Add the src directory to the Python path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
sys.path.insert(0, src_dir)

from ifc_to_graph.database import Neo4jConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Neo4j connection parameters
NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "test1234"  # Update with your actual password
NEO4J_DATABASE = None  # Use default database

def check_node_properties():
    """Check that nodes have expected properties."""
    logger.info("Checking node properties")
    
    # Create connector
    connector = Neo4jConnector(
        uri=NEO4J_URI,
        username=NEO4J_USER,
        password=NEO4J_PASSWORD,
        database=NEO4J_DATABASE
    )
    
    # Check for missing GlobalId
    query_missing_id = """
        MATCH (n)
        WHERE NOT exists(n.GlobalId) AND n:IfcProduct
        RETURN count(n) AS missing
    """
    result = connector.run_query(query_missing_id)
    missing_id_count = result[0]["missing"]
    
    logger.info(f"Found {missing_id_count} IfcProduct nodes without GlobalId")
    
    # Check property completeness by type
    query_props_by_type = """
        MATCH (n:IfcProduct)
        RETURN labels(n)[0] AS type,
               count(n) AS total,
               sum(CASE WHEN exists(n.Name) THEN 1 ELSE 0 END) AS with_name,
               sum(CASE WHEN exists(n.GlobalId) THEN 1 ELSE 0 END) AS with_id,
               sum(CASE WHEN exists(n.ObjectType) THEN 1 ELSE 0 END) AS with_type
        ORDER BY total DESC
        LIMIT 10
    """
    results = connector.run_query(query_props_by_type)
    
    # Calculate completeness scores
    for row in results:
        total = row["total"]
        name_pct = (row["with_name"] / total) * 100 if total > 0 else 0
        id_pct = (row["with_id"] / total) * 100 if total > 0 else 0
        type_pct = (row["with_type"] / total) * 100 if total > 0 else 0
        
        logger.info(f"Type: {row['type']}")
        logger.info(f"  Total: {total} nodes")
        logger.info(f"  Name: {name_pct:.1f}% complete")
        logger.info(f"  GlobalId: {id_pct:.1f}% complete")
        logger.info(f"  ObjectType: {type_pct:.1f}% complete")
    
    connector.close()
    
    return missing_id_count == 0

def check_relationship_consistency():
    """Check that relationships are consistent and complete."""
    logger.info("Checking relationship consistency")
    
    # Create connector
    connector = Neo4jConnector(
        uri=NEO4J_URI,
        username=NEO4J_USER,
        password=NEO4J_PASSWORD,
        database=NEO4J_DATABASE
    )
    
    # Check relationship counts by type
    query_rel_counts = """
        MATCH ()-[r]->()
        RETURN type(r) AS relationship_type,
               count(r) AS count
        ORDER BY count DESC
    """
    results = connector.run_query(query_rel_counts)
    
    logger.info("Relationship counts by type:")
    for row in results:
        logger.info(f"  {row['relationship_type']}: {row['count']}")
    
    # Check for orphaned elements (elements not connected to spatial structure)
    query_orphans = """
        MATCH (n:IfcElement)
        WHERE NOT (n)-[:CONTAINED_IN]->()
        RETURN count(n) AS orphan_count
    """
    result = connector.run_query(query_orphans)
    orphan_count = result[0]["orphan_count"]
    
    logger.info(f"Found {orphan_count} orphaned elements (not connected to spatial structure)")
    
    connector.close()
    
    return orphan_count == 0

def generate_quality_report():
    """Generate a quality report as JSON."""
    logger.info("Generating quality report")
    
    # Create connector
    connector = Neo4jConnector(
        uri=NEO4J_URI,
        username=NEO4J_USER,
        password=NEO4J_PASSWORD,
        database=NEO4J_DATABASE
    )
    
    # Gather graph statistics
    stats = {}
    
    # Total node count
    query_nodes = "MATCH (n) RETURN count(n) AS count"
    result = connector.run_query(query_nodes)
    stats["total_nodes"] = result[0]["count"]
    
    # Total relationship count
    query_rels = "MATCH ()-[r]->() RETURN count(r) AS count"
    result = connector.run_query(query_rels)
    stats["total_relationships"] = result[0]["count"]
    
    # Node counts by label
    query_by_label = """
        MATCH (n)
        WITH labels(n) AS labels, count(n) AS count
        UNWIND labels AS label
        RETURN label, sum(count) AS count
        ORDER BY count DESC
    """
    results = connector.run_query(query_by_label)
    stats["nodes_by_label"] = {row["label"]: row["count"] for row in results}
    
    # Relationship counts by type
    query_by_rel = """
        MATCH ()-[r]->()
        RETURN type(r) AS type, count(r) AS count
        ORDER BY count DESC
    """
    results = connector.run_query(query_by_rel)
    stats["relationships_by_type"] = {row["type"]: row["count"] for row in results}
    
    # Property completeness
    query_props = """
        MATCH (n:IfcProduct)
        RETURN 
            count(n) AS total,
            sum(CASE WHEN exists(n.Name) THEN 1 ELSE 0 END) AS with_name,
            sum(CASE WHEN exists(n.GlobalId) THEN 1 ELSE 0 END) AS with_id,
            sum(CASE WHEN exists(n.Description) THEN 1 ELSE 0 END) AS with_description
    """
    result = connector.run_query(query_props)
    if result and result[0]["total"] > 0:
        total = result[0]["total"]
        stats["property_completeness"] = {
            "Name": (result[0]["with_name"] / total) * 100,
            "GlobalId": (result[0]["with_id"] / total) * 100,
            "Description": (result[0]["with_description"] / total) * 100
        }
    
    connector.close()
    
    # Save report to file
    report_path = os.path.join(os.path.dirname(__file__), "..", "output", "graph_quality_report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, "w") as f:
        json.dump(stats, f, indent=2)
    
    logger.info(f"Quality report saved to {report_path}")
    
    return stats["total_nodes"] > 0

def main():
    """Run all quality checks and return appropriate exit code."""
    logger.info("Running graph quality tests")
    
    # Run checks
    props_check = check_node_properties()
    rel_check = check_relationship_consistency()
    report_check = generate_quality_report()
    
    # Print summary
    logger.info("\nTest summary:")
    logger.info(f"Node properties: {'PASSED' if props_check else 'ISSUES FOUND'}")
    logger.info(f"Relationship consistency: {'PASSED' if rel_check else 'ISSUES FOUND'}")
    logger.info(f"Quality report: {'GENERATED' if report_check else 'FAILED'}")
    
    # Return success if all checks passed
    return 0 if (props_check and rel_check and report_check) else 1

if __name__ == "__main__":
    sys.exit(main()) 