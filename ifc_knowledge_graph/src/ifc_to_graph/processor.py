"""
IFC to Neo4j Processor

This module coordinates between the IFC parser and Neo4j database components
to process IFC files and populate the graph database.
"""

import logging
import time
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .parser import IfcParser
from .database import Neo4jConnector, SchemaManager, IfcToGraphMapper
from .database.performance_monitor import timing_decorator

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
        monitoring_output_dir: Optional[str] = None
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
        """
        self.ifc_file_path = ifc_file_path
        self.enable_monitoring = enable_monitoring
        self.monitoring_output_dir = monitoring_output_dir
        
        # Create monitoring directory if it doesn't exist
        if enable_monitoring and monitoring_output_dir:
            os.makedirs(monitoring_output_dir, exist_ok=True)
        
        # Initialize parser
        logger.info(f"Initializing IFC parser for {ifc_file_path}")
        self.parser = IfcParser(ifc_file_path)
        
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
        self.mapper = IfcToGraphMapper(self.db_connector)
        
        # Statistics
        self.stats = {
            "element_count": 0,
            "relationship_count": 0,
            "property_set_count": 0,
            "material_count": 0,
            "processing_time": 0,
            "start_time": time.time(),
            "end_time": 0
        }
    
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
            self.mapper.clear_graph()
        
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
            self.db_connector.performance_monitor.measure_memory("process_start", {
                "file_path": self.ifc_file_path,
                "batch_size": batch_size
            })
        
        # Process project info
        self._process_project_info()
        
        # Process spatial structure
        self._process_spatial_structure()
        
        # Process elements with batch processing
        self._process_elements(batch_size)
        
        # Process relationships
        self._process_relationships()
        
        # Track memory at end
        if self.enable_monitoring:
            self.db_connector.performance_monitor.measure_memory("process_end", {
                "file_path": self.ifc_file_path,
                "batch_size": batch_size,
                "element_count": self.stats["element_count"],
                "relationship_count": self.stats["relationship_count"]
            })
        
        self.stats["processing_time"] = time.time() - start_time
        self.stats["end_time"] = time.time()
        
        logger.info(f"Processing completed in {self.stats['processing_time']:.2f} seconds")
        
        # Log statistics
        logger.info(f"Processed {self.stats['element_count']} elements")
        logger.info(f"Created {self.stats['relationship_count']} relationships")
        logger.info(f"Created {self.stats['property_set_count']} property sets")
        logger.info(f"Created {self.stats['material_count']} materials")
        
        # Get graph statistics
        node_count = self.mapper.get_node_count()
        rel_count = self.mapper.get_relationship_count()
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
            self.mapper.create_node_from_element(project_info)
    
    @timing_decorator
    def _process_spatial_structure(self) -> None:
        """Process the spatial structure hierarchy."""
        logger.info("Processing spatial structure")
        
        # Get spatial structure from IFC file
        spatial_structure = self.parser.get_spatial_structure()
        
        # Create nodes for each spatial element
        
        # Process sites
        for site in spatial_structure.get("sites", []):
            site["IFCType"] = "IfcSite"
            site_id = self.mapper.create_node_from_element(site)
            
            # Connect site to project
            if site_id and spatial_structure.get("project", {}).get("GlobalId"):
                self.mapper.create_relationship(
                    spatial_structure["project"]["GlobalId"],
                    site_id,
                    "IfcRelAggregates"
                )
                self.stats["relationship_count"] += 1
        
        # Process buildings
        for building in spatial_structure.get("buildings", []):
            building["IFCType"] = "IfcBuilding"
            building_id = self.mapper.create_node_from_element(building)
            
            # Connect building to site if available, or to project
            if building_id:
                if building.get("SiteGlobalId") and any(site["GlobalId"] == building["SiteGlobalId"] for site in spatial_structure.get("sites", [])):
                    # Connect to site
                    self.mapper.create_relationship(
                        building["SiteGlobalId"],
                        building_id,
                        "IfcRelAggregates"
                    )
                elif spatial_structure.get("project", {}).get("GlobalId"):
                    # Connect to project if no site
                    self.mapper.create_relationship(
                        spatial_structure["project"]["GlobalId"],
                        building_id,
                        "IfcRelAggregates"
                    )
                self.stats["relationship_count"] += 1
        
        # Process storeys
        for storey in spatial_structure.get("storeys", []):
            storey["IFCType"] = "IfcBuildingStorey"
            storey_id = self.mapper.create_node_from_element(storey)
            
            # Connect storey to building
            if storey_id and storey.get("BuildingGlobalId"):
                self.mapper.create_relationship(
                    storey["BuildingGlobalId"],
                    storey_id,
                    "IfcRelAggregates"
                )
                self.stats["relationship_count"] += 1
        
        # Process spaces
        for space in spatial_structure.get("spaces", []):
            space["IFCType"] = "IfcSpace"
            space_id = self.mapper.create_node_from_element(space)
            
            # Connect space to storey
            if space_id and space.get("StoreyGlobalId"):
                self.mapper.create_relationship(
                    space["StoreyGlobalId"],
                    space_id,
                    "IfcRelAggregates"
                )
                self.stats["relationship_count"] += 1
    
    @timing_decorator
    def _process_elements(self, batch_size: int = 100) -> None:
        """
        Process IFC elements.
        
        Args:
            batch_size: Number of elements to process in a batch
        """
        logger.info("Processing IFC elements")
        
        # Get all elements
        elements = self.parser.get_elements()
        total_elements = len(elements)
        logger.info(f"Found {total_elements} elements to process")
        
        # Record metric for element count if monitoring enabled
        if self.enable_monitoring:
            self.db_connector.performance_monitor.record_metric(
                name="total_ifc_elements",
                value=total_elements,
                unit="count",
                context={"ifc_file": os.path.basename(self.ifc_file_path)}
            )
        
        # Process elements in batches
        for i in range(0, total_elements, batch_size):
            batch = elements[i:i+batch_size]
            batch_start_time = time.time()
            
            logger.info(f"Processing batch of {len(batch)} elements ({i+1}-{min(i+batch_size, total_elements)} of {total_elements})")
            
            # Start batch timer if monitoring enabled
            batch_timer = None
            if self.enable_monitoring:
                batch_timer = self.db_connector.performance_monitor.start_timer(
                    "element_batch_processing",
                    {
                        "batch_number": i // batch_size + 1,
                        "batch_size": len(batch),
                        "batch_start_index": i + 1,
                        "batch_end_index": min(i+batch_size, total_elements),
                        "total_elements": total_elements
                    }
                )
            
            for element in batch:
                # Skip if no GlobalId
                if not hasattr(element, "GlobalId"):
                    continue
                
                # Extract element attributes
                attributes = self.parser.get_element_attributes(element)
                
                # Create node for element
                element_id = self.mapper.create_node_from_element(attributes)
                
                if element_id:
                    self.stats["element_count"] += 1
                    
                    # Process property sets
                    self._process_element_property_sets(element, element_id)
                    
                    # Process materials
                    self._process_element_materials(element, element_id)
                    
                    # Connect to spatial structure
                    self._connect_element_to_spatial_structure(element, element_id)
            
            # Record batch processing time if monitoring enabled
            if self.enable_monitoring and batch_timer:
                batch_timer()  # Stop the timer
                batch_processing_time = time.time() - batch_start_time
                self.db_connector.performance_monitor.record_metric(
                    name="batch_processing_time",
                    value=batch_processing_time,
                    unit="s",
                    context={
                        "batch_number": i // batch_size + 1,
                        "batch_size": len(batch),
                        "elements_per_second": len(batch) / batch_processing_time if batch_processing_time > 0 else 0
                    }
                )
    
    def _process_element_property_sets(self, element, element_id: str) -> None:
        """
        Process property sets for an element.
        
        Args:
            element: IFC element
            element_id: GlobalId of the element
        """
        # Get property sets for this element
        property_sets = self.parser.get_element_property_sets(element)
        
        if property_sets:
            # Create property set nodes and relationships
            for pset in property_sets:
                pset_id = self.mapper.create_property_set(pset, element_id)
                if pset_id:
                    self.stats["property_set_count"] += 1
    
    def _process_element_materials(self, element, element_id: str) -> None:
        """
        Process materials for an element.
        
        Args:
            element: IFC element
            element_id: GlobalId of the element
        """
        # Get materials for this element
        materials = self.parser.get_element_materials(element)
        
        if materials:
            # Create material nodes and relationships
            for material in materials:
                material_id = self.mapper.create_material(material, element_id)
                if material_id:
                    self.stats["material_count"] += 1
    
    def _connect_element_to_spatial_structure(self, element, element_id: str) -> None:
        """
        Connect element to spatial structure.
        
        Args:
            element: IFC element
            element_id: GlobalId of the element
        """
        # Get containing spatial structure
        container = self.parser.get_element_container(element)
        
        if container and container.get("GlobalId"):
            # Create containment relationship
            self.mapper.create_relationship(
                container["GlobalId"],
                element_id,
                "IfcRelContainedInSpatialStructure"
            )
            self.stats["relationship_count"] += 1
    
    @timing_decorator
    def _process_relationships(self) -> None:
        """Process relationships between elements."""
        logger.info("Processing element relationships")
        
        # Get all relationships
        relationships = self.parser.get_relationships()
        
        logger.info(f"Found {len(relationships)} relationships to process")
        
        # Record metric for relationship count if monitoring enabled
        if self.enable_monitoring:
            self.db_connector.performance_monitor.record_metric(
                name="total_ifc_relationships",
                value=len(relationships),
                unit="count",
                context={"ifc_file": os.path.basename(self.ifc_file_path)}
            )
        
        # Create relationships in the graph
        for rel in relationships:
            # Skip if missing source or target
            if not rel.get("SourceGlobalId") or not rel.get("TargetGlobalId"):
                continue
            
            # Create the relationship
            success = self.mapper.create_relationship(
                rel["SourceGlobalId"],
                rel["TargetGlobalId"],
                rel["RelationshipType"],
                rel.get("Properties")
            )
            
            if success:
                self.stats["relationship_count"] += 1
    
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
                report_file.write(f"Processing Time: {self.stats['processing_time']:.2f} seconds\n")
                report_file.write(f"Nodes in Graph: {self.stats['node_count']}\n")
                report_file.write(f"Relationships in Graph: {self.stats.get('relationship_count', 0)}\n")
            
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