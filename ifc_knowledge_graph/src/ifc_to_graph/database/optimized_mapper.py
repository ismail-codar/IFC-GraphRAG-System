"""
Optimized IFC to Graph Mapper

This is an optimized version of the IFC to Graph mapper with performance improvements
including query caching, optimized Cypher queries, and batch processing.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple

from ..parser.element import Element
from ..parser.property import Property
from ..parser.property_set import PropertySet
from ..parser.material import Material
from ..database.neo4j_connector import Neo4jConnector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueryCache:
    """Simple in-memory cache for database queries."""
    
    def __init__(self, max_size=1000):
        self.cache = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def get(self, key):
        """Get a value from the cache."""
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None
    
    def set(self, key, value):
        """Add a value to the cache."""
        if len(self.cache) >= self.max_size:
            # Simple LRU: just clear half the cache when full
            keys = list(self.cache.keys())[:self.max_size//2]
            for k in keys:
                del self.cache[k]
        self.cache[key] = value
    
    def clear(self):
        """Clear the cache."""
        self.cache.clear()
        
    def stats(self):
        """Return cache statistics."""
        return {
            "size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": self.hits / (self.hits + self.misses) if (self.hits + self.misses) > 0 else 0
        }

class OptimizedMapper:
    """Optimized mapper for converting IFC objects to Neo4j graph entities."""
    
    def __init__(self, neo4j_connector: Neo4jConnector):
        self.neo4j = neo4j_connector
        self.query_cache = QueryCache()
        self.batch_size = 100
        
        # Set of already processed IDs to avoid duplicate queries
        self.processed_elements = set()
        self.processed_property_sets = set()
        self.processed_properties = set()
        self.processed_materials = set()
        
    def element_exists(self, global_id: str) -> bool:
        """
        Check if an element exists in the database.
        Uses caching to avoid redundant queries.
        
        Args:
            global_id: GlobalId of the element
            
        Returns:
            True if element exists, False otherwise
        """
        cache_key = f"element_exists_{global_id}"
        cached = self.query_cache.get(cache_key)
        if cached is not None:
            return cached
        
        query = "MATCH (e:Element {GlobalId: $GlobalId}) RETURN count(e) > 0 as exists"
        params = {"GlobalId": global_id}
        result = self.neo4j.execute_query(query, params)
        
        exists = result[0]["exists"] if result else False
        self.query_cache.set(cache_key, exists)
        return exists
    
    def create_element(self, element: Element) -> Optional[str]:
        """
        Create an Element node in the database.
        Uses optimized queries with ON CREATE for better performance.
        
        Args:
            element: Element object
            
        Returns:
            GlobalId of the created element or None if failed
        """
        if not element or not element.guid:
            logger.warning("Missing element or GlobalId")
            return None
            
        # Skip if already processed in this session
        if element.guid in self.processed_elements:
            return element.guid
            
        # Prepare parameters
        params = {
            "GlobalId": element.guid,
            "Name": element.name or "",
            "Description": element.description or "",
            "type": element.type or "",
            "Tag": element.tag or ""
        }
        
        # Use optimized query with ON CREATE - only sets properties when creating new nodes
        query = """
        MERGE (e:Element {GlobalId: $GlobalId}) 
        ON CREATE SET e.Name = $Name, e.Description = $Description, e.type = $type, e.Tag = $Tag 
        RETURN e
        """
        
        result = self.neo4j.execute_query(query, params)
        
        if result and result[0] and 'e' in result[0]:
            self.processed_elements.add(element.guid)
            return element.guid
        
        logger.warning(f"Failed to create Element: {element.guid}")
        return None
    
    def create_property(self, property: Property) -> Optional[str]:
        """
        Create a Property node in the database.
        Uses optimized queries with ON CREATE for better performance.
        
        Args:
            property: Property object
            
        Returns:
            GlobalId of the created property or None if failed
        """
        if not property or not property.guid:
            logger.warning("Missing property or GlobalId")
            return None
            
        # Skip if already processed in this session
        if property.guid in self.processed_properties:
            return property.guid
            
        # Prepare parameters
        params = {
            "GlobalId": property.guid,
            "Name": property.name or "",
            "Description": property.description or "",
            "NominalValue": str(property.nominal_value) if property.nominal_value is not None else "",
            "PropertyType": property.property_type or ""
        }
        
        # Use optimized query with ON CREATE - only sets properties when creating new nodes
        query = """
        MERGE (p:Property {GlobalId: $GlobalId})
        ON CREATE SET p.Name = $Name, p.Description = $Description, 
                      p.NominalValue = $NominalValue, p.PropertyType = $PropertyType
        RETURN p
        """
        
        result = self.neo4j.execute_query(query, params)
        
        if result and result[0] and 'p' in result[0]:
            self.processed_properties.add(property.guid)
            return property.guid
        
        logger.warning(f"Failed to create Property: {property.guid}")
        return None
    
    def create_property_set(self, property_set: PropertySet) -> Optional[str]:
        """
        Create a PropertySet node and link it to its properties.
        Uses optimized queries with ON CREATE for better performance.
        
        Args:
            property_set: PropertySet object
            
        Returns:
            GlobalId of the created property set or None if failed
        """
        if not property_set or not property_set.guid:
            logger.warning("Missing property set or GlobalId")
            return None
            
        # Skip if already processed in this session
        if property_set.guid in self.processed_property_sets:
            return property_set.guid
            
        # Prepare parameters
        params = {
            "GlobalId": property_set.guid,
            "Name": property_set.name or "",
            "Description": property_set.description or ""
        }
        
        # Use optimized query with ON CREATE
        query = """
        MERGE (ps:PropertySet {GlobalId: $GlobalId})
        ON CREATE SET ps.Name = $Name, ps.Description = $Description
        RETURN ps
        """
        
        result = self.neo4j.execute_query(query, params)
        
        if result and result[0] and 'ps' in result[0]:
            # Create properties and link them to the property set
            for property in property_set.properties:
                property_id = self.create_property(property)
                if property_id:
                    self.link_property_set_to_property(property_set.guid, property_id)
            
            self.processed_property_sets.add(property_set.guid)
            return property_set.guid
        
        logger.warning(f"Failed to create PropertySet: {property_set.guid}")
        return None
    
    def create_material(self, material: Material) -> Optional[str]:
        """
        Create a Material node in the database.
        Uses optimized queries with ON CREATE for better performance.
        
        Args:
            material: Material object
            
        Returns:
            Name of the created material or None if failed
        """
        if not material or not material.name:
            logger.warning("Missing material or name")
            return None
            
        # Skip if already processed in this session
        if material.name in self.processed_materials:
            return material.name
            
        # Prepare parameters
        params = {
            "Name": material.name,
            "Description": material.description or "",
            "Category": material.category or ""
        }
        
        # Use optimized query with ON CREATE
        query = """
        MERGE (m:Material {Name: $Name})
        ON CREATE SET m.Description = $Description, m.Category = $Category
        RETURN m
        """
        
        result = self.neo4j.execute_query(query, params)
        
        if result and result[0] and 'm' in result[0]:
            self.processed_materials.add(material.name)
            return material.name
        
        logger.warning(f"Failed to create Material: {material.name}")
        return None
    
    def link_element_to_property_set(self, element_id: str, pset_id: str) -> bool:
        """
        Create a relationship between an element and a property set.
        Uses LIMIT 1 to ensure only one relationship is created.
        
        Args:
            element_id: GlobalId of the element
            pset_id: GlobalId of the property set
            
        Returns:
            True if successful, False otherwise
        """
        if not element_id or not pset_id:
            logger.warning("Missing element ID or property set ID")
            return False
            
        # Use cache to avoid redundant operations
        cache_key = f"link_element_pset_{element_id}_{pset_id}"
        cached = self.query_cache.get(cache_key)
        if cached is not None:
            return cached
            
        # Optimized query with LIMIT 1
        query = """
        MATCH (e:Element {GlobalId: $element_id})
        MATCH (ps:PropertySet {GlobalId: $pset_id})
        WITH e, ps LIMIT 1
        MERGE (e)-[r:HAS_PROPERTY_SET]->(ps)
        RETURN type(r)
        """
        
        params = {
            "element_id": element_id,
            "pset_id": pset_id
        }
        
        result = self.neo4j.execute_query(query, params)
        success = len(result) > 0
        
        # Cache the result
        self.query_cache.set(cache_key, success)
        
        return success
    
    def link_property_set_to_property(self, pset_id: str, property_id: str) -> bool:
        """
        Create a relationship between a property set and a property.
        Uses LIMIT 1 to ensure only one relationship is created.
        
        Args:
            pset_id: GlobalId of the property set
            property_id: GlobalId of the property
            
        Returns:
            True if successful, False otherwise
        """
        if not pset_id or not property_id:
            logger.warning("Missing property set ID or property ID")
            return False
            
        # Use cache to avoid redundant operations
        cache_key = f"link_pset_prop_{pset_id}_{property_id}"
        cached = self.query_cache.get(cache_key)
        if cached is not None:
            return cached
            
        # Optimized query with LIMIT 1
        query = """
        MATCH (ps:PropertySet {GlobalId: $pset_id})
        MATCH (p:Property {GlobalId: $property_id})
        WITH ps, p LIMIT 1
        MERGE (ps)-[r:HAS_PROPERTY]->(p)
        RETURN type(r)
        """
        
        params = {
            "pset_id": pset_id,
            "property_id": property_id
        }
        
        result = self.neo4j.execute_query(query, params)
        success = len(result) > 0
        
        # Cache the result
        self.query_cache.set(cache_key, success)
        
        return success
    
    def link_element_to_material(self, element_id: str, material_name: str) -> bool:
        """
        Create a relationship between an element and a material.
        Uses LIMIT 1 to ensure only one relationship is created.
        
        Args:
            element_id: GlobalId of the element
            material_name: Name of the material
            
        Returns:
            True if successful, False otherwise
        """
        if not element_id or not material_name:
            logger.warning("Missing element ID or material name")
            return False
            
        # Use cache to avoid redundant operations
        cache_key = f"link_element_material_{element_id}_{material_name}"
        cached = self.query_cache.get(cache_key)
        if cached is not None:
            return cached
            
        # Optimized query with LIMIT 1
        query = """
        MATCH (e:Element {GlobalId: $element_id})
        MATCH (m:Material {Name: $material_name})
        WITH e, m LIMIT 1
        MERGE (e)-[r:HAS_MATERIAL]->(m)
        RETURN type(r)
        """
        
        params = {
            "element_id": element_id,
            "material_name": material_name
        }
        
        result = self.neo4j.execute_query(query, params)
        success = len(result) > 0
        
        # Cache the result
        self.query_cache.set(cache_key, success)
        
        return success
    
    def create_containment_relationship(self, parent_id: str, child_id: str) -> bool:
        """
        Create a containment relationship between elements.
        Uses LIMIT 1 to ensure only one relationship is created.
        
        Args:
            parent_id: GlobalId of the parent element
            child_id: GlobalId of the child element
            
        Returns:
            True if successful, False otherwise
        """
        if not parent_id or not child_id:
            logger.warning("Missing parent ID or child ID")
            return False
            
        # Skip self-referential relationships
        if parent_id == child_id:
            logger.warning(f"Skipping self-referential relationship: {parent_id}")
            return False
            
        # Use cache to avoid redundant operations
        cache_key = f"containment_{parent_id}_{child_id}"
        cached = self.query_cache.get(cache_key)
        if cached is not None:
            return cached
            
        # Optimized query with LIMIT 1
        query = """
        MATCH (p:Element {GlobalId: $parent_id})
        MATCH (c:Element {GlobalId: $child_id})
        WITH p, c LIMIT 1
        MERGE (p)-[r:CONTAINS]->(c)
        RETURN type(r)
        """
        
        params = {
            "parent_id": parent_id,
            "child_id": child_id
        }
        
        result = self.neo4j.execute_query(query, params)
        success = len(result) > 0
        
        # Cache the result
        self.query_cache.set(cache_key, success)
        
        return success
    
    def process_elements_batch(self, elements: List[Element]) -> Tuple[int, int, float]:
        """
        Process a batch of elements more efficiently by grouping similar operations.
        
        Args:
            elements: List of Element objects to process
            
        Returns:
            Tuple of (successful_count, total_count, elapsed_time)
        """
        if not elements:
            return 0, 0, 0.0
            
        start_time = time.time()
        successful = 0
        
        # Group elements by type to optimize similar operations
        elements_by_type = {}
        for element in elements:
            if not element.type in elements_by_type:
                elements_by_type[element.type] = []
            elements_by_type[element.type].append(element)
        
        # Process each type group
        for element_type, type_elements in elements_by_type.items():
            logger.info(f"Processing {len(type_elements)} elements of type {element_type}")
            
            # Step 1: Create all elements first
            for element in type_elements:
                element_id = self.create_element(element)
                if element_id:
                    successful += 1
            
            # Step 2: Create all property sets for this batch
            for element in type_elements:
                for pset in element.property_sets:
                    pset_id = self.create_property_set(pset)
                    if pset_id and element.guid:
                        self.link_element_to_property_set(element.guid, pset_id)
            
            # Step 3: Create all materials for this batch
            for element in type_elements:
                for material_name in element.materials:
                    material_name = self.create_material(element.materials[material_name])
                    if material_name and element.guid:
                        self.link_element_to_material(element.guid, material_name)
            
            # Step 4: Create all containment relationships
            for element in type_elements:
                if element.parent_id and element.guid:
                    self.create_containment_relationship(element.parent_id, element.guid)
        
        elapsed_time = time.time() - start_time
        return successful, len(elements), elapsed_time
    
    def process_all_elements(self, elements: List[Element], batch_size: int = None) -> Tuple[int, int, float]:
        """
        Process all elements with efficient batching.
        
        Args:
            elements: List of all Element objects
            batch_size: Override default batch size (optional)
            
        Returns:
            Tuple of (successful_count, total_count, elapsed_time)
        """
        if batch_size:
            self.batch_size = batch_size
            
        logger.info(f"Processing {len(elements)} elements in batches of {self.batch_size}")
        
        start_time = time.time()
        total_successful = 0
        
        # Process in batches
        for i in range(0, len(elements), self.batch_size):
            batch = elements[i:i+self.batch_size]
            successful, total, elapsed = self.process_elements_batch(batch)
            total_successful += successful
            
            logger.info(f"Batch {i//self.batch_size + 1}: {successful}/{total} elements processed in {elapsed:.2f}s")
            
            # Log cache stats periodically
            if (i//self.batch_size + 1) % 5 == 0:
                stats = self.query_cache.stats()
                logger.info(f"Cache stats: {stats['size']} entries, {stats['hit_ratio']:.2f} hit ratio")
        
        total_elapsed = time.time() - start_time
        logger.info(f"Total: {total_successful}/{len(elements)} elements processed in {total_elapsed:.2f}s")
        
        return total_successful, len(elements), total_elapsed
    
    def clear_cache(self):
        """Clear the query cache."""
        self.query_cache.clear()
        self.processed_elements.clear()
        self.processed_property_sets.clear()
        self.processed_properties.clear()
        self.processed_materials.clear() 