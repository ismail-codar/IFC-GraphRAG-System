#!/usr/bin/env python
"""
Test script to verify that IfcParser can load the test IFC file correctly.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # ifc_knowledge_graph directory
sys.path.insert(0, os.path.join(parent_dir, "src"))

from ifc_to_graph.parser.ifc_parser import IfcParser

def test_ifc_parser():
    """Test that IfcParser can load and parse the test IFC file."""
    # IFC file path
    ifc_file_path = os.path.join(parent_dir, "data", "ifc_files", "Duplex_A_20110907.ifc")
    
    # Verify file exists
    if not os.path.exists(ifc_file_path):
        print(f"ERROR: Test IFC file not found: {ifc_file_path}")
        return False
    
    try:
        # Create parser
        print(f"Loading IFC file: {ifc_file_path}")
        parser = IfcParser(ifc_file_path)
        
        # Check if the file was loaded
        if not parser.file:
            print("ERROR: Failed to load IFC file")
            return False
            
        # Get schema version
        schema_version = parser.get_schema_version()
        print(f"IFC Schema Version: {schema_version}")
        
        # Get project info
        project_info = parser.get_project_info()
        print(f"Project Info: {project_info}")
        
        # Get elements
        elements = parser.get_elements()
        print(f"Found {len(elements)} elements")
        
        # Sample a few elements for debugging
        for i, element in enumerate(elements[:5]):
            print(f"Element {i+1}: {element.is_a()} - GlobalId: {element.GlobalId if hasattr(element, 'GlobalId') else 'None'}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Exception while parsing IFC file: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = test_ifc_parser()
    sys.exit(0 if result else 1) 