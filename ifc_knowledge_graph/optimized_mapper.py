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
        
        # Process each type in a separate batch for better query optimization
        for element_type, type_elements in elements_by_type.items():
            # Create simpler Cypher query without UNWIND for compatibility
            for element in type_elements:
                query = """
                MERGE (e:IfcElement {GlobalId: $GlobalId})
                ON CREATE SET e.Name = $Name, e.IFCType = $IFCType
                RETURN count(e) AS created_count
                """
                
                # Create minimal parameters from element
                params = {
                    "GlobalId": element.get("GlobalId", f"Unknown_{id(element)}"),
                    "Name": element.get("Name", ""),
                    "IFCType": element.get("IFCType", element_type)
                }
                
                # Execute single operation
                try:
                    result = self.connector.run_query(query, params)
                    created_count = 0
                    for record in result:
                        created_count += record["created_count"]
                    
                    self.elements_created += created_count
                except Exception as e:
                    logger.error(f"Error creating node: {e}")
            
            logger.info(f"Created nodes of type {element_type}")
    
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
        """Create relationships in batches"""
        if not relationships:
            return
            
        # Group relationships by type for better performance
        relationships_by_type = {}
        for rel_data in relationships:
            rel_type = rel_data.get('type', 'RELATED_TO')
            if rel_type not in relationships_by_type:
                relationships_by_type[rel_type] = []
            relationships_by_type[rel_type].append(rel_data)
        
        # Process each relationship type separately
        for rel_type, type_relationships in relationships_by_type.items():
            created_count = 0
            
            # Create each relationship individually for compatibility
            for rel in type_relationships:
                query = f"""
                MATCH (source:IfcElement {{GlobalId: $sourceId}})
                MATCH (target:IfcElement {{GlobalId: $targetId}})
                MERGE (source)-[r:{rel_type}]->(target)
                RETURN count(r) AS created_count
                """
                
                params = {
                    "sourceId": rel.get("sourceId"),
                    "targetId": rel.get("targetId")
                }
                
                try:
                    result = self.connector.run_query(query, params)
                    for record in result:
                        created_count += record["created_count"]
                except Exception as e:
                    logger.error(f"Error creating relationship: {e}")
            
            self.relationships_created += created_count
            logger.info(f"Created {created_count} {rel_type} relationships")
    
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
        """Add element to batch instead of creating immediately"""
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