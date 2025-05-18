#!/usr/bin/env python
"""
Script to check Neo4j database connectivity and create test nodes if needed.
"""

import logging
from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector
from src.ifc_to_graph.parser.ifc_parser import IfcParser
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Connect to Neo4j
    logger.info("Connecting to Neo4j...")
    connector = Neo4jConnector(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="test1234"
    )
    
    # Test connection
    if not connector.test_connection():
        logger.error("Neo4j connection failed")
        return
    
    logger.info("Neo4j connection successful")
    
    # Check for existing nodes
    node_count_query = "MATCH (n) RETURN COUNT(n) as count"
    result = connector.run_query(node_count_query)
    node_count = result[0]["count"] if result else 0
    
    logger.info(f"Found {node_count} nodes in the database")
    
    if node_count == 0:
        # If no nodes exist, we need to create some
        logger.info("No nodes found, creating test nodes...")
        
        # Load an IFC file to get element IDs
        ifc_file = str(Path(__file__).parent / "data" / "ifc_files" / "Duplex_A_20110907.ifc")
        parser = IfcParser(ifc_file)
        
        # Get some elements
        elements = parser.get_elements()
        logger.info(f"Loaded {len(elements)} elements from IFC file")
        
        # Create nodes for some elements
        created_count = 0
        for element in elements[:50]:  # Just create a few nodes
            if not hasattr(element, "GlobalId"):
                continue
                
            element_type = element.is_a()
            element_name = element.Name if hasattr(element, "Name") and element.Name else ""
            
            # Create Cypher query to create the node
            query = """
            CREATE (e:Element {GlobalId: $global_id, IFCType: $ifc_type, Name: $name})
            RETURN e.GlobalId
            """
            
            params = {
                "global_id": element.GlobalId,
                "ifc_type": element_type,
                "name": element_name
            }
            
            try:
                connector.run_query(query, params)
                created_count += 1
            except Exception as e:
                logger.error(f"Error creating node: {str(e)}")
                
        logger.info(f"Created {created_count} test nodes")
        
        # Check node count again
        result = connector.run_query(node_count_query)
        node_count = result[0]["count"] if result else 0
        logger.info(f"Now have {node_count} nodes in the database")

if __name__ == "__main__":
    main() 