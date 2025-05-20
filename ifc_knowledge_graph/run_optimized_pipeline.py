#!/usr/bin/env python3
"""
Run the optimized IFC processor with fixed topological analysis
"""

import os
import sys
import logging
import time
import glob

# Add parent directory to path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("optimized_pipeline.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Import the optimized processor
from optimized_processor import OptimizedIfcProcessor, TOPOLOGICPY_AVAILABLE

def find_ifc_file():
    """Find an IFC file to process"""
    # Look in common locations
    search_paths = [
        "data/ifc_files/*.ifc",
        "data/*.ifc",
        "*.ifc",
        "../data/ifc_files/*.ifc",
        "../data/*.ifc",
        "../*.ifc",
    ]
    
    for pattern in search_paths:
        files = glob.glob(pattern)
        if files:
            return os.path.abspath(files[0])
    
    return None

def clear_database():
    """Clear the Neo4j database before processing"""
    from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector
    
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

def run_optimized_pipeline():
    """Run the optimized IFC processor with fixed topological analysis"""
    start_time = time.time()
    
    # Log system information
    logger.info("=== System Information ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"TopologicPy available: {TOPOLOGICPY_AVAILABLE}")
    
    # Find an IFC file
    ifc_file = find_ifc_file()
    if not ifc_file:
        logger.error("No IFC file found. Please place an IFC file in the data directory.")
        return
    
    logger.info(f"Using IFC file: {ifc_file}")
    
    # Clear the database
    if not clear_database():
        logger.warning("Failed to clear database. Continuing with processing anyway.")
    
    try:
        # Initialize the processor with topological analysis enabled
        logger.info("=== Initializing processor ===")
        processor = OptimizedIfcProcessor(
            ifc_file_path=ifc_file,
            neo4j_uri="neo4j://localhost:7687",
            neo4j_username="neo4j",
            neo4j_password="test1234",
            neo4j_database="neo4j",
            enable_monitoring=True,
            parallel_processing=False,
            enable_topological_analysis=True,  # Enable topological analysis
            batch_size=1000,
            use_cache=True
        )
        
        # Process the IFC file
        logger.info("=== Starting processing ===")
        processor.process()
        
        # Close connections
        logger.info("=== Closing connections ===")
        processor.close()
        
    except Exception as e:
        logger.exception(f"Error during processing: {e}")
    
    # Calculate and log total time
    elapsed = time.time() - start_time
    logger.info(f"=== Processing finished in {elapsed:.2f} seconds ({elapsed/60:.2f} minutes) ===")
    
    # Check the database for results
    logger.info("=== Checking database results ===")
    try:
        from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector
        
        # Connect to Neo4j
        conn = Neo4jConnector('neo4j://localhost:7687', 'neo4j', 'test1234')
        
        # Query all relationship types and counts
        query = """
        MATCH ()-[r]->() 
        RETURN type(r) as relationship_type, count(r) as count 
        ORDER BY count DESC
        """
        
        result = conn.run_query(query)
        
        logger.info("Relationships in the graph:")
        total = 0
        for record in result:
            rel_type = record["relationship_type"]
            count = record["count"]
            total += count
            logger.info(f"{rel_type}: {count}")
        
        logger.info(f"Total relationships: {total}")
        
        # Query node labels
        node_query = """
        MATCH (n)
        RETURN distinct labels(n) as node_labels, count(*) as count
        ORDER BY count DESC
        """
        
        result = conn.run_query(node_query)
        
        logger.info("Node labels in the graph:")
        total_nodes = 0
        for record in result:
            labels = record["node_labels"]
            count = record["count"]
            total_nodes += count
            logger.info(f"{labels}: {count}")
            
        logger.info(f"Total nodes: {total_nodes}")
        
        # Close connection
        conn.close()
        
    except Exception as e:
        logger.exception(f"Error checking database results: {e}")

if __name__ == "__main__":
    run_optimized_pipeline() 