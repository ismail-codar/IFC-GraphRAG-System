"""
Optimized IFC to Neo4j Processor

This module provides an optimized implementation of the IFC to Neo4j processing
pipeline with significant performance improvements.
"""

import logging
import time
import os
from typing import Dict, List, Any, Optional, Tuple, Callable
from datetime import datetime
import concurrent.futures
import traceback

from .parser import IfcParser
from .database import Neo4jConnector, SchemaManager
from .database.optimized_mapper import OptimizedMapper
from .database.performance_monitor import timing_decorator
from .topology.topologic_analyzer import TopologicAnalyzer, TOPOLOGICPY_AVAILABLE
from .database.topologic_to_graph_mapper import TopologicToGraphMapper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizedProcessor:
    """
    Optimized processor for converting IFC files to Neo4j knowledge graphs.
    
    This version includes performance improvements like:
    - Query caching
    - Optimized Cypher queries
    - Better batching
    - Type-based processing
    - Memory optimizations
    - Selective topology analysis
    """
    
    def __init__(
        self, 
        ifc_file_path: str,
        neo4j_connector: Neo4jConnector,
        clear_existing: bool = False,
        enable_parallel: bool = False,
        enable_topological_analysis: bool = False,
        batch_size: int = 100,
        topology_relevant_types: Optional[List[str]] = None
    ):
        """
        Initialize the processor.
        
        Args:
            ifc_file_path: Path to IFC file
            neo4j_connector: Neo4j connector instance
            clear_existing: Clear existing data in database
            enable_parallel: Enable parallel processing
            enable_topological_analysis: Enable topological analysis
            batch_size: Elements per batch
            topology_relevant_types: Element types to include in topology analysis
        """
        self.ifc_file_path = ifc_file_path
        self.neo4j_connector = neo4j_connector
        self.clear_existing = clear_existing
        self.enable_parallel = enable_parallel
        self.enable_topological_analysis = enable_topological_analysis
        self.batch_size = batch_size
        self.topology_relevant_types = topology_relevant_types
        
        # Default relevant types for topology if none provided
        if self.enable_topological_analysis and not self.topology_relevant_types:
            self.topology_relevant_types = [
                "IfcWall", "IfcWindow", "IfcDoor", "IfcSlab", "IfcSpace", 
                "IfcColumn", "IfcBeam", "IfcRoof", "IfcStair", "IfcRailing"
            ]
        
        # Initialize mapper
        self.mapper = OptimizedMapper(self.neo4j_connector)
        self.mapper.batch_size = self.batch_size
        
        # Initialize schema manager
        self.schema_manager = SchemaManager(self.neo4j_connector)
        
        # Performance metrics
        self.metrics = {
            "start_time": None,
            "end_time": None,
            "parsing_time": 0,
            "schema_setup_time": 0,
            "processing_time": 0,
            "topology_time": 0,
            "elements_processed": 0,
            "total_elements": 0,
            "batches": 0,
            "relationships_created": 0
        }
    
    @timing_decorator
    def setup_schema(self):
        """
        Set up the Neo4j schema (indexes and constraints).
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("Setting up Neo4j schema...")
        start_time = time.time()
        
        try:
            # Create constraints and indexes
            self.schema_manager.create_uniqueness_constraints()
            self.schema_manager.create_indexes()
            
            # Additional indexes for better performance
            additional_indexes = [
                {"label": "Element", "property": "type"},
                {"label": "Element", "property": "Name"},
                {"label": "Material", "property": "Name"},
                {"label": "Property", "property": "Name"},
                {"label": "PropertySet", "property": "Name"}
            ]
            
            for idx in additional_indexes:
                label = idx["label"]
                prop = idx["property"]
                index_name = f"idx_{label.lower()}_{prop.lower()}"
                query = f"CREATE INDEX {index_name} IF NOT EXISTS FOR (n:{label}) ON (n.{prop})"
                
                try:
                    self.neo4j_connector.execute_query(query)
                    logger.info(f"Created additional index: {index_name}")
                except Exception as e:
                    logger.warning(f"Error creating index {index_name}: {str(e)}")
            
            self.metrics["schema_setup_time"] = time.time() - start_time
            return True
            
        except Exception as e:
            logger.error(f"Error setting up schema: {str(e)}")
            return False
    
    @timing_decorator
    def parse_ifc(self):
        """
        Parse the IFC file.
        
        Returns:
            IfcParser object if successful, None otherwise
        """
        logger.info(f"Parsing IFC file: {self.ifc_file_path}")
        start_time = time.time()
        
        try:
            parser = IfcParser(self.ifc_file_path)
            parser.parse()
            
            logger.info(f"Parsed {len(parser.elements)} elements")
            logger.info(f"Parsed {len(parser.property_sets)} property sets")
            logger.info(f"Parsed {len(parser.materials)} materials")
            
            self.metrics["parsing_time"] = time.time() - start_time
            self.metrics["total_elements"] = len(parser.elements)
            
            return parser
        except Exception as e:
            logger.error(f"Error parsing IFC file: {str(e)}")
            return None
    
    def __process_elements(self, elements: List[Any]):
        """
        Process a batch of elements.
        
        Args:
            elements: List of elements to process
            
        Returns:
            Number of successfully processed elements
        """
        successful, total, elapsed = self.mapper.process_elements_batch(elements)
        return successful
    
    def __process_elements_parallel(self, elements: List[Any], max_workers: int = 4):
        """
        Process elements in parallel.
        
        Args:
            elements: List of elements to process
            max_workers: Maximum number of worker threads
            
        Returns:
            Number of successfully processed elements
        """
        # Group elements by type for better efficiency
        elements_by_type = {}
        for element in elements:
            if not element.type in elements_by_type:
                elements_by_type[element.type] = []
            elements_by_type[element.type].append(element)
        
        # Process each type group with a separate mapper to avoid thread contention
        total_successful = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for element_type, type_elements in elements_by_type.items():
                # Split into smaller batches
                for i in range(0, len(type_elements), self.batch_size // 2):
                    batch = type_elements[i:i+self.batch_size // 2]
                    # Each batch gets a new mapper to avoid concurrency issues
                    mapper = OptimizedMapper(self.neo4j_connector)
                    futures.append(executor.submit(mapper.process_elements_batch, batch))
            
            # Wait for all futures to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    successful, total, elapsed = future.result()
                    total_successful += successful
                except Exception as e:
                    logger.error(f"Error in parallel batch process: {str(e)}")
        
        return total_successful
    
    @timing_decorator
    def process_topology(self, elements: Dict[str, Any]):
        """
        Process topological relationships between elements.
        
        Args:
            elements: Dictionary of elements
            
        Returns:
            Number of relationships created
        """
        if not self.enable_topological_analysis:
            logger.info("Topological analysis disabled. Skipping.")
            return 0
            
        if not TOPOLOGICPY_AVAILABLE:
            logger.warning("TopologicPy not available. Skipping topology analysis.")
            return 0
        
        start_time = time.time()
        logger.info("Processing topological relationships...")
        
        try:
            # Filter elements by type if relevant types specified
            if self.topology_relevant_types:
                filtered_elements = {
                    guid: elem for guid, elem in elements.items()
                    if elem.type in self.topology_relevant_types
                }
                logger.info(f"Filtered {len(filtered_elements)} out of {len(elements)} elements for topology analysis")
            else:
                filtered_elements = elements
                
            # Skip if no elements to process
            if not filtered_elements:
                logger.warning("No elements matched for topology analysis")
                return 0
                
            # Analyze topology
            analyzer = TopologicAnalyzer(self.ifc_file_path)
            relationships = analyzer.analyze_elements(filtered_elements)
            
            if not relationships:
                logger.warning("No topological relationships found")
                return 0
                
            # Create relationships in graph
            logger.info(f"Creating {len(relationships)} topological relationships in Neo4j")
            mapper = TopologicToGraphMapper(self.neo4j_connector)
            
            # Process in batches
            batch_size = 500  # Larger batch size for relationship operations
            relationship_count = mapper.create_topologic_relationships(relationships, batch_size)
            
            logger.info(f"Created {relationship_count} topological relationships")
            
            self.metrics["topology_time"] = time.time() - start_time
            self.metrics["relationships_created"] = relationship_count
            
            return relationship_count
            
        except Exception as e:
            logger.error(f"Error in topology analysis: {str(e)}")
            logger.error(traceback.format_exc())
            return 0
    
    def process(self):
        """
        Execute the full processing pipeline.
        
        Returns:
            True if successful, False otherwise
        """
        self.metrics["start_time"] = time.time()
        
        # Check Neo4j connection
        if not self.neo4j_connector.test_connection():
            logger.error("Failed to connect to Neo4j")
            return False
        
        # Clear existing data if requested
        if self.clear_existing:
            logger.info("Clearing existing data...")
            self.neo4j_connector.clear_database()
        
        # Setup schema
        if not self.setup_schema():
            logger.error("Failed to set up schema")
            return False
        
        # Parse IFC file
        parser = self.parse_ifc()
        if not parser:
            logger.error("Failed to parse IFC file")
            return False
        
        # Process elements
        logger.info(f"Processing {len(parser.elements)} elements...")
        start_time = time.time()
        
        successful = 0
        
        if self.enable_parallel:
            logger.info("Using parallel processing")
            successful = self.__process_elements_parallel(parser.elements)
        else:
            logger.info(f"Using sequential processing with batch size {self.batch_size}")
            successful, total, elapsed = self.mapper.process_all_elements(parser.elements, self.batch_size)
        
        self.metrics["elements_processed"] = successful
        self.metrics["processing_time"] = time.time() - start_time
        
        logger.info(f"Processed {successful}/{len(parser.elements)} elements in {self.metrics['processing_time']:.2f}s")
        
        # Process topological relationships if enabled
        if self.enable_topological_analysis:
            elements_dict = {element.guid: element for element in parser.elements}
            relationships_created = self.process_topology(elements_dict)
            logger.info(f"Created {relationships_created} topological relationships")
        
        self.metrics["end_time"] = time.time()
        
        # Log overall performance
        total_time = self.metrics["end_time"] - self.metrics["start_time"]
        logger.info(f"Total processing time: {total_time:.2f}s")
        logger.info(f"Parsing time: {self.metrics['parsing_time']:.2f}s ({(self.metrics['parsing_time']/total_time)*100:.1f}%)")
        logger.info(f"Schema setup time: {self.metrics['schema_setup_time']:.2f}s ({(self.metrics['schema_setup_time']/total_time)*100:.1f}%)")
        logger.info(f"Element processing time: {self.metrics['processing_time']:.2f}s ({(self.metrics['processing_time']/total_time)*100:.1f}%)")
        
        if self.enable_topological_analysis:
            logger.info(f"Topology time: {self.metrics['topology_time']:.2f}s ({(self.metrics['topology_time']/total_time)*100:.1f}%)")
        
        return True
    
    def get_performance_metrics(self):
        """Get performance metrics."""
        if self.metrics["start_time"] and self.metrics["end_time"]:
            total_time = self.metrics["end_time"] - self.metrics["start_time"]
            self.metrics["total_time"] = total_time
            
            # Calculate element rate
            if self.metrics["elements_processed"] > 0 and total_time > 0:
                self.metrics["elements_per_second"] = self.metrics["elements_processed"] / self.metrics["processing_time"]
            else:
                self.metrics["elements_per_second"] = 0
                
            # Calculate relationship rate
            if self.metrics["relationships_created"] > 0 and self.metrics["topology_time"] > 0:
                self.metrics["relationships_per_second"] = self.metrics["relationships_created"] / self.metrics["topology_time"]
            else:
                self.metrics["relationships_per_second"] = 0
        
        return self.metrics 