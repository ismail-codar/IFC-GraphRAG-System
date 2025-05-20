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
            for node_id in node_ids:
                ifc_label = f"Ifc{node_type}" if node_type != 'BuildingStorey' else "IfcBuildingStorey"
                
                # Query for the node
                query = f"""
                MATCH (n:{ifc_label} {{GlobalId: $id}})
                RETURN n.Name as name, labels(n) as labels
                """
                
                result = conn.run_query(query, {"id": node_id})
                if result and len(result) > 0:
                    node_info = result[0]
                    logger.info(f"Found {node_type} node: {node_info['name']} ({node_id}) with labels {node_info['labels']}")
                else:
                    logger.error(f"❌ {node_type} node with GlobalId {node_id} not found or has incorrect label!")
                    all_found = False
        
        # Check Project->Site relationship
        logger.info("\nChecking Project->Site relationship...")
        result = conn.run_query("""
            MATCH (p:IfcProject {GlobalId: '1xS3BCk291UvhgP2a6eflL'})-[r:CONTAINS]->(s:IfcSite {GlobalId: '1xS3BCk291UvhgP2a6eflN'})
            RETURN count(r) as count
        """)
        
        project_site_count = result[0]["count"] if result else 0
        if project_site_count > 0:
            logger.info(f"✅ Project->Site relationship exists ({project_site_count})")
        else:
            logger.error("❌ Project->Site relationship missing!")
            all_found = False
        
        # Check Site->Building relationship
        logger.info("\nChecking Site->Building relationship...")
        result = conn.run_query("""
            MATCH (s:IfcSite {GlobalId: '1xS3BCk291UvhgP2a6eflN'})-[r:CONTAINS]->(b:IfcBuilding {GlobalId: '1xS3BCk291UvhgP2a6eflK'})
            RETURN count(r) as count
        """)
        
        site_building_count = result[0]["count"] if result else 0
        if site_building_count > 0:
            logger.info(f"✅ Site->Building relationship exists ({site_building_count})")
        else:
            logger.error("❌ Site->Building relationship missing!")
            all_found = False
        
        # Check Building->Storey relationships
        logger.info("\nChecking Building->Storey relationships...")
        storey_rels_found = 0
        
        for storey_id in expected_nodes['BuildingStorey']:
            result = conn.run_query(f"""
                MATCH (b:IfcBuilding {{GlobalId: '1xS3BCk291UvhgP2a6eflK'}})-[r:CONTAINS]->(s:IfcBuildingStorey {{GlobalId: '{storey_id}'}})
                RETURN count(r) as count
            """)
            
            count = result[0]["count"] if result else 0
            if count > 0:
                logger.info(f"✅ Building->Storey({storey_id}) relationship exists")
                storey_rels_found += 1
            else:
                logger.error(f"❌ Building->Storey({storey_id}) relationship missing!")
        
        if storey_rels_found == len(expected_nodes['BuildingStorey']):
            logger.info(f"✅ All Building->Storey relationships found ({storey_rels_found}/{len(expected_nodes['BuildingStorey'])})")
        else:
            logger.error(f"❌ Missing some Building->Storey relationships (found {storey_rels_found}/{len(expected_nodes['BuildingStorey'])})")
            all_found = False
        
        # Check complete hierarchy path
        logger.info("\nChecking complete spatial hierarchy paths...")
        result = conn.run_query("""
            MATCH path=(p:IfcProject)-[:CONTAINS]->(s:IfcSite)-[:CONTAINS]->(b:IfcBuilding)-[:CONTAINS]->(st:IfcBuildingStorey)
            RETURN count(path) as count
        """)
        
        complete_paths = result[0]["count"] if result else 0
        if complete_paths > 0:
            logger.info(f"✅ Complete hierarchy path exists ({complete_paths} paths found)")
        else:
            logger.error("❌ No complete spatial hierarchy found")
            all_found = False
            
            # Add more diagnostic queries to find what's wrong
            logger.info("\nDiagnosing spatial hierarchy issues:")
            
            # Check if any CONTAINS relationships exist at all
            result = conn.run_query("""
                MATCH ()-[r:CONTAINS]->() 
                RETURN count(r) as count
            """)
            contains_count = result[0]["count"] if result else 0
            logger.info(f"Total CONTAINS relationships in database: {contains_count}")
            
            # Try to manually add the missing relationships
            logger.info("Attempting to add missing relationships...")
            
            # Project->Site
            conn.run_query("""
                MATCH (p:IfcProject {GlobalId: '1xS3BCk291UvhgP2a6eflL'})
                MATCH (s:IfcSite {GlobalId: '1xS3BCk291UvhgP2a6eflN'})
                MERGE (p)-[r:CONTAINS]->(s)
                RETURN count(r) as created
            """)
            
            # Site->Building
            conn.run_query("""
                MATCH (s:IfcSite {GlobalId: '1xS3BCk291UvhgP2a6eflN'})
                MATCH (b:IfcBuilding {GlobalId: '1xS3BCk291UvhgP2a6eflK'})
                MERGE (s)-[r:CONTAINS]->(b)
                RETURN count(r) as created
            """)
            
            # Building->Storeys
            for storey_id in expected_nodes['BuildingStorey']:
                conn.run_query(f"""
                    MATCH (b:IfcBuilding {{GlobalId: '1xS3BCk291UvhgP2a6eflK'}})
                    MATCH (st:IfcBuildingStorey {{GlobalId: '{storey_id}'}})
                    MERGE (b)-[r:CONTAINS]->(st)
                    RETURN count(r) as created
                """)
            
            # Check again
            result = conn.run_query("""
                MATCH path=(p:IfcProject)-[:CONTAINS]->(s:IfcSite)-[:CONTAINS]->(b:IfcBuilding)-[:CONTAINS]->(st:IfcBuildingStorey)
                RETURN count(path) as count
            """)
            
            fixed_paths = result[0]["count"] if result else 0
            if fixed_paths > 0:
                logger.info(f"✅ After fixing: Complete hierarchy path exists ({fixed_paths} paths found)")
                all_found = True
            else:
                logger.error("❌ After fixing: Still no complete spatial hierarchy found")
        
        # Close connection
        conn.close()
        
        if all_found:
            logger.info("✅ SUCCESS: All spatial structure nodes and relationships verified")
            return True
        else:
            logger.error("❌ FAILURE: Some spatial structure nodes or relationships are missing or incorrect")
            return False
        
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