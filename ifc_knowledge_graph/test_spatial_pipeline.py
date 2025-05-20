import logging
import time
from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector
from optimized_processor import OptimizedIfcProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clear_database():
    """Clear the Neo4j database before testing"""
    try:
        # Connect to Neo4j
        conn = Neo4jConnector('neo4j://localhost:7687', 'neo4j', 'test1234')
        
        # Clear all data
        query = "MATCH (n) DETACH DELETE n"
        conn.run_query(query)
        
        logger.info("Cleared existing data from Neo4j database")
        
        # Close connection
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        return False

def verify_spatial_structure_nodes():
    """Verify that all spatial structure nodes exist in the database with correct labels"""
    try:
        # Connect to Neo4j
        conn = Neo4jConnector('neo4j://localhost:7687', 'neo4j', 'test1234')
        
        # Expected node IDs from the IFC file
        expected_nodes = {
            'Project': ['1xS3BCk291UvhgP2a6eflL'],
            'Site': ['1xS3BCk291UvhgP2a6eflN'],
            'Building': ['1xS3BCk291UvhgP2a6eflK'],
            'BuildingStorey': [
                '1xS3BCk291UvhgP2dvNMKI',
                '1xS3BCk291UvhgP2dvNMQJ',
                '1xS3BCk291UvhgP2dvNsgp',
                '1xS3BCk291UvhgP2dvNtSE'
            ]
        }
        
        # Check each type
        all_found = True
        for node_type, node_ids in expected_nodes.items():
            # Use IFC type naming
            ifc_type = f"Ifc{node_type}"
            
            # Check for each expected ID
            for node_id in node_ids:
                query = f"""
                MATCH (n:{ifc_type} {{GlobalId: '{node_id}'}})
                RETURN n.Name as name, labels(n) as labels
                """
                
                result = conn.run_query(query)
                
                if result and len(result) > 0:
                    name = result[0].get("name", "Unnamed")
                    labels = result[0].get("labels", [])
                    logger.info(f"Found {node_type} node: {name} ({node_id}) with labels {labels}")
                else:
                    logger.error(f"Missing {node_type} node with ID {node_id}")
                    all_found = False
                    
                    # Try to find the node with any label
                    backup_query = f"""
                    MATCH (n {{GlobalId: '{node_id}'}})
                    RETURN n.Name as name, labels(n) as labels
                    """
                    
                    backup_result = conn.run_query(backup_query)
                    if backup_result and len(backup_result) > 0:
                        name = backup_result[0].get("name", "Unnamed")
                        labels = backup_result[0].get("labels", [])
                        logger.warning(f"Node exists but with wrong labels: {name} ({node_id}) has {labels}")
                    else:
                        logger.warning(f"Node doesn't exist at all: {node_id}")
        
        # Check CONTAINS relationships
        containment_query = """
        MATCH (p:IfcProject)-[r:CONTAINS]->(s:IfcSite)-[r2:CONTAINS]->(b:IfcBuilding)-[r3:CONTAINS]->(st:IfcBuildingStorey)
        RETURN p.GlobalId as projectId, s.GlobalId as siteId, b.GlobalId as buildingId, st.GlobalId as storeyId
        """
        
        result = conn.run_query(containment_query)
        
        if result and len(result) > 0:
            logger.info(f"Found {len(result)} complete spatial hierarchy paths")
            for record in result:
                logger.info(f"Project ({record['projectId']}) -> Site ({record['siteId']}) -> Building ({record['buildingId']}) -> Storey ({record['storeyId']})")
        else:
            logger.error("No complete spatial hierarchy found")
            all_found = False
        
        # Close connection
        conn.close()
        
        return all_found
        
    except Exception as e:
        logger.error(f"Error verifying spatial structure: {e}")
        return False

def run_pipeline():
    """Run the optimized IFC processor pipeline"""
    try:
        # Find IFC file
        ifc_file = "data/ifc_files/Duplex_A_20110907.ifc"
        
        # Initialize the processor
        processor = OptimizedIfcProcessor(
            ifc_file_path=ifc_file,
            neo4j_uri="neo4j://localhost:7687",
            neo4j_username="neo4j",
            neo4j_password="test1234",
            neo4j_database="neo4j",
            enable_monitoring=True,
            parallel_processing=False,
            enable_topological_analysis=False,  # Disable for this test
            batch_size=1000,
            use_cache=True
        )
        
        # Process the IFC file
        processor.process()
        
        # Close connections
        processor.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Error running pipeline: {e}")
        return False

def main():
    """Main test function"""
    logger.info("==== Starting Spatial Structure Pipeline Test ====")
    
    # Clear the database
    logger.info("Clearing database...")
    if not clear_database():
        logger.error("Failed to clear database. Aborting test.")
        return
    
    # Run the pipeline
    logger.info("Running IFC processing pipeline...")
    start_time = time.time()
    if not run_pipeline():
        logger.error("Failed to run pipeline. Aborting test.")
        return
    elapsed = time.time() - start_time
    logger.info(f"Pipeline completed in {elapsed:.2f} seconds")
    
    # Verify spatial structure
    logger.info("Verifying spatial structure nodes and relationships...")
    if verify_spatial_structure_nodes():
        logger.info("✅ SUCCESS: All spatial structure nodes and relationships verified!")
    else:
        logger.error("❌ FAILURE: Some spatial structure nodes or relationships are missing or incorrect")
    
    logger.info("==== Spatial Structure Pipeline Test Completed ====")

if __name__ == "__main__":
    main() 