#!/usr/bin/env python3
"""
Optimized IFC Processor with better batching and memory management
"""

import logging
import time
import os
import gc
import sys
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ifc_to_graph.processor import IfcProcessor
from src.ifc_to_graph.parser.ifc_parser import IfcParser
from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector
from optimized_mapper import OptimizedIfcToGraphMapper

try:
    from src.ifc_to_graph.topology.topologic_analyzer import TopologicAnalyzer
    TOPOLOGICPY_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("TopologicPy successfully imported")
except ImportError as e:
    TOPOLOGICPY_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to import TopologicPy: {e}")

class OptimizedIfcProcessor(IfcProcessor):
    """
    Optimized IFC processor with improved memory management and processing speed
    """
    
    def __init__(self, ifc_file_path: str, neo4j_uri: str, neo4j_username: str, neo4j_password: str,
                neo4j_database: str = "neo4j", enable_monitoring: bool = False,
                parallel_processing: bool = False, enable_topological_analysis: bool = False,
                batch_size: int = 5000, use_cache: bool = True):
        """
        Initialize the optimized processor
        
        Args:
            ifc_file_path: Path to the IFC file
            neo4j_uri: URI for the Neo4j database
            neo4j_username: Username for the Neo4j database
            neo4j_password: Password for the Neo4j database
            neo4j_database: Name of the Neo4j database
            enable_monitoring: Whether to enable monitoring
            parallel_processing: Whether to use parallel processing
            enable_topological_analysis: Whether to enable topological analysis
            batch_size: Size of batches for bulk operations (default: 5000)
            use_cache: Whether to use caching for node existence checks
        """
        super().__init__(
            ifc_file_path=ifc_file_path,
            neo4j_uri=neo4j_uri,
            neo4j_username=neo4j_username,
            neo4j_password=neo4j_password,
            neo4j_database=neo4j_database,
            enable_monitoring=enable_monitoring,
            parallel_processing=parallel_processing,
            enable_topological_analysis=enable_topological_analysis
        )
        
        self.batch_size = batch_size
        self.use_cache = use_cache
        
        # Replace standard mapper with optimized mapper
        self.neo4j = Neo4jConnector(neo4j_uri, neo4j_username, neo4j_password, neo4j_database)
        self.mapper = OptimizedIfcToGraphMapper(self.neo4j, batch_size=batch_size, use_cache=use_cache)
        
        # Track progress
        self.processing_start_time = None
        self.elements_processed = 0
        self.last_progress_report = 0
        
    def clear_memory(self):
        """Force garbage collection to free memory"""
        gc.collect()
    
    def _process_elements_by_type(self, element_type: str, elements: List[Any]) -> None:
        """Process elements by type for better batching efficiency"""
        count = len(elements)
        start_time = time.time()
        logger.info(f"Processing {count} elements of type {element_type}")
        
        for i, element in enumerate(elements):
            # Get element data and create node
            element_data = self.parser.get_element_attributes(element)
            element_id = self.mapper.create_node_from_element(element_data)
            
            # Process property sets
            property_sets = self.parser.get_element_property_sets(element)
            for pset_name, properties in property_sets.items():
                # Create property set data
                property_set_data = {
                    "GlobalId": f"{element_id}_{pset_name}",
                    "Name": pset_name,
                    "properties": properties
                }
                property_set_id = self.mapper.create_property_set(property_set_data)
                self.mapper.create_relationship(element_id, property_set_id, "HAS_PROPERTY_SET")
            
            # Report progress periodically
            self.elements_processed += 1
            if i % 100 == 0:
                self._report_progress()
        
        # Force batch processing of any remaining elements in the queue
        self.mapper.flush_batches()
        
        elapsed = time.time() - start_time
        logger.info(f"Finished processing {count} elements of type {element_type} in {elapsed:.2f} seconds")
        
        # Clear memory periodically
        if count > 1000:
            self.clear_memory()
    
    def _report_progress(self) -> None:
        """Report processing progress"""
        current_time = time.time()
        if self.processing_start_time is None:
            self.processing_start_time = current_time
            return
            
        elapsed = current_time - self.processing_start_time
        if elapsed - self.last_progress_report >= 10:  # Report every 10 seconds
            total_elements = len(self.parser.get_elements())
            progress_percent = (self.elements_processed / total_elements) * 100 if total_elements > 0 else 0
            
            logger.info(f"Progress: {self.elements_processed}/{total_elements} elements processed "
                       f"({progress_percent:.2f}%) in {elapsed:.2f} seconds")
            
            # Estimate remaining time
            if self.elements_processed > 0:
                elements_per_second = self.elements_processed / elapsed
                remaining_elements = total_elements - self.elements_processed
                estimated_remaining_time = remaining_elements / elements_per_second if elements_per_second > 0 else 0
                
                logger.info(f"Processing rate: {elements_per_second:.2f} elements/second, "
                           f"Estimated time remaining: {estimated_remaining_time:.2f} seconds "
                           f"({estimated_remaining_time/60:.2f} minutes)")
            
            self.last_progress_report = elapsed
    
    def process(self) -> None:
        """Process the IFC file and create the graph database"""
        start_time = time.time()
        logger.info(f"Starting optimized processing of {self.ifc_file_path}")
        
        # Setup the parser
        logger.info("Parsing IFC file...")
        self.parser = IfcParser(self.ifc_file_path)
        
        # Setup the database
        logger.info("Setting up database schema...")
        self.setup_database(clear_existing=True)
        
        # Add processing of project information and spatial structure
        logger.info("Processing project information...")
        self._process_project_info()
        
        logger.info("Processing spatial structure...")
        self._process_spatial_structure()
        
        # Process elements by type for better batching
        logger.info("Processing elements by type...")
        elements = self.parser.get_elements()
        
        # Group elements by type
        elements_by_type = {}
        for element in elements:
            element_type = element.is_a()
            if element_type not in elements_by_type:
                elements_by_type[element_type] = []
            elements_by_type[element_type].append(element)
        
        # Process each element type
        self.processing_start_time = time.time()
        
        # Process element types in order of frequency for better memory usage
        sorted_types = sorted(elements_by_type.items(), key=lambda x: len(x[1]), reverse=True)
        
        for element_type, type_elements in sorted_types:
            self._process_elements_by_type(element_type, type_elements)
        
        # Process spatial relationships
        logger.info("Processing spatial relationships...")
        self._process_spatial_relationships()
        
        # Flush any remaining batches
        self.mapper.flush_batches()
        
        # Run topological analysis if enabled
        if self.enable_topological_analysis:
            if TOPOLOGICPY_AVAILABLE:
                logger.info("Running topological analysis...")
                self._run_topological_analysis()
            else:
                logger.warning("Topological analysis is enabled but TopologicPy is not available. Skipping.")
        else:
            logger.info("Topological analysis is disabled. Skipping.")
        
        elapsed = time.time() - start_time
        logger.info(f"Finished processing {self.ifc_file_path} in {elapsed:.2f} seconds")
    
    def _process_project_info(self) -> None:
        """Process project information"""
        try:
            # Get project info from parser
            project_info = self.parser.get_project_info()
            
            # Create node for project
            self.mapper.create_node_from_element(project_info)
            
            logger.info(f"Created project node: {project_info.get('Name', 'Unnamed Project')}")
        except Exception as e:
            logger.error(f"Error processing project information: {e}")
    
    def _process_spatial_structure(self) -> None:
        """Process the spatial structure and create corresponding nodes and relationships"""
        # Get the spatial structure
        spatial_structure = self.parser.get_spatial_structure()
        logger.info(f"Spatial structure contains: {len(spatial_structure.get('sites', []))} sites, "
                  f"{len(spatial_structure.get('buildings', []))} buildings, "
                  f"{len(spatial_structure.get('storeys', []))} storeys, "
                  f"{len(spatial_structure.get('spaces', []))} spaces")
        
        # Process project
        project_data = spatial_structure.get('project', {})
        if project_data:
            project_id = self.mapper.create_node_from_element(project_data)
            logger.info(f"Created project node: {project_data.get('Name', 'Unnamed')} ({project_id})")
        else:
            logger.warning("No project data found in the IFC file")
            project_id = None
            
        # Process sites
        site_ids = []
        for site_data in spatial_structure.get('sites', []):
            site_id = self.mapper.create_node_from_element(site_data)
            site_ids.append(site_id)
            logger.info(f"Created site node: {site_data.get('Name', 'Unnamed')} ({site_id})")
            
            # Connect project to site
            if project_id:
                self.mapper.create_relationship(project_id, site_id, "CONTAINS")
                logger.info(f"Created CONTAINS relationship: Project ({project_id}) -> Site ({site_id})")
        
        # Process buildings
        building_ids = []
        for building_data in spatial_structure.get('buildings', []):
            building_id = self.mapper.create_node_from_element(building_data)
            building_ids.append(building_id)
            logger.info(f"Created building node: {building_data.get('Name', 'Unnamed Building')} ({building_id})")
            
            # Buildings should be connected to sites, but this can vary based on IFC model
            # For simplicity, connect each building to each site if no explicit information is available
            for site_id in site_ids:
                self.mapper.create_relationship(site_id, building_id, "CONTAINS")
                
        # Process storeys
        storey_ids = []
        for storey_data in spatial_structure.get('storeys', []):
            storey_id = self.mapper.create_node_from_element(storey_data)
            storey_ids.append(storey_id)
            logger.info(f"Created storey node: {storey_data.get('Name', 'Unnamed Storey')} ({storey_id})")
            
            # Connect each storey to each building for now
            # A more robust approach would follow the decomposition structure in the IFC model
            for building_id in building_ids:
                self.mapper.create_relationship(building_id, storey_id, "CONTAINS")
                
        # Process spaces - using the specialized method for spaces
        if spatial_structure.get('spaces'):
            self.mapper.create_nodes_from_spaces(spatial_structure.get('spaces', []))
            
            # Connect spaces to storeys
            for space_data in spatial_structure.get('spaces', []):
                space_id = space_data.get('GlobalId')
                # If we have containment information, use it; otherwise connect to all storeys
                containing_storey = space_data.get('containingStorey')
                if containing_storey and containing_storey in storey_ids:
                    self.mapper.create_relationship(containing_storey, space_id, "CONTAINS")
                else:
                    # As a fallback, connect to the most likely storey based on elevation
                    # This is a simplified approach and could be improved
                    for storey_id in storey_ids:
                        self.mapper.create_relationship(storey_id, space_id, "CONTAINS")
                        
        # Ensure all required relationships exist
        self._ensure_spatial_relationships(project_id, site_ids, building_ids, storey_ids)
        
        logger.info("Completed spatial structure processing")
    
    def _ensure_spatial_relationships(self, project_id, site_ids, building_ids, storey_ids):
        """Ensure all spatial hierarchy relationships exist"""
        # This method is called at the end of spatial structure processing
        # to make sure all necessary relationships are created
        
        # If we have no project ID, we can't establish the hierarchy
        if not project_id:
            logger.warning("No project ID available, cannot ensure spatial relationships")
            return
            
        # Ensure Project->Site relationships
        for site_id in site_ids:
            # Use direct database operations for reliability
            query = f"""
            MATCH (p:IfcProject {{GlobalId: "{project_id}"}})
            MATCH (s:IfcSite {{GlobalId: "{site_id}"}})
            MERGE (p)-[r:CONTAINS]->(s)
            RETURN count(r) as created
            """
            try:
                self.mapper.connector.run_query(query)
            except Exception as e:
                logger.error(f"Error ensuring Project->Site relationship: {e}")
                
        # Ensure Site->Building relationships
        for site_id in site_ids:
            for building_id in building_ids:
                query = f"""
                MATCH (s:IfcSite {{GlobalId: "{site_id}"}})
                MATCH (b:IfcBuilding {{GlobalId: "{building_id}"}})
                MERGE (s)-[r:CONTAINS]->(b)
                RETURN count(r) as created
                """
                try:
                    self.mapper.connector.run_query(query)
                except Exception as e:
                    logger.error(f"Error ensuring Site->Building relationship: {e}")
                    
        # Ensure Building->Storey relationships
        for building_id in building_ids:
            for storey_id in storey_ids:
                query = f"""
                MATCH (b:IfcBuilding {{GlobalId: "{building_id}"}})
                MATCH (s:IfcBuildingStorey {{GlobalId: "{storey_id}"}})
                MERGE (b)-[r:CONTAINS]->(s)
                RETURN count(r) as created
                """
                try:
                    self.mapper.connector.run_query(query)
                except Exception as e:
                    logger.error(f"Error ensuring Building->Storey relationship: {e}")
                    
        logger.info("Ensured all spatial structure relationships")
    
    def _process_spatial_relationships(self) -> None:
        """Process spatial relationships between elements and the spatial structure"""
        try:
            # Get all elements
            elements = self.parser.get_elements()
            
            # Process each element's container relationship
            relationships_count = 0
            
            for element in elements:
                # Skip elements that are part of the spatial structure
                if element.is_a() in ["IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace"]:
                    continue
                    
                # Get the element's container
                container = self.parser.get_element_container(element)
                
                if container and "GlobalId" in container and hasattr(element, "GlobalId"):
                    # Create relationship between container and element
                    self.mapper.create_relationship(
                        container["GlobalId"],
                        element.GlobalId,
                        "CONTAINS"
                    )
                    relationships_count += 1
            
            logger.info(f"Created {relationships_count} spatial containment relationships")
            
        except Exception as e:
            logger.error(f"Error processing spatial relationships: {e}")
    
    def _run_topological_analysis(self) -> None:
        """Run topological analysis for spatial relationships"""
        start_time = time.time()
        
        if not TOPOLOGICPY_AVAILABLE:
            logger.error("TopologicPy is not available. Cannot run topological analysis.")
            return
            
        logger.info("Beginning topological analysis...")
        
        try:
            # Only analyze specific element types that benefit from topology analysis
            topology_element_types = [
                "IfcWall", "IfcSlab", "IfcColumn", "IfcBeam", "IfcWindow", "IfcDoor", 
                "IfcSpace", "IfcBuildingStorey", "IfcBuilding", "IfcSite", "IfcWallStandardCase",
                "IfcCovering", "IfcRoof", "IfcStair", "IfcStairFlight", "IfcFurnishingElement"
            ]
            
            # Filter elements for topological analysis to reduce processing time
            topology_elements = {}
            all_elements = self.parser.get_elements()
            logger.info(f"Filtering elements for topology analysis from {len(all_elements)} total elements")
            
            # Log the types of elements available
            element_types = {}
            for element in all_elements:
                element_type = element.is_a()
                if element_type not in element_types:
                    element_types[element_type] = 0
                element_types[element_type] += 1
            
            logger.info(f"IFC file contains the following element types: {element_types}")
            
            for element in all_elements:
                if element.is_a() in topology_element_types:
                    topology_elements[element.GlobalId] = element
            
            logger.info(f"Selected {len(topology_elements)} elements for topological analysis")
            
            if not topology_elements:
                logger.warning("No elements found for topological analysis. Skipping.")
                return
                
            # Initialize the topologic analyzer
            logger.info(f"Initializing topologic analyzer with IFC file: {self.ifc_file_path}")
            try:
                # Pass the parsed IFC file instead of just the path
                analyzer = TopologicAnalyzer(self.parser.file)
                analyzer.set_ifc_parser(self.parser.file)  # Make sure the parser is set
                # Store the file path in case it's needed
                analyzer.ifc_file_path = self.ifc_file_path
                logger.info("TopologicAnalyzer initialized successfully")
            except Exception as init_error:
                logger.error(f"Failed to initialize TopologicAnalyzer: {init_error}", exc_info=True)
                return
                
            # Run the analysis for adjacency relationships
            logger.info("Starting adjacency analysis of elements...")
            try:
                adjacency_dict = analyzer.get_adjacency_relationships()
                # Convert dictionary to list format
                adjacency_relationships = []
                for source_id, target_ids in adjacency_dict.items():
                    for target_id in target_ids:
                        adjacency_relationships.append({
                            'source_id': source_id,
                            'target_id': target_id,
                            'relationship_type': 'ADJACENT_TO'
                        })
                logger.info(f"Adjacency analysis completed. Found {len(adjacency_relationships)} adjacency relationships.")
            except Exception as adjacency_error:
                logger.error(f"Error during adjacency analysis: {adjacency_error}", exc_info=True)
                adjacency_relationships = []
            
            # Run the analysis for containment relationships
            logger.info("Starting containment analysis of elements...")
            try:
                containment_dict = analyzer.get_containment_relationships()
                # Convert dictionary to list format
                containment_relationships = []
                for container_id, contained_ids in containment_dict.items():
                    for contained_id in contained_ids:
                        containment_relationships.append({
                            'source_id': container_id,
                            'target_id': contained_id,
                            'relationship_type': 'CONTAINS_TOPOLOGICALLY'
                        })
                logger.info(f"Containment analysis completed. Found {len(containment_relationships)} containment relationships.")
            except Exception as containment_error:
                logger.error(f"Error during containment analysis: {containment_error}", exc_info=True)
                containment_relationships = []
                
            # Run the analysis for space boundary relationships
            logger.info("Starting space boundary analysis...")
            try:
                space_boundary_relationships = analyzer.get_space_boundary_relationships()
                logger.info(f"Space boundary analysis completed. Found {len(space_boundary_relationships)} space boundary relationships.")
            except Exception as space_error:
                logger.error(f"Error during space boundary analysis: {space_error}", exc_info=True)
                space_boundary_relationships = []
                
            # Combine all relationships
            relationships = adjacency_relationships + containment_relationships + space_boundary_relationships
            logger.info(f"Total topological relationships found: {len(relationships)}")
            
            if not relationships:
                logger.warning("No relationships were found by the topological analyzer.")
                return
                
            # Log each type of relationship found
            rel_types = {}
            for rel in relationships:
                rel_type = rel.get('relationship_type', 'unknown')
                if rel_type not in rel_types:
                    rel_types[rel_type] = 0
                rel_types[rel_type] += 1
                
            logger.info(f"Found relationships by type: {rel_types}")
            
            # Log a sample of the relationships
            for i, rel in enumerate(relationships[:10]):
                logger.info(f"Sample relation {i+1}: {rel.get('source_id', 'unknown')} {rel.get('relationship_type', 'unknown')} {rel.get('target_id', 'unknown')}")
            
            # Convert relationships to mapper format
            logger.info("Converting relationships to mapper format...")
            relationship_batch = []
            
            # Import the schema mapping for topological relationships
            from src.ifc_to_graph.database.schema import get_topologic_relationship_type
            
            for rel in relationships:
                # Make sure relationship has required fields
                if 'source_id' not in rel or 'target_id' not in rel or 'relationship_type' not in rel:
                    logger.warning(f"Skipping malformed relationship: {rel}")
                    continue
                
                # Map the topological relationship type to proper Neo4j relationship type
                mapped_rel_type = get_topologic_relationship_type(rel['relationship_type'])
                if not mapped_rel_type:
                    # If no mapping found, use as-is but with proper Neo4j formatting
                    mapped_rel_type = rel['relationship_type'].upper().replace(' ', '_')
                
                # Extract properties if available
                rel_properties = {}
                if 'properties' in rel and isinstance(rel['properties'], dict):
                    rel_properties = rel['properties']
                
                logger.debug(f"Adding relationship: {rel['source_id']} {mapped_rel_type} {rel['target_id']}")
                
                # Convert from analyzer format to mapper format
                relationship_batch.append({
                    'sourceId': rel['source_id'],
                    'targetId': rel['target_id'],
                    'type': mapped_rel_type,
                    'properties': rel_properties,
                    'is_topological': True
                })
                
                if len(relationship_batch) >= self.batch_size:
                    logger.info(f"Processing batch of {len(relationship_batch)} relationships")
                    self.mapper.create_relationships_batch(relationship_batch)
                    relationship_batch = []
            
            # Process any remaining relationships
            if relationship_batch:
                logger.info(f"Processing final batch of {len(relationship_batch)} relationships")
                self.mapper.create_relationships_batch(relationship_batch)
            
            # Flush any remaining batches
            self.mapper.flush_batches()
            
            elapsed = time.time() - start_time
            logger.info(f"Finished topological analysis in {elapsed:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error during topological analysis: {e}", exc_info=True)
    
    def close(self) -> None:
        """Close connections and clean up resources"""
        if hasattr(self, 'mapper') and self.mapper:
            # Ensure all batches are processed
            self.mapper.flush_batches()
        
        # Close Neo4j connection
        if hasattr(self, 'neo4j') and self.neo4j:
            self.neo4j.close()
        
        # Force garbage collection
        self.clear_memory() 