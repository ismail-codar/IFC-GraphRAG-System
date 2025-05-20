#!/usr/bin/env python3
"""
Simple script to test Neo4j connection.
"""

import logging
from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_neo4j_connection():
    """Test connection to Neo4j using the provided credentials."""
    try:
        # Initialize connection
        logger.info("Attempting to connect to Neo4j...")
        connector = Neo4jConnector(
            uri="neo4j://localhost:7687",
            username="neo4j",
            password="test1234"
        )
        
        # Test connection
        connected = connector.test_connection()
        if connected:
            logger.info("✅ Successfully connected to Neo4j!")
            
            # Get basic database stats
            node_count = connector.run_query("MATCH (n) RETURN count(n) as count")[0]["count"]
            rel_count = connector.run_query("MATCH ()-[r]->() RETURN count(r) as count")[0]["count"]
            
            logger.info(f"Database contains {node_count} nodes and {rel_count} relationships")
            
            # Check relationship types
            rel_types = connector.run_query(
                "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC"
            )
            
            if rel_types:
                logger.info("Relationship types in the database:")
                for rel in rel_types:
                    logger.info(f"  - {rel['type']}: {rel['count']} relationships")
            else:
                logger.info("No relationships found in the database")
                
        else:
            logger.error("❌ Failed to connect to Neo4j")
            
        # Close connection
        connector.close()
        
    except Exception as e:
        logger.error(f"❌ Error connecting to Neo4j: {str(e)}")

if __name__ == "__main__":
    test_neo4j_connection() 