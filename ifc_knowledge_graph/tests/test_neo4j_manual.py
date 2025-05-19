"""
Manual test for Neo4j connector.

Run this script directly to test the Neo4j connector functionality.
"""

import os
import sys
import logging

# Add the src directory to the Python path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
sys.path.insert(0, src_dir)

from ifc_to_graph.database import Neo4jConnector, SchemaManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_connection():
    """Test connection to Neo4j database."""
    logger.info("Testing connection to Neo4j database")
    
    try:
        # Create connector with performance monitoring disabled
        connector = Neo4jConnector(
            uri="neo4j://localhost:7687",
            username="neo4j",
            password="test1234",  # Updated with actual password
            enable_monitoring=False  # Disable performance monitoring
        )
        
        # Test connection with different queries
        queries = [
            "RETURN true AS connected",
            "RETURN 'Connected!' AS message"
        ]
        
        for query in queries:
            logger.info(f"Testing query: {query}")
            try:
                result = connector.run_query(query)
                logger.info(f"Query result: {result}")
                
                if result and len(result) > 0:
                    logger.info(f"Result[0]: {result[0]}")
                    for key, value in result[0].items():
                        logger.info(f"Key: {key}, Value: {value}, Type: {type(value)}")
            except Exception as e:
                logger.error(f"Query failed: {str(e)}")
        
        # Close connection
        connector.close()
        
        return True
    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        return False


def test_schema_setup():
    """Test setting up schema in Neo4j database."""
    logger.info("Testing schema setup in Neo4j database")
    
    try:
        # Create connector with performance monitoring disabled
        connector = Neo4jConnector(
            uri="neo4j://localhost:7687",
            username="neo4j",
            password="test1234",  # Updated with actual password
            enable_monitoring=False  # Disable performance monitoring
        )
        
        # Create schema manager
        schema_manager = SchemaManager(connector)
        
        # Set up schema
        schema_manager.setup_schema()
        
        # Test schema by counting constraints and indexes
        constraints = connector.run_query("SHOW CONSTRAINTS")
        indexes = connector.run_query("SHOW INDEXES")
        
        logger.info(f"Created {len(constraints)} constraints and {len(indexes)} indexes")
        
        # Close connection
        connector.close()
        
        return True
    except Exception as e:
        logger.error(f"Schema setup test failed: {str(e)}")
        return False


def run_all_tests():
    """Run all tests."""
    logger.info("Running all Neo4j connector tests")
    
    # Run tests
    connection_result = test_connection()
    schema_result = test_schema_setup() if connection_result else False
    
    # Print summary
    logger.info("Test summary:")
    logger.info(f"- Connection test: {'PASSED' if connection_result else 'FAILED'}")
    logger.info(f"- Schema setup test: {'PASSED' if schema_result else 'FAILED'}")
    
    return connection_result and schema_result


if __name__ == "__main__":
    # Run all tests
    success = run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1) 