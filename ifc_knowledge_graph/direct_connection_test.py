"""
Direct Neo4j connection test.

This script tests the connection to Neo4j without relying on our custom modules.
"""

import os
import sys
import logging
from neo4j import GraphDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Neo4j connection details - try different options
CONNECTION_OPTIONS = [
    {
        "uri": "bolt://localhost:7687",
        "description": "Default Bolt protocol"
    },
    {
        "uri": "neo4j://localhost:7687",
        "description": "Neo4j protocol"
    },
    {
        "uri": "bolt://127.0.0.1:7687",
        "description": "Explicit IP using Bolt"
    },
    {
        "uri": "http://localhost:7474",
        "description": "HTTP protocol (browser port)"
    }
]

USERNAME = "neo4j"
PASSWORD = "test1234"  # Change this to your actual password


def test_connection_options():
    """Test connection to Neo4j with different options."""
    logger.info("Testing connection to Neo4j with different options")
    
    for option in CONNECTION_OPTIONS:
        uri = option["uri"]
        description = option["description"]
        
        logger.info(f"Trying connection: {description} - {uri}")
        
        try:
            # Create driver
            driver = GraphDatabase.driver(uri, auth=(USERNAME, PASSWORD))
            
            # Verify connectivity
            driver.verify_connectivity()
            logger.info("✅ Connection verified successfully")
            
            # Run a simple query
            with driver.session() as session:
                result = session.run("RETURN 'Hello from Neo4j!' AS message")
                message = result.single()["message"]
                logger.info(f"Query result: {message}")
            
            # Close the driver
            driver.close()
            logger.info("Connection closed")
            
            return True
        except Exception as e:
            logger.error(f"❌ Connection failed: {str(e)}")
    
    logger.error("All connection attempts failed")
    return False


if __name__ == "__main__":
    # Run test
    success = test_connection_options()
    
    # Print additional help
    if not success:
        logger.info("\nTroubleshooting steps:")
        logger.info("1. Make sure Neo4j Desktop is running")
        logger.info("2. In Neo4j Desktop, click on your database and ensure it's started (green button)")
        logger.info("3. Check the connection details by clicking 'Connection Details' in Neo4j Desktop")
        logger.info("4. Verify that your password is correct (default is 'neo4j' for new installations)")
        logger.info("5. Try accessing Neo4j Browser at http://localhost:7474 to verify connectivity")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1) 