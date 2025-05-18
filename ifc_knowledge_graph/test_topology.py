#!/usr/bin/env python
"""
Topology Analysis Test Script

This script tests the topological analysis functionality on an IFC model.
"""

import os
import logging
import sys
import json
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the package to the path
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

# Import required modules
from src.ifc_to_graph.parser.ifc_parser import IfcParser
from src.ifc_to_graph.topology.topologic_analyzer import TopologicAnalyzer

def main():
    """Main entry point for the topology test."""
    try:
        # Check if the IFC file path is provided as an argument
        if len(sys.argv) > 1:
            ifc_path = sys.argv[1]
        else:
            # Default IFC file path (adjust as needed)
            ifc_path = os.path.join(current_dir, "examples", "model.ifc")
        
        # Check if the file exists
        if not os.path.isfile(ifc_path):
            logger.error(f"IFC file not found: {ifc_path}")
            return 1
        
        logger.info(f"Analyzing IFC file: {ifc_path}")
        
        # Initialize the IFC parser
        ifc_parser = IfcParser(ifc_path)
        
        # Initialize the topological analyzer
        analyzer = TopologicAnalyzer(ifc_parser)
        
        # Get all elements
        elements = ifc_parser.get_elements()
        
        # Print summary of elements
        logger.info(f"Found {len(elements)} elements in the IFC model")
        
        # Convert some elements to topologic entities
        converted_count = 0
        for element in elements[:10]:  # Process first 10 elements for demo
            if hasattr(element, "GlobalId"):
                logger.info(f"Converting element {element.GlobalId} of type {element.is_a()}")
                topologic_entity = analyzer.convert_ifc_to_topologic(element)
                if topologic_entity:
                    converted_count += 1
                    logger.info(f"  Converted to topologic entity: {type(topologic_entity).__name__}")
                else:
                    logger.warning(f"  Failed to convert element {element.GlobalId}")
        
        logger.info(f"Converted {converted_count} elements to topologic entities")
        
        # Extract adjacency relationships
        logger.info("Extracting adjacency relationships...")
        adjacency_map = analyzer.get_adjacency_relationships()
        
        # Print adjacency relationships
        adjacency_count = sum(len(adjacents) for adjacents in adjacency_map.values())
        logger.info(f"Found {adjacency_count} adjacency relationships")
        
        # Print some examples of adjacency relationships
        for i, (element_id, adjacent_ids) in enumerate(adjacency_map.items()):
            if adjacent_ids:
                element = ifc_parser.get_element_by_id(element_id)
                element_type = element.is_a() if element else "Unknown"
                logger.info(f"Element {element_id} ({element_type}) is adjacent to {len(adjacent_ids)} elements:")
                
                for adjacent_id in adjacent_ids[:3]:  # Show max 3 adjacencies per element
                    adjacent_element = ifc_parser.get_element_by_id(adjacent_id)
                    adjacent_type = adjacent_element.is_a() if adjacent_element else "Unknown"
                    logger.info(f"  - Adjacent to {adjacent_id} ({adjacent_type})")
                
                # Only show 5 elements with adjacencies
                if i >= 4:
                    break
        
        # Extract containment relationships
        logger.info("Extracting containment relationships...")
        containment_map = analyzer.get_containment_relationships()
        
        # Print containment relationships
        containment_count = sum(len(contained) for contained in containment_map.values())
        logger.info(f"Found {containment_count} containment relationships")
        
        # Print some examples of containment relationships
        for i, (container_id, contained_ids) in enumerate(containment_map.items()):
            if contained_ids:
                container = ifc_parser.get_element_by_id(container_id)
                container_type = container.is_a() if container else "Unknown"
                logger.info(f"Element {container_id} ({container_type}) contains {len(contained_ids)} elements:")
                
                for contained_id in contained_ids[:3]:  # Show max 3 contained elements
                    contained_element = ifc_parser.get_element_by_id(contained_id)
                    contained_type = contained_element.is_a() if contained_element else "Unknown"
                    logger.info(f"  - Contains {contained_id} ({contained_type})")
                
                # Only show 5 elements with containment
                if i >= 4:
                    break
        
        # Extract space boundaries
        logger.info("Extracting space boundary relationships...")
        space_boundaries = analyzer.get_space_boundaries()
        
        # Print space boundary relationships
        space_boundary_count = sum(len(boundaries) for boundaries in space_boundaries.values())
        logger.info(f"Found {space_boundary_count} space boundary relationships")
        
        # Print some examples of space boundary relationships
        for i, (space_id, boundary_ids) in enumerate(space_boundaries.items()):
            if boundary_ids:
                space = ifc_parser.get_element_by_id(space_id)
                space_name = space.Name if space and hasattr(space, "Name") else "Unnamed"
                logger.info(f"Space {space_id} ({space_name}) has {len(boundary_ids)} boundary elements:")
                
                for boundary_id in boundary_ids[:3]:  # Show max 3 boundaries per space
                    boundary = ifc_parser.get_element_by_id(boundary_id)
                    boundary_type = boundary.is_a() if boundary else "Unknown"
                    logger.info(f"  - Bounded by {boundary_id} ({boundary_type})")
                
                # Only show 5 spaces with boundaries
                if i >= 4:
                    break
        
        # Extract connectivity graph
        logger.info("Generating connectivity graph...")
        connectivity_graph = analyzer.get_connectivity_graph()
        
        # Print connectivity graph information
        element_count = len(connectivity_graph)
        logger.info(f"Connectivity graph contains {element_count} elements")
        
        # Print some examples of connectivity relationships
        element_count = 0
        for element_id, connections in connectivity_graph.items():
            total_connections = sum(len(connections[rel_type]) for rel_type in connections)
            
            if total_connections > 0:
                element = ifc_parser.get_element_by_id(element_id)
                element_type = element.is_a() if element else "Unknown"
                element_name = element.Name if element and hasattr(element, "Name") else "Unnamed"
                
                logger.info(f"Element {element_id} ({element_type}: {element_name}) has {total_connections} connections:")
                
                # Print some connection details
                for rel_type in ["adjacent", "contains", "contained_by", "bounds_space", "bounded_by"]:
                    if connections[rel_type]:
                        logger.info(f"  - {rel_type.replace('_', ' ').title()}: {len(connections[rel_type])} connections")
                        
                        # Show max 2 connections per type
                        for i, connection in enumerate(connections[rel_type][:2]):
                            connected_element = ifc_parser.get_element_by_id(connection["id"])
                            connected_name = connected_element.Name if connected_element and hasattr(connected_element, "Name") else "Unnamed"
                            logger.info(f"    - {connection['type']}: {connected_name} ({connection['id']})")
                
                # Only show 5 elements
                element_count += 1
                if element_count >= 5:
                    break
        
        # Test path finding
        logger.info("Testing path finding functionality...")
        
        # Try to find a path between two arbitrary elements
        # First find some suitable elements
        space_ids = []
        wall_ids = []
        
        for element_id, element in connectivity_graph.items():
            element_obj = ifc_parser.get_element_by_id(element_id)
            if not element_obj:
                continue
                
            if element_obj.is_a("IfcSpace"):
                space_ids.append(element_id)
            elif element_obj.is_a("IfcWall"):
                wall_ids.append(element_id)
        
        # Try to find a path between spaces or walls
        if len(space_ids) >= 2:
            start_id = space_ids[0]
            end_id = space_ids[-1]
            
            logger.info(f"Finding path between spaces {start_id} and {end_id}")
            path = analyzer.find_path(start_id, end_id)
            
            if path:
                logger.info(f"Found path with {len(path)} elements:")
                for i, node in enumerate(path):
                    element = ifc_parser.get_element_by_id(node["id"])
                    element_name = element.Name if element and hasattr(element, "Name") else "Unnamed"
                    
                    if i < len(path) - 1:
                        logger.info(f"  {i+1}. {node['type']} ({element_name}) -> {node['connection']} -> {node['to']['type']}")
                    else:
                        logger.info(f"  {i+1}. {node['type']} ({element_name})")
            else:
                logger.warning(f"No path found between spaces {start_id} and {end_id}")
        elif len(wall_ids) >= 2:
            start_id = wall_ids[0]
            end_id = wall_ids[-1]
            
            logger.info(f"Finding path between walls {start_id} and {end_id}")
            path = analyzer.find_path(start_id, end_id)
            
            if path:
                logger.info(f"Found path with {len(path)} elements:")
                for i, node in enumerate(path):
                    element = ifc_parser.get_element_by_id(node["id"])
                    element_name = element.Name if element and hasattr(element, "Name") else "Unnamed"
                    
                    if i < len(path) - 1:
                        logger.info(f"  {i+1}. {node['type']} ({element_name}) -> {node['connection']} -> {node['to']['type']}")
                    else:
                        logger.info(f"  {i+1}. {node['type']} ({element_name})")
            else:
                logger.warning(f"No path found between walls {start_id} and {end_id}")
        
        # Perform full topological analysis
        logger.info("Performing full topological analysis...")
        analysis_results = analyzer.analyze_building_topology()
        
        # Print analysis summary
        adjacency_count = sum(len(adjacents) for adjacents in analysis_results["adjacency"].values())
        containment_count = sum(len(contained) for contained in analysis_results["containment"].values())
        space_boundary_count = sum(len(boundaries) for boundaries in analysis_results["space_boundaries"].values())
        connectivity_count = len(analysis_results["connectivity"])
        
        logger.info(f"Analysis complete: {adjacency_count} adjacency relationships, " + 
                    f"{containment_count} containment relationships, " +
                    f"{space_boundary_count} space boundary relationships, " +
                    f"{connectivity_count} elements in connectivity graph")
        
        # Save analysis results to file
        output_dir = os.path.join(current_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "topology_analysis.json")
        
        # Convert the analysis results to a serializable format (remove topologic entities)
        serializable_results = {
            "adjacency": analysis_results["adjacency"],
            "containment": analysis_results["containment"],
            "space_boundaries": analysis_results["space_boundaries"],
            "connectivity": analysis_results["connectivity"]
        }
        
        with open(output_file, "w") as f:
            json.dump(serializable_results, f, indent=2)
            
        logger.info(f"Analysis results saved to {output_file}")
        
        logger.info("Topology analysis completed successfully")
        return 0
        
    except Exception as e:
        logger.exception(f"Error in topology analysis: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 