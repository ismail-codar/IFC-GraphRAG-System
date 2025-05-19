"""
Domain-Specific Enrichment Module

This module provides functionality to enrich the IFC model with domain-specific information
such as building systems classification, material properties, performance properties,
semantic tagging, and custom property mappings.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Set

import ifcopenshell

# Configure logging
logger = logging.getLogger(__name__)


class DomainEnrichment:
    """
    Provides domain-specific enrichment for IFC models to enhance the knowledge graph.
    """
    
    def __init__(self, ifc_file):
        """
        Initialize the domain enrichment with an IFC file.
        
        Args:
            ifc_file: Loaded IFC file object from IfcOpenShell
        """
        self.file = ifc_file
        
        # Classification systems for building elements
        self.classification_systems = {
            "Uniclass": "Uniclass 2015",
            "OmniClass": "OmniClass",
            "Uniformat": "Uniformat",
            "IFC": "IFC",
            "MasterFormat": "MasterFormat"
        }
        
        # Common building systems
        self.building_systems = {
            "HVAC": ["IfcAirTerminal", "IfcAirTerminalBox", "IfcAirToAirHeatRecovery", "IfcBoiler", "IfcBurner", 
                    "IfcChiller", "IfcCoil", "IfcCompressor", "IfcCondenser", "IfcCooledBeam", "IfcCoolingTower", 
                    "IfcDamper", "IfcDuctFitting", "IfcDuctSegment", "IfcDuctSilencer", "IfcEngine", "IfcEvaporativeCooler",
                    "IfcEvaporator", "IfcFan", "IfcFlowMeter", "IfcHeatExchanger", "IfcHumidifier", "IfcMedicalDevice", 
                    "IfcMotorConnection", "IfcPump", "IfcSpaceHeater", "IfcTank", "IfcTubeBundle", "IfcUnitaryEquipment", 
                    "IfcValve", "IfcVibrationIsolator"],
            "Electrical": ["IfcElectricAppliance", "IfcElectricDistributionBoard", "IfcElectricFlowStorageDevice", 
                          "IfcElectricGenerator", "IfcElectricMotor", "IfcElectricTimeControl", "IfcEnergyConversionDevice", 
                          "IfcFlowInstrument", "IfcFlowMeter", "IfcLamp", "IfcLightFixture", "IfcMotorConnection", 
                          "IfcOutlet", "IfcProtectiveDevice", "IfcProtectiveDeviceTrippingUnit", "IfcSolarDevice", 
                          "IfcSwitchingDevice", "IfcTransformer"],
            "Plumbing": ["IfcInterceptor", "IfcPipeFitting", "IfcPipeSegment", "IfcPump", "IfcSanitaryTerminal", 
                        "IfcTank", "IfcValve", "IfcWasteTerminal"],
            "FireProtection": ["IfcActuator", "IfcAlarm", "IfcController", "IfcFlowInstrument", "IfcProtectiveDevice", 
                              "IfcSensor", "IfcUnitaryControlElement"],
            "Communication": ["IfcAudioVisualAppliance", "IfcCommunicationsAppliance", "IfcController", "IfcSensor"],
            "Structural": ["IfcBeam", "IfcColumn", "IfcFooting", "IfcMember", "IfcPile", "IfcPlate", "IfcRoof", 
                          "IfcSlab", "IfcWall", "IfcWallStandardCase", "IfcReinforcingBar", "IfcReinforcingMesh", 
                          "IfcTendon", "IfcTendonAnchor"],
            "Architectural": ["IfcCovering", "IfcDoor", "IfcRailing", "IfcRamp", "IfcRampFlight", "IfcRoof", 
                             "IfcStair", "IfcStairFlight", "IfcWindow"]
        }
        
        # Performance properties by category
        self.performance_properties = {
            "Thermal": ["ThermalTransmittance", "ThermalResistance", "ThermalConductivity", "SpecificHeatCapacity"],
            "Acoustic": ["AcousticRating", "SoundInsulationIndex", "SoundAbsorption"],
            "Fire": ["FireRating", "FireResistanceRating", "FlammabilityRating", "CombustibilityRating"],
            "Energy": ["EnergyEfficiencyRating", "EnergyConsumption", "EnergySource"],
            "Structural": ["LoadBearing", "StructuralStrength", "CompressionStrength", "TensileStrength", "FlexuralStrength"]
        }
        
        # Material properties to extract
        self.material_properties = [
            "Density", "YoungModulus", "ShearModulus", "PoissonRatio", "ThermalConductivity", 
            "ThermalExpansionCoefficient", "SpecificHeatCapacity", "MassDensity", "Porosity", 
            "Reflectivity", "Transmittance", "Absorptance", "Permeability"
        ]
        
        # Semantic tags by element type
        self.semantic_tags = {
            "IfcWall": ["partition", "exterior", "interior", "loadbearing", "non-loadbearing", "shear"],
            "IfcSlab": ["floor", "roof", "landing", "baseslab", "foundation"],
            "IfcBeam": ["lintel", "girder", "joist", "hollowcore", "lintel", "t-beam", "i-beam"],
            "IfcColumn": ["pillar", "main", "secondary", "support", "facade"],
            "IfcWindow": ["fixed", "operable", "skylight", "lightwell", "casement", "sliding", "awning"],
            "IfcDoor": ["entrance", "emergency", "interior", "exterior", "revolving", "sliding", "folding", "swinging"],
            "IfcStair": ["main", "emergency", "spiral", "curved", "straight", "service"],
            "IfcSpace": ["office", "corridor", "meeting", "bathroom", "technical", "storage", "living", "outdoor"]
        }
        
    def classify_building_systems(self, element: Any) -> Dict[str, Any]:
        """
        Classify an element into building systems based on its type and properties.
        
        Args:
            element: IFC element
            
        Returns:
            Dictionary of building system classifications
        """
        if not element:
            return {}
            
        element_type = element.is_a()
        system_classifications = {}
        
        # Classify by element type
        for system_name, element_types in self.building_systems.items():
            if element_type in element_types:
                system_classifications[system_name] = True
        
        # Additional classification from property sets
        try:
            # Check for system type in property sets
            for rel in self.file.by_type("IfcRelDefinesByProperties"):
                if element in rel.RelatedObjects:
                    prop_def = rel.RelatingPropertyDefinition
                    
                    if prop_def.is_a("IfcPropertySet"):
                        for prop in prop_def.HasProperties:
                            # Look for system-related properties
                            if prop.is_a("IfcPropertySingleValue") and prop.NominalValue:
                                prop_name = prop.Name.lower()
                                if "system" in prop_name or "classification" in prop_name:
                                    prop_value = self._extract_value(prop.NominalValue)
                                    if prop_value and isinstance(prop_value, str):
                                        # Add custom system classification
                                        prop_key = prop.Name.replace(" ", "")
                                        system_classifications[prop_key] = prop_value
        except Exception as e:
            logger.warning(f"Error during building system classification: {str(e)}")
        
        return system_classifications
    
    def extract_material_properties(self, material: Any) -> Dict[str, Any]:
        """
        Extract enriched material properties.
        
        Args:
            material: IFC material object
            
        Returns:
            Dictionary of material properties
        """
        if not material or not material.is_a("IfcMaterial"):
            return {}
            
        material_props = {
            "name": material.Name,
            "category": self._determine_material_category(material.Name),
            "properties": {}
        }
        
        try:
            # Extract material properties from material property sets
            for rel in self.file.by_type("IfcRelDefinesByProperties"):
                for obj in rel.RelatedObjects:
                    if obj.id() == material.id():
                        prop_def = rel.RelatingPropertyDefinition
                        
                        if prop_def.is_a("IfcPropertySet"):
                            # Extract standard material properties
                            for prop in prop_def.HasProperties:
                                if prop.is_a("IfcPropertySingleValue") and prop.NominalValue:
                                    prop_value = self._extract_value(prop.NominalValue)
                                    material_props["properties"][prop.Name] = {
                                        "value": prop_value,
                                        "type": prop.NominalValue.is_a()
                                    }
            
            # Extract material properties from material profile sets
            for mat_prof_set in self.file.by_type("IfcMaterialProfileSet"):
                for mat_prof in mat_prof_set.MaterialProfiles:
                    if mat_prof.Material and mat_prof.Material.id() == material.id():
                        if mat_prof.Profile:
                            # Add profile information
                            material_props["profile"] = {
                                "type": mat_prof.Profile.is_a(),
                                "id": mat_prof.Profile.id()
                            }
                            
                            # Extract specific profile properties based on type
                            if mat_prof.Profile.is_a("IfcParameterizedProfileDef"):
                                for attr_name in ["ProfileType", "ProfileName"]:
                                    if hasattr(mat_prof.Profile, attr_name):
                                        attr_value = getattr(mat_prof.Profile, attr_name)
                                        if attr_value:
                                            material_props["profile"][attr_name] = attr_value
        
        except Exception as e:
            logger.warning(f"Error extracting material properties: {str(e)}")
            
        return material_props
        
    def extract_performance_properties(self, element: Any) -> Dict[str, Dict[str, Any]]:
        """
        Extract performance-related properties for an element.
        
        Args:
            element: IFC element
            
        Returns:
            Dictionary of performance properties by category
        """
        if not element:
            return {}
            
        performance_props = {
            "Thermal": {},
            "Acoustic": {},
            "Fire": {},
            "Energy": {},
            "Structural": {}
        }
        
        try:
            # Get property sets
            for rel in self.file.by_type("IfcRelDefinesByProperties"):
                if element in rel.RelatedObjects:
                    prop_def = rel.RelatingPropertyDefinition
                    
                    if prop_def.is_a("IfcPropertySet"):
                        for prop in prop_def.HasProperties:
                            if prop.is_a("IfcPropertySingleValue") and prop.NominalValue:
                                prop_name = prop.Name
                                prop_value = self._extract_value(prop.NominalValue)
                                
                                # Categorize property
                                for category, prop_names in self.performance_properties.items():
                                    # Check if this property is in any of our performance categories
                                    matches = [name for name in prop_names if name.lower() in prop_name.lower()]
                                    if matches:
                                        performance_props[category][prop_name] = {
                                            "value": prop_value,
                                            "type": prop.NominalValue.is_a()
                                        }
                                
                                # Check for any performance-related keywords
                                performance_keywords = ["rating", "resistance", "performance", "efficiency"]
                                for keyword in performance_keywords:
                                    if keyword.lower() in prop_name.lower():
                                        # Check if it's already categorized
                                        already_categorized = any(
                                            prop_name in category_props 
                                            for category_props in performance_props.values()
                                        )
                                        
                                        # If not, add to a "General" category
                                        if not already_categorized:
                                            if "General" not in performance_props:
                                                performance_props["General"] = {}
                                            
                                            performance_props["General"][prop_name] = {
                                                "value": prop_value,
                                                "type": prop.NominalValue.is_a()
                                            }
        
        except Exception as e:
            logger.warning(f"Error extracting performance properties: {str(e)}")
            
        # Remove empty categories
        performance_props = {k: v for k, v in performance_props.items() if v}
        
        return performance_props
    
    def generate_semantic_tags(self, element: Any) -> List[str]:
        """
        Generate semantic tags for an element based on its type and properties.
        
        Args:
            element: IFC element
            
        Returns:
            List of semantic tags
        """
        if not element:
            return []
            
        element_type = element.is_a()
        tags = set()
        
        # Add tags based on element type
        if element_type in self.semantic_tags:
            # Start with potential tags for this element type
            potential_tags = self.semantic_tags[element_type]
            
            # Element name might contain useful tags
            if hasattr(element, "Name") and element.Name:
                element_name = element.Name.lower()
                for tag in potential_tags:
                    if tag.lower() in element_name:
                        tags.add(tag)
            
            # Check property sets for clues about the element's function
            try:
                for rel in self.file.by_type("IfcRelDefinesByProperties"):
                    if element in rel.RelatedObjects:
                        prop_def = rel.RelatingPropertyDefinition
                        
                        if prop_def.is_a("IfcPropertySet"):
                            for prop in prop_def.HasProperties:
                                if prop.is_a("IfcPropertySingleValue") and prop.NominalValue:
                                    # Look for properties indicating function
                                    prop_name = prop.Name.lower()
                                    prop_value = str(self._extract_value(prop.NominalValue)).lower()
                                    
                                    # Check for function/type in property name or value
                                    for tag in potential_tags:
                                        if tag.lower() in prop_name or tag.lower() in prop_value:
                                            tags.add(tag)
                                            
                                    # Look for load-bearing property specifically for walls
                                    if element_type == "IfcWall" and "load" in prop_name:
                                        if "bearing" in prop_name:
                                            # Check boolean value
                                            if prop_value in ["true", "1", "yes"]:
                                                tags.add("loadbearing")
                                            else:
                                                tags.add("non-loadbearing")
                                    
                                    # Look for interior/exterior property
                                    if "exterior" in prop_name or "isexternal" in prop_name:
                                        if prop_value in ["true", "1", "yes"]:
                                            tags.add("exterior")
                                        else:
                                            tags.add("interior")
            
            except Exception as e:
                logger.warning(f"Error generating semantic tags: {str(e)}")
                
            # Add generic tags based on element type
            if element_type == "IfcWall":
                if "loadbearing" not in tags and "non-loadbearing" not in tags:
                    # Default to interior if not specified
                    if "interior" not in tags and "exterior" not in tags:
                        tags.add("interior")
                        
            elif element_type == "IfcSlab":
                # Check for position and function
                if hasattr(element, "PredefinedType") and element.PredefinedType:
                    slab_type = element.PredefinedType.lower()
                    if "roof" in slab_type:
                        tags.add("roof")
                    elif "floor" in slab_type:
                        tags.add("floor")
                    elif "foundation" in slab_type or "base" in slab_type:
                        tags.add("foundation")
                else:
                    # Default to floor if not specified
                    tags.add("floor")
                    
            elif element_type == "IfcSpace":
                # Add tag for space based on name or long name
                if hasattr(element, "Name") and element.Name:
                    space_name = element.Name.lower()
                    for tag in self.semantic_tags["IfcSpace"]:
                        if tag.lower() in space_name:
                            tags.add(tag)
                
                if hasattr(element, "LongName") and element.LongName:
                    space_long_name = element.LongName.lower()
                    for tag in self.semantic_tags["IfcSpace"]:
                        if tag.lower() in space_long_name:
                            tags.add(tag)
        
        return list(tags)
    
    def apply_custom_property_mapping(self, element: Any) -> Dict[str, Any]:
        """
        Apply custom property mappings to standardize and unify property names.
        
        Args:
            element: IFC element
            
        Returns:
            Dictionary of mapped properties
        """
        if not element:
            return {}
            
        # Custom property mapping dictionary
        # Maps commonly used IFC property names to standardized ones
        property_mapping = {
            # Thermal properties
            "ThermalTransmittance": "U-Value",
            "ThermalResistance": "R-Value",
            "ThermalTransmittanceValue": "U-Value",
            "ThermalConductivity": "Lambda-Value",
            "SpecificHeatCapacity": "SpecificHeat",
            "ThermalConductance": "C-Value",
            
            # Fire properties
            "FireResistance": "FireRating",
            "FireRating": "FireRating",
            "FireResistanceRating": "FireRating",
            "FireResistanceClass": "FireRating",
            
            # Acoustic properties
            "AcousticRating": "SoundInsulation",
            "SoundInsulationRating": "SoundInsulation",
            "SoundResistanceValue": "SoundInsulation",
            "AcousticInsulationValue": "SoundInsulation",
            
            # Dimensional properties
            "Width": "Width",
            "Height": "Height",
            "Length": "Length",
            "Thickness": "Thickness",
            "NominalHeight": "Height",
            "NominalWidth": "Width",
            "NominalLength": "Length",
            "NominalThickness": "Thickness",
            
            # Performance properties
            "LoadBearing": "IsLoadBearing",
            "IsLoadBearing": "IsLoadBearing",
            "IsExternal": "IsExternal",
            "External": "IsExternal",
            
            # Material properties
            "Density": "Density",
            "Weight": "Weight",
            "MassDensity": "Density",
            "YoungModulus": "ElasticModulus",
            "ElasticModulus": "ElasticModulus",
            "ShearStrength": "ShearStrength"
        }
        
        mapped_properties = {}
        
        try:
            # Extract all properties
            for rel in self.file.by_type("IfcRelDefinesByProperties"):
                if element in rel.RelatedObjects:
                    prop_def = rel.RelatingPropertyDefinition
                    
                    if prop_def.is_a("IfcPropertySet"):
                        for prop in prop_def.HasProperties:
                            if prop.is_a("IfcPropertySingleValue") and prop.NominalValue:
                                prop_name = prop.Name
                                prop_value = self._extract_value(prop.NominalValue)
                                
                                # Map property name if it exists in mapping
                                for original, mapped in property_mapping.items():
                                    if original.lower() == prop_name.lower():
                                        mapped_properties[mapped] = {
                                            "value": prop_value,
                                            "original_name": prop_name,
                                            "type": prop.NominalValue.is_a()
                                        }
                                        break
        
        except Exception as e:
            logger.warning(f"Error applying custom property mapping: {str(e)}")
            
        return mapped_properties
    
    def _determine_material_category(self, material_name: str) -> str:
        """
        Determine the material category based on its name.
        
        Args:
            material_name: Name of the material
            
        Returns:
            Material category string
        """
        material_name = material_name.lower()
        
        # Material categories with common keywords
        categories = {
            "Concrete": ["concrete", "cement", "grout"],
            "Steel": ["steel", "metal", "iron", "stainless"],
            "Wood": ["wood", "timber", "plywood", "oak", "pine", "maple", "birch"],
            "Masonry": ["brick", "masonry", "block", "stone", "ceramic", "tile"],
            "Glass": ["glass", "glazing"],
            "Insulation": ["insulation", "insulating", "thermal", "acoustic"],
            "Plastic": ["plastic", "pvc", "vinyl", "abs", "polyethylene", "polystyrene"],
            "Finish": ["paint", "finish", "coating", "plaster", "gypsum", "drywall"],
            "Composite": ["composite", "fiber", "fibre", "laminate"],
            "Membrane": ["membrane", "waterproofing", "dampproof", "vapor", "vapour"],
            "Aluminum": ["aluminum", "aluminium"]
        }
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in material_name:
                    return category
                    
        return "Other"
    
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