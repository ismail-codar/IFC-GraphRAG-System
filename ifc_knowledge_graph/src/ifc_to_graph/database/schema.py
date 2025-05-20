"""
Neo4j Schema Definition

This module defines the Neo4j schema for mapping IFC entities to a graph structure,
including node labels, relationship types, constraints, and indexes.
"""

import logging
from typing import Dict, List, Any, Optional
from enum import Enum, auto

# Configure logging
logger = logging.getLogger(__name__)


class NodeLabels(Enum):
    """Enum defining the main node labels in the graph schema."""
    PROJECT = "IfcProject"
    SITE = "IfcSite"
    BUILDING = "IfcBuilding"
    STOREY = "IfcBuildingStorey"
    SPACE = "IfcSpace"
    ELEMENT = "Element"
    WALL = "Wall"
    WINDOW = "Window"
    DOOR = "Door"
    SLAB = "Slab"
    BEAM = "Beam"
    COLUMN = "Column"
    RAILING = "Railing"
    FURNITURE = "Furniture"
    MATERIAL = "Material"
    PROPERTY_SET = "PropertySet"
    PROPERTY = "Property"
    TYPE = "Type"
    # Topological entity labels - used for advanced querying
    CELL = "Cell"
    FACE = "Face"
    EDGE = "Edge"
    VERTEX = "Vertex"
    
    # Map IFC entity types to node labels
    @classmethod
    def from_ifc_type(cls, ifc_type: str) -> 'NodeLabels':
        """Map an IFC entity type to a node label."""
        mapping = {
            "IfcProject": cls.PROJECT,
            "IfcSite": cls.SITE,
            "IfcBuilding": cls.BUILDING,
            "IfcBuildingStorey": cls.STOREY,
            "IfcSpace": cls.SPACE,
            "IfcWall": cls.WALL,
            "IfcWallStandardCase": cls.WALL,
            "IfcWindow": cls.WINDOW,
            "IfcDoor": cls.DOOR,
            "IfcSlab": cls.SLAB,
            "IfcBeam": cls.BEAM,
            "IfcColumn": cls.COLUMN,
            "IfcRailing": cls.RAILING,
            "IfcFurniture": cls.FURNITURE,
            "IfcFurnishingElement": cls.FURNITURE,
            "IfcMaterial": cls.MATERIAL,
            "IfcPropertySet": cls.PROPERTY_SET,
            "IfcElementType": cls.TYPE,
        }
        return mapping.get(ifc_type, cls.ELEMENT)


class RelationshipTypes(Enum):
    """Enum defining the relationship types in the graph schema."""
    CONTAINS = "CONTAINS"  # Spatial containment
    DEFINES = "DEFINES"  # Type definitions
    HAS_PROPERTY_SET = "HAS_PROPERTY_SET"  # Element to property set
    HAS_PROPERTY = "HAS_PROPERTY"  # Property set to property
    IS_MADE_OF = "IS_MADE_OF"  # Material associations
    CONNECTED_TO = "CONNECTED_TO"  # Physical connections
    BOUNDED_BY = "BOUNDED_BY"  # Space boundaries
    HOSTED_BY = "HOSTED_BY"  # Opening in element
    FILLS = "FILLS"  # Door/window fills opening
    ADJACENT_TO = "ADJACENT_TO"  # Adjacent elements
    GROUPS = "GROUPS"  # Element grouping
    # Topological relationship types
    ADJACENT = "ADJACENT"  # Adjacency relationship detected by topology
    CONTAINS_TOPOLOGICALLY = "CONTAINS_TOPOLOGICALLY"  # Spatial containment detected by topology
    IS_CONTAINED_IN = "IS_CONTAINED_IN"  # Inverse of CONTAINS_TOPOLOGICALLY
    BOUNDS_SPACE = "BOUNDS_SPACE"  # Element bounds a space
    IS_BOUNDED_BY = "IS_BOUNDED_BY"  # Space is bounded by an element
    CONNECTS_SPACES = "CONNECTS_SPACES"  # Element (e.g., door) connects spaces
    PATH_TO = "PATH_TO"  # Path relationship (with steps as properties)
    
    # Map IFC relationship types to graph relationship types
    @classmethod
    def from_ifc_relationship(cls, relationship_type: str) -> 'RelationshipTypes':
        """Map an IFC relationship type to a graph relationship type."""
        mapping = {
            "IfcRelContainedInSpatialStructure": cls.CONTAINS,
            "IfcRelAggregates": cls.CONTAINS,
            "IfcRelDefinesByType": cls.DEFINES,
            "IfcRelDefinesByProperties": cls.HAS_PROPERTY_SET,
            "IfcRelAssociatesMaterial": cls.IS_MADE_OF,
            "IfcRelConnectsElements": cls.CONNECTED_TO,
            "IfcRelSpaceBoundary": cls.BOUNDED_BY,
            "IfcRelFillsElement": cls.FILLS,
            "IfcRelVoidsElement": cls.HOSTED_BY,
            "IfcRelAssigns": cls.GROUPS,
        }
        return mapping.get(relationship_type, cls.CONNECTED_TO)
    
    @classmethod
    def from_topologic_relationship(cls, topology_relationship: str) -> 'RelationshipTypes':
        """Map a topological relationship to a graph relationship type."""
        mapping = {
            "adjacent": cls.ADJACENT,
            "contains": cls.CONTAINS_TOPOLOGICALLY,
            "contained_by": cls.IS_CONTAINED_IN,
            "bounds_space": cls.BOUNDS_SPACE,
            "bounded_by": cls.IS_BOUNDED_BY,
        }
        return mapping.get(topology_relationship, cls.CONNECTED_TO)


