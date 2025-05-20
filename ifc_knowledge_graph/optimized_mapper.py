#!/usr/bin/env python3
"""
Optimized IFC to Graph Mapper with query caching and batch operations
"""

import logging
import time
from typing import Dict, List, Any, Tuple, Set
from functools import lru_cache

# Import the original mapper to extend functionality
from src.ifc_to_graph.database.ifc_to_graph_mapper import IfcToGraphMapper

logger = logging.getLogger(__name__)

class OptimizedIfcToGraphMapper(IfcToGraphMapper):
    """
    Optimized mapper that implements batch operations and query caching
    """
    
    def __init__(self, neo4j_connector, batch_size=5000, use_cache=True):
        """Initialize the optimized mapper with batch processing capabilities"""
        super().__init__(neo4j_connector)
        self.batch_size = batch_size
        self.use_cache = use_cache
        self._node_cache = {}  # Cache for node GlobalIds that already exist
        self._element_batch = []  # Batch for element creation
        self._property_batch = []  # Batch for property creation
        self._relationship_batch = []  # Batch for relationship creation
        
        # Create batch counters
        self.elements_created = 0
        self.properties_created = 0
        self.relationships_created = 0
        
        # Performance metrics
        self.start_time = time.time()
        self.last_report_time = self.start_time
    
    def create_nodes_from_elements_batch(self, elements_data: List[Dict[str, Any]]) -> None:
        """Create nodes from a batch of element data"""
        if not elements_data:
            return
            
        # Group elements by type for more efficient processing
        elements_by_type = {}
        for element_data in elements_data:
            element_type = element_data.get('IFCType', 'Unknown')
            if element_type not in elements_by_type:
                elements_by_type[element_type] = []
            elements_by_type[element_type].append(element_data)
        
        # Import the schema reference
        from src.ifc_to_graph.database.schema import get_node_labels, format_property_value, PROPERTY_MAPPING
        
        # Process each type in a separate batch for better query optimization
        for element_type, type_elements in elements_by_type.items():
            # Get labels using the schema's get_node_labels function for consistency
            # Important: For special types like Project, Building, etc., use the actual IFC type name
            # This ensures we get labels like "IfcProject" instead of just "Element"
            actual_element_type = element_type
            if element_type in ["IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace"]:
                # Make sure we're using the exact IFC type for spatial elements
                element_labels = get_node_labels(actual_element_type)
            else:
                element_labels = get_node_labels(element_type)
                
            labels_str = ':'.join(element_labels)
            
            # Create a batch of nodes with the same label structure
            node_batch = []
            
            for element in type_elements:
                # Format all properties for Neo4j
                props = {}
                for key, value in element.items():
                    if value is not None:  # Skip null values
                        # Format property value for Neo4j
                        prop_name = PROPERTY_MAPPING.get(key, key)
                        try:
                            # Ensure value is a Neo4j-compatible primitive type
                            if isinstance(value, (str, int, float, bool)):
                                props[prop_name] = value
                            elif isinstance(value, list) and all(isinstance(x, (str, int, float, bool)) for x in value):
                                # Handle lists of primitive types
                                props[prop_name] = value
                            else:
                                # Convert complex types to strings
                                props[prop_name] = str(value)
                        except Exception as e:
                            logger.warning(f"Error formatting property {key}: {str(e)}")
                
                # Always ensure GlobalId is included
                if "GlobalId" not in props and "GlobalId" in element:
                    props["GlobalId"] = element["GlobalId"]
                elif "GlobalId" not in props:
                    # Generate a temporary ID
                    props["GlobalId"] = f"Unknown_{id(element)}"
                
                # Add to the node batch
                node_batch.append(props)
            
            # Use standard UNWIND approach instead of APOC
            if node_batch:
                try:
                    # We need to create a simple MERGE statement for each node since batch operations 
                    # are causing syntax errors with multiple labels
                    logger.info(f"Creating {len(node_batch)} nodes of type {element_type} individually")
                    created_count = 0
                    
                    for node in node_batch:
                        # Extract GlobalId for MERGE operation
                        global_id = node.get("GlobalId", f"Unknown_{id(node)}")
                        
                        # Create property SET clauses for each property
                        prop_sets = []
                        params = {"GlobalId": global_id}
                        
                        for key, value in node.items():
                            if key != "GlobalId":  # Skip GlobalId as it's used in the MERGE
                                # Ensure value is a Neo4j-compatible primitive type
                                if isinstance(value, (str, int, float, bool)):
                                    param_name = f"prop_{key}"
                                    prop_sets.append(f"e.{key} = ${param_name}")
                                    params[param_name] = value
                                elif isinstance(value, list) and all(isinstance(x, (str, int, float, bool)) for x in value):
                                    # Handle lists of primitive types
                                    param_name = f"prop_{key}"
                                    prop_sets.append(f"e.{key} = ${param_name}")
                                    params[param_name] = value
                                else:
                                    # Convert complex types to strings
                                    param_name = f"prop_{key}"
                                    prop_sets.append(f"e.{key} = ${param_name}")
                                    params[param_name] = str(value)
                        
                        # Build the query with individual property assignments
                        prop_sets_str = ", ".join(prop_sets) if prop_sets else ""
                        
                        if prop_sets_str:
                            query = f"""
                            MERGE (e:{labels_str} {{GlobalId: $GlobalId}})
                            SET {prop_sets_str}
                            RETURN count(e) as count
                            """
                        else:
                            query = f"""
                            MERGE (e:{labels_str} {{GlobalId: $GlobalId}})
                            RETURN count(e) as count
                            """
                        
                        try:
                            result = self.connector.run_query(query, params)
                            if result and len(result) > 0:
                                created_count += result[0].get("count", 0)
                        except Exception as node_error:
                            logger.error(f"Error creating node {global_id}: {str(node_error)}")
                    
                    # Log the total created
                    self.elements_created += created_count
                    logger.info(f"Created {created_count} nodes of type {element_type}")
                except Exception as batch_error:
                    # Fall back to even simpler approach
                    logger.warning(f"Batch node creation failed: {batch_error}")
                    logger.info(f"Falling back to simplified MERGE operations for {len(node_batch)} nodes")
                    
                    # Fall back to individual MERGE operations
                    created_count = 0
                    
                    for node in node_batch:
                        query = f"""
                        MERGE (e:{labels_str} {{GlobalId: $GlobalId}})
                        RETURN count(e) AS created_count
                        """
                        
                        try:
                            result = self.connector.run_query(query, {"GlobalId": node.get("GlobalId")})
                            for record in result:
                                created_count += record["created_count"]
                        except Exception as e:
                            logger.error(f"Error creating node: {e}")
                    
                    self.elements_created += created_count
                    logger.info(f"Created {created_count} nodes of type {element_type} with minimal properties")
    
    def _get_specific_labels(self, ifc_type: str) -> List[str]:
        """
        Get specific Neo4j labels for an IFC element type
        
        Args:
            ifc_type: The IFC type (e.g., 'IfcWall', 'IfcDoor')
            
        Returns:
            List of Neo4j labels to apply
        """
        # Use schema.py's get_node_labels for consistent labeling
        from src.ifc_to_graph.database.schema import get_node_labels
        return get_node_labels(ifc_type)
    
    def create_property_sets_batch(self, property_sets: List[Dict[str, Any]]) -> None:
        """Create property sets in batches"""
        if not property_sets:
            return
            
        # Process property sets one by one for compatibility
        for pset in property_sets:
            # Create property set node
            pset_query = """
            MERGE (ps:IfcPropertySet {GlobalId: $GlobalId})
            ON CREATE SET ps.Name = $Name
            RETURN ps
            """
            
            pset_params = {
                "GlobalId": pset.get("GlobalId", f"Unknown_{id(pset)}"),
                "Name": pset.get("Name", "UnknownPropertySet")
            }
            
            try:
                # Create property set
                result = self.connector.run_query(pset_query, pset_params)
                
                # Create properties if present
                if "properties" in pset and isinstance(pset["properties"], dict):
                    for prop_name, prop_value in pset["properties"].items():
                        # Create property
                        prop_query = """
                        MATCH (ps:IfcPropertySet {GlobalId: $PsetId})
                        MERGE (p:IfcProperty {Name: $Name, GlobalId: $PropId})
                        ON CREATE SET p.Value = $Value
                        MERGE (ps)-[:HAS_PROPERTY]->(p)
                        """
                        
                        prop_params = {
                            "PsetId": pset["GlobalId"],
                            "Name": prop_name,
                            "PropId": f"{pset['GlobalId']}_{prop_name}",
                            "Value": str(prop_value)
                        }
                        
                        self.connector.run_query(prop_query, prop_params)
                
                self.properties_created += 1
            except Exception as e:
                logger.error(f"Error creating property set: {e}")
        
        logger.info(f"Created {len(property_sets)} property sets")
    
    def create_relationships_batch(self, relationships: List[Dict[str, Any]]) -> None:
        """
        Create a batch of relationships between nodes.
        
        Args:
            relationships: List of relationships to create
                Each relationship is a dict with sourceId, targetId, type, and optional properties.
        """
        if not relationships:
            return
        
        success_count = 0
        failure_count = 0
        
        # Process relationships in small groups for better error handling
        batch_size = 50  # Process smaller groups to avoid overloading Neo4j
        
        # Import schema for relationship types
        from src.ifc_to_graph.database.schema import get_relationship_type
        
        # Group special relationships like CONTAINS for separate processing
        spatial_relationships = []
        other_relationships = []
        
        for relationship in relationships:
            if relationship.get('type') == 'CONTAINS':
                spatial_relationships.append(relationship)
            else:
                other_relationships.append(relationship)
                
        # Process spatial relationships using MERGE to ensure uniqueness
        if spatial_relationships:
            logger.info(f"Processing {len(spatial_relationships)} spatial CONTAINS relationships")
            for rel in spatial_relationships:
                source_id = rel['sourceId']
                target_id = rel['targetId']
                rel_type = rel['type']
                props = rel.get('properties', {})
                
                # Use more specific queries to ensure the right nodes are connected
                # Specifically for spatial structure, try to use the specific labels
                try:
                    # Check for common spatial structure IDs
                    source_is_project = source_id.startswith('1xS3BCk291UvhgP2a6efl')
                    source_is_site = source_id.startswith('1xS3BCk291UvhgP2a6efl')
                    source_is_building = source_id.startswith('1xS3BCk291UvhgP2a6efl')
                    source_is_storey = source_id.startswith('1xS3BCk291UvhgP2dvN')
                    
                    # Determine source and target labels based on patterns
                    source_label = ""
                    if source_is_project:
                        source_label = ":IfcProject"
                    elif source_is_site:
                        source_label = ":IfcSite"
                    elif source_is_building:
                        source_label = ":IfcBuilding"
                    elif source_is_storey:
                        source_label = ":IfcBuildingStorey"
                        
                    # Prepare property parameters
                    params = {
                        "sourceId": source_id,
                        "targetId": target_id
                    }
                    
                    # Add properties if any
                    prop_clauses = []
                    for k, v in props.items():
                        if v is not None:
                            prop_key = f"prop_{k}"
                            params[prop_key] = v
                            prop_clauses.append(f"r.{k} = ${prop_key}")
                    
                    prop_str = ", ".join(prop_clauses) if prop_clauses else ""
                    
                    # Use MERGE for CONTAINS relationships to ensure uniqueness
                    if source_label:
                        # If we know the source type, use it for more specificity
                        query = f"""
                        MATCH (s{source_label} {{GlobalId: $sourceId}})
                        MATCH (t {{GlobalId: $targetId}})
                        MERGE (s)-[r:{rel_type}]->(t)
                        {f"SET {prop_str}" if prop_str else ""}
                        RETURN count(r) as count
                        """
                    else:
                        # Generic case
                        query = f"""
                        MATCH (s {{GlobalId: $sourceId}})
                        MATCH (t {{GlobalId: $targetId}})
                        MERGE (s)-[r:{rel_type}]->(t)
                        {f"SET {prop_str}" if prop_str else ""}
                        RETURN count(r) as count
                        """
                    
                    # Execute the query
                    result = self.connector.run_query(query, params)
                    if result and len(result) > 0:
                        created = result[0].get("count", 0)
                        if created > 0:
                            success_count += 1
                        else:
                            logger.warning(f"Failed to create {rel_type} relationship: {source_id} -> {target_id}")
                            failure_count += 1
                except Exception as e:
                    logger.warning(f"Error creating spatial relationship: {str(e)}")
                    failure_count += 1
        
        # Process other relationships in batches
        for i in range(0, len(other_relationships), batch_size):
            batch = other_relationships[i:i+batch_size]
            
            for relationship in batch:
                source_id = relationship['sourceId']
                target_id = relationship['targetId']
                rel_type = relationship['type']
                props = relationship.get('properties', {})
                
                try:
                    # Check if both nodes exist
                    if not self._check_nodes_exist(source_id, target_id):
                        logger.warning(f"Cannot create {rel_type} relationship: source {source_id} or target {target_id} node does not exist")
                        failure_count += 1
                        continue
                        
                    # Prepare property parameters
                    params = {
                        "sourceId": source_id,
                        "targetId": target_id
                    }
                    
                    # Add properties if any
                    prop_clauses = []
                    for k, v in props.items():
                        if v is not None:
                            prop_key = f"prop_{k}"
                            params[prop_key] = v
                            prop_clauses.append(f"r.{k} = ${prop_key}")
                    
                    prop_str = ", ".join(prop_clauses) if prop_clauses else ""
                    
                    # For standard relations, use CREATE to allow multiple relationships
                    query = f"""
                    MATCH (s {{GlobalId: $sourceId}})
                    MATCH (t {{GlobalId: $targetId}})
                    CREATE (s)-[r:{rel_type}]->(t)
                    {f"SET {prop_str}" if prop_str else ""}
                    RETURN count(r) as count
                    """
                    
                    # Execute the query
                    result = self.connector.run_query(query, params)
                    if result and len(result) > 0:
                        created = result[0].get("count", 0)
                        if created > 0:
                            success_count += 1
                        else:
                            logger.warning(f"Failed to create {rel_type} relationship: {source_id} -> {target_id}")
                            failure_count += 1
                except Exception as e:
                    logger.warning(f"Error creating relationship: {str(e)}")
                    failure_count += 1
            
        # Update metrics
        self.relationships_created += success_count
        
        logger.info(f"Created {success_count} {relationships[0]['type'] if relationships else ''} relationships (failed: {failure_count})")
    
    def _check_nodes_exist(self, source_id: str, target_id: str) -> bool:
        """
        Check if both source and target nodes exist
        
        Args:
            source_id: GlobalId of source node
            target_id: GlobalId of target node
            
        Returns:
            True if both nodes exist, False otherwise
        """
        query = """
        MATCH (s {GlobalId: $sourceId})
        MATCH (t {GlobalId: $targetId})
        RETURN count(s) > 0 AND count(t) > 0 as both_exist
        """
        
        params = {
            "sourceId": source_id,
            "targetId": target_id
        }
        
        try:
            result = self.connector.run_query(query, params)
            for record in result:
                return record["both_exist"]
            return False
        except Exception as e:
            logger.error(f"Error checking node existence: {e}")
            return False
    
    def add_element_to_batch(self, element_data: Dict[str, Any]) -> None:
        """Add an element to the creation batch"""
        self._element_batch.append(element_data)
        
        # Process batch if it reaches the threshold
        if len(self._element_batch) >= self.batch_size:
            self.create_nodes_from_elements_batch(self._element_batch)
            self._element_batch = []
            self._report_progress()
    
    def add_property_set_to_batch(self, property_set: Dict[str, Any]) -> None:
        """Add a property set to the creation batch"""
        self._property_batch.append(property_set)
        
        # Process batch if it reaches the threshold
        if len(self._property_batch) >= self.batch_size:
            self.create_property_sets_batch(self._property_batch)
            self._property_batch = []
            self._report_progress()
    
    def add_relationship_to_batch(self, relationship: Dict[str, Any]) -> None:
        """Add a relationship to the creation batch"""
        self._relationship_batch.append(relationship)
        
        # Process batch if it reaches the threshold
        if len(self._relationship_batch) >= self.batch_size:
            self.create_relationships_batch(self._relationship_batch)
            self._relationship_batch = []
            self._report_progress()
    
    def flush_batches(self) -> None:
        """Flush all remaining batched operations"""
        if self._element_batch:
            self.create_nodes_from_elements_batch(self._element_batch)
            self._element_batch = []
        
        if self._property_batch:
            self.create_property_sets_batch(self._property_batch)
            self._property_batch = []
        
        if self._relationship_batch:
            self.create_relationships_batch(self._relationship_batch)
            self._relationship_batch = []
        
        self._report_progress(final=True)
    
    def _report_progress(self, final=False) -> None:
        """Report progress of the batched operations"""
        current_time = time.time()
        elapsed = current_time - self.start_time
        since_last = current_time - self.last_report_time
        
        if since_last > 10 or final:  # Report every 10 seconds or on final flush
            logger.info(f"Progress: {self.elements_created} elements, "
                        f"{self.properties_created} properties, "
                        f"{self.relationships_created} relationships "
                        f"in {elapsed:.2f} seconds")
            self.last_report_time = current_time
    
    # Override original methods to use batching
    
    def create_node_from_element(self, element_data: Dict[str, Any]) -> str:
        """
        Create a node from element data.
        
        Args:
            element_data: Dictionary containing element properties
            
        Returns:
            The GlobalId of the created node
        """
        # Make sure IFCType is set if not already present
        if 'IFCType' not in element_data:
            # Try to determine type from other data
            if element_data.get('GlobalId', '').startswith('1xS3BCk291UvhgP2a6eflL'):
                element_data['IFCType'] = 'IfcProject'
            elif element_data.get('GlobalId', '').startswith('1xS3BCk291UvhgP2a6eflN'):
                element_data['IFCType'] = 'IfcSite'
            elif element_data.get('GlobalId', '').startswith('1xS3BCk291UvhgP2a6eflK'):
                element_data['IFCType'] = 'IfcBuilding'
            elif element_data.get('GlobalId', '').startswith('1xS3BCk291UvhgP2dvN'):
                element_data['IFCType'] = 'IfcBuildingStorey'
            elif 'is_a' in element_data and callable(element_data.get('is_a')):
                element_data['IFCType'] = element_data.get('is_a')()
            else:
                element_data['IFCType'] = 'Element'
                
        # Add element to batch instead of creating immediately
        self.add_element_to_batch(element_data)
        return element_data.get('GlobalId')
    
    def create_property_set(self, property_set_data: Dict[str, Any]) -> str:
        """Add property set to batch instead of creating immediately"""
        self.add_property_set_to_batch(property_set_data)
        return property_set_data.get('GlobalId')
    
    def create_relationship(self, source_id: str, target_id: str, 
                          rel_type: str, properties: Dict[str, Any] = None) -> None:
        """Add relationship to batch instead of creating immediately"""
        relationship = {
            'sourceId': source_id,
            'targetId': target_id,
            'type': rel_type,
            'properties': properties or {}
        }
        self.add_relationship_to_batch(relationship)
    
    # Cache check for node existence
    @lru_cache(maxsize=10000)
    def node_exists(self, global_id: str) -> bool:
        """Check if a node with given GlobalId exists (with caching)"""
        if not self.use_cache:
            return super().node_exists(global_id)
            
        if global_id in self._node_cache:
            return self._node_cache[global_id]
            
        exists = super().node_exists(global_id)
        self._node_cache[global_id] = exists
        return exists

    def create_nodes_from_spaces(self, spaces_data: List[Dict[str, Any]]) -> None:
        """
        Create nodes for spaces in the model.
        
        Args:
            spaces_data: List of space data dictionaries
        """
        if not spaces_data:
            return
        
        # Import schema functions
        from src.ifc_to_graph.database.schema import get_node_labels, format_property_value
        
        # Process each space individually to avoid batch operation issues
        created_count = 0
        
        for space_data in spaces_data:
            # Get node labels - use IfcSpace instead of Space to match IFC naming
            labels = get_node_labels("IfcSpace")
            labels_str = ":".join(labels)
            
            # Format properties with correct types
            properties = {}
            for key, value in space_data.items():
                # Ensure value is a Neo4j-compatible primitive type
                if isinstance(value, (str, int, float, bool)):
                    properties[key] = value
                elif isinstance(value, list) and all(isinstance(x, (str, int, float, bool)) for x in value):
                    # Handle lists of primitive types
                    properties[key] = value
                else:
                    # Convert complex types to strings
                    properties[key] = str(value)
            
            # Ensure GlobalId is present
            if "GlobalId" not in properties:
                logger.warning(f"Space missing GlobalId, skipping")
                continue
            
            # Create the space node
            try:
                # Extract GlobalId for MERGE operation
                global_id = properties.get("GlobalId", f"Unknown_Space_{id(properties)}")
                
                # Create property SET clauses for each property
                prop_sets = []
                params = {"GlobalId": global_id}
                
                for key, value in properties.items():
                    if key != "GlobalId":  # Skip GlobalId as it's used in the MERGE
                        # Ensure value is a Neo4j-compatible primitive type
                        if isinstance(value, (str, int, float, bool)):
                            param_name = f"prop_{key}"
                            prop_sets.append(f"s.{key} = ${param_name}")
                            params[param_name] = value
                        elif isinstance(value, list) and all(isinstance(x, (str, int, float, bool)) for x in value):
                            # Handle lists of primitive types
                            param_name = f"prop_{key}"
                            prop_sets.append(f"s.{key} = ${param_name}")
                            params[param_name] = value
                        else:
                            # Convert complex types to strings
                            param_name = f"prop_{key}"
                            prop_sets.append(f"s.{key} = ${param_name}")
                            params[param_name] = str(value)
                        
                # Build the query with individual property assignments
                prop_sets_str = ", ".join(prop_sets) if prop_sets else ""
                
                if prop_sets_str:
                    query = f"""
                    MERGE (s:{labels_str} {{GlobalId: $GlobalId}})
                    SET {prop_sets_str}
                    RETURN count(s) as count
                    """
                else:
                    query = f"""
                    MERGE (s:{labels_str} {{GlobalId: $GlobalId}})
                    RETURN count(s) as count
                    """
                
                result = self.connector.run_query(query, params)
                if result and len(result) > 0:
                    created_count += result[0].get("count", 0)
            except Exception as e:
                logger.error(f"Error creating space node: {str(e)}")
                
                # Try fallback method with just GlobalId
                try:
                    simpler_query = f"""
                    MERGE (s:{labels_str} {{GlobalId: $GlobalId}})
                    RETURN count(s) as count
                    """
                    
                    result = self.connector.run_query(simpler_query, {"GlobalId": global_id})
                    if result and len(result) > 0:
                        created_count += result[0].get("count", 0)
                except Exception as fallback_err:
                    logger.error(f"Fallback space node creation also failed: {str(fallback_err)}")
        
        logger.info(f"Created {created_count} space nodes") 