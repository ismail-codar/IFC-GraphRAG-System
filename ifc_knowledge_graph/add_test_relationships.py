#!/usr/bin/env python3
"""
Add Test Topological Relationships

This script adds test topological relationships to demonstrate what should appear in the Neo4j graph.
"""

import logging
from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    """Add test topological relationships to the database."""
    try:
        # Connect to Neo4j
        conn = Neo4jConnector('neo4j://localhost:7687', 'neo4j', 'test1234')
        
        # 1. Add ADJACENT_TO relationships between walls
        logger.info("Adding test ADJACENT_TO relationships between walls...")
        wall_adjacent_query = """
        MATCH (w1:Wall)
        MATCH (w2:Wall)
        WHERE w1 <> w2
        WITH w1, w2 LIMIT 10 
        MERGE (w1)-[r:ADJACENT_TO {relationshipSource: 'topologicalAnalysis'}]->(w2) 
        RETURN count(r) as created
        """
        result = conn.run_query(wall_adjacent_query)
        logger.info(f"Created {result[0]['created']} wall adjacency relationships")
        
        # 2. Add BOUNDS_SPACE relationships between storey and walls
        # Since we don't have IfcSpace nodes, we'll use IfcBuildingStorey instead
        logger.info("Adding test BOUNDS_SPACE relationships between storeys and walls...")
        bounds_query = """
        MATCH (s:IfcBuildingStorey)
        MATCH (w:Wall)
        WITH s, w LIMIT 10 
        MERGE (w)-[r:BOUNDS_SPACE {relationshipSource: 'topologicalAnalysis'}]->(s) 
        RETURN count(r) as created
        """
        result = conn.run_query(bounds_query)
        logger.info(f"Created {result[0]['created']} space boundary relationships")
        
        # 3. Add CONTAINS_TOPOLOGICALLY relationships between storeys and elements
        logger.info("Adding test CONTAINS_TOPOLOGICALLY relationships...")
        contains_query = """
        MATCH (s:IfcBuildingStorey)
        MATCH (e:Element) 
        WHERE NOT (e:Wall)
        WITH s, e LIMIT 10 
        MERGE (s)-[r:CONTAINS_TOPOLOGICALLY {relationshipSource: 'topologicalAnalysis'}]->(e) 
        RETURN count(r) as created
        """
        result = conn.run_query(contains_query)
        logger.info(f"Created {result[0]['created']} containment relationships")
        
        # 4. Add CONNECTS_SPACES relationships for doors (between storeys)
        logger.info("Adding test CONNECTS_SPACES relationships for doors...")
        connects_query = """
        MATCH (s1:IfcBuildingStorey)
        MATCH (s2:IfcBuildingStorey)
        MATCH (d:Door)
        WHERE s1 <> s2
        WITH s1, s2, d LIMIT 5 
        MERGE (d)-[r1:CONNECTS_SPACES {relationshipSource: 'topologicalAnalysis'}]->(s1) 
        MERGE (d)-[r2:CONNECTS_SPACES {relationshipSource: 'topologicalAnalysis'}]->(s2) 
        RETURN count(r1) + count(r2) as created
        """
        result = conn.run_query(connects_query)
        logger.info(f"Created {result[0]['created']} door connection relationships")
            
        # 5. Add window-to-wall relationship
        logger.info("Adding test IS_CONTAINED_IN relationships for windows...")
        window_query = """
        MATCH (w:Window)
        MATCH (wall:Wall)
        WITH w, wall LIMIT 10
        MERGE (w)-[r:IS_CONTAINED_IN {relationshipSource: 'topologicalAnalysis'}]->(wall)
        RETURN count(r) as created
        """
        result = conn.run_query(window_query)
        logger.info(f"Created {result[0]['created']} window containment relationships")
        
        # Verify all topological relationships
        logger.info("Verifying all topological relationships...")
        verify_query = """
        MATCH ()-[r]->() 
        WHERE r.relationshipSource = 'topologicalAnalysis' 
        RETURN type(r) as type, count(r) as count 
        ORDER BY count DESC
        """
        result = conn.run_query(verify_query)
        
        logger.info("Topological relationships in the database:")
        for rel in result:
            logger.info(f"  - {rel['type']}: {rel['count']} relationships")
        
        conn.close()
        logger.info("Done!")
        
    except Exception as e:
        logger.error(f"Error adding test relationships: {e}")

if __name__ == "__main__":
    main() 