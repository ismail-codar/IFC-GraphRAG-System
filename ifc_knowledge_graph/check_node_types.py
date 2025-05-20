#!/usr/bin/env python3
"""
Check Node Types in Neo4j

This script checks what node types exist in the Neo4j database.
"""

import logging
from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    """Check node types in the Neo4j database."""
    try:
        # Connect to Neo4j
        conn = Neo4jConnector('neo4j://localhost:7687', 'neo4j', 'test1234')
        
        # Get a count of node types
        logger.info("Checking node types in the database...")
        node_query = """
        MATCH (n) 
        RETURN labels(n) as labels, count(*) as count 
        ORDER BY count DESC
        """
        result = conn.run_query(node_query)
        
        logger.info("Node types in the database:")
        for node in result:
            logger.info(f"  - {node['labels']}: {node['count']} nodes")
        
        # Check if Element nodes exist
        logger.info("\nChecking for Element nodes...")
        element_query = """
        MATCH (e:Element) 
        RETURN count(e) as count
        """
        result = conn.run_query(element_query)
        element_count = result[0]['count'] if result else 0
        logger.info(f"Found {element_count} Element nodes")
        
        # Check for different IFC types
        logger.info("\nChecking IFC types...")
        ifc_type_query = """
        MATCH (n) 
        WHERE n.IFCType IS NOT NULL 
        RETURN n.IFCType as type, count(*) as count 
        ORDER BY count DESC
        """
        result = conn.run_query(ifc_type_query)
        
        logger.info("IFC types in the database:")
        for ifc_type in result:
            logger.info(f"  - {ifc_type['type']}: {ifc_type['count']} nodes")
            
        # Check specifically for IfcWall and IfcSpace nodes
        logger.info("\nChecking for specific IFC types...")
        
        # Check wall elements (by Element label with IFCType)
        wall_query = """
        MATCH (w:Element {IFCType: 'IfcWall'}) 
        RETURN count(w) as count
        """
        result = conn.run_query(wall_query)
        wall_count = result[0]['count'] if result else 0
        logger.info(f"Found {wall_count} Element nodes with IFCType='IfcWall'")
        
        # Check wall elements (by Wall label)
        wall_label_query = """
        MATCH (w:Wall) 
        RETURN count(w) as count
        """
        result = conn.run_query(wall_label_query)
        wall_label_count = result[0]['count'] if result else 0
        logger.info(f"Found {wall_label_count} Wall labeled nodes")
        
        # Check space elements (by IfcSpace label)
        space_query = """
        MATCH (s:IfcSpace) 
        RETURN count(s) as count
        """
        result = conn.run_query(space_query)
        space_count = result[0]['count'] if result else 0
        logger.info(f"Found {space_count} IfcSpace nodes")
        
        # Check space elements (by Element label with IFCType)
        space_element_query = """
        MATCH (s:Element {IFCType: 'IfcSpace'}) 
        RETURN count(s) as count
        """
        result = conn.run_query(space_element_query)
        space_element_count = result[0]['count'] if result else 0
        logger.info(f"Found {space_element_count} Element nodes with IFCType='IfcSpace'")
        
        # Sample some actual nodes to see how they are structured
        logger.info("\nSampling some nodes to check structure...")
        sample_query = """
        MATCH (n) 
        WHERE n.IFCType = 'IfcWall' OR n.IFCType = 'IfcSpace' OR labels(n) CONTAINS 'IfcSpace' OR labels(n) CONTAINS 'Wall'
        RETURN labels(n) as labels, n.GlobalId as id, n.IFCType as type, n.Name as name 
        LIMIT 5
        """
        result = conn.run_query(sample_query)
        
        logger.info("Sample nodes:")
        for node in result:
            logger.info(f"  - Labels: {node['labels']}, ID: {node['id']}, IFCType: {node['type']}, Name: {node['name']}")
        
        conn.close()
        logger.info("Done!")
        
    except Exception as e:
        logger.error(f"Error checking node types: {e}")

if __name__ == "__main__":
    main() 