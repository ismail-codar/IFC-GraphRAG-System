#!/usr/bin/env python3
"""
Run the optimized processor with enhanced logging for diagnostics
"""

import os
import sys
import logging
import time

# Add parent directory to path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("diagnostic_process.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Import the optimized processor
from optimized_processor import OptimizedIfcProcessor, TOPOLOGICPY_AVAILABLE

def run_diagnostic_process():
    """Run the optimized processor with detailed logging"""
    start_time = time.time()
    
    # Log system information
    logger.info("=== System Information ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"TopologicPy available: {TOPOLOGICPY_AVAILABLE}")
    
    # Find IFC files in the data directory
    logger.info("=== Looking for IFC files ===")
    ifc_files = []
    for root, _, files in os.walk('data'):
        for file in files:
            if file.lower().endswith('.ifc'):
                ifc_files.append(os.path.join(root, file))
    
    if not ifc_files:
        logger.error("No IFC files found in the data directory")
        return
    
    # Use the first IFC file found
    ifc_file = ifc_files[0]
    logger.info(f"Using IFC file: {ifc_file}")
    
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
        
        # Query IFC element types
        query_types = """
        MATCH (n) 
        WHERE n.IFCType IS NOT NULL
        RETURN n.IFCType as element_type, count(*) as count 
        ORDER BY count DESC
        """
        
        result = conn.run_query(query_types)
        
        logger.info("IFC Element Types in the database:")
        for record in result:
            element_type = record["element_type"]
            count = record["count"]
            logger.info(f"{element_type}: {count}")
        
        # Close connection
        conn.close()
        
    except Exception as e:
        logger.exception(f"Error checking database results: {e}")

if __name__ == "__main__":
    run_diagnostic_process() 