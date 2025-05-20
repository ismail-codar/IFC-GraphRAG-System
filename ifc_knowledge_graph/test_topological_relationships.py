#!/usr/bin/env python3
"""
Test Topological Relationships

This script tests the topological analysis capabilities by:
1. Checking if TopologicPy is available
2. Creating topological relationships in an existing graph
3. Verifying that they were created correctly
"""

import logging
import os
import sys
import time
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import required modules
from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector
from src.ifc_to_graph.database.schema import RelationshipTypes
from src.ifc_to_graph.topology.topologic_analyzer import TopologicAnalyzer, TOPOLOGICPY_AVAILABLE

# Database connection settings
NEO4J_URI = "neo4j://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "test1234"

def check_topologicpy():
    """Check if TopologicPy is available and correctly installed."""
    logger.info("Checking TopologicPy availability...")
    if TOPOLOGICPY_AVAILABLE:
        logger.info("✓ TopologicPy is available")
        return True
    else:
        logger.error("✗ TopologicPy is not available. Please install it with: pip install topologicpy")
        return False

def check_existing_relationships():
    """Check existing relationship types in the database."""
    logger.info("Checking existing relationships in the database...")
    
    try:
        connector = Neo4jConnector(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
        
        # Get existing relationship types and counts
        query = """
        MATCH ()-[r]->() 
        RETURN type(r) as type, count(r) as count, 
               sum(CASE WHEN r.relationshipSource = 'topologicalAnalysis' THEN 1 ELSE 0 END) as topo_count
        ORDER BY count DESC
        """
        rel_types = connector.run_query(query)
        
        if not rel_types:
            logger.info("No relationships found in the database.")
            connector.close()
            return {}
        
        logger.info("Current relationship types in the database:")
        rel_counts = {}
        for rel in rel_types:
            rel_type = rel.get('type')
            rel_count = rel.get('count', 0)
            topo_count = rel.get('topo_count', 0)
            rel_counts[rel_type] = {
                'total': rel_count,
                'topological': topo_count
            }
            logger.info(f"  - {rel_type}: {rel_count} total, {topo_count} topological")
        
        connector.close()
        return rel_counts
        
    except Exception as e:
        logger.error(f"Error checking existing relationships: {e}")
        return {}

def force_enable_topological_analysis():
    """
    Enable topological analysis by directly modifying the database.
    This is useful if the original import did not have topology enabled.
    
    This approach uses the existing IFC elements and analyzes them for topological relationships.
    """
    logger.info("Enabling topological analysis...")
    
    try:
        # Connect to the database
        connector = Neo4jConnector(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
        
        # First, get the IFC file path from the database if available
        try:
            query = """
            MATCH (p:IfcProject) 
            RETURN p.sourcePath as ifc_path 
            LIMIT 1
            """
            result = connector.run_query(query)
            ifc_path = result[0].get('ifc_path') if result else None
            
            if not ifc_path:
                logger.warning("Could not find IFC file path in the database. Using default test file.")
                ifc_path = os.path.join("tests", "files", "test_model.ifc")  # Default fallback
                
            if not os.path.exists(ifc_path):
                logger.warning(f"IFC file not found at {ifc_path}. Seeking alternative paths...")
                # Try looking for IFC files in the project directory
                ifc_files = []
                for root, _, files in os.walk("."):
                    ifc_files.extend([os.path.join(root, f) for f in files if f.lower().endswith('.ifc')])
                
                if ifc_files:
                    ifc_path = ifc_files[0]
                    logger.info(f"Found alternative IFC file: {ifc_path}")
                else:
                    logger.error("No IFC files found. Cannot proceed with topological analysis.")
                    return 0
        except Exception as e:
            logger.error(f"Error finding IFC file path: {e}")
            return 0
        
        # Retrieve all relevant IFC elements
        logger.info("Retrieving IFC elements from the database...")
        query = """
        MATCH (e) 
        WHERE e.GlobalId IS NOT NULL AND e.IFCType IN [
          'IfcWall', 'IfcSlab', 'IfcColumn', 'IfcBeam', 'IfcWindow', 'IfcDoor', 
          'IfcSpace', 'IfcBuildingStorey', 'IfcBuilding', 'IfcSite', 'IfcWallStandardCase',
          'IfcRoof', 'IfcStair', 'IfcOpeningElement'
        ]
        RETURN e.GlobalId as id, e.IFCType as type
        """
        elements = connector.run_query(query)
        
        if not elements:
            logger.warning("No relevant IFC elements found in the database.")
            return 0
        
        logger.info(f"Found {len(elements)} elements for topological analysis.")
        
        # Initialize the TopologicAnalyzer
        import ifcopenshell
        ifc_file = ifcopenshell.open(ifc_path)
        
        # Get elements from the IFC file with GlobalId matching database elements
        elements_dict = {}
        # Handle IFC elements for IFC2X3 schema - IfcElement is common across schemas
        for ifc_element in ifc_file.by_type("IfcElement"):
            if hasattr(ifc_element, "GlobalId"):
                elements_dict[ifc_element.GlobalId] = ifc_element
        
        # Get spatial structure elements (different naming in IFC2X3)
        for entity_type in ["IfcSpatialStructureElement", "IfcSpace", "IfcBuilding", "IfcBuildingStorey", "IfcSite", "IfcProject"]:
            try:
                for ifc_element in ifc_file.by_type(entity_type):
                    if hasattr(ifc_element, "GlobalId"):
                        elements_dict[ifc_element.GlobalId] = ifc_element
            except Exception as e:
                logger.debug(f"Could not get elements of type {entity_type}: {e}")
                
        logger.info(f"Found {len(elements_dict)} elements in the IFC file.")
        
        # Filter to only elements that exist in both the database and IFC file
        db_element_ids = {element.get('id') for element in elements}
        common_elements = {
            guid: element for guid, element in elements_dict.items()
            if guid in db_element_ids
        }
        
        logger.info(f"Found {len(common_elements)} elements in both DB and IFC file.")
        
        if not common_elements:
            logger.error("No matching elements found between database and IFC file.")
            return 0
        
        # Initialize the TopologicAnalyzer with the IFC file
        analyzer = TopologicAnalyzer(ifc_file)
        analyzer.set_ifc_parser(ifc_file)  # Make sure the parser is set
        
        # Analyze the common elements
        start_time = time.time()
        logger.info("Running topological analysis...")
        relationships = analyzer.analyze_elements(common_elements)
        elapsed = time.time() - start_time
        
        logger.info(f"Completed analysis in {elapsed:.2f} seconds.")
        logger.info(f"Found {len(relationships)} topological relationships.")
        
        # Add the relationships to the database
        if relationships:
            # Group relationships by type
            rel_by_type = {}
            for rel in relationships:
                rel_type = rel.get('relationship_type', 'UNKNOWN')
                if rel_type not in rel_by_type:
                    rel_by_type[rel_type] = 0
                rel_by_type[rel_type] += 1
            
            # Log relationship types found
            logger.info("Relationship types found:")
            for rel_type, count in rel_by_type.items():
                logger.info(f"  - {rel_type}: {count}")
            
            # Create batches of relationships
            batch_size = 500
            rel_batches = [relationships[i:i+batch_size] for i in range(0, len(relationships), batch_size)]
            
            # Process each batch
            total_created = 0
            for i, batch in enumerate(rel_batches):
                logger.info(f"Processing batch {i+1}/{len(rel_batches)} with {len(batch)} relationships...")
                
                # Generate Cypher for batch
                queries = []
                for rel in batch:
                    source_id = rel.get('source_id')
                    target_id = rel.get('target_id')
                    rel_type = rel.get('relationship_type')
                    
                    # Skip if missing required data
                    if not source_id or not target_id or not rel_type:
                        continue
                    
                    # Map relationship type to Neo4j format
                    neo4j_rel_type = RelationshipTypes.from_topologic_relationship(rel_type).value
                    
                    # Create query to merge the relationship
                    query = {
                        "query": """
                        MATCH (a), (b)
                        WHERE a.GlobalId = $source_id AND b.GlobalId = $target_id
                        MERGE (a)-[r:%s]->(b)
                        ON CREATE SET r.relationshipSource = 'topologicalAnalysis',
                                      r.relationshipType = $rel_type,
                                      r.created = datetime()
                        RETURN count(r) as created
                        """ % neo4j_rel_type,
                        "parameters": {
                            "source_id": source_id,
                            "target_id": target_id,
                            "rel_type": rel_type
                        }
                    }
                    queries.append(query)
                
                # Execute batch in a transaction
                if queries:
                    try:
                        results = connector.run_transaction(queries)
                        batch_created = sum([result[0].get('created', 0) for result in results if result])
                        total_created += batch_created
                        logger.info(f"Created {batch_created} relationships in batch {i+1}")
                    except Exception as e:
                        logger.error(f"Error creating relationships batch {i+1}: {e}")
            
            logger.info(f"Successfully created {total_created} topological relationships")
            return total_created
        else:
            logger.warning("No relationships found by topological analysis.")
            return 0
            
    except Exception as e:
        logger.error(f"Error in topological analysis: {e}")
        return 0
    finally:
        if 'connector' in locals():
            connector.close()

def verify_topological_relationships():
    """Verify that topological relationships were created successfully."""
    logger.info("Verifying topological relationships...")
    
    try:
        connector = Neo4jConnector(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
        
        # Count relationships with topological source
        query = """
        MATCH ()-[r]->()
        WHERE r.relationshipSource = 'topologicalAnalysis'
        RETURN type(r) as type, count(r) as count
        ORDER BY count DESC
        """
        rel_types = connector.run_query(query)
        
        if not rel_types:
            logger.warning("No topological relationships found.")
            connector.close()
            return False
        
        logger.info("Topological relationships in the database:")
        for rel in rel_types:
            logger.info(f"  - {rel.get('type')}: {rel.get('count')} relationships")
        
        # Verify specific relationship types exist
        topo_rel_types = {rel.get('type') for rel in rel_types}
        expected_types = {
            'ADJACENT', 'ADJACENT_TO', 
            'CONTAINS', 'CONTAINS_TOPOLOGICALLY',
            'IS_CONTAINED_IN', 
            'BOUNDS_SPACE', 'IS_BOUNDED_BY'
        }
        
        # Check which expected types are found
        found_types = expected_types.intersection(topo_rel_types)
        missing_types = expected_types - topo_rel_types
        
        if missing_types:
            logger.warning(f"Missing expected relationship types: {missing_types}")
        
        if found_types:
            logger.info(f"Found expected relationship types: {found_types}")
            
        # Run detailed checks for specific relationship pattern examples
        example_queries = [
            {
                "name": "Wall-to-Wall adjacency",
                "query": """
                MATCH (w1:Element {IFCType: 'IfcWall'})-[r:ADJACENT|ADJACENT_TO]->(w2:Element {IFCType: 'IfcWall'})
                WHERE r.relationshipSource = 'topologicalAnalysis'
                RETURN COUNT(r) as count
                """
            },
            {
                "name": "Space boundaries",
                "query": """
                MATCH (s:Element {IFCType: 'IfcSpace'})-[r:IS_BOUNDED_BY|BOUNDED_BY]->(:Element)
                WHERE r.relationshipSource = 'topologicalAnalysis'
                RETURN COUNT(r) as count
                """
            },
            {
                "name": "Element containment",
                "query": """
                MATCH (s)-[r:CONTAINS|CONTAINS_TOPOLOGICALLY]->(e)
                WHERE r.relationshipSource = 'topologicalAnalysis'
                RETURN COUNT(r) as count
                """
            }
        ]
        
        example_results = {}
        for example in example_queries:
            result = connector.run_query(example["query"])
            count = result[0].get('count', 0) if result else 0
            example_results[example["name"]] = count
            logger.info(f"  - {example['name']}: {count} relationships")
        
        connector.close()
        
        # Success if we found at least some topological relationships
        return len(found_types) > 0 and sum(example_results.values()) > 0
        
    except Exception as e:
        logger.error(f"Error verifying topological relationships: {e}")
        return False

def main():
    """Main function to test topological relationships."""
    logger.info("=== Topological Relationships Test ===")
    
    # Check if TopologicPy is available
    if not check_topologicpy():
        logger.error("Cannot proceed with TopologicPy unavailable.")
        return
    
    # Check existing relationships
    existing_relationships = check_existing_relationships()
    
    # Check if topological relationships already exist
    has_topo_rels = any(
        rel_data.get('topological', 0) > 0 
        for rel_data in existing_relationships.values()
    )
    
    if has_topo_rels:
        logger.info("Database already has topological relationships. Skipping creation.")
    else:
        logger.info("No topological relationships found. Creating them...")
        created_count = force_enable_topological_analysis()
        logger.info(f"Created {created_count} topological relationships.")
    
    # Verify relationships
    success = verify_topological_relationships()
    
    # Report results
    if success:
        logger.info("✓ Topological relationships test passed!")
    else:
        logger.warning("✗ Topological relationships test failed or incomplete.")
    
    logger.info("Test completed.")

if __name__ == "__main__":
    main() 