"""
Manual test for IFC to Neo4j processor.

Run this script directly to test the complete IFC to Neo4j conversion process.
"""

import os
import sys
import logging
import time

# Add the src directory to the Python path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
sys.path.insert(0, src_dir)

from ifc_to_graph.processor import IfcProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_processor():
    """Test the IFC to Neo4j processor with a sample IFC file."""
    logger.info("Testing IFC to Neo4j processor")
    
    # Path to test IFC file
    ifc_file_path = os.path.join("data", "ifc_files", "Duplex_A_20110907.ifc")
    
    if not os.path.exists(ifc_file_path):
        logger.error(f"Test IFC file not found: {ifc_file_path}")
        return False
    
    try:
        # Create processor
        processor = IfcProcessor(
            ifc_file_path=ifc_file_path,
            neo4j_uri="neo4j://localhost:7687",
            neo4j_username="neo4j",
            neo4j_password="password"  # Replace with your actual password
        )
        
        # Process the file with clear_existing=True to start with a clean database
        start_time = time.time()
        stats = processor.process(clear_existing=True)
        total_time = time.time() - start_time
        
        # Close connection
        processor.close()
        
        # Print statistics
        logger.info(f"Processing completed in {total_time:.2f} seconds")
        logger.info(f"Statistics:")
        logger.info(f"- Processed {stats['element_count']} elements")
        logger.info(f"- Created {stats['node_count']} nodes")
        logger.info(f"- Created {stats['relationship_count']} relationships")
        logger.info(f"- Created {stats['property_set_count']} property sets")
        logger.info(f"- Created {stats['material_count']} materials")
        
        return True
    except Exception as e:
        logger.error(f"Processor test failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Run test
    success = test_processor()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1) 