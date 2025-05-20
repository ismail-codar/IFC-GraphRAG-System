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
    from src.ifc_to_graph.analyzer.topologic_analyzer import TopologicAnalyzer
    TOPOLOGICPY_AVAILABLE = True
except ImportError:
    TOPOLOGICPY_AVAILABLE = False

logger = logging.getLogger(__name__)

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
        
        # Flush any remaining batches
        self.mapper.flush_batches()
        
        # Run topological analysis if enabled
        if self.enable_topological_analysis and TOPOLOGICPY_AVAILABLE:
            logger.info("Running topological analysis...")
            self._run_topological_analysis()
        
        elapsed = time.time() - start_time
        logger.info(f"Finished processing {self.ifc_file_path} in {elapsed:.2f} seconds")
        
    def _run_topological_analysis(self) -> None:
        """Run topological analysis for spatial relationships"""
        start_time = time.time()
        
        try:
            # Only analyze specific element types that benefit from topology analysis
            topology_element_types = [
                "IfcWall", "IfcSlab", "IfcColumn", "IfcBeam", "IfcWindow", "IfcDoor", 
                "IfcSpace", "IfcBuildingStorey", "IfcBuilding", "IfcSite"
            ]
            
            # Filter elements for topological analysis to reduce processing time
            topology_elements = {}
            for element in self.parser.get_elements():
                if element.is_a() in topology_element_types:
                    topology_elements[element.GlobalId] = element
            
            logger.info(f"Running topological analysis on {len(topology_elements)} elements...")
            
            # Use the topologic analyzer
            analyzer = TopologicAnalyzer(self.ifc_file_path)
            relationships = analyzer.analyze_elements(topology_elements)
            
            # Create relationships in batches
            relationship_batch = []
            for rel in relationships:
                relationship_batch.append({
                    'sourceId': rel['source_id'],
                    'targetId': rel['target_id'],
                    'type': rel['relationship_type'],
                    'properties': {}
                })
                
                if len(relationship_batch) >= self.batch_size:
                    self.mapper.create_relationships_batch(relationship_batch)
                    relationship_batch = []
            
            # Process any remaining relationships
            if relationship_batch:
                self.mapper.create_relationships_batch(relationship_batch)
            
            elapsed = time.time() - start_time
            logger.info(f"Finished topological analysis in {elapsed:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error during topological analysis: {e}")
    
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