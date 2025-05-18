#!/usr/bin/env python
"""
Neo4j Topology Relationship Test Script

This script tests the enhanced Neo4j schema for topological relationships
by importing topological analysis results into a Neo4j database.
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
from src.ifc_to_graph.parser.ifc_parser import IFCParser
from src.ifc_to_graph.topology.topologic_analyzer import TopologicAnalyzer
from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector
from src.ifc_to_graph.database.schema import SchemaManager
from src.ifc_to_graph.database.ifc_to_graph_mapper import IfcToGraphMapper
from src.ifc_to_graph.database.topologic_to_graph_mapper import TopologicToGraphMapper


def main():
    """Main entry point for the Neo4j topology test."""
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
        
        # Initialize the Neo4j connector
        connector = Neo4jConnector(
            uri="bolt://localhost:7687",
            user="neo4j",
            password="test1234"  # Use your actual password
        )
        
        # Initialize the schema manager and set up the enhanced schema
        schema_manager = SchemaManager(connector)
        schema_manager.setup_schema()
        
        # Initialize mappers
        ifc_mapper = IfcToGraphMapper(connector)
        topo_mapper = TopologicToGraphMapper(connector)
        
        # Initialize the IFC parser
        ifc_parser = IFCParser(ifc_path)
        
        # Initialize the topological analyzer
        analyzer = TopologicAnalyzer(ifc_parser)
        
        # First, clear the graph database (optional - comment out if you want to keep existing data)
        logger.info("Clearing the graph database...")
        ifc_mapper.clear_graph()
        
        # Import IFC elements to Neo4j
        logger.info("Importing IFC elements into Neo4j...")
        elements = ifc_parser.get_elements()
        elements_count = 0
        
        for element in elements:
            if hasattr(element, "GlobalId"):
                # Get element data
                element_data = ifc_parser.get_element_attributes(element)
                
                # Import element to Neo4j
                result = ifc_mapper.create_node_from_element(element_data)
                if result:
                    elements_count += 1
        
        logger.info(f"Imported {elements_count} IFC elements into Neo4j")
        
        # Import IFC relationships to Neo4j (basic relationships)
        logger.info("Importing IFC relationships into Neo4j...")
        relationships = ifc_parser.get_relationships()
        rel_count = 0
        
        for rel in relationships:
            if hasattr(rel, "GlobalId") and hasattr(rel, "is_a"):
                rel_type = rel.is_a()
                
                # Handle different relationship types
                if rel_type == "IfcRelContainedInSpatialStructure":
                    relating_structure = rel.RelatingStructure
                    related_elements = rel.RelatedElements
                    
                    if relating_structure and hasattr(relating_structure, "GlobalId"):
                        for element in related_elements:
                            if hasattr(element, "GlobalId"):
                                # Create containment relationship
                                success = ifc_mapper.create_relationship(
                                    relating_structure.GlobalId,
                                    element.GlobalId,
                                    rel_type
                                )
                                if success:
                                    rel_count += 1
                
                # Add other relationship types as needed
        
        logger.info(f"Imported {rel_count} IFC relationships into Neo4j")
        
        # Perform topological analysis
        logger.info("Performing topological analysis...")
        analysis_results = analyzer.analyze_building_topology()
        
        # Import topological relationships to Neo4j
        logger.info("Importing topological relationships into Neo4j...")
        import_results = topo_mapper.import_all_topological_relationships(analysis_results)
        
        logger.info(f"Imported a total of {import_results['total']} topological relationships:")
        for rel_type, count in import_results.items():
            if rel_type != 'total':
                logger.info(f"  - {rel_type}: {count} relationships")
        
        # Test topological path finding
        logger.info("Testing topological path finding...")
        
        # Find two nodes to test with
        sample_elements = connector.run_query("""
        MATCH (a:Element), (b:Element)
        WHERE a <> b
        RETURN a.GlobalId as startId, a.Name as startName, 
               b.GlobalId as endId, b.Name as endName
        LIMIT 1
        """)
        
        if sample_elements:
            start_id = sample_elements[0].get('startId')
            end_id = sample_elements[0].get('endId')
            start_name = sample_elements[0].get('startName', 'Unknown')
            end_name = sample_elements[0].get('endName', 'Unknown')
            
            logger.info(f"Finding path between {start_name} ({start_id}) and {end_name} ({end_id})")
            
            # Run path finding query
            paths = topo_mapper.run_topology_path_query(start_id, end_id)
            
            if paths:
                logger.info(f"Found {len(paths)} paths between elements")
                for i, path in enumerate(paths):
                    logger.info(f"Path {i+1} (length {path['length']}):")
                    
                    # Print the path details
                    for j in range(len(path['nodeIds'])):
                        node_id = path['nodeIds'][j]
                        node_name = path['nodeNames'][j] if j < len(path['nodeNames']) else 'Unknown'
                        
                        if j < len(path['relationshipTypes']):
                            rel_type = path['relationshipTypes'][j]
                            logger.info(f"  {j+1}. {node_name} ({node_id}) --[{rel_type}]--> ", end='')
                        else:
                            logger.info(f"  {j+1}. {node_name} ({node_id})")
            else:
                logger.info("No paths found between the elements")
        
        # Get overall graph statistics
        node_count = ifc_mapper.get_node_count()
        rel_count = ifc_mapper.get_relationship_count()
        logger.info(f"Graph database contains {node_count} nodes and {rel_count} relationships")
        
        # Run a Cypher query to count topological relationships by type
        topo_rel_counts = connector.run_query("""
        MATCH ()-[r]-()
        WHERE r.relationshipSource = 'topologicalAnalysis'
        RETURN type(r) AS relType, count(r) AS count
        ORDER BY count DESC
        """)
        
        if topo_rel_counts:
            logger.info("Topological relationship counts by type:")
            for record in topo_rel_counts:
                rel_type = record.get('relType', 'Unknown')
                count = record.get('count', 0)
                logger.info(f"  - {rel_type}: {count}")
        
        logger.info("Neo4j topology test completed successfully")
        return 0
        
    except Exception as e:
        logger.exception(f"Error in Neo4j topology test: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 