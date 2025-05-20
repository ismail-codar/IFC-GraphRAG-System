#!/usr/bin/env python3
"""
Clear the Neo4j database before running a new test
"""

import os
import sys
import logging

# Add parent directory to path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector

def clear_database():
    """Clear all data from the Neo4j database"""
    try:
        # Connect to Neo4j
        logger.info("Connecting to Neo4j database...")
        conn = Neo4jConnector('neo4j://localhost:7687', 'neo4j', 'test1234')
        
        # Count existing nodes and relationships before clearing
        count_query = """
        MATCH (n) 
        RETURN count(n) as nodes
        """
        
        rel_query = """
        MATCH ()-[r]->() 
        RETURN count(r) as relationships
        """
        
        # Get counts
        result = conn.run_query(count_query)
        node_count = 0
        for record in result:
            node_count = record["nodes"]
            
        result = conn.run_query(rel_query)
        rel_count = 0
        for record in result:
            rel_count = record["relationships"]
            
        logger.info(f"Found {node_count} nodes and {rel_count} relationships in the database")
        
        # Clear all data
        logger.info("Clearing all data from the database...")
        query = "MATCH (n) DETACH DELETE n"
        conn.run_query(query)
        
        # Verify database is empty
        result = conn.run_query(count_query)
        for record in result:
            if record["nodes"] == 0:
                logger.info("Database cleared successfully")
            else:
                logger.warning(f"Database still contains {record['nodes']} nodes")
        
        # Close connection
        conn.close()
        logger.info("Database connection closed")
        
        return True
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        return False

if __name__ == "__main__":
    clear_database() 