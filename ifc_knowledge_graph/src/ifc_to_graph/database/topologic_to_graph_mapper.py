"""
Topological to Neo4j Graph Mapper

This module maps topological relationships to Neo4j graph relationships.
It extends the IFC to Neo4j graph mapping with topological information.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

from .schema import (
    get_node_labels,
    get_topologic_relationship_type,
    format_property_value,
    PROPERTY_MAPPING,
    TOPOLOGICAL_PROPERTIES
)

# Configure logging
logger = logging.getLogger(__name__)


class TopologicToGraphMapper:
    """
    Maps topological relationships to Neo4j graph relationships.
    """
    
    def __init__(self, connector):
        """
        Initialize the mapper with a Neo4j connector.
        
        Args:
            connector: Neo4jConnector instance
        """
        self.connector = connector
    
    def create_topologic_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create a topological relationship between two nodes.
        
        Args:
            source_id: GlobalId of the source node
            target_id: GlobalId of the target node
            relationship_type: Type of topological relationship
            properties: Optional properties for the relationship
            
        Returns:
            True if successful, False otherwise
        """
        if not source_id or not target_id:
            logger.warning("Missing source or target ID for topological relationship")
            return False
        
        # Get appropriate relationship type
        rel_type = get_topologic_relationship_type(relationship_type)
        
        # Format properties for Neo4j
        formatted_props = {}
        if properties:
            for key, value in properties.items():
                prop_name = PROPERTY_MAPPING.get(key, key)
                formatted_props[prop_name] = format_property_value(value)
        
        # Add relationship_source property to indicate this is from topological analysis
        formatted_props["relationshipSource"] = "topologicalAnalysis"
        
        # Generate Cypher parameters
        params = {
            "source_id": source_id,
            "target_id": target_id,
            "props": formatted_props
        }
        
        # Generate Cypher query with properties
        query = f"""
        MATCH (a), (b)
        WHERE a.GlobalId = $source_id AND b.GlobalId = $target_id
        MERGE (a)-[r:{rel_type}]->(b)
        SET r = $props
        RETURN type(r) as RelationType
        """
        
        try:
            # Execute query
            result = self.connector.run_query(query, params)
            return bool(result)
        except Exception as e:
            logger.error(f"Error creating topological relationship: {str(e)}")
            return False
    
    def import_adjacency_relationships(self, adjacency_map: Dict[str, List[str]]) -> int:
        """
        Import adjacency relationships from topological analysis into Neo4j.
        
        Args:
            adjacency_map: Dictionary of adjacency relationships
            
        Returns:
            Number of relationships created
        """
        created_count = 0
        
        # Process each adjacency relationship
        for source_id, adjacent_ids in adjacency_map.items():
            for target_id in adjacent_ids:
                # Define properties for this relationship
                properties = {
                    "relationshipType": "adjacency",
                    "distanceTolerance": 0.001,  # Default tolerance
                }
                
                # Create the relationship
                success = self.create_topologic_relationship(
                    source_id,
                    target_id,
                    "adjacent",
                    properties
                )
                
                if success:
                    created_count += 1
        
        logger.info(f"Created {created_count} adjacency relationships in Neo4j")
        return created_count
    
    def import_containment_relationships(self, containment_map: Dict[str, List[str]]) -> int:
        """
        Import containment relationships from topological analysis into Neo4j.
        
        Args:
            containment_map: Dictionary of containment relationships
            
        Returns:
            Number of relationships created
        """
        created_count = 0
        
        # Process each containment relationship
        for container_id, contained_ids in containment_map.items():
            for contained_id in contained_ids:
                # Define properties for this relationship
                properties = {
                    "relationshipType": "containment",
                    "distanceTolerance": 0.001,  # Default tolerance
                    "containmentType": "full"
                }
                
                # Create the relationship
                success = self.create_topologic_relationship(
                    container_id,
                    contained_id,
                    "contains",
                    properties
                )
                
                if success:
                    created_count += 1
                    
                    # Also create the inverse relationship
                    inverse_success = self.create_topologic_relationship(
                        contained_id,
                        container_id,
                        "contained_by",
                        properties
                    )
                    
                    if inverse_success:
                        created_count += 1
        
        logger.info(f"Created {created_count} containment relationships in Neo4j")
        return created_count
    
    def import_space_boundary_relationships(self, space_boundaries: Dict[str, List[str]]) -> int:
        """
        Import space boundary relationships from topological analysis into Neo4j.
        
        Args:
            space_boundaries: Dictionary of space boundary relationships
            
        Returns:
            Number of relationships created
        """
        created_count = 0
        
        # Process each space boundary relationship
        for space_id, boundary_ids in space_boundaries.items():
            for boundary_id in boundary_ids:
                # Define properties for this relationship
                properties = {
                    "relationshipType": "spaceBoundary",
                    "boundaryType": "physical"  # Default type
                }
                
                # Create the space is bounded by element relationship
                success = self.create_topologic_relationship(
                    space_id,
                    boundary_id,
                    "bounded_by",
                    properties
                )
                
                if success:
                    created_count += 1
                    
                    # Also create the inverse relationship (element bounds space)
                    inverse_success = self.create_topologic_relationship(
                        boundary_id,
                        space_id,
                        "bounds_space",
                        properties
                    )
                    
                    if inverse_success:
                        created_count += 1
        
        logger.info(f"Created {created_count} space boundary relationships in Neo4j")
        return created_count
    
    def import_connectivity_graph(self, connectivity_graph: Dict[str, Dict[str, List[Dict[str, Any]]]]) -> int:
        """
        Import the full connectivity graph from topological analysis into Neo4j.
        
        Args:
            connectivity_graph: The connectivity graph with all relationships
            
        Returns:
            Number of relationships created
        """
        created_count = 0
        
        # Track created relationships to avoid duplicates
        created_relationships = set()
        
        # Process each element and its connections
        for source_id, connections in connectivity_graph.items():
            for rel_type, rel_connections in connections.items():
                for connection in rel_connections:
                    target_id = connection.get("id")
                    
                    if not target_id:
                        continue
                    
                    # Create a unique key for this relationship to avoid duplicates
                    rel_key = f"{source_id}_{rel_type}_{target_id}"
                    if rel_key in created_relationships:
                        continue
                    
                    # Define properties for this relationship
                    properties = {
                        "relationshipType": rel_type,
                        "targetType": connection.get("type", "Unknown")
                    }
                    
                    # Add any additional properties from the connection
                    for key, value in connection.items():
                        if key not in ["id", "type"]:
                            properties[key] = value
                    
                    # Create the relationship
                    success = self.create_topologic_relationship(
                        source_id,
                        target_id,
                        rel_type,
                        properties
                    )
                    
                    if success:
                        created_count += 1
                        created_relationships.add(rel_key)
        
        logger.info(f"Created {created_count} connectivity relationships in Neo4j")
        return created_count
    
    def import_all_topological_relationships(self, topology_results: Dict[str, Any]) -> Dict[str, int]:
        """
        Import all topological relationships into Neo4j.
        
        Args:
            topology_results: Dictionary with all topological analysis results
            
        Returns:
            Dictionary with counts of created relationships by type
        """
        results = {}
        
        # Import adjacency relationships
        if "adjacency" in topology_results:
            results["adjacency"] = self.import_adjacency_relationships(
                topology_results["adjacency"]
            )
        
        # Import containment relationships
        if "containment" in topology_results:
            results["containment"] = self.import_containment_relationships(
                topology_results["containment"]
            )
        
        # Import space boundary relationships
        if "space_boundaries" in topology_results:
            results["space_boundaries"] = self.import_space_boundary_relationships(
                topology_results["space_boundaries"]
            )
        
        # Import full connectivity graph
        if "connectivity" in topology_results:
            results["connectivity"] = self.import_connectivity_graph(
                topology_results["connectivity"]
            )
        
        # Calculate total
        results["total"] = sum(results.values())
        
        logger.info(f"Imported a total of {results['total']} topological relationships into Neo4j")
        return results
    
    def run_topology_path_query(self, start_id: str, end_id: str, 
                             relationship_types: Optional[List[str]] = None,
                             max_depth: int = 10) -> List[Dict[str, Any]]:
        """
        Find paths between elements using topological relationships in Neo4j.
        
        Args:
            start_id: GlobalId of the starting element
            end_id: GlobalId of the ending element
            relationship_types: List of relationship types to consider (default: all)
            max_depth: Maximum path length to consider
            
        Returns:
            List of paths found between the elements
        """
        # Default to all relationship types if none specified
        if not relationship_types:
            relationship_types = [
                "ADJACENT", "CONTAINS_TOPOLOGICALLY", "IS_CONTAINED_IN",
                "BOUNDS_SPACE", "IS_BOUNDED_BY", "CONNECTS_SPACES"
            ]
        
        # Generate the relationship pattern
        rel_pattern = "|".join(f":{rel_type}" for rel_type in relationship_types)
        
        # Generate Cypher parameters
        params = {
            "start_id": start_id,
            "end_id": end_id,
            "max_depth": max_depth
        }
        
        # Generate Cypher query
        query = f"""
        MATCH path = (start)-[:{rel_pattern}*1..{max_depth}]->(end)
        WHERE start.GlobalId = $start_id AND end.GlobalId = $end_id
        RETURN path, 
               length(path) AS pathLength,
               [node in nodes(path) | node.GlobalId] AS nodeIds,
               [node in nodes(path) | node.Name] AS nodeNames,
               [relationship in relationships(path) | type(relationship)] AS relationshipTypes
        ORDER BY pathLength ASC
        LIMIT 5
        """
        
        try:
            # Execute query
            paths = self.connector.run_query(query, params)
            
            # Format the results
            formatted_paths = []
            for path in paths:
                formatted_path = {
                    "length": path.get("pathLength"),
                    "nodeIds": path.get("nodeIds", []),
                    "nodeNames": path.get("nodeNames", []),
                    "relationshipTypes": path.get("relationshipTypes", [])
                }
                formatted_paths.append(formatted_path)
            
            return formatted_paths
            
        except Exception as e:
            logger.error(f"Error finding paths: {str(e)}")
            return [] 