#!/usr/bin/env python3
"""
Run IFC to Neo4j Conversion with Topological Analysis

This script runs the IFC to Neo4j conversion with topological analysis enabled to create
spatial relationship information in the knowledge graph.
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('topology_processing.log')
    ]
)
logger = logging.getLogger(__name__)

# Import the processor
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from optimized_processor import OptimizedIfcProcessor

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Run IFC to Neo4j conversion with topological analysis'
    )
    
    parser.add_argument(
        '--ifc-file',
        type=str,
        required=True,
        help='Path to the IFC file to process'
    )
    
    parser.add_argument(
        '--neo4j-uri',
        type=str,
        default='neo4j://localhost:7687',
        help='URI for the Neo4j database (default: neo4j://localhost:7687)'
    )
    
    parser.add_argument(
        '--neo4j-user',
        type=str,
        default='neo4j',
        help='Username for the Neo4j database (default: neo4j)'
    )
    
    parser.add_argument(
        '--neo4j-password',
        type=str,
        default='test1234',
        help='Password for the Neo4j database (default: test1234)'
    )
    
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear the database before processing'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=500,
        help='Batch size for database operations (default: 500)'
    )
    
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_args()
    
    # Check if the IFC file exists
    if not os.path.exists(args.ifc_file):
        logger.error(f"IFC file not found: {args.ifc_file}")
        return 1
    
    start_time = time.time()
    logger.info(f"Starting IFC to Neo4j conversion with topological analysis...")
    logger.info(f"Processing file: {args.ifc_file}")
    
    try:
        # Create the processor
        processor = OptimizedIfcProcessor(
            ifc_file_path=args.ifc_file,
            neo4j_uri=args.neo4j_uri,
            neo4j_username=args.neo4j_user,
            neo4j_password=args.neo4j_password,
            batch_size=args.batch_size,
            clear_existing=args.clear,
            enable_topological_analysis=True  # Ensure topological analysis is enabled
        )
        
        # Run the processor
        logger.info("Processing IFC file...")
        processor.process()
        
        # Report completion
        elapsed_time = time.time() - start_time
        logger.info(f"Processing completed in {elapsed_time:.2f} seconds")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error processing IFC file: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 