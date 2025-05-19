"""
IFC to Neo4j Graph Mapper

This module maps IFC entities to Neo4j graph entities based on the schema.
It generates Cypher queries for creating nodes and relationships from IFC data.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

from .schema import (
    get_node_labels, 
    get_relationship_type, 
    format_property_value,
    PROPERTY_MAPPING
)

# Configure logging
logger = logging.getLogger(__name__)


class IfcToGraphMapper:
    """
    Maps IFC entities to Neo4j graph entities and generates Cypher queries.
    """
    
    def __init__(self, connector):
        """
        Initialize the mapper with a Neo4j connector.
        
        Args:
            connector: Neo4jConnector instance
        """
        self.connector = connector
        
    def create_node_from_element(self, element_data: Dict[str, Any]) -> str:
        """
        Generate a Cypher query to create a node from an IFC element.
        
        Args:
            element_data: Dictionary with element attributes
            
        Returns:
            GlobalId of the created node
        """
        # Make a copy to avoid modifying the original data
        element_data = element_data.copy()
        
        if "IFCType" not in element_data:
            logger.warning("Missing required field IFCType in element data")
            return None
            
        # Check for missing or null GlobalId and generate a unique ID if needed
        if "GlobalId" not in element_data or element_data["GlobalId"] is None:
            # Generate a deterministic ID based on other element properties for consistency
            element_type = element_data.get("IFCType", "unknown")
            element_name = element_data.get("Name", "")
            element_hash = hash(f"{element_type}_{element_name}_{id(element_data)}")
            temp_id = f"temp_id_{element_type}_{abs(element_hash)}"
            
            logger.error(f"GlobalId is still null after preprocessing")
            element_data["GlobalId"] = temp_id
        
        # Get appropriate labels based on IFC type
        labels = get_node_labels(element_data["IFCType"])
        labels_str = ":".join(labels)
        
        # Format properties for Neo4j
        properties = {}
        for key, value in element_data.items():
            # Skip null values to avoid Neo4j errors
            if value is None:
                continue
                
            # Map property names to standardized format if possible
            prop_name = PROPERTY_MAPPING.get(key, key)
            
            # Format the property value for Neo4j
            try:
                formatted_value = format_property_value(value)
                if formatted_value is not None:  # Skip None values
                    properties[prop_name] = formatted_value
            except Exception as e:
                # Just log and skip problematic properties rather than failing completely
                logger.warning(f"Error formatting property {key}: {str(e)}")
        
        # Always ensure GlobalId is included
        if "GlobalId" not in properties:
            if "GlobalId" in element_data and element_data["GlobalId"] is not None:
                # Use the original GlobalId if available
                properties["GlobalId"] = element_data["GlobalId"]
            else:
                # Generate a deterministic temporary ID
                element_type = element_data.get("IFCType", "unknown")
                element_hash = hash(f"{element_type}_{id(element_data)}")
                properties["GlobalId"] = f"temp_id_{element_type}_{abs(element_hash)}"
                logger.warning(f"Generated temporary GlobalId for {element_type}: {properties['GlobalId']}")
        
        # Build properties string for Cypher
        props_list = []
        for key, value in properties.items():
            # Use safe parameter for values
            props_list.append(f"{key}: ${key}")
        
        props_string = "{" + ", ".join(props_list) + "}"
        
        # Generate Cypher query using MERGE to avoid duplicates
        query = f"""
        MERGE (e:{labels_str} {props_string})
        RETURN e.GlobalId as id
        """
        
        try:
            # Execute query
            result = self.connector.run_query(query, properties)
            if result and result[0].get('id'):
                return result[0]['id']
            
            logger.warning(f"Failed to create node for element with type {element_data.get('IFCType')}")
            return None
        except Exception as e:
            logger.error(f"Error creating node: {str(e)}")
            return None
    
    def create_relationship(
        self, 
        source_id: str, 
        target_id: str, 
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create a relationship between two nodes.
        
        Args:
            source_id: GlobalId of the source node
            target_id: GlobalId of the target node
            relationship_type: Type of relationship (IFC relationship type)
            properties: Optional properties for the relationship
            
        Returns:
            True if successful, False otherwise
        """
        if not source_id or not target_id:
            logger.warning("Missing source or target ID for relationship")
            return False
        
        # Get appropriate relationship type
        rel_type = get_relationship_type(relationship_type)
        
        # Format properties for Neo4j
        formatted_props = {}
        if properties:
            for key, value in properties.items():
                prop_name = PROPERTY_MAPPING.get(key, key)
                formatted_props[prop_name] = format_property_value(value)
        
        try:
            # Use the optimized method from the connector
            result = self.connector.create_relationship(
                source_id=source_id,
                target_id=target_id,
                relationship_type=rel_type,
                properties=formatted_props if formatted_props else None
            )
            
            return result is not None
        except Exception as e:
            logger.error(f"Error creating relationship: {str(e)}")
            return False
    
    def create_property_node(
        self, 
        property_name: str, 
        property_value: Any, 
        property_type: str = "Property"
    ) -> str:
        """
        Create a property node with value.
        
        Args:
            property_name: Name of the property
            property_value: Value of the property
            property_type: Type of property node
            
        Returns:
            ID of the created property node
        """
        # Format property value for Neo4j
        formatted_value = format_property_value(property_value)
        
        # Generate Cypher parameters
        params = {
            "name": property_name,
            "value": formatted_value,
            "type": property_type
        }
        
        # Generate a unique ID for the property node
        # Use a combination of name and value, which should be unique in context
        query = """
        CREATE (p:Property {
            name: $name,
            value: $value,
            type: $type,
            id: randomUUID()
        })
        RETURN p.id as PropertyId
        """
        
        try:
            # Execute query
            result = self.connector.run_query(query, params)
            if result and result[0].get('PropertyId'):
                return result[0]['PropertyId']
            return None
        except Exception as e:
            logger.error(f"Error creating property node: {str(e)}")
            return None
    
    def create_property_set_node(self, pset_name: str, pset_data: Dict[str, Any]) -> str:
        """
        Create a property set node with associated property nodes.
        
        Args:
            pset_name: Name of the property set
            pset_data: Dictionary of property name-value pairs
            
        Returns:
            ID of the created property set node
        """
        # Generate Cypher parameters for property set
        params = {
            "name": pset_name,
            "id": f"pset_{pset_name.replace(' ', '_')}_{hash(pset_name)}"  # Generate a deterministic ID
        }
        
        # Create property set node
        query = """
        MERGE (ps:PropertySet {id: $id})
        SET ps.name = $name
        RETURN ps.id as PsetId
        """
        
        try:
            # Execute query to create property set
            result = self.connector.run_query(query, params)
            if not result or not result[0].get('PsetId'):
                return None
            
            pset_id = result[0]['PsetId']
            
            # Create property nodes and relationships
            for prop_name, prop_value in pset_data.items():
                # Create property node
                prop_params = {
                    "name": prop_name,
                    "value": format_property_value(prop_value),
                    "pset_id": pset_id,
                    "prop_id": f"prop_{prop_name.replace(' ', '_')}_{pset_id}"  # Generate a deterministic ID
                }
                
                prop_query = """
                MERGE (p:Property {id: $prop_id})
                SET p.name = $name, p.value = $value
                WITH p
                MATCH (ps:PropertySet {id: $pset_id})
                MERGE (ps)-[:HAS_PROPERTY]->(p)
                RETURN p.id as PropId
                """
                
                self.connector.run_query(prop_query, prop_params)
            
            return pset_id
        
        except Exception as e:
            logger.error(f"Error creating property set node: {str(e)}")
            return None
    
    def link_element_to_property_set(self, element_id: str, pset_id: str) -> bool:
        """
        Create a relationship between an element and a property set.
        
        Args:
            element_id: GlobalId of the element
            pset_id: ID of the property set
            
        Returns:
            True if successful, False otherwise
        """
        if not element_id or not pset_id:
            logger.warning("Missing element or property set ID")
            return False
        
        # Generate optimized query that avoids Cartesian product
        query = """
        MATCH (e {GlobalId: $element_id})
        WITH e
        MATCH (ps:PropertySet {id: $pset_id})
        MERGE (e)-[r:HAS_PROPERTY_SET]->(ps)
        RETURN type(r) as RelationType
        """
        
        # Generate parameters
        params = {
            "element_id": element_id,
            "pset_id": pset_id
        }
        
        try:
            # Execute query
            result = self.connector.run_query(query, params)
            return bool(result)
        except Exception as e:
            logger.error(f"Error linking element to property set: {str(e)}")
            return False
    
    def create_material_node(self, material_data: Dict[str, Any]) -> str:
        """
        Create a material node.
        
        Args:
            material_data: Dictionary with material properties
            
        Returns:
            Name of the created material node
        """
        if "Name" not in material_data:
            logger.warning("Missing Name field in material data")
            return None
        
        # Format properties for Neo4j
        properties = {}
        for key, value in material_data.items():
            prop_name = PROPERTY_MAPPING.get(key, key)
            properties[prop_name] = format_property_value(value)
        
        # Generate Cypher parameters
        params = {
            "props": properties
        }
        
        # Generate Cypher query
        query = """
        MERGE (m:Material {name: $props.name})
        SET m = $props
        RETURN m.name as Name
        """
        
        try:
            # Execute query
            result = self.connector.run_query(query, params)
            if result and result[0].get('Name'):
                return result[0]['Name']
            return None
        except Exception as e:
            logger.error(f"Error creating material node: {str(e)}")
            return None
    
    def link_element_to_material(self, element_id: str, material_name: str) -> bool:
        """
        Create a relationship between an element and a material.
        
        Args:
            element_id: GlobalId of the element
            material_name: Name of the material
            
        Returns:
            True if successful, False otherwise
        """
        if not element_id or not material_name:
            logger.warning("Missing element ID or material name")
            return False
        
        # Get the optimized query creator from Neo4j connector
        try:
            # First ensure material exists
            material_query = """
            MERGE (m:Material {name: $material_name})
            RETURN m.name as name
            """
            self.connector.run_query(material_query, {"material_name": material_name})
            
            # Then create relationship using the optimized method
            result = self.connector.create_relationship(
                source_id=element_id,
                target_id=material_name,
                relationship_type="IS_MADE_OF",
                properties=None
            )
            return result is not None
        except Exception as e:
            logger.error(f"Error linking element to material: {str(e)}")
            return False
    
    def clear_graph(self) -> bool:
        """
        Clear all data from the graph.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.warning("Clearing all data from the graph")
            query = "MATCH (n) DETACH DELETE n"
            self.connector.run_query(query)
            return True
        except Exception as e:
            logger.error(f"Error clearing graph: {str(e)}")
            return False
    
    def get_node_count(self) -> int:
        """
        Get the total number of nodes in the graph.
        
        Returns:
            Number of nodes
        """
        try:
            query = "MATCH (n) RETURN count(n) as count"
            result = self.connector.run_query(query)
            if result and 'count' in result[0]:
                return result[0]['count']
            return 0
        except Exception as e:
            logger.error(f"Error getting node count: {str(e)}")
            return 0
    
    def get_relationship_count(self) -> int:
        """
        Get the total number of relationships in the graph.
        
        Returns:
            Number of relationships
        """
        try:
            query = "MATCH ()-[r]->() RETURN count(r) as count"
            result = self.connector.run_query(query)
            if result and 'count' in result[0]:
                return result[0]['count']
            return 0
        except Exception as e:
            logger.error(f"Error getting relationship count: {str(e)}")
            return 0
    
    def get_count_by_label(self, label: str) -> int:
        """
        Get the count of nodes with a specific label.
        
        Args:
            label: Node label to count
            
        Returns:
            Integer count of nodes with that label
        """
        query = f"""
        MATCH (n:{label})
        RETURN count(n) as count
        """
        
        try:
            result = self.connector.run_query(query)
            return result[0]["count"] if result else 0
        except Exception as e:
            logger.error(f"Error getting count for label {label}: {str(e)}")
            return 0
            
    def get_relationship_count_by_type(self, rel_type: str) -> int:
        """
        Get the count of relationships with a specific type.
        
        Args:
            rel_type: Relationship type to count
            
        Returns:
            Integer count of relationships with that type
        """
        query = f"""
        MATCH ()-[r:{rel_type}]->()
        RETURN count(r) as count
        """
        
        try:
            result = self.connector.run_query(query)
            return result[0]["count"] if result else 0
        except Exception as e:
            logger.error(f"Error getting count for relationship type {rel_type}: {str(e)}")
            return 0 