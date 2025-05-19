#!/usr/bin/env python
"""
Domain Enrichment Example

This script demonstrates the domain-specific enrichment capabilities 
of the IFC to Neo4j Knowledge Graph project.
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Add the src directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ifc_to_graph.parser import IfcParser
from src.ifc_to_graph.parser.domain_enrichment import DomainEnrichment
from src.ifc_to_graph.database import Neo4jConnector, IfcToGraphMapper
from src.ifc_to_graph.processor import IfcProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Domain Enrichment Example for IFC to Neo4j Knowledge Graph"
    )
    
    parser.add_argument(
        "--ifc-file", "-i",
        required=True,
        help="Path to the IFC file to process"
    )
    
    parser.add_argument(
        "--neo4j-uri", "-u",
        default="neo4j://localhost:7687",
        help="Neo4j connection URI (default: neo4j://localhost:7687)"
    )
    
    parser.add_argument(
        "--neo4j-user", "-n",
        default="neo4j",
        help="Neo4j username (default: neo4j)"
    )
    
    parser.add_argument(
        "--neo4j-password", "-p",
        default="password",
        help="Neo4j password (default: password)"
    )
    
    parser.add_argument(
        "--example-mode", "-m",
        choices=["print", "neo4j", "both"],
        default="print",
        help="Example mode: print to console, store in Neo4j, or both (default: print)"
    )
    
    parser.add_argument(
        "--element-type", "-t",
        default=None,
        help="Filter by IFC element type (e.g., IfcWall)"
    )
    
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=5,
        help="Limit the number of elements to process (default: 5)"
    )
    
    return parser.parse_args()


def print_element_enrichment(element, enrichment):
    """Print enriched element data to console."""
    element_type = element.is_a()
    element_id = element.GlobalId if hasattr(element, "GlobalId") else "Unknown"
    element_name = element.Name if hasattr(element, "Name") and element.Name else "Unnamed"
    
    print("\n" + "=" * 80)
    print(f"Element: {element_name} ({element_type}) - {element_id}")
    print("=" * 80)
    
    # Print building systems classification
    systems = enrichment.classify_building_systems(element)
    if systems:
        print("\nBUILDING SYSTEMS CLASSIFICATION:")
        for system, value in systems.items():
            print(f"  - {system}: {value}")
    
    # Print semantic tags
    tags = enrichment.generate_semantic_tags(element)
    if tags:
        print("\nSEMANTIC TAGS:")
        for tag in tags:
            print(f"  - {tag}")
    
    # Print performance properties
    perf_props = enrichment.extract_performance_properties(element)
    if perf_props:
        print("\nPERFORMANCE PROPERTIES:")
        for category, props in perf_props.items():
            print(f"  {category}:")
            for prop_name, prop_data in props.items():
                print(f"    - {prop_name}: {prop_data['value']} ({prop_data['type']})")
    
    # Print mapped properties
    mapped_props = enrichment.apply_custom_property_mapping(element)
    if mapped_props:
        print("\nMAPPED PROPERTIES:")
        for prop_name, prop_data in mapped_props.items():
            print(f"  - {prop_name}: {prop_data['value']} (from {prop_data['original_name']})")
    
    # Extract material information if available
    try:
        from ifcopenshell.util import element
        materials = element.get_materials(element)
        if materials:
            print("\nMATERIALS:")
            for material in materials:
                if hasattr(material, "Name"):
                    mat_name = material.Name
                    # Get material properties
                    mat_props = enrichment.extract_material_properties(material)
                    print(f"  - {mat_name}:")
                    if "category" in mat_props:
                        print(f"    Category: {mat_props['category']}")
                    if "properties" in mat_props and mat_props["properties"]:
                        print("    Properties:")
                        for prop_name, prop_data in mat_props["properties"].items():
                            print(f"      - {prop_name}: {prop_data['value']}")
    except Exception as e:
        logger.warning(f"Error extracting materials: {e}")
        
    print("-" * 80)


def store_enriched_element_in_neo4j(element, enrichment, parser, mapper):
    """Store enriched element data in Neo4j."""
    try:
        # Extract element attributes
        attributes = parser.get_element_attributes(element)
        
        # Apply domain enrichment
        system_classifications = enrichment.classify_building_systems(element)
        if system_classifications:
            attributes["BuildingSystems"] = system_classifications
        
        semantic_tags = enrichment.generate_semantic_tags(element)
        if semantic_tags:
            attributes["SemanticTags"] = semantic_tags
        
        performance_props = enrichment.extract_performance_properties(element)
        if performance_props:
            attributes["PerformanceProperties"] = performance_props
        
        mapped_props = enrichment.apply_custom_property_mapping(element)
        if mapped_props:
            attributes["MappedProperties"] = mapped_props
        
        # Create node for element
        element_id = mapper.create_node_from_element(attributes)
        
        if element_id:
            logger.info(f"Created enriched node for {element.is_a()} (GlobalId: {element_id})")
            
            # Process property sets
            property_sets = parser.get_property_sets(element)
            if property_sets:
                for pset_name, pset_data in property_sets.items():
                    pset = {
                        "name": pset_name,
                        "properties": pset_data
                    }
                    pset_id = mapper.create_property_set(pset, element_id)
                    if pset_id:
                        logger.info(f"  - Added property set {pset_name}")
            
            # Process materials
            materials = parser.extract_material_info(element)
            if materials:
                for material in materials:
                    material_name = material.get("name")
                    if material_name:
                        # Enrich material with additional properties
                        material_obj = parser.file.by_id(material.get("id"))
                        material_props = enrichment.extract_material_properties(material_obj)
                        if material_props:
                            # Merge properties with original material data
                            material.update(material_props)
                    
                    material_id = mapper.create_material(material, element_id)
                    if material_id:
                        logger.info(f"  - Added material {material_name}")
            
            return element_id
        else:
            logger.warning(f"Failed to create node for {element.is_a()}")
            return None
    
    except Exception as e:
        logger.error(f"Error storing enriched element: {str(e)}")
        return None


def main():
    """Main function."""
    args = parse_args()
    
    # Verify IFC file exists
    if not os.path.exists(args.ifc_file):
        logger.error(f"IFC file not found: {args.ifc_file}")
        sys.exit(1)
    
    try:
        # Initialize the IFC parser
        logger.info(f"Loading IFC file: {args.ifc_file}")
        parser = IfcParser(args.ifc_file)
        
        # Initialize domain enrichment
        logger.info("Initializing domain enrichment")
        enrichment = DomainEnrichment(parser.file)
        
        # Get elements to process
        if args.element_type:
            elements = parser.get_elements(args.element_type)
            logger.info(f"Found {len(elements)} elements of type {args.element_type}")
        else:
            elements = parser.get_elements()
            logger.info(f"Found {len(elements)} elements in total")
        
        # Limit elements if requested
        if args.limit and args.limit < len(elements):
            elements = elements[:args.limit]
            logger.info(f"Processing {len(elements)} elements (limited by --limit)")
        
        # Neo4j connection setup if needed
        if args.example_mode in ["neo4j", "both"]:
            logger.info(f"Connecting to Neo4j at {args.neo4j_uri}")
            connector = Neo4jConnector(
                uri=args.neo4j_uri,
                username=args.neo4j_user,
                password=args.neo4j_password
            )
            
            if not connector.test_connection():
                logger.error("Failed to connect to Neo4j database")
                sys.exit(1)
            
            mapper = IfcToGraphMapper(connector)
        else:
            connector = None
            mapper = None
        
        # Process each element
        processed_count = 0
        enriched_count = 0
        
        for element in elements:
            # Skip elements without GlobalId
            if not hasattr(element, "GlobalId"):
                continue
            
            # Print to console if requested
            if args.example_mode in ["print", "both"]:
                print_element_enrichment(element, enrichment)
            
            # Store in Neo4j if requested
            if args.example_mode in ["neo4j", "both"]:
                element_id = store_enriched_element_in_neo4j(element, enrichment, parser, mapper)
                if element_id:
                    enriched_count += 1
            
            processed_count += 1
        
        # Print summary
        logger.info(f"Processed {processed_count} elements")
        
        if args.example_mode in ["neo4j", "both"]:
            logger.info(f"Stored {enriched_count} enriched elements in Neo4j")
            connector.close()
    
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main() 