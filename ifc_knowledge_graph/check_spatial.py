import logging
from src.ifc_to_graph.parser.ifc_parser import IfcParser
from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_parser_extraction():
    """Check what the parser extracts from the IFC file"""
    # Path to the IFC file
    ifc_file_path = "data/ifc_files/Duplex_A_20110907.ifc"
    
    # Initialize the parser
    logger.info(f"Initializing IFC parser with file: {ifc_file_path}")
    parser = IfcParser(ifc_file_path)
    
    # Get the spatial structure
    spatial = parser.get_spatial_structure()
    
    # Print summary of what was found
    print(f"Project GlobalId: {spatial.get('project', {}).get('GlobalId', None)}")
    print(f"Project Name: {spatial.get('project', {}).get('Name', None)}")
    print(f"Sites count: {len(spatial.get('sites', []))}")
    print(f"Buildings count: {len(spatial.get('buildings', []))}")
    print(f"Storeys count: {len(spatial.get('storeys', []))}")
    print(f"Spaces count: {len(spatial.get('spaces', []))}")
    
    # Print first site details if available
    if spatial.get('sites'):
        site = spatial['sites'][0]
        print(f"\nFirst site details:")
        print(f"  GlobalId: {site.get('GlobalId')}")
        print(f"  Name: {site.get('Name')}")
        print(f"  Buildings: {len(site.get('Buildings', []))}")

def check_database_content():
    """Check what's actually in the Neo4j database"""
    try:
        # Connect to Neo4j
        conn = Neo4jConnector('neo4j://localhost:7687', 'neo4j', 'test1234')
        
        # Query for spatial structure nodes
        query = """
        MATCH (n)
        WHERE any(label IN labels(n) WHERE label IN ['IfcProject', 'IfcSite', 'IfcBuilding', 'IfcBuildingStorey', 'IfcSpace'])
        WITH labels(n) as labels, count(n) as count
        RETURN labels, count
        ORDER BY count DESC
        """
        
        result = conn.run_query(query)
        
        print("\nSpatial nodes in database:")
        for record in result:
            print(f"  {record['labels']}: {record['count']} nodes")
        
        # Check if specific nodes from the IFC exist in the database
        project_id = "1xS3BCk291UvhgP2a6eflL"  # From debug_spatial.py output
        query = f"""
        MATCH (n {{GlobalId: '{project_id}'}})
        RETURN labels(n) as labels, n.Name as name, n.GlobalId as id
        """
        
        result = conn.run_query(query)
        
        print("\nLooking for project node in database:")
        if result:
            for record in result:
                print(f"  Found: {record['labels']} - {record['name']} ({record['id']})")
        else:
            print("  Project node not found in database!")
        
        # Close connection
        conn.close()
        
    except Exception as e:
        logger.error(f"Error checking database: {e}")

if __name__ == "__main__":
    print("\n===== CHECKING PARSER EXTRACTION =====")
    check_parser_extraction()
    
    print("\n===== CHECKING DATABASE CONTENT =====")
    check_database_content() 