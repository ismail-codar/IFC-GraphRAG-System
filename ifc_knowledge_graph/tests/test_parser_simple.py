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
    
    # Verify file exists
    if not os.path.exists(ifc_file_path):
        logger.error(f"Test IFC file not found: {ifc_file_path}")
        return False
    
    try:
        # Initialize parser
        parser = IfcParser(ifc_file_path)
        logger.info(f"IFC Parser initialized with file: {ifc_file_path}")
        
        # Get and print schema version
        schema_version = parser.get_schema_version()
        logger.info(f"IFC Schema Version: {schema_version}")
        
        # Get all elements
        elements = parser.get_elements()
        logger.info(f"Found {len(elements)} elements in the IFC file")
        
        # Count elements by type
        element_types = {}
        for element in elements:
            element_type = element.is_a()
            if element_type not in element_types:
                element_types[element_type] = 0
            element_types[element_type] += 1
        
        logger.info("Element types in the IFC file:")
        for element_type, count in element_types.items():
            logger.info(f"  {element_type}: {count}")
        
        # Check for null GlobalId
        elements_with_null_globalid = []
        for element in elements:
            attrs = parser.get_element_attributes(element)
            if attrs.get("GlobalId") is None:
                elements_with_null_globalid.append({
                    "type": element.is_a(),
                    "name": element.Name if hasattr(element, "Name") else "Unnamed",
                    "all_attrs": attrs
                })
        
        logger.info(f"Found {len(elements_with_null_globalid)} elements with null GlobalId")
        if elements_with_null_globalid:
            logger.info("Elements with null GlobalId:")
            for i, element in enumerate(elements_with_null_globalid[:10]):  # Show first 10
                logger.info(f"  {i+1}. Type: {element['type']}, Name: {element['name']}")
                logger.info(f"     Attributes: {element['all_attrs']}")
            
            if len(elements_with_null_globalid) > 10:
                logger.info(f"  ... (and {len(elements_with_null_globalid) - 10} more)")
        
        # Get spatial structure
        spatial_structure = parser.get_spatial_structure()
        logger.info("Spatial structure:")
        logger.info(f"  Project: {spatial_structure['project'].get('Name')}")
        logger.info(f"  Sites: {len(spatial_structure['sites'])}")
        logger.info(f"  Buildings: {len(spatial_structure['buildings'])}")
        logger.info(f"  Storeys: {len(spatial_structure['storeys'])}")
        logger.info(f"  Spaces: {len(spatial_structure['spaces'])}")
        
        return True
    except Exception as e:
        logger.error(f"Error testing IFC parser: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = test_ifc_parser()
    if success:
        logger.info("IFC Parser test completed successfully")
    else:
        logger.error("IFC Parser test failed")
        sys.exit(1) 