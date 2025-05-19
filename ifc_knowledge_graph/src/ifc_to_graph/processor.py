"""
IFC to Neo4j Processor

This module coordinates between the IFC parser and Neo4j database components
to process IFC files and populate the graph database.
"""

import logging
import time
import os
from typing import Dict, List, Any, Optional, Tuple, Callable
from datetime import datetime

from .parser import IfcParser
from .parser.domain_enrichment import DomainEnrichment
from .database import Neo4jConnector, SchemaManager, IfcToGraphMapper
from .database.performance_monitor import timing_decorator
from .utils.parallel_processor import ParallelProcessor, TaskBatch, parallel_batch_process

# Configure logging
logger = logging.getLogger(__name__)


class IfcProcessor:
    """
    Main processor class that coordinates the conversion of IFC data to Neo4j.
    """
    
    def __init__(
        self, 
        ifc_file_path: str, 
        neo4j_uri: str = "neo4j://localhost:7687", 
        neo4j_username: str = "neo4j",
        neo4j_password: str = "password",
        neo4j_database: Optional[str] = None,
        enable_monitoring: bool = False,
        monitoring_output_dir: Optional[str] = None,
        parallel_processing: bool = False,
        max_workers: Optional[int] = None,
        enable_domain_enrichment: bool = True
    ):
        """
        Initialize the processor with file and database connection details.
        
        Args:
            ifc_file_path: Path to the IFC file to process
            neo4j_uri: URI for Neo4j connection
            neo4j_username: Neo4j username
            neo4j_password: Neo4j password
            neo4j_database: Optional Neo4j database name
            enable_monitoring: Whether to enable performance monitoring
            monitoring_output_dir: Directory to save performance reports
            parallel_processing: Whether to enable parallel processing
            max_workers: Maximum number of parallel workers (default: number of CPUs)
            enable_domain_enrichment: Whether to enable domain-specific enrichment
        """
        self.ifc_file_path = ifc_file_path
        self.enable_monitoring = enable_monitoring
        self.monitoring_output_dir = monitoring_output_dir
        self.parallel_processing = parallel_processing
        self.max_workers = max_workers
        self.enable_domain_enrichment = enable_domain_enrichment
        
        # Set up logger
        self.logger = logging.getLogger(__name__)
        
        # Create monitoring directory if it doesn't exist
        if enable_monitoring and monitoring_output_dir:
            os.makedirs(monitoring_output_dir, exist_ok=True)
        
        # Initialize parser
        logger.info(f"Initializing IFC parser for {ifc_file_path}")
        self.parser = IfcParser(ifc_file_path)
        
        # Initialize domain enrichment if enabled
        if enable_domain_enrichment:
            logger.info("Initializing domain enrichment")
            self.domain_enricher = DomainEnrichment(self.parser.file)
        else:
            self.domain_enricher = None
        
        # Initialize database connection with monitoring
        logger.info(f"Connecting to Neo4j database at {neo4j_uri}")
        self.db_connector = Neo4jConnector(
            uri=neo4j_uri,
            username=neo4j_username,
            password=neo4j_password,
            database=neo4j_database,
            enable_monitoring=enable_monitoring
        )
        
        # Initialize schema manager
        self.schema_manager = SchemaManager(self.db_connector)
        
        # Initialize mapper
        self.graph_mapper = IfcToGraphMapper(self.db_connector)
        
        # Initialize processor configuration
        self.processor_config = {
            'batch_size': 30,
            'max_workers': max_workers or (os.cpu_count() if parallel_processing else 1)
        }
        
        # Statistics
        self.stats = {
            "element_count": 0,
            "relationship_count": 0,
            "property_set_count": 0,
            "material_count": 0,
            "enriched_element_count": 0,
            "processing_time": 0,
            "start_time": time.time(),
            "end_time": 0,
            "element_types": {},
            "parallel_workers": self.processor_config['max_workers']
        }
        
        # Initialize performance monitor
        self.performance_monitor = self.db_connector.performance_monitor
        
        # Initialize parallel processor if enabled
        if self.parallel_processing:
            logger.info(f"Parallel processing enabled with {self.stats['parallel_workers']} workers")
    
    @timing_decorator
    def setup_database(self, clear_existing: bool = False) -> None:
        """
        Set up the Neo4j database schema.
        
        Args:
            clear_existing: Whether to clear existing data
        """
        logger.info("Setting up database schema")
        
        if clear_existing:
            logger.warning("Clearing existing graph data")
            self.graph_mapper.clear_graph()
        
        # Set up schema constraints and indexes
        self.schema_manager.setup_schema()
        logger.info("Database schema setup complete")
    
    def process(
        self, 
        clear_existing: bool = False, 
        batch_size: int = 100,
        save_performance_report: bool = True
    ) -> Dict[str, Any]:
        """
        Process the IFC file and populate the Neo4j database.
        
        Args:
            clear_existing: Whether to clear existing data
            batch_size: Batch size for processing elements
            save_performance_report: Whether to save a performance report
            
        Returns:
            Dictionary with processing statistics
        """
        self.stats["start_time"] = time.time()
        start_time = time.time()
        
        # Set up database schema
        self.setup_database(clear_existing)
        
        # Track memory at start
        if self.enable_monitoring:
            self.performance_monitor.measure_memory("process_start", {
                "file_path": self.ifc_file_path,
                "batch_size": batch_size,
                "parallel": self.parallel_processing,
                "workers": self.stats["parallel_workers"]
            })
        
        # Process project info
        self._process_project_info()
        
        # Process spatial structure
        self._process_spatial_structure()
        
        # Process elements with batch processing
        self._process_elements()
        
        # Process relationships
        self._process_relationships(batch_size)
        
        # Track memory at end
        if self.enable_monitoring:
            self.performance_monitor.measure_memory("process_end", {
                "file_path": self.ifc_file_path,
                "batch_size": batch_size,
                "element_count": self.stats["element_count"],
                "relationship_count": self.stats["relationship_count"],
                "parallel": self.parallel_processing,
                "workers": self.stats["parallel_workers"]
            })
        
        self.stats["processing_time"] = time.time() - start_time
        self.stats["end_time"] = time.time()
        
        logger.info(f"Processing completed in {self.stats['processing_time']:.2f} seconds")
        
        # Log statistics
        logger.info(f"Processed {self.stats['element_count']} elements")
        logger.info(f"Created {self.stats['relationship_count']} relationships")
        logger.info(f"Created {self.stats['property_set_count']} property sets")
        logger.info(f"Created {self.stats['material_count']} materials")
        
        if self.enable_domain_enrichment:
            logger.info(f"Applied domain enrichment to {self.stats['enriched_element_count']} elements")
        
        # Get graph statistics
        node_count = self.graph_mapper.get_node_count()
        rel_count = self.graph_mapper.get_relationship_count()
        logger.info(f"Graph now contains {node_count} nodes and {rel_count} relationships")
        
        self.stats["node_count"] = node_count
        self.stats["relationship_count"] = rel_count
        
        # Save performance report if monitoring is enabled
        if self.enable_monitoring and save_performance_report:
            self._save_performance_report()
        
        return self.stats
    
    @timing_decorator
    def _process_project_info(self) -> None:
        """Process project information."""
        logger.info("Processing project information")
        
        # Get project info from IFC file
        project_info = self.parser.get_project_info()
        
        # Create project node
        if project_info:
            project_info["IFCType"] = "IfcProject"
            self.graph_mapper.create_node_from_element(project_info)
    
    @timing_decorator
    def _process_spatial_structure(self) -> None:
        """Process spatial structure (project, site, building, storey)."""
        self.logger.info("Processing spatial structure")
        
        try:
            # Get spatial structure elements
            spatial_info = self.parser.get_spatial_structure()
            
            # Create project node
            if "Project" in spatial_info:
                project_data = spatial_info["Project"]
                
                # Flatten nested dictionaries
                for key, value in list(project_data.items()):
                    if isinstance(value, dict):
                        # Convert nested dictionaries to string representation
                        project_data[key] = str(value)
                
                project_id = self.graph_mapper.create_node_from_element(project_data)
                
                if not project_id:
                    self.logger.warning("Failed to create project node")
            
            # Create site node
            if "Site" in spatial_info and project_id:
                site_data = spatial_info["Site"]
                
                # Flatten nested dictionaries
                for key, value in list(site_data.items()):
                    if isinstance(value, dict) or isinstance(value, list):
                        # Convert nested dictionaries to string representation
                        site_data[key] = str(value)
                
                site_id = self.graph_mapper.create_node_from_element(site_data)
                
                if site_id:
                    # Link project to site
                    self.graph_mapper.create_relationship(
                        project_id, site_id, "HAS_SITE"
                    )
                else:
                    self.logger.warning("Failed to create site node")
            
            # Process buildings
            if "Buildings" in spatial_info and site_id:
                buildings = spatial_info["Buildings"]
                
                for building_data in buildings:
                    # Save storey info for later
                    storey_data_list = []
                    if "Storeys" in building_data:
                        storey_data_list = building_data["Storeys"]
                        # Remove nested structures
                        building_data["Storeys"] = f"[{len(storey_data_list)} storeys]"
                    
                    # Flatten nested dictionaries
                    for key, value in list(building_data.items()):
                        if isinstance(value, dict) or (isinstance(value, list) and key != "Storeys"):
                            # Convert nested dictionaries to string representation
                            building_data[key] = str(value)
                    
                    building_id = self.graph_mapper.create_node_from_element(building_data)
                    
                    if building_id:
                        # Link site to building
                        self.graph_mapper.create_relationship(
                            site_id, building_id, "HAS_BUILDING"
                        )
                        
                        # Process storeys
                        for storey_data in storey_data_list:
                            # Save space info for later
                            space_data_list = []
                            if "Spaces" in storey_data:
                                space_data_list = storey_data["Spaces"]
                                # Remove nested structures
                                storey_data["Spaces"] = f"[{len(space_data_list)} spaces]"
                            
                            # Flatten nested dictionaries
                            for key, value in list(storey_data.items()):
                                if isinstance(value, dict) or (isinstance(value, list) and key != "Spaces"):
                                    # Convert nested dictionaries to string representation
                                    storey_data[key] = str(value)
                            
                            # Use friendly name for database
                            storey_data["name"] = storey_data.get("Name", "")
                            storey_data["description"] = storey_data.get("Description", "")
                            storey_data["globalId"] = storey_data.get("GlobalId", "")
                            storey_data["Elevation"] = storey_data.get("Elevation", 0.0)
                            
                            # Create storey node
                            storey_id = self.graph_mapper.create_node_from_element(storey_data)
                            
                            if storey_id:
                                # Link building to storey
                                self.graph_mapper.create_relationship(
                                    building_id, storey_id, "HAS_STOREY"
                                )
                                
                                # Process spaces
                                for space_data in space_data_list:
                                    # Flatten nested dictionaries
                                    for key, value in list(space_data.items()):
                                        if isinstance(value, dict) or isinstance(value, list):
                                            # Convert nested dictionaries to string representation
                                            space_data[key] = str(value)
                                    
                                    space_id = self.graph_mapper.create_node_from_element(space_data)
                                    
                                    if space_id:
                                        # Link storey to space
                                        self.graph_mapper.create_relationship(
                                            storey_id, space_id, "HAS_SPACE"
                                        )
                                    else:
                                        self.logger.warning(f"Failed to create space node for {space_data.get('Name', 'unknown')}")
                            else:
                                self.logger.warning(f"Failed to create storey node for {storey_data.get('Name', 'unknown')}")
                    else:
                        self.logger.warning(f"Failed to create building node for {building_data.get('Name', 'unknown')}")
        except Exception as e:
            self.logger.error(f"Error processing spatial structure: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def _process_elements(self) -> None:
        """Process all elements in the IFC file and create nodes in the graph."""
        elements = self.parser.get_elements()
        self.logger.info(f"Found {len(elements)} elements to process")
        
        # Process elements in batches
        batch_size = self.processor_config.get('batch_size', 30)
        elements_batches = [elements[i:i + batch_size] for i in range(0, len(elements), batch_size)]
        
        for i, batch in enumerate(elements_batches):
            start_idx = i * batch_size + 1
            end_idx = min(start_idx + len(batch) - 1, len(elements))
            self.logger.info(f"Processing batch of {len(batch)} elements ({start_idx}-{end_idx} of {len(elements)})")
            
            with self.performance_monitor.measure_time("batch_processing"):
                for element in batch:
                    try:
                        # Get element data
                        element_data = self.parser.get_element_attributes(element)
                        
                        # Debug element data
                        if "GlobalId" not in element_data or element_data["GlobalId"] is None:
                            self.logger.warning(f"Element missing GlobalId: Type={element.is_a()}, Name={element.Name if hasattr(element, 'Name') else 'Unnamed'}")
                            # Try to print raw attributes
                            try:
                                self.logger.debug(f"Raw element attributes: {dir(element)}")
                                if hasattr(element, "GlobalId"):
                                    self.logger.debug(f"Direct GlobalId access: {element.GlobalId}")
                            except Exception as e:
                                self.logger.error(f"Error accessing element attributes: {str(e)}")
                        
                        # Create node in graph
                        element_id = self.graph_mapper.create_node_from_element(element_data)
                        
                        if element_id:
                            # Increment counters
                            self.stats["element_count"] += 1
                            
                            if element_data.get("IFCType"):
                                element_type = element_data["IFCType"]
                                if element_type not in self.stats["element_types"]:
                                    self.stats["element_types"][element_type] = 0
                                self.stats["element_types"][element_type] += 1
                            
                            # Process property sets
                            self._process_element_property_sets(element, element_id)
                            
                            # Process materials
                            self._process_element_materials(element, element_id)
                            
                            # Apply domain enrichment
                            if self.domain_enricher:
                                self.domain_enricher.enrich_element(element_id, element_data)
                                self.stats["enriched_element_count"] += 1
                    except Exception as e:
                        self.logger.error(f"Error processing element: {str(e)}")
            
            # Log batch performance
            elapsed_time = self.performance_monitor.get_last_timing("batch_processing")
            if elapsed_time > 0:
                elements_per_second = len(batch) / elapsed_time
                self.logger.info(f"Batch processed in {elapsed_time:.2f}s ({elements_per_second:.2f} elements/s)")
            else:
                self.logger.info(f"Batch processed (timing unavailable)")
    
    def _process_relationship_batch(self, relationship_batch: List[Dict[str, Any]]) -> int:
        """
        Process a batch of relationships.
        
        Args:
            relationship_batch: List of relationship dictionaries
            
        Returns:
            Number of relationships created
        """
        created_count = 0
        
        for rel in relationship_batch:
            # Skip if missing source or target
            if not rel.get("SourceGlobalId") or not rel.get("TargetGlobalId"):
                continue
            
            # Create the relationship
            success = self.graph_mapper.create_relationship(
                rel["SourceGlobalId"],
                rel["TargetGlobalId"],
                rel["RelationshipType"],
                rel.get("Properties")
            )
            
            if success:
                created_count += 1
        
        return created_count
    
    @timing_decorator
    def _process_relationships(self, batch_size: int = 100) -> None:
        """
        Process relationships between elements, optionally in parallel.
        
        Args:
            batch_size: Batch size for processing relationships
        """
        logger.info("Processing element relationships")
        
        # Get all elements first
        elements = self.parser.get_elements()
        
        # Collect all relationships from each element
        all_relationships = []
        for element in elements:
            # Skip elements with null GlobalId
            if not element.GlobalId:
                continue
            
            element_relationships = self.parser.get_relationships(element)
            
            # Convert the element relationships to a format suitable for batch processing
            for rel_type, related_items in element_relationships.items():
                for rel_item in related_items:
                    # Build relationship record
                    relationship = {
                        "SourceGlobalId": element.GlobalId,
                        "RelationshipType": rel_type,
                        "Properties": {}  # Additional properties if needed
                    }
                    
                    # Add target information based on relationship type
                    if rel_type in ["ContainedIn", "HostedBy"]:
                        # These relationship types have a RelatingObject
                        if "RelatingObjectId" in rel_item:
                            relationship["TargetGlobalId"] = rel_item["RelatingObjectId"]
                        else:
                            continue  # Skip if no target ID
                        
                    elif rel_type in ["Decomposes", "HasOpenings"]:
                        # These relationship types have a RelatedObject
                        if "RelatedObjectId" in rel_item:
                            relationship["TargetGlobalId"] = rel_item["RelatedObjectId"]
                        else:
                            continue  # Skip if no target ID
                        
                    elif rel_type == "HasPropertySets":
                        # Property set relationships are handled separately
                        continue
                        
                    elif rel_type == "HasAssociations":
                        # Material associations are complex, handle based on type
                        if rel_item["RelationType"] == "HasMaterial" and "MaterialName" in rel_item:
                            # Create material node and relationship in a single call
                            self.graph_mapper.link_element_to_material(
                                element.GlobalId, 
                                rel_item["MaterialName"]
                            )
                        continue  # Skip adding to batch since it's handled directly
                        
                    else:
                        # Skip unknown relationship types
                        continue
                    
                    # Add valid relationship to the collection
                    all_relationships.append(relationship)
        
        total_relationships = len(all_relationships)
        
        logger.info(f"Found {total_relationships} relationships to process")
        
        # Record metric for relationship count if monitoring enabled
        if self.enable_monitoring:
            self.performance_monitor.record_metric(
                name="total_ifc_relationships",
                value=total_relationships,
                unit="count",
                context={
                    "ifc_file": os.path.basename(self.ifc_file_path),
                    "parallel": self.parallel_processing
                }
            )
        
        if not self.parallel_processing:
            # Process relationships sequentially
            self._process_relationships_sequential(all_relationships, batch_size)
        else:
            # Process relationships in parallel
            self._process_relationships_parallel(all_relationships, batch_size)
    
    def _process_relationships_sequential(self, relationships: List[Dict[str, Any]], batch_size: int) -> None:
        """
        Process relationships sequentially in batches.
        
        Args:
            relationships: List of relationship dictionaries
            batch_size: Batch size
        """
        total_relationships = len(relationships)
        
        # Process relationships in batches
        for i in range(0, total_relationships, batch_size):
            batch = relationships[i:i+batch_size]
            batch_start_time = time.time()
            
            logger.info(
                f"Processing relationship batch {i//batch_size + 1}/{(total_relationships-1)//batch_size + 1} "
                f"({len(batch)} relationships)"
            )
            
            # Process the batch
            created_count = self._process_relationship_batch(batch)
            
            # Update statistics
            self.stats["relationship_count"] += created_count
            
            # Log batch processing time
            batch_processing_time = time.time() - batch_start_time
            logger.info(
                f"Relationship batch processed in {batch_processing_time:.2f}s "
                f"({len(batch)/batch_processing_time:.2f} relationships/s)"
            )
    
    def _process_relationships_parallel(self, relationships: List[Dict[str, Any]], batch_size: int) -> None:
        """
        Process relationships in parallel batches.
        
        Args:
            relationships: List of relationship dictionaries
            batch_size: Size of each batch
        """
        total_relationships = len(relationships)
        
        # Create batches for parallel processing
        task_batch = TaskBatch(relationships, batch_size, "relationships")
        batches = task_batch.get_batches()
        batch_count = len(batches)
        
        logger.info(
            f"Processing {total_relationships} relationships in {batch_count} batches "
            f"with {self.stats['parallel_workers']} parallel workers"
        )
        
        # Use thread pool for processing
        with ParallelProcessor(
            max_workers=self.max_workers, 
            use_processes=False,
            name="Relationship Processor"
        ) as processor:
            # Process batches in parallel and collect counts
            all_created_counts = processor.process_batches(
                self._process_relationship_batch,
                task_batch,
                show_progress=True
            )
            
            # Sum up created relationships
            self.stats["relationship_count"] += sum(all_created_counts)
    
    def _process_element_property_sets(self, element, element_id: str) -> None:
        """
        Process property sets for an element and create nodes and relationships.
        
        Args:
            element: The IFC element
            element_id: The GlobalId of the element in the graph
        """
        try:
            # Get property sets for the element
            property_sets = self.parser.get_element_property_sets(element)
            
            if not property_sets:
                return
                
            # Process each property set
            for pset_name, properties in property_sets.items():
                # Create property set node
                pset_id = self.graph_mapper.create_property_set_node(pset_name, properties)
                
                if pset_id:
                    # Link element to property set
                    self.graph_mapper.create_relationship(
                        element_id, 
                        pset_id, 
                        "HAS_PROPERTY_SET"
                    )
                    
                    # Increment counters
                    self.stats["property_set_count"] += 1
                    
                    # Create individual property nodes and link them to the property set
                    for prop_name, prop_value in properties.items():
                        # Skip None values
                        if prop_value is None:
                            continue
                            
                        # Convert complex values to string representation
                        if not isinstance(prop_value, (str, int, float, bool)):
                            prop_value = str(prop_value)
                            
                        # Create property node
                        prop_id = self.graph_mapper.create_property_node(
                            prop_name, 
                            prop_value
                        )
                        
                        if prop_id:
                            # Link property set to property
                            self.graph_mapper.create_relationship(
                                pset_id, 
                                prop_id, 
                                "HAS_PROPERTY"
                            )
                            
                            # Increment counters
                            self.stats["property_count"] += 1
        except Exception as e:
            self.logger.error(f"Error processing property sets for element {element_id}: {str(e)}")
            
    def _process_element_materials(self, element, element_id: str) -> None:
        """
        Process materials for an element and create nodes and relationships.
        
        Args:
            element: The IFC element
            element_id: The GlobalId of the element in the graph
        """
        try:
            # Get material data for the element
            materials = self.parser.get_element_materials(element)
            
            if not materials:
                return
                
            # Process each material
            for material_name in materials:
                if not material_name:
                    continue
                    
                # Create material node and relationship in one operation
                success = self.graph_mapper.link_element_to_material(
                    element_id, 
                    material_name
                )
                
                if success:
                    # Increment counters
                    self.stats["material_count"] += 1
        except Exception as e:
            self.logger.error(f"Error processing materials for element {element_id}: {str(e)}")
    
    def _save_performance_report(self) -> None:
        """
        Save performance monitoring report and metrics to files.
        """
        if not self.enable_monitoring or not self.monitoring_output_dir:
            return
        
        try:
            # Generate timestamp for filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = os.path.basename(self.ifc_file_path).split('.')[0]
            
            # Save summary report
            report_path = os.path.join(
                self.monitoring_output_dir, 
                f"{base_filename}_perf_report_{timestamp}.txt"
            )
            
            with open(report_path, 'w') as report_file:
                report_file.write(self.db_connector.get_performance_report())
                
                # Add processing statistics
                report_file.write("\n\nProcessing Statistics\n")
                report_file.write("=" * 80 + "\n")
                report_file.write(f"Elements: {self.stats['element_count']}\n")
                report_file.write(f"Relationships: {self.stats['relationship_count']}\n")
                report_file.write(f"Property Sets: {self.stats['property_set_count']}\n")
                report_file.write(f"Materials: {self.stats['material_count']}\n")
                report_file.write(f"Domain Enrichment: {self.stats['enriched_element_count']}\n")
                report_file.write(f"Processing Time: {self.stats['processing_time']:.2f} seconds\n")
                report_file.write(f"Nodes in Graph: {self.stats['node_count']}\n")
                report_file.write(f"Relationships in Graph: {self.stats.get('relationship_count', 0)}\n")
                report_file.write(f"Parallel Processing: {'Enabled' if self.parallel_processing else 'Disabled'}\n")
                if self.parallel_processing:
                    report_file.write(f"Parallel Workers: {self.stats['parallel_workers']}\n")
            
            logger.info(f"Performance report saved to {report_path}")
            
            # Export detailed metrics to JSON
            metrics_path = os.path.join(
                self.monitoring_output_dir, 
                f"{base_filename}_perf_metrics_{timestamp}.json"
            )
            
            self.db_connector.export_performance_metrics(metrics_path)
            logger.info(f"Performance metrics exported to {metrics_path}")
            
        except Exception as e:
            logger.error(f"Error saving performance report: {str(e)}")
    
    def close(self) -> None:
        """
        Close database connection and clean up resources.
        """
        if self.db_connector:
            self.db_connector.close()

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current state of the Neo4j database.
        
        Returns:
            Dictionary with node and relationship counts
        """
        try:
            node_count = self.graph_mapper.get_node_count()
            relationship_count = self.graph_mapper.get_relationship_count()
            
            # Count by node type
            node_types = {}
            for node_type in ["Project", "Site", "Building", "Storey", "Space", "Element"]:
                count = self.graph_mapper.get_count_by_label(node_type)
                node_types[node_type] = count
            
            # Count by relationship type
            relationship_types = {}
            for rel_type in ["HAS_SITE", "HAS_BUILDING", "HAS_STOREY", "HAS_SPACE", "CONTAINS", "HAS_PROPERTY_SET"]:
                count = self.graph_mapper.get_relationship_count_by_type(rel_type)
                relationship_types[rel_type] = count
            
            stats = {
                "node_count": node_count,
                "relationship_count": relationship_count,
                "node_types": node_types,
                "relationship_types": relationship_types
            }
            
            return stats
        except Exception as e:
            self.logger.error(f"Error getting database stats: {str(e)}")
            return {
                "node_count": 0,
                "relationship_count": 0,
                "error": str(e)
            } 