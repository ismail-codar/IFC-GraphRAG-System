#!/usr/bin/env python3
"""
Check the Neo4j database schema against the code schema.
"""

import logging
import sys
from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector
from src.ifc_to_graph.database.schema import NodeLabels, RelationshipTypes, SchemaManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_database(conn):
    """Clear all data from the database"""
    print("Clearing all data from database...", flush=True)
    result = conn.run_query("MATCH (n) DETACH DELETE n")
    print("Database cleared", flush=True)

def main():
    """Main function to check schema"""
    try:
        # Connect to Neo4j
        conn = Neo4jConnector('neo4j://localhost:7687', 'neo4j', 'test1234')
        
        # Clear the database first
        clear_database(conn)
        
        # Get schema from the database
        print("=== CONSTRAINTS IN DATABASE ===", flush=True)
        constraints = conn.run_query("SHOW CONSTRAINTS")
        for constraint in constraints:
            print(f"Constraint: {constraint}", flush=True)
        
        print("\n=== INDEXES IN DATABASE ===", flush=True)
        indexes = conn.run_query("SHOW INDEXES")
        for index in indexes:
            print(f"Index: {index}", flush=True)
        
        # Extract labels from database
        print("\n=== NODE LABELS IN DATABASE ===", flush=True)
        labels_result = conn.run_query("CALL db.labels()")
        db_labels = [record["label"] for record in labels_result]
        for label in sorted(db_labels):
            print(f"Label: {label}", flush=True)
        
        # Extract relationship types from database
        print("\n=== RELATIONSHIP TYPES IN DATABASE ===", flush=True)
        rel_types_result = conn.run_query("CALL db.relationshipTypes()")
        db_rel_types = [record["relationshipType"] for record in rel_types_result]
        for rel_type in sorted(db_rel_types):
            print(f"RelType: {rel_type}", flush=True)
        
        # Compare with expected schema from code
        print("\n=== NODE LABELS IN CODE ===", flush=True)
        code_labels = [label.value for label in NodeLabels]
        for label in sorted(code_labels):
            in_db = label in db_labels
            status = "✓" if in_db else "✗"
            print(f"{status} {label}", flush=True)
        
        print("\n=== RELATIONSHIP TYPES IN CODE ===", flush=True)
        code_rel_types = [rel_type.value for rel_type in RelationshipTypes]
        for rel_type in sorted(code_rel_types):
            in_db = rel_type in db_rel_types
            status = "✓" if in_db else "✗"
            print(f"{status} {rel_type}", flush=True)
        
        # Output summary
        print("\n=== SUMMARY ===", flush=True)
        extra_labels = [label for label in db_labels if label not in code_labels]
        if extra_labels:
            print(f"Labels in database but not in code: {extra_labels}", flush=True)
        else:
            print("No extra labels in database", flush=True)
        
        missing_labels = [label for label in code_labels if label not in db_labels]
        if missing_labels:
            print(f"Labels in code but not in database: {missing_labels}", flush=True)
        else:
            print("No missing labels in database", flush=True)
        
        extra_rel_types = [rel_type for rel_type in db_rel_types if rel_type not in code_rel_types]
        if extra_rel_types:
            print(f"Relationship types in database but not in code: {extra_rel_types}", flush=True)
        else:
            print("No extra relationship types in database", flush=True)
        
        missing_rel_types = [rel_type for rel_type in code_rel_types if rel_type not in db_rel_types]
        if missing_rel_types:
            print(f"Relationship types in code but not in database: {missing_rel_types}", flush=True)
        else:
            print("No missing relationship types in database", flush=True)
        
        # Close connection
        conn.close()
    
    except Exception as e:
        logger.error(f"Error checking schema: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
    print("Script completed successfully", flush=True) 