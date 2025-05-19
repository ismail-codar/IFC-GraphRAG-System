#!/usr/bin/env python
"""
Simple test script to verify IfcParser functionality
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # ifc_knowledge_graph directory
sys.path.insert(0, parent_dir)

# Import parser
try:
    from src.ifc_to_graph.parser.ifc_parser import IfcParser
    logger.info("Successfully imported IfcParser")
except ImportError as e:
    logger.error(f"Error importing IfcParser: {e}")
    sys.exit(1)

def test_ifc_parser():
    """
    Test if IfcParser can load and parse the test IFC file
    """
    # IFC file path
    ifc_file_path = os.path.join(parent_dir, "data", "ifc_files", "Duplex_A_20110907.ifc")
    
    # Check if file exists
    if not os.path.exists(ifc_file_path):
        logger.error(f"Test IFC file not found: {ifc_file_path}")
        return
    
    logger.info(f"Found IFC file: {ifc_file_path}")
    
    try:
        # Create parser
        parser = IfcParser(ifc_file_path)
        logger.info("Successfully created IfcParser instance")
        
        # Test loading
        parser.load_file()
        logger.info("Successfully loaded IFC file")
        
        # Get elements
        elements = parser.get_elements()
        logger.info(f"Found {len(elements)} elements in the IFC file")
        
        # Get project info
        project = parser.get_project_info()
        logger.info(f"Project info: {project}")
        
        # Get schema version
        schema = parser.get_schema_version()
        logger.info(f"IFC Schema version: {schema}")
        
        return True
    except Exception as e:
        logger.error(f"Error parsing IFC file: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting IFC parser test")
    success = test_ifc_parser()
    if success:
        logger.info("IfcParser test completed successfully")
    else:
        logger.error("IfcParser test failed")
        sys.exit(1) 