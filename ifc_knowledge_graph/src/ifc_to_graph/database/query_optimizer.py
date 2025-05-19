"""
Query Optimizer for Neo4j

This module contains functions to optimize Cypher queries for Neo4j,
addressing performance issues and avoiding anti-patterns.
"""

import logging

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
    Create an optimized query to merge multiple relationships in a single batch operation.
    
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
    
    # Build CALL apoc.periodic.iterate if apoc is available, otherwise build a regular UNWIND query
    # We'll use the simpler UNWIND approach for better compatibility
    
    # Build parameter list
    batch_params = []
    params = {}
    
    for i, rel in enumerate(relationship_batch):
        # Validate required fields
        if not rel.get('source_id') or not rel.get('target_id') or not rel.get('type'):
            continue
            
        # Create parameter names
        source_param = f"source_{i}"
        target_param = f"target_{i}"
        type_param = f"type_{i}"
        
        # Add parameters
        params[source_param] = rel['source_id']
        params[target_param] = rel['target_id']
        params[type_param] = rel['type']
        
        # Handle properties if provided
        props_string = ""
        if rel.get('properties'):
            prop_items = []
            for key, value in rel['properties'].items():
                if value is not None:
                    prop_param = f"prop_{i}_{key}"
                    prop_items.append(f"{key}: ${prop_param}")
                    params[prop_param] = value
            
            if prop_items:
                props_string = " {" + ", ".join(prop_items) + "}"
        
        # Add to batch
        batch_params.append({
            "source_param": source_param,
            "target_param": target_param,
            "type_param": type_param,
            "props_string": props_string
        })
    
    # If we have no valid relationships, return empty query
    if not batch_params:
        return "", {}
    
    # Build optimized query with multiple small sub-queries to avoid Cartesian products
    query_parts = []
    for i, bp in enumerate(batch_params):
        # Each relationship gets its own sub-query to avoid Cartesian product
        sub_query = f"""
        // Relationship {i+1}
        MATCH (a{i})
        WHERE a{i}.GlobalId = ${bp['source_param']}
        WITH a{i}
        MATCH (b{i})
        WHERE b{i}.GlobalId = ${bp['target_param']}
        MERGE (a{i})-[r{i}:${bp['type_param']}{bp['props_string']}]->(b{i})
        """
        query_parts.append(sub_query)
    
    # Combine all sub-queries and return results
    query = "\n".join(query_parts) + "\nRETURN 'Done' as result"
    
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
    Create an optimized query for batch node creation.
    
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
            
        processed_batch.append({
            "labels": labels,
            "properties": node["properties"]
        })
    
    # Create query using UNWIND and apoc.create.node
    query = """
        UNWIND $nodes AS node
        CALL apoc.create.node(node.labels, node.properties)
        YIELD node as created
        RETURN count(created) as count
    """
    
    return query, {"nodes": processed_batch}

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