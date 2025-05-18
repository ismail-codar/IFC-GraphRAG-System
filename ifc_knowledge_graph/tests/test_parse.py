import os
import sys
import logging

import ifcopenshell
import ifcopenshell.geom

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ifc_parsing():
    """Test basic IFC parsing functionality."""
    try:
        # Path to the IFC file
        ifc_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "01_Duplex_A.ifc")
        
        # Check if the file exists
        if not os.path.exists(ifc_file_path):
            logger.error(f"IFC file not found: {ifc_file_path}")
            return False
        
        # Load the IFC file
        logger.info(f"Loading IFC file: {ifc_file_path}")
        ifc_file = ifcopenshell.open(ifc_file_path)
        
        # Get some basic information
        element_count = len(ifc_file.by_type("IfcElement"))
        logger.info(f"IFC file loaded successfully with {element_count} elements")
        
        # Get project info
        project = ifc_file.by_type("IfcProject")[0]
        logger.info(f"Project GlobalId: {project.GlobalId}")
        logger.info(f"Project Name: {project.Name if project.Name else 'Unnamed project'}")
    
        # Success!
        logger.info("IFC parsing test completed successfully!")
        return True
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_ifc_parsing()
    sys.exit(0 if success else 1) 