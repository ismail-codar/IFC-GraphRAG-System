#!/usr/bin/env python3
"""
Optimized IFC Processor Runner
This script provides a command-line interface to run the optimized IFC processor.
"""

import os
import sys
import argparse
import logging
import time
import json
from pathlib import Path

# Fix import paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from optimized_processor import OptimizedIfcProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ifc_processing.log')
    ]
)
logger = logging.getLogger(__name__)

def load_config(config_path):
    """Load configuration from a JSON file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config file: {e}")
        return {}

def main():
    parser = argparse.ArgumentParser(description='Run the optimized IFC processor')
    parser.add_argument('ifc_file', help='Path to the IFC file')
    parser.add_argument('--uri', default='neo4j://localhost:7687', help='Neo4j URI')
    parser.add_argument('--username', default='neo4j', help='Neo4j username')
    parser.add_argument('--password', required=True, help='Neo4j password')
    parser.add_argument('--database', default='neo4j', help='Neo4j database name')
    parser.add_argument('--batch-size', type=int, default=5000, help='Size of batches for database operations')
    parser.add_argument('--enable-topology', action='store_true', help='Enable topological analysis')
    parser.add_argument('--parallel', action='store_true', help='Enable parallel processing')
    parser.add_argument('--config', help='Path to config file (overrides command line arguments)')
    
    args = parser.parse_args()
    
    # Load config file if provided
    config = {}
    if args.config:
        config = load_config(args.config)
    
    # Set default Neo4j connection parameters
    neo4j_uri = config.get('neo4j_uri', args.uri)
    neo4j_username = config.get('neo4j_username', args.username)
    neo4j_password = config.get('neo4j_password', args.password)
    neo4j_database = config.get('neo4j_database', args.database)
    
    # Set processing parameters
    batch_size = config.get('batch_size', args.batch_size)
    enable_topology = config.get('enable_topology', args.enable_topology)
    parallel_processing = config.get('parallel_processing', args.parallel)
    
    # Get IFC file path
    ifc_file_path = config.get('ifc_file_path', args.ifc_file)
    
    # Validate IFC file
    if not os.path.exists(ifc_file_path):
        logger.error(f"IFC file not found: {ifc_file_path}")
        sys.exit(1)
    
    logger.info(f"Starting optimized processing of {ifc_file_path}")
    logger.info(f"Using Neo4j at {neo4j_uri}")
    logger.info(f"Batch size: {batch_size}")
    logger.info(f"Topological analysis: {'Enabled' if enable_topology else 'Disabled'}")
    logger.info(f"Parallel processing: {'Enabled' if parallel_processing else 'Disabled'}")
    
    try:
        # Configure and run Neo4j performance tweaks first
        try:
            from ifc_knowledge_graph.neo4j_performance_fix import setup_indexes_and_constraints
            setup_indexes_and_constraints(neo4j_uri, neo4j_username, neo4j_password, neo4j_database)
        except Exception as e:
            logger.warning(f"Could not apply Neo4j performance fixes: {e}")
        
        # Initialize and run the processor
        start_time = time.time()
        
        processor = OptimizedIfcProcessor(
            ifc_file_path=ifc_file_path,
            neo4j_uri=neo4j_uri,
            neo4j_username=neo4j_username,
            neo4j_password=neo4j_password,
            neo4j_database=neo4j_database,
            enable_monitoring=True,
            parallel_processing=parallel_processing,
            enable_topological_analysis=enable_topology,
            batch_size=batch_size,
            use_cache=True
        )
        
        processor.process()
        processor.close()
        
        elapsed = time.time() - start_time
        logger.info(f"Processing completed successfully in {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
        
    except Exception as e:
        logger.error(f"Error during processing: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main() 