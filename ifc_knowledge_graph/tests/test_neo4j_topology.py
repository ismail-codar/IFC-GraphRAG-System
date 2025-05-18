"""
Test Neo4j Topology Relationships

This script tests the topology-related functions for storing IFC topology in Neo4j.
"""

import os
import sys
import logging
import ifcopenshell

# Add the src directory to the Python path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
sys.path.insert(0, src_dir)

from ifc_to_graph.database import Neo4jConnector
from ifc_to_graph.processor import IfcProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Test file paths
TEST_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "01_Duplex_A.ifc")
SMALL_TEST_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "small_test.ifc")

# Neo4j connection parameters
URI = "neo4j://localhost:7687"
USERNAME = "neo4j"
PASSWORD = "test1234"  # Update with your actual password
DATABASE = None  # Use default database


def test_process_topology():
    """Test processing IFC topology into Neo4j."""
    logger.info("Testing topology processing to Neo4j")
    
    # Load IFC file
    if os.path.exists(SMALL_TEST_FILE_PATH):
        ifc_file_path = SMALL_TEST_FILE_PATH
        logger.info(f"Using small test file: {SMALL_TEST_FILE_PATH}")
    else:
        ifc_file_path = TEST_FILE_PATH
        logger.info(f"Using main test file: {TEST_FILE_PATH}")
    
    try:
        # Create Neo4j connector
        connector = Neo4jConnector(
            uri=URI,
            username=USERNAME,
            password=PASSWORD,
            database=DATABASE
        )
        
        # Clear existing data
        logger.info("Clearing existing graph data")
        connector.clear_database()
        
        # Create processor
        processor = IfcProcessor(connector)
        
        # Process IFC file
        logger.info(f"Processing IFC file: {ifc_file_path}")
        processor.process_file(ifc_file_path)
        
        # Verify processing by counting nodes
        count_query = "MATCH (n) RETURN count(n) AS nodeCount"
        result = connector.run_query(count_query)
        node_count = result[0]["nodeCount"] if result else 0
        
        logger.info(f"Created {node_count} nodes in Neo4j")
        
        # Check for spatial structure
        spatial_query = """
            MATCH (s:IfcSpatialElement)
            RETURN s.GlobalId AS id, s.Name AS name, labels(s) AS types, count
            ORDER BY count DESC
            LIMIT 5
        """
        spatial_result = connector.run_query(spatial_query)
        
        logger.info("Spatial elements in graph:")
        for i, record in enumerate(spatial_result):
            logger.info(f"  {i+1}. {record['name']} ({', '.join(record['types'])})")
        
        # Check for element relationships
        rel_query = """
            MATCH (a)-[r]->(b)
            RETURN type(r) AS relType, count(r) AS count
            ORDER BY count DESC
        """
        rel_result = connector.run_query(rel_query)
        
        logger.info("Relationship types in graph:")
        for record in rel_result:
            logger.info(f"  {record['relType']}: {record['count']} relationships")
        
        # Close connection
        connector.close()
        
        # If we got here without errors, the test passed
        return node_count > 0
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return False


def main():
    """Run tests and return appropriate exit code."""
    logger.info("Running Neo4j topology tests")
    
    # Run tests
    success = test_process_topology()
    
    # Print result
    logger.info(f"Test {'PASSED' if success else 'FAILED'}")
    
    # Return appropriate exit code
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 