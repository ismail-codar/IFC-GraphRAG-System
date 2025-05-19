#!/usr/bin/env python
"""
Debug script to test the Neo4jConnector.run_query method
"""

import sys
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for more detailed logs
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add src to path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
sys.path.insert(0, src_dir)

from ifc_to_graph.database import Neo4jConnector

def main():
    """Test the run_query method with different queries to debug the issue."""
    try:
        # Create connector
        logger.info("Creating Neo4jConnector...")
        connector = Neo4jConnector(
            uri="neo4j://localhost:7687",
            username="neo4j",
            password="test1234"
        )
        
        # Try different queries
        queries = [
            "RETURN true AS connected",
            "RETURN 'Hello' AS message",
            "RETURN 1 AS test"
        ]
        
        for query in queries:
            logger.info(f"Testing query: {query}")
            try:
                result = connector.run_query(query)
                logger.info(f"Query result: {result}")
                if result:
                    logger.info(f"First record: {result[0]}")
                    for key, value in result[0].items():
                        logger.info(f"Key: {key}, Value: {value}, Type: {type(value)}")
            except Exception as e:
                logger.error(f"Query failed: {str(e)}")
        
        # Close connection
        connector.close()
        logger.info("Connection closed")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 