#!/usr/bin/env python
"""
Clear Neo4j Database

This script connects to Neo4j and clears all data from the database.
Use with caution as this permanently deletes all nodes and relationships.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ifc_to_graph.database import Neo4jConnector

def clear_database():
    """Connect to Neo4j and clear all data."""
    print("Connecting to Neo4j database...")
    
    # Create connector
    connector = Neo4jConnector(
        uri="neo4j://localhost:7687",
        username="neo4j", 
        password="password"
    )
    
    # Test connection
    if not connector.test_connection():
        print("ERROR: Failed to connect to Neo4j")
        return False
    
    print("Connected to Neo4j successfully.")
    print("WARNING: About to delete all data from the database!")
    
    confirm = input("Type 'yes' to confirm: ")
    if confirm.lower() != 'yes':
        print("Operation canceled.")
        return False
    
    # Clear database
    print("Clearing database...")
    query = "MATCH (n) DETACH DELETE n"
    connector.run_query(query)
    
    # Verify
    node_count = connector.run_query("MATCH (n) RETURN count(n) as count")[0]['count']
    
    print(f"Database cleared. Node count: {node_count}")
    connector.close()
    
    return node_count == 0

if __name__ == "__main__":
    success = clear_database()
    sys.exit(0 if success else 1) 