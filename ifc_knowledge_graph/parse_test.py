import os
import sys
import logging

import ifcopenshell
import ifcopenshell.geom

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    # Path to the IFC file
    ifc_file_path = os.path.join("data", "ifc_files", "Duplex_A_20110907.ifc")
    
    # Check if the file exists
    if not os.path.exists(ifc_file_path):
        print(f"IFC file not found: {ifc_file_path}")
        sys.exit(1)
    
    # Load the IFC file
    print(f"Loading IFC file: {ifc_file_path}")
    ifc_file = ifcopenshell.open(ifc_file_path)
    
    # Get some basic information
    element_count = len(ifc_file.by_type("IfcElement"))
    print(f"IFC file loaded successfully with {element_count} elements")
    
    # Get project info
    project = ifc_file.by_type("IfcProject")[0]
    print(f"Project GlobalId: {project.GlobalId}")
    print(f"Project Name: {project.Name if project.Name else 'Unnamed project'}")

    # Success!
    print("IFC parsing test completed successfully!")

except Exception as e:
    print(f"Error: {str(e)}")
    sys.exit(1) 