"""
IFC to Neo4j Processor

This module coordinates between the IFC parser and Neo4j database components
to process IFC files and populate the graph database.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple

from .parser import IfcParser
from .database import Neo4jConnector, SchemaManager, IfcToGraphMapper

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
        neo4j_database: Optional[str] = None
    ):
        """
        Initialize the processor with file and database connection details.
        
        Args:
            ifc_file_path: Path to the IFC file to process
            neo4j_uri: URI for Neo4j connection
            neo4j_username: Neo4j username
            neo4j_password: Neo4j password
            neo4j_database: Optional Neo4j database name
        """
        self.ifc_file_path = ifc_file_path
        
        # Initialize parser
        logger.info(f"Initializing IFC parser for {ifc_file_path}")
        self.parser = IfcParser(ifc_file_path)
        
        # Initialize database connection
        logger.info(f"Connecting to Neo4j database at {neo4j_uri}")
        self.db_connector = Neo4jConnector(
            uri=neo4j_uri,
            username=neo4j_username,
            password=neo4j_password,
            database=neo4j_database
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
            "processing_time": 0
        }
    
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
    
    def process(self, clear_existing: bool = False, batch_size: int = 100) -> Dict[str, Any]:
        """
        Process the IFC file and populate the Neo4j database.
        
        Args:
            clear_existing: Whether to clear existing data
            batch_size: Batch size for processing elements
            
        Returns:
            Dictionary with processing statistics
        """
        start_time = time.time()
        
        # Set up database schema
        self.setup_database(clear_existing)
        
        # Process project info
        self._process_project_info()
        
        # Process spatial structure
        self._process_spatial_structure()
        
        # Process elements with batch processing
        self._process_elements(batch_size)
        
        # Process relationships
        self._process_relationships()
        
        self.stats["processing_time"] = time.time() - start_time
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
        
        return self.stats
    
    def _process_project_info(self) -> None:
        """Process project information."""
        logger.info("Processing project information")
        
        # Get project info from IFC file
        project_info = self.parser.get_project_info()
        
        # Create project node
        if project_info:
            project_info["IFCType"] = "IfcProject"
            self.mapper.create_node_from_element(project_info)
    
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
        
        # Process elements in batches
        for i in range(0, total_elements, batch_size):
            batch = elements[i:i+batch_size]
            logger.info(f"Processing batch of {len(batch)} elements ({i+1}-{min(i+batch_size, total_elements)} of {total_elements})")
            
            for element in batch:
                # Skip if no GlobalId
                if not hasattr(element, "GlobalId"):
                    continue
                
                # Extract element attributes
                attributes = self.parser.get_element_attributes(element)
                
                # Create node for element
                element_id = self.mapper.create_node_from_element(attributes)
                if not element_id:
                    continue
                
                self.stats["element_count"] += 1
                
                # Process property sets
                self._process_element_property_sets(element, element_id)
                
                # Process materials
                self._process_element_materials(element, element_id)
                
                # Connect to spatial structure
                self._connect_element_to_spatial_structure(element, element_id)
    
    def _process_element_property_sets(self, element, element_id: str) -> None:
        """
        Process property sets for an element.
        
        Args:
            element: IFC element
            element_id: GlobalId of the element
        """
        # Get property sets
        property_sets = self.parser.get_property_sets(element)
        
        for pset_name, properties in property_sets.items():
            # Create property set node
            pset_id = self.mapper.create_property_set_node(pset_name, properties)
            
            if pset_id:
                # Link element to property set
                self.mapper.link_element_to_property_set(element_id, pset_id)
                self.stats["property_set_count"] += 1
    
    def _process_element_materials(self, element, element_id: str) -> None:
        """
        Process materials for an element.
        
        Args:
            element: IFC element
            element_id: GlobalId of the element
        """
        # Get materials
        materials = self.parser.extract_material_info(element)
        
        for material in materials:
            # Create material node
            material_name = self.mapper.create_material_node(material)
            
            if material_name:
                # Link element to material
                self.mapper.link_element_to_material(element_id, material_name)
                self.stats["material_count"] += 1
    
    def _connect_element_to_spatial_structure(self, element, element_id: str) -> None:
        """
        Connect an element to its spatial structure.
        
        Args:
            element: IFC element
            element_id: GlobalId of the element
        """
        # Get relationships
        relationships = self.parser.get_relationships(element)
        
        # Find spatial containment relationships
        contained_in = relationships.get("ContainedInStructure", [])
        
        for container in contained_in:
            if hasattr(container, "GlobalId"):
                # Create relationship
                self.mapper.create_relationship(
                    container.GlobalId,
                    element_id,
                    "IfcRelContainedInSpatialStructure"
                )
                self.stats["relationship_count"] += 1
    
    def _process_relationships(self) -> None:
        """Process relationships between elements."""
        logger.info("Processing element relationships")
        
        # Get all elements
        elements = self.parser.get_elements()
        
        for element in elements:
            # Skip if no GlobalId
            if not hasattr(element, "GlobalId"):
                continue
            
            element_id = element.GlobalId
            
            # Get relationships
            relationships = self.parser.get_relationships(element)
            
            # Process each relationship type
            for rel_type, related_elements in relationships.items():
                # Skip spatial containment (already processed)
                if rel_type == "ContainedInStructure":
                    continue
                
                for related in related_elements:
                    if hasattr(related, "GlobalId"):
                        # Create relationship based on type
                        if rel_type == "Aggregates":
                            # Element is aggregated by the related element
                            self.mapper.create_relationship(
                                related.GlobalId,
                                element_id,
                                "IfcRelAggregates"
                            )
                        elif rel_type == "ConnectedTo":
                            # Element is connected to the related element
                            self.mapper.create_relationship(
                                element_id,
                                related.GlobalId,
                                "IfcRelConnectsElements"
                            )
                        elif rel_type == "Fills":
                            # Element fills the related element (e.g., door fills opening)
                            self.mapper.create_relationship(
                                element_id,
                                related.GlobalId,
                                "IfcRelFillsElement"
                            )
                        elif rel_type == "VoidsElements":
                            # Element voids the related element (e.g., opening in wall)
                            self.mapper.create_relationship(
                                related.GlobalId,
                                element_id,
                                "IfcRelVoidsElement"
                            )
                        elif rel_type == "BoundedBy":
                            # Space is bounded by element
                            self.mapper.create_relationship(
                                element_id,
                                related.GlobalId,
                                "IfcRelSpaceBoundary"
                            )
                        else:
                            # Generic relationship
                            self.mapper.create_relationship(
                                element_id,
                                related.GlobalId,
                                "IfcRelConnectsElements"
                            )
                        
                        self.stats["relationship_count"] += 1
    
    def close(self) -> None:
        """Close database connection and release resources."""
        if self.db_connector:
            self.db_connector.close()
            logger.info("Database connection closed") 