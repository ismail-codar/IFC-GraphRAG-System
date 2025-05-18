"""
IFC to Neo4j CLI Module

This module provides a command-line interface for converting IFC files to Neo4j.
"""

import os
import sys
import argparse
import logging
import time
from typing import Dict, List, Any, Optional

from ifc_to_graph.processor import IfcProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Convert IFC files to a Neo4j knowledge graph."
    )
    
    # IFC file input
    parser.add_argument(
        "ifc_file",
        help="Path to the IFC file to process"
    )
    
    # Neo4j connection options
    parser.add_argument(
        "--uri", "-u",
        default="neo4j://localhost:7687",
        help="Neo4j connection URI (default: neo4j://localhost:7687)"
    )
    
    parser.add_argument(
        "--username", "-n",
        default="neo4j",
        help="Neo4j username (default: neo4j)"
    )
    
    parser.add_argument(
        "--password", "-p",
        default="password",
        help="Neo4j password (default: password)"
    )
    
    parser.add_argument(
        "--database", "-d",
        default=None,
        help="Neo4j database name (default: None, uses the default database)"
    )
    
    # Processing options
    parser.add_argument(
        "--clear", "-c",
        action="store_true",
        help="Clear existing graph data before processing"
    )
    
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=100,
        help="Batch size for processing elements (default: 100)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser.parse_args()


def main() -> None:
    """Main entry point for the IFC to Neo4j CLI."""
    args = parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check if IFC file exists
    if not os.path.exists(args.ifc_file):
        logger.error(f"IFC file not found: {args.ifc_file}")
        sys.exit(1)
    
    # Process the IFC file
    try:
        logger.info(f"Starting conversion of {args.ifc_file} to Neo4j")
        start_time = time.time()
        
        # Initialize processor
        processor = IfcProcessor(
            ifc_file_path=args.ifc_file,
            neo4j_uri=args.uri,
            neo4j_username=args.username,
            neo4j_password=args.password,
            neo4j_database=args.database
        )
        
        # Process the file
        stats = processor.process(
            clear_existing=args.clear,
            batch_size=args.batch_size
        )
        
        # Close connections
        processor.close()
        
        # Print statistics
        total_time = time.time() - start_time
        logger.info(f"Conversion completed in {total_time:.2f} seconds")
        logger.info(f"Statistics:")
        logger.info(f"- Processed {stats['element_count']} elements")
        logger.info(f"- Created {stats['node_count']} nodes")
        logger.info(f"- Created {stats['relationship_count']} relationships")
        logger.info(f"- Created {stats['property_set_count']} property sets")
        logger.info(f"- Created {stats['material_count']} materials")
        
    except Exception as e:
        logger.error(f"Error processing IFC file: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main() 