class SchemaManager:
    """
    Manages the Neo4j schema setup for the IFC graph database.
    Handles creation of constraints and indexes.
    """
    
    # Cypher statements for schema setup
    SCHEMA_CONSTRAINTS = [
        # Unique GlobalId constraint for Elements
        """
        CREATE CONSTRAINT IF NOT EXISTS FOR (e:Element) 
        REQUIRE e.GlobalId IS UNIQUE
        """,
        
        # Unique GlobalId constraint for Project
        """
        CREATE CONSTRAINT IF NOT EXISTS FOR (p:IfcProject) 
        REQUIRE p.GlobalId IS UNIQUE
        """,
        
        # Additional constraints for other node types
        """
        CREATE CONSTRAINT IF NOT EXISTS FOR (s:IfcSite) 
        REQUIRE s.GlobalId IS UNIQUE
        """,
        
        """
        CREATE CONSTRAINT IF NOT EXISTS FOR (b:IfcBuilding) 
        REQUIRE b.GlobalId IS UNIQUE
        """,
        
        """
        CREATE CONSTRAINT IF NOT EXISTS FOR (s:IfcBuildingStorey) 
        REQUIRE s.GlobalId IS UNIQUE
        """,
        
        """
        CREATE CONSTRAINT IF NOT EXISTS FOR (s:IfcSpace) 
        REQUIRE s.GlobalId IS UNIQUE
        """,
        
        """
        CREATE CONSTRAINT IF NOT EXISTS FOR (m:Material) 
        REQUIRE m.Name IS UNIQUE
        """,
        
        """
        CREATE CONSTRAINT IF NOT EXISTS FOR (t:Type) 
        REQUIRE t.GlobalId IS UNIQUE
        """
    ]
    
    SCHEMA_INDEXES = [
        # Index on Element IFC type for faster querying
        """
        CREATE INDEX IF NOT EXISTS FOR (e:Element) ON (e.IFCType)
        """,
        
        # Index on Element Name for text search
        """
        CREATE INDEX IF NOT EXISTS FOR (e:Element) ON (e.Name)
        """,
        
        # Index on Space Name for text search
        """
        CREATE INDEX IF NOT EXISTS FOR (s:IfcSpace) ON (s.Name)
        """,
        
        # Index on PropertySet Name
        """
        CREATE INDEX IF NOT EXISTS FOR (ps:PropertySet) ON (ps.Name)
        """,
        
        # Index on Property Name
        """
        CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.Name)
        """,
        
        # Index for faster topological relationship queries
        """
        CREATE INDEX IF NOT EXISTS FOR (e:Element) ON (e.topologicEntity)
        """
    ]
    
    def __init__(self, connector):
        """
        Initialize with a Neo4j connector.
        
        Args:
            connector: Neo4jConnector instance
        """
        self.connector = connector
    
    def setup_schema(self) -> None:
        """Create all constraints and indexes for the IFC graph schema."""
        try:
            logger.info("Setting up Neo4j schema constraints and indexes")
            
            # Create constraints
            for constraint_query in self.SCHEMA_CONSTRAINTS:
                self.connector.run_query(constraint_query)
                
            # Create indexes
            for index_query in self.SCHEMA_INDEXES:
                self.connector.run_query(index_query)
                
            logger.info("Schema setup completed successfully")
            
        except Exception as e:
            logger.error(f"Error setting up schema: {str(e)}")
            raise
    
    def drop_schema(self) -> None:
        """
        Drop all constraints and indexes.
        Useful for testing or schema migration.
        """
        try:
            logger.info("Dropping Neo4j schema constraints and indexes")
            
            # Drop constraints - use a more general approach
            self.connector.run_query(
                "SHOW CONSTRAINTS"
            )
            constraints = self.connector.run_query("SHOW CONSTRAINTS")
            
            for constraint in constraints:
                name = constraint.get('name')
                if name:
                    self.connector.run_query(f"DROP CONSTRAINT {name}")
            
            # Drop indexes - use a more general approach
            indexes = self.connector.run_query("SHOW INDEXES")
            
            for index in indexes:
                name = index.get('name')
                if name and not name.startswith("constraint_"):
                    self.connector.run_query(f"DROP INDEX {name}")
            
            logger.info("Schema dropped successfully")
            
        except Exception as e:
            logger.error(f"Error dropping schema: {str(e)}")
            raise


# Dictionary mapping common IFC properties to Neo4j property names
# This helps standardize property names in the graph
PROPERTY_MAPPING = {
    "Name": "name",
    "Description": "description",
    "GlobalId": "globalId",
    "ObjectType": "objectType",
    "Tag": "tag",
    "PredefinedType": "predefinedType",
    "ObjectPlacement": "placement",
    "Representation": "representation",
    "ElementType": "elementType",
}

# Dictionary of topological relationship properties
TOPOLOGICAL_PROPERTIES = {
    "ADJACENT": [
        "distanceTolerance",
        "sharedFaceCount",
        "sharedEdgeCount",
        "sharedVertexCount",
        "contactArea"
    ],
    "CONTAINS_TOPOLOGICALLY": [
        "distanceTolerance",
        "volume",
        "containmentType"  # full or partial
    ],
    "BOUNDS_SPACE": [
        "boundaryType",  # physical, virtual, etc.
        "area",
        "normalVector"
    ],
    "CONNECTS_SPACES": [
        "connectionType",  # door, window, opening
        "isPassable",
        "width",
        "height"
    ],
    "PATH_TO": [
        "pathLength",
        "stepCount",
        "pathType",
        "isAccessible"
    ]
}


def get_node_labels(ifc_type: str) -> List[str]:
    """
    Get the appropriate Neo4j node labels for an IFC entity type.
    
    Args:
        ifc_type: IFC entity type string
        
    Returns:
        List of Neo4j labels to apply
    """
    # Handle the spatial structure elements specifically to ensure they get the right labels
    if ifc_type in ["IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace"]:
        # For spatial structure elements, use ONLY the specific IFC label
        specific_label = NodeLabels.from_ifc_type(ifc_type).value
        return [specific_label]
    
    # For regular elements, get the specific label for this IFC type
    specific_label = NodeLabels.from_ifc_type(ifc_type).value
    
    # For regular elements, add the Element label as a parent class
    labels = [specific_label]
    
    # All physical elements should also have the Element label
    if specific_label not in [
        NodeLabels.PROJECT.value, 
        NodeLabels.SITE.value,
        NodeLabels.BUILDING.value,
        NodeLabels.STOREY.value,
        NodeLabels.SPACE.value,
        NodeLabels.MATERIAL.value,
        NodeLabels.PROPERTY.value,
        NodeLabels.PROPERTY_SET.value,
        NodeLabels.TYPE.value
    ]:
        labels.append(NodeLabels.ELEMENT.value)
    
    return labels


def get_relationship_type(ifc_relationship_type: str) -> str:
    """
    Get the appropriate Neo4j relationship type for an IFC relationship.
    
    Args:
        ifc_relationship_type: IFC relationship type string
        
    Returns:
        Neo4j relationship type
    """
    return RelationshipTypes.from_ifc_relationship(ifc_relationship_type).value


def get_topologic_relationship_type(topology_relationship: str) -> str:
    """
    Get the appropriate Neo4j relationship type for a topological relationship.
    
    Args:
        topology_relationship: Topological relationship type string
        
    Returns:
        Neo4j relationship type
    """
    return RelationshipTypes.from_topologic_relationship(topology_relationship).value


def format_property_value(value: Any) -> Any:
    """
    Format property values for Neo4j storage.
    
    Args:
        value: The property value to format
        
    Returns:
        Formatted value suitable for Neo4j
    """
    # None values should be passed as is
    if value is None:
        return None
    
    # Handle common types that need conversion
    if isinstance(value, (list, tuple)) and len(value) == 0:
        return None
    elif isinstance(value, (list, tuple)) and len(value) == 1:
        return format_property_value(value[0])
    elif isinstance(value, (list, tuple)):
        return [format_property_value(v) for v in value]
    elif hasattr(value, "is_a") and callable(getattr(value, "is_a")):
        # Handle IFC entity references by returning the GlobalId 
        # or another identifier that can be used for lookup
        if hasattr(value, "GlobalId"):
            return value.GlobalId
        elif hasattr(value, "id"):
            return value.id()
        elif hasattr(value, "Name"):
            return value.Name
        else:
            return str(value)
    
    # Return other types as is (strings, numbers, booleans)
    return value 