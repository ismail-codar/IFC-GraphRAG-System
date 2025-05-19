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
            
    def get_element_global_id(self, element: Any) -> Optional[str]:
        """
        Get the GlobalId of an element.
        
        Args:
            element: IFC element
            
        Returns:
            GlobalId string if found, None otherwise
        """
        try:
            if hasattr(element, "GlobalId"):
                return element.GlobalId
            return None
        except Exception as e:
            logger.error(f"Error getting GlobalId for element: {str(e)}")
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
        if self._spatial_structure_cache:
            return self._spatial_structure_cache
        
        structure = {
            "project": {},
            "sites": [],
            "buildings": [],
            "storeys": [],
            "spaces": []
        }
        
        try:
            # Get project
            projects = self.file.by_type("IfcProject")
            if projects:
                project = projects[0]
                structure["project"] = {
                    "GlobalId": project.GlobalId,
                    "Name": project.Name if project.Name else "Unnamed Project",
                    "Description": project.Description if project.Description else ""
                }
                
                # Navigate down the spatial structure using decomposition relationships
                for rel in project.IsDecomposedBy:
                    for site in rel.RelatedObjects:
                        if site.is_a("IfcSite"):
                            site_data = {
                                "GlobalId": site.GlobalId,
                                "Name": site.Name if site.Name else "Unnamed Site",
                                "Description": site.Description if site.Description else "",
                                "Buildings": []
                            }
                            
                            # Get buildings in the site
                            for site_rel in site.IsDecomposedBy:
                                for building in site_rel.RelatedObjects:
                                    if building.is_a("IfcBuilding"):
                                        building_data = {
                                            "GlobalId": building.GlobalId,
                                            "Name": building.Name if building.Name else "Unnamed Building",
                                            "Description": building.Description if building.Description else "",
                                            "Storeys": []
                                        }
                                        
                                        # Get storeys in the building
                                        for building_rel in building.IsDecomposedBy:
                                            for storey in building_rel.RelatedObjects:
                                                if storey.is_a("IfcBuildingStorey"):
                                                    storey_data = {
                                                        "GlobalId": storey.GlobalId,
                                                        "Name": storey.Name if storey.Name else "Unnamed Storey",
                                                        "Description": storey.Description if storey.Description else "",
                                                        "Elevation": storey.Elevation if hasattr(storey, "Elevation") else None,
                                                        "Spaces": []
                                                    }
                                                    
                                                    # Get spaces in the storey
                                                    space_elements = []
                                                    for storey_rel in storey.ContainsElements:
                                                        space_elements.extend([e for e in storey_rel.RelatedElements if e.is_a("IfcSpace")])
                                                    
                                                    for space in space_elements:
                                                        space_data = {
                                                            "GlobalId": space.GlobalId,
                                                            "Name": space.Name if space.Name else "Unnamed Space",
                                                            "Description": space.Description if space.Description else "",
                                                            "LongName": space.LongName if hasattr(space, "LongName") else "",
                                                        }
                                                        storey_data["Spaces"].append(space_data)
                                                        structure["spaces"].append(space_data)
                                                    
                                                    building_data["Storeys"].append(storey_data)
                                                    structure["storeys"].append(storey_data)
                                        
                                        site_data["Buildings"].append(building_data)
                                        structure["buildings"].append(building_data)
                            
                            structure["sites"].append(site_data)
            
            self._spatial_structure_cache = structure
            
        except Exception as e:
            logger.error(f"Error extracting spatial structure: {str(e)}")
        
        return structure
    
    def get_relationships(self, element: Any) -> Dict[str, List[Any]]:
        """
        Get relationships for a specific element.
        
        Args:
            element: The IFC element to get relationships for
            
        Returns:
            Dictionary mapping relationship types to related elements
        """
        if not element:
            return {}
            
        element_id = element.GlobalId
        
        # Check if relationships for this element are already cached
        if element_id in self._relationships_cache:
            return self._relationships_cache[element_id]
            
        relationships = {
            "ContainedIn": [],          # Spatial containment relationships
            "HostedBy": [],             # Hosted by relationships (e.g., window in a wall)
            "Decomposes": [],           # Part of a larger element
            "HasOpenings": [],          # Openings in walls for doors/windows
            "IsConnectedTo": [],        # Connected elements
            "HasAssociations": [],      # Material associations, etc.
            "HasPropertySets": []       # Property sets
        }
        
        try:
            # Get containment relationships (elements to spatial structure)
            for rel in self.file.by_type("IfcRelContainedInSpatialStructure"):
                if element in rel.RelatedElements:
                    relationships["ContainedIn"].append({
                        "RelationType": "ContainedIn",
                        "RelatingObject": rel.RelatingStructure,
                        "RelatingObjectId": rel.RelatingStructure.GlobalId,
                        "RelatingObjectType": rel.RelatingStructure.is_a()
                    })
            
            # Get decomposition relationships (element is part of a larger element)
            for rel in self.file.by_type("IfcRelAggregates"):
                if element == rel.RelatingObject:
                    # This element has parts
                    for part in rel.RelatedObjects:
                        relationships["Decomposes"].append({
                            "RelationType": "HasParts",
                            "RelatedObject": part,
                            "RelatedObjectId": part.GlobalId,
                            "RelatedObjectType": part.is_a()
                        })
                elif element in rel.RelatedObjects:
                    # This element is part of another element
                    relationships["Decomposes"].append({
                        "RelationType": "IsPartOf",
                        "RelatingObject": rel.RelatingObject,
                        "RelatingObjectId": rel.RelatingObject.GlobalId,
                        "RelatingObjectType": rel.RelatingObject.is_a()
                    })
            
            # Get opening relationships (wall has openings for doors/windows)
            if element.is_a() in ["IfcWall", "IfcWallStandardCase"]:
                for rel in self.file.by_type("IfcRelVoidsElement"):
                    if element == rel.RelatingBuildingElement:
                        opening = rel.RelatedOpeningElement
                        # Find elements that fill this opening
                        for fill_rel in self.file.by_type("IfcRelFillsElement"):
                            if opening == fill_rel.RelatingOpeningElement:
                                filling_element = fill_rel.RelatedBuildingElement
                                relationships["HasOpenings"].append({
                                    "RelationType": "HasOpening",
                                    "RelatedObject": filling_element,
                                    "RelatedObjectId": filling_element.GlobalId,
                                    "RelatedObjectType": filling_element.is_a()
                                })
            
            # Get "fills opening" relationships (door/window in a wall opening)
            if element.is_a() in ["IfcDoor", "IfcWindow"]:
                for rel in self.file.by_type("IfcRelFillsElement"):
                    if element == rel.RelatedBuildingElement:
                        opening = rel.RelatingOpeningElement
                        # Find the element that is voided by this opening
                        for void_rel in self.file.by_type("IfcRelVoidsElement"):
                            if opening == void_rel.RelatedOpeningElement:
                                host_element = void_rel.RelatingBuildingElement
                                relationships["HostedBy"].append({
                                    "RelationType": "HostedBy",
                                    "RelatingObject": host_element,
                                    "RelatingObjectId": host_element.GlobalId,
                                    "RelatingObjectType": host_element.is_a()
                                })
            
            # Get material associations
            for rel in self.file.by_type("IfcRelAssociatesMaterial"):
                if element in rel.RelatedObjects:
                    material = rel.RelatingMaterial
                    material_type = material.is_a()
                    
                    if material_type == "IfcMaterial":
                        relationships["HasAssociations"].append({
                            "RelationType": "HasMaterial",
                            "RelatingObject": material,
                            "MaterialName": material.Name,
                            "MaterialType": "Single"
                        })
                    elif material_type == "IfcMaterialList":
                        materials = []
                        for mat in material.Materials:
                            materials.append({
                                "MaterialName": mat.Name,
                                "MaterialId": mat.id()
                            })
                        relationships["HasAssociations"].append({
                            "RelationType": "HasMaterials",
                            "Materials": materials,
                            "MaterialType": "List"
                        })
                    elif material_type == "IfcMaterialLayerSetUsage":
                        layer_set = material.ForLayerSet
                        materials = []
                        for i, layer in enumerate(layer_set.MaterialLayers):
                            materials.append({
                                "MaterialName": layer.Material.Name if layer.Material else "Unknown",
                                "MaterialId": layer.Material.id() if layer.Material else None,
                                "LayerThickness": layer.LayerThickness,
                                "LayerPosition": i
                            })
                        relationships["HasAssociations"].append({
                            "RelationType": "HasMaterialLayers",
                            "Materials": materials,
                            "MaterialType": "LayerSet"
                        })
            
            # Get property sets
            for definition in self.file.by_type("IfcRelDefinesByProperties"):
                if element in definition.RelatedObjects:
                    prop_set = definition.RelatingPropertyDefinition
                    if prop_set.is_a("IfcPropertySet"):
                        relationships["HasPropertySets"].append({
                            "RelationType": "HasPropertySet",
                            "PropertySetName": prop_set.Name,
                            "PropertySetId": prop_set.id()
                        })
            
            # Cache the results
            self._relationships_cache[element_id] = relationships
            
        except Exception as e:
            logger.error(f"Error extracting relationships for element {element_id}: {str(e)}")
        
        return relationships
    
    def get_property_sets(self, element: Any) -> Dict[str, Dict[str, Any]]:
        """
        Extract property sets for an IFC element.
        
        Args:
            element: The IFC element to extract property sets from
            
        Returns:
            Dictionary of property set names and their property dictionaries
        """
        # Check cache
        element_id = None
        if hasattr(element, "GlobalId"):
            element_id = element.GlobalId
            if element_id in self._property_sets_cache:
                return self._property_sets_cache[element_id]
        
        property_sets = {}
        
        try:
            # Get property sets through IfcRelDefinesByProperties
            if hasattr(element, "IsDefinedBy"):
                for definition in element.IsDefinedBy:
                    if definition.is_a("IfcRelDefinesByProperties"):
                        prop_def = definition.RelatingPropertyDefinition
                        
                        if prop_def.is_a("IfcPropertySet"):
                            # Standard property set
                            pset_name = prop_def.Name
                            properties = {}
                            
                            for prop in prop_def.HasProperties:
                                if prop.is_a("IfcPropertySingleValue"):
                                    # Extract single values
                                    if prop.NominalValue:
                                        # Convert value to Python native type
                                        value = self._extract_value(prop.NominalValue)
                                        properties[prop.Name] = value
                                    else:
                                        properties[prop.Name] = None
                                        
                                # Add support for more property types as needed
                                # IfcPropertyEnumeratedValue, IfcPropertyTableValue, etc.
                                
                            property_sets[pset_name] = properties
                            
                        elif prop_def.is_a("IfcElementQuantity"):
                            # Quantity set
                            qset_name = prop_def.Name
                            quantities = {}
                            
                            for quantity in prop_def.Quantities:
                                if quantity.is_a("IfcQuantityLength"):
                                    quantities[quantity.Name] = quantity.LengthValue
                                elif quantity.is_a("IfcQuantityArea"):
                                    quantities[quantity.Name] = quantity.AreaValue
                                elif quantity.is_a("IfcQuantityVolume"):
                                    quantities[quantity.Name] = quantity.VolumeValue
                                elif quantity.is_a("IfcQuantityCount"):
                                    quantities[quantity.Name] = quantity.CountValue
                                elif quantity.is_a("IfcQuantityWeight"):
                                    quantities[quantity.Name] = quantity.WeightValue
                                # Add other quantity types as needed
                            
                            property_sets[qset_name] = quantities
        
            # Cache the result
            if element_id:
                self._property_sets_cache[element_id] = property_sets
                
        except Exception as e:
            logger.error(f"Error extracting property sets for element: {str(e)}")
            
        return property_sets
        
    def get_element_property_sets(self, element: Any) -> Dict[str, Dict[str, Any]]:
        """
        Alias for get_property_sets for compatibility with the processor.
        
        Args:
            element: The IFC element to extract property sets from
            
        Returns:
            Dictionary of property set names and their property dictionaries
        """
        return self.get_property_sets(element)
    
    def _extract_value(self, nominal_value: Any) -> Any:
        """
        Extract the actual value from an IFC value entity.
        
        Args:
            nominal_value: The IFC value entity
            
        Returns:
            The extracted value in Python native type
        """
        if nominal_value.is_a("IfcLabel") or nominal_value.is_a("IfcText") or nominal_value.is_a("IfcIdentifier"):
            return nominal_value.wrappedValue
        elif nominal_value.is_a("IfcInteger") or nominal_value.is_a("IfcCountMeasure"):
            return int(nominal_value.wrappedValue)
        elif nominal_value.is_a("IfcReal") or nominal_value.is_a("IfcLengthMeasure") or \
             nominal_value.is_a("IfcAreaMeasure") or nominal_value.is_a("IfcVolumeMeasure") or \
             nominal_value.is_a("IfcPositiveLengthMeasure") or nominal_value.is_a("IfcMassMeasure") or \
             nominal_value.is_a("IfcRatioMeasure") or nominal_value.is_a("IfcThermalTransmittanceMeasure"):
            return float(nominal_value.wrappedValue)
        elif nominal_value.is_a("IfcBoolean"):
            return nominal_value.wrappedValue
        elif nominal_value.is_a("IfcLogical"):
            if nominal_value.wrappedValue == ".T.":
                return True
            elif nominal_value.wrappedValue == ".F.":
                return False
            else:
                return None
        else:
            # For other types, just return the wrapped value
            if hasattr(nominal_value, "wrappedValue"):
                return nominal_value.wrappedValue
            else:
                return str(nominal_value)
    
    def extract_material_info(self, element: Any) -> List[Dict[str, Any]]:
        """
        Extract material information for an element.
        
        Args:
            element: The IFC element to extract material info from
            
        Returns:
            List of dictionaries with material information
        """
        materials = []
        
        try:
            for rel in self.file.by_type("IfcRelAssociatesMaterial"):
                if element in rel.RelatedObjects:
                    material = rel.RelatingMaterial
                    
                    if material.is_a("IfcMaterial"):
                        # Single material
                        materials.append({
                            "name": material.Name,
                            "type": "Single",
                            "id": material.id()
                        })
                    
                    elif material.is_a("IfcMaterialList"):
                        # Material list (multiple materials)
                        for mat in material.Materials:
                            materials.append({
                                "name": mat.Name,
                                "type": "List",
                                "id": mat.id()
                            })
                    
                    elif material.is_a("IfcMaterialLayerSetUsage"):
                        # Material layers with specific usage (e.g., wall layers)
                        layer_set = material.ForLayerSet
                        
                        # Get the orientation information
                        dir_sense = material.DirectionSense
                        
                        for i, layer in enumerate(layer_set.MaterialLayers):
                            if layer.Material:
                                materials.append({
                                    "name": layer.Material.Name,
                                    "type": "Layer",
                                    "id": layer.Material.id(),
                                    "thickness": layer.LayerThickness,
                                    "position": i,
                                    "direction_sense": dir_sense,
                                    "is_ventilated": layer.IsVentilated if hasattr(layer, "IsVentilated") else None
                                })
                    
                    elif material.is_a("IfcMaterialLayerSet"):
                        # Material layer set without usage information
                        for i, layer in enumerate(material.MaterialLayers):
                            if layer.Material:
                                materials.append({
                                    "name": layer.Material.Name,
                                    "type": "Layer",
                                    "id": layer.Material.id(),
                                    "thickness": layer.LayerThickness,
                                    "position": i,
                                    "is_ventilated": layer.IsVentilated if hasattr(layer, "IsVentilated") else None
                                })
        
        except Exception as e:
            logger.error(f"Error extracting material info for element {element.GlobalId if element else None}: {str(e)}")
        
        return materials
    
    def get_schema_version(self) -> str:
        """
        Get the schema version of the loaded IFC file.
        
        Returns:
            String representing the IFC schema version (e.g., 'IFC2X3', 'IFC4', etc.)
        """
        try:
            # Check if the file is loaded
            if not self.file:
                logger.warning("IFC file not loaded when trying to get schema version")
                return "Unknown"
            
            # Get the schema identifier from the file
            schema_id = self.file.schema
            
            # Common schema identifiers: 'IFC2X3', 'IFC4', 'IFC4X1', etc.
            return schema_id
        
        except Exception as e:
            logger.error(f"Error getting IFC schema version: {str(e)}")
            return "Unknown" 