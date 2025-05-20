"""
Query Optimizer for Neo4j

This module contains functions to optimize Cypher queries for Neo4j,
addressing performance issues and avoiding anti-patterns.
"""

import logging
import json

logger = logging.getLogger(__name__)

def optimize_node_connection_query(source_id, target_id, relationship_type, properties=None):
    """
    Create an optimized query to connect nodes by GlobalId.
    Avoids Cartesian product warnings by using MATCH...WHERE pattern instead of separate MATCHes.
    
    Args:
        source_id: GlobalId of the source node
        target_id: GlobalId of the target node  
        relationship_type: Type of relationship to create
        properties: Optional dictionary of relationship properties
        
    Returns:
        tuple: (query, params) - The optimized query and parameters
    """
    # Build the property string if properties are provided
    property_string = ""
    params = {"source_id": source_id, "target_id": target_id}
    
    if properties:
        property_parts = []
        for key, value in properties.items():
            param_name = f"prop_{key}"
            property_parts.append(f"{key}: ${param_name}")
            params[param_name] = value
        
        if property_parts:
            property_string = " {" + ", ".join(property_parts) + "}"
    
    # Create query that avoids Cartesian product
    query = f"""
        MATCH (a)
        WHERE a.GlobalId = $source_id
        WITH a
        MATCH (b)
        WHERE b.GlobalId = $target_id
        MERGE (a)-[r:{relationship_type}{property_string}]->(b)
        RETURN type(r) as RelationType
    """
    
    return query, params

def optimize_batch_merge_query(relationship_batch):
    """
    Create an optimized query to merge multiple relationships in a single batch operation using APOC.
    
    Args:
        relationship_batch: List of dictionaries, each containing:
            - source_id: GlobalId of source node
            - target_id: GlobalId of target node
            - type: Relationship type
            - properties: Optional relationship properties
            
    Returns:
        tuple: (query, params) - The optimized batch query and parameters
    """
    if not relationship_batch:
        return "", {}
    
    # Prepare parameters for unified batch processing with UNWIND
    batch_data = []
    
    for rel in relationship_batch:
        # Clean up properties - ensure serializable
        clean_props = {}
        if rel.get("properties"):
            for key, value in rel["properties"].items():
                # Convert any complex objects to strings to avoid type mismatch errors
                if isinstance(value, (dict, list)):
                    clean_props[key] = json.dumps(value)
                elif value is None:
                    # Skip None values or replace with empty string based on preference
                    continue
                else:
                    clean_props[key] = value
        
        batch_data.append({
            "source_id": rel["source_id"],
            "target_id": rel["target_id"],
            "type": rel["type"],
            "properties": clean_props
        })
    
    # Create query using UNWIND and apoc.merge.relationship
    query = """
    UNWIND $batch AS rel
    MATCH 
        (source {GlobalId: rel.source_id}),
        (target {GlobalId: rel.target_id})
    CALL apoc.merge.relationship(
        source,
        rel.type,
        {},
        rel.properties,
        target,
        {}
    )
    YIELD rel as created
    RETURN count(created)
    """
    
    params = {"batch": batch_data}
    return query, params

def optimize_entity_lookup_query(global_id):
    """
    Create an optimized query to lookup an entity by GlobalId.
    
    Args:
        global_id: The GlobalId to lookup
        
    Returns:
        tuple: (query, params) - The optimized query and parameters
    """
    query = """
        MATCH (n {GlobalId: $global_id})
        RETURN n, labels(n) as labels
    """
    return query, {"global_id": global_id}

def optimize_batch_node_creation_query(node_batch):
    """
    Create an optimized query for batch node creation using APOC.
    
    Args:
        node_batch: List of node dictionaries with labels, properties
        
    Returns:
        tuple: (query, params) - The optimized query and parameters
    """
    # Process nodes to ensure consistent format
    processed_batch = []
    for node in node_batch:
        if isinstance(node["labels"], str):
            labels = [node["labels"]]
        else:
            labels = node["labels"]
            
        # Ensure all properties are correctly serialized
        cleaned_props = {}
        for key, value in node["properties"].items():
            # Convert any complex objects to strings to avoid type mismatch errors
            if isinstance(value, (dict, list)):
                cleaned_props[key] = json.dumps(value)
            elif value is None:
                # Skip None values or replace with empty string based on preference
                # cleaned_props[key] = ""  # Uncomment to replace None with empty string
                continue
            else:
                cleaned_props[key] = value
            
        processed_batch.append({
            "labels": labels,
            "properties": cleaned_props
        })
    
    # Create query using UNWIND and apoc.merge.node (more stable than complex MERGE statements)
    query = """
    UNWIND $nodes AS node
    CALL apoc.merge.node(
        node.labels,
        node.properties,
        {},
        {}
    )
    YIELD node as created
    RETURN count(created)
    """
    
    params = {"nodes": processed_batch}
    return query, params

def optimize_property_merge_query(node_id, property_name, property_value):
    """
    Create an optimized query to add or update a property.
    
    Args:
        node_id: The GlobalId of the node
        property_name: The name of the property
        property_value: The value to set
        
    Returns:
        tuple: (query, params) - The optimized query and parameters
    """
    query = """
        MATCH (n {GlobalId: $node_id})
        SET n[$property_name] = $property_value
        RETURN n
    """
    
    params = {
        "node_id": node_id,
        "property_name": property_name,
        "property_value": property_value
    }
    
    return query, params

def optimize_spatial_hierarchy_query():
    """
    Create an optimized query to retrieve the spatial hierarchy.
    
    Returns:
        str: The optimized query
    """
    # Query that returns the full spatial hierarchy without Cartesian products
    query = """
        MATCH (project:Project)
        OPTIONAL MATCH path1 = (project)-[:HAS_SITE]->(site:Site)
        OPTIONAL MATCH path2 = (site)-[:HAS_BUILDING]->(building:Building)
        OPTIONAL MATCH path3 = (building)-[:HAS_STOREY]->(storey:Storey)
        OPTIONAL MATCH path4 = (storey)-[:CONTAINS]->(space:Space)
        OPTIONAL MATCH path5 = (storey)-[:CONTAINS]->(element:Element)
        
        RETURN project, 
               collect(DISTINCT site) as sites,
               collect(DISTINCT building) as buildings,
               collect(DISTINCT storey) as storeys,
               collect(DISTINCT space) as spaces,
               collect(DISTINCT element) as elements
    """
    
    return query 