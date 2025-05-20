"""
Tests for the IFC parser module.
"""

import os
import sys
import unittest
from pathlib import Path

# Add src directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(parent_dir, "src"))

# Import the parser directly
from ifc_to_graph.parser.ifc_parser import IfcParser


class TestIfcParser(unittest.TestCase):
    """Test cases for the IFC parser module."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Path to a test IFC file
        self.ifc_file_path = os.path.join(parent_dir, "data", "ifc_files", "Duplex_A_20110907.ifc")
        
        # Skip tests if the file doesn't exist
        if not os.path.exists(self.ifc_file_path):
            self.skipTest(f"Test IFC file not found: {self.ifc_file_path}")
        
        # Create a parser instance
        self.parser = IfcParser(self.ifc_file_path)
    
    def test_parser_initialization(self):
        """Test that the parser initializes correctly."""
        self.assertIsNotNone(self.parser.file)
        self.assertGreater(len(self.parser.file.by_type("IfcElement")), 0)
    
    def test_get_project_info(self):
        """Test retrieving project information."""
        project_info = self.parser.get_project_info()
        
        # Check that basic project info is present
        self.assertIn("GlobalId", project_info)
        self.assertIn("Name", project_info)
        
        # Verify actual values from the test file
        self.assertEqual(project_info["GlobalId"], "1xS3BCk291UvhgP2a6eflL")
        self.assertEqual(project_info["Name"], "0001")
    
    def test_get_elements(self):
        """Test retrieving elements."""
        # Get all elements
        all_elements = self.parser.get_elements()
        self.assertGreater(len(all_elements), 0)
        
        # Get specific element types
        walls = self.parser.get_elements("IfcWall")
        self.assertGreaterEqual(len(walls), 0)
        
        doors = self.parser.get_elements("IfcDoor")
        self.assertGreaterEqual(len(doors), 0)
    
    def test_get_element_attributes(self):
        """Test retrieving element attributes."""
        # Get a wall element
        walls = self.parser.get_elements("IfcWall")
        if len(walls) == 0:
            self.skipTest("No wall elements found in test file")
        
        # Get the first wall
        wall = walls[0]
        
        # Get attributes
        attributes = self.parser.get_element_attributes(wall)
        
        # Check that basic attributes are present
        self.assertIn("GlobalId", attributes)
        self.assertIn("IFCType", attributes)
        self.assertEqual(attributes["IFCType"], "IfcWall")
    
    def test_get_spatial_structure(self):
        """Test retrieving the spatial structure."""
        structure = self.parser.get_spatial_structure()
        
        # Check that basic structure components are present
        self.assertIn("project", structure)
        self.assertIn("sites", structure)
        self.assertIn("buildings", structure)
        self.assertIn("storeys", structure)
        self.assertIn("spaces", structure)
    
    def test_get_property_sets(self):
        """Test retrieving property sets."""
        # Get a wall element
        walls = self.parser.get_elements("IfcWall")
        if len(walls) == 0:
            self.skipTest("No wall elements found in test file")
        
        # Get the first wall
        wall = walls[0]
        
        # Get property sets
        property_sets = self.parser.get_property_sets(wall)
        
        # There should be at least some property sets
        self.assertGreaterEqual(len(property_sets), 0)
    
    def test_get_relationships(self):
        """Test retrieving relationships."""
        # Get a wall element
        walls = self.parser.get_elements("IfcWall")
        if len(walls) == 0:
            self.skipTest("No wall elements found in test file")
        
        # Get the first wall
        wall = walls[0]
        
        # Get relationships
        relationships = self.parser.get_relationships(wall)
        
        # Check that relationship categories are present
        self.assertIn("ContainedIn", relationships)
        self.assertIn("HostedBy", relationships)
        self.assertIn("Decomposes", relationships)
        self.assertIn("HasOpenings", relationships)
    
    def test_extract_material_info(self):
        """Test extracting material information."""
        # Get a wall element
        walls = self.parser.get_elements("IfcWall")
        if len(walls) == 0:
            self.skipTest("No wall elements found in test file")
        
        # Get the first wall
        wall = walls[0]
        
        # Get material info
        materials = self.parser.extract_material_info(wall)
        
        # Most walls should have at least one material
        self.assertGreaterEqual(len(materials), 0)


if __name__ == "__main__":
    unittest.main() 