"""
Manual test for IFC processor

This script:
1. Loads an IFC file
2. Process it using the IfcProcessor
3. Stores it in Neo4j
"""

import os
import sys
import logging

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

# Test file path - adjust as needed
TEST_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "01_Duplex_A.ifc")

def test_process_file():
    """Test processing an IFC file and storing it in Neo4j."""
    logger.info(f"Testing processing file: {TEST_FILE_PATH}")
    
    try:
        # Create connector
        connector = Neo4jConnector(
            uri="neo4j://localhost:7687",
            username="neo4j",
            password="test1234"  # Update with your actual password
        )
        
        # Clear database first
        logger.info("Clearing database")
        connector.clear_database()
        
        # Create processor
        processor = IfcProcessor(connector)
        
        # Process file
        logger.info("Processing file")
        processor.process_file(TEST_FILE_PATH)
        
        # Verify that data was stored
        count_query = "MATCH (n) RETURN count(n) AS count"
        result = connector.run_query(count_query)
        node_count = result[0]["count"]
        
        logger.info(f"Created {node_count} nodes in Neo4j")
        
        # Check relationship counts
        rel_query = "MATCH ()-[r]->() RETURN count(r) AS count"
        result = connector.run_query(rel_query)
        rel_count = result[0]["count"]
        
        logger.info(f"Created {rel_count} relationships in Neo4j")
        
        # Close connector
        connector.close()
        
        return True
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Run test
    success = test_process_file()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1) 