"""
IFC Parser Module

This module provides functionality to parse IFC files using IfcOpenShell,
extracting entities, relationships, attributes, and property sets.
"""

import os
import logging
from typing import Dict, List, Set, Tuple, Optional, Any, Iterator

import ifcopenshell
import ifcopenshell.geom

# Configure logging
logger = logging.getLogger(__name__)


class IfcParser:
    """
    Main parser class for extracting data from IFC files using IfcOpenShell.
    """
    
    def __init__(self, ifc_file_path: str):
        """
        Initialize the IFC parser with a file path.
        
        Args:
            ifc_file_path: Path to the IFC file
        """
        self.ifc_file_path = ifc_file_path
        self.file = None
        self._elements_cache = {}
        self._spatial_structure_cache = {}
        self._relationships_cache = {}
        self._property_sets_cache = {}
        
        # Load file
        self._load_file()
        
    def _load_file(self) -> None:
        """Load the IFC file using IfcOpenShell."""
        if not os.path.exists(self.ifc_file_path):
            raise FileNotFoundError(f"IFC file not found: {self.ifc_file_path}")
        
        try:
            logger.info(f"Loading IFC file: {self.ifc_file_path}")
            self.file = ifcopenshell.open(self.ifc_file_path)
            logger.info(f"IFC file loaded successfully with {len(self.file.by_type('IfcElement'))} elements")
        except Exception as e:
            logger.error(f"Failed to load IFC file: {str(e)}")
            raise
    
    def get_project_info(self) -> Dict[str, Any]:
        """
        Extract basic project information.
        
        Returns:
            Dictionary with project information
        """
        project = self.file.by_type("IfcProject")[0]
        
        # Get units
        units_info = {}
        for unit in project.UnitsInContext.Units:
            if hasattr(unit, "UnitType"):
                unit_type = unit.UnitType
                if hasattr(unit, "Name"):
                    units_info[unit_type] = unit.Name
        
        # Basic project info
        project_info = {
            "GlobalId": project.GlobalId,
            "Name": project.Name if project.Name else "Unnamed project",
            "Description": project.Description if project.Description else "",
            "Units": units_info
        }
        
        return project_info
    
    def get_elements(self, element_type: Optional[str] = None) -> List[Any]:
        """
        Get elements from the IFC file, optionally filtered by type.
        
        Args:
            element_type: Optional IFC type to filter elements
        
        Returns:
            List of matching IFC elements
        """
        if element_type:
            if element_type in self._elements_cache:
                return self._elements_cache[element_type]
            
            try:
                elements = self.file.by_type(element_type)
                self._elements_cache[element_type] = elements
                return elements
            except Exception as e:
                logger.error(f"Error getting elements of type {element_type}: {str(e)}")
                return []
        else:
            # Get all IfcElement entities
            all_elements = self.file.by_type("IfcElement")
            return all_elements
    
    def get_element_by_id(self, global_id: str) -> Optional[Any]:
        """
        Get an element by its GlobalId.
        
        Args:
            global_id: The GlobalId to search for
            
        Returns:
            The element if found, None otherwise
        """
        try:
            for element in self.file.by_type("IfcRoot"):
                if element.GlobalId == global_id:
                    return element
            return None
        except Exception as e:
            logger.error(f"Error getting element by GlobalId {global_id}: {str(e)}")
            return None
    
    def get_element_attributes(self, element: Any) -> Dict[str, Any]:
        """
        Extract basic attributes from an IFC element.
        
        Args:
            element: The IFC element to extract attributes from
            
        Returns:
            Dictionary of attribute names and values
        """
        attributes = {}
        
        try:
            # Standard attributes present in most IfcElements
            if hasattr(element, "GlobalId"):
                attributes["GlobalId"] = element.GlobalId
            
            if hasattr(element, "Name"):
                attributes["Name"] = element.Name if element.Name else ""
                
            if hasattr(element, "Description"):
                attributes["Description"] = element.Description if element.Description else ""
                
            if hasattr(element, "ObjectType"):
                attributes["ObjectType"] = element.ObjectType if element.ObjectType else ""
                
            # Get the IFC class name
            attributes["IFCType"] = element.is_a()
            
            # Add element-specific attributes based on type
            if element.is_a("IfcWall") or element.is_a("IfcWallStandardCase"):
                # Wall-specific attributes
                pass  # Will be implemented in detail later
                
            elif element.is_a("IfcDoor") or element.is_a("IfcWindow"):
                # Door/Window specific attributes
                pass  # Will be implemented in detail later
            
            elif element.is_a("IfcSpace"):
                # Space/Room specific attributes
                pass  # Will be implemented in detail later
                
        except Exception as e:
            logger.error(f"Error extracting attributes for element: {str(e)}")
        
        return attributes
    
    def get_spatial_structure(self) -> Dict[str, Any]:
        """
        Extract the spatial structure of the building (Project > Site > Building > Storey > Space).
        
        Returns:
            Dictionary representing the building spatial structure
        """
        # To be implemented
        return {}
    
    def get_relationships(self, element: Any) -> Dict[str, List[Any]]:
        """
        Get relationships for a specific element.
        
        Args:
            element: The IFC element to get relationships for
            
        Returns:
            Dictionary mapping relationship types to related elements
        """
        # To be implemented
        return {}
    
    def get_property_sets(self, element: Any) -> Dict[str, Dict[str, Any]]:
        """
        Extract property sets for an element.
        
        Args:
            element: The IFC element to extract property sets from
            
        Returns:
            Dictionary mapping property set names to property dictionaries
        """
        # To be implemented
        return {}
    
    def extract_material_info(self, element: Any) -> List[Dict[str, Any]]:
        """
        Extract material information for an element.
        
        Args:
            element: The IFC element to extract material info from
            
        Returns:
            List of dictionaries with material information
        """
        # To be implemented
        return [] 