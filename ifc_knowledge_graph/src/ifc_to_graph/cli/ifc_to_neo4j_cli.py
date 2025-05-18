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
from datetime import datetime

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
    
    # Performance monitoring options
    parser.add_argument(
        "--monitor", "-m",
        action="store_true",
        help="Enable performance monitoring"
    )
    
    parser.add_argument(
        "--monitor-dir",
        default="performance_reports",
        help="Directory to store performance monitoring reports (default: 'performance_reports')"
    )
    
    parser.add_argument(
        "--report-console",
        action="store_true",
        help="Display performance report in console after processing"
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
    
    # Create performance monitoring directory if enabled
    if args.monitor:
        monitoring_dir = args.monitor_dir
        if not os.path.exists(monitoring_dir):
            os.makedirs(monitoring_dir, exist_ok=True)
            logger.info(f"Created performance monitoring directory: {monitoring_dir}")
    else:
        monitoring_dir = None
    
    # Process the IFC file
    try:
        logger.info(f"Starting conversion of {args.ifc_file} to Neo4j")
        start_time = time.time()
        
        # Initialize processor with monitoring if enabled
        processor = IfcProcessor(
            ifc_file_path=args.ifc_file,
            neo4j_uri=args.uri,
            neo4j_username=args.username,
            neo4j_password=args.password,
            neo4j_database=args.database,
            enable_monitoring=args.monitor,
            monitoring_output_dir=monitoring_dir
        )
        
        # Process the file
        stats = processor.process(
            clear_existing=args.clear,
            batch_size=args.batch_size,
            save_performance_report=args.monitor
        )
        
        # Print performance report to console if requested
        if args.monitor and args.report_console:
            print("\n" + "=" * 80)
            print("PERFORMANCE REPORT")
            print("=" * 80)
            print(processor.db_connector.get_performance_report())
            print("=" * 80 + "\n")
        
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
        
        # Print performance monitoring info
        if args.monitor:
            report_path = os.path.join(
                monitoring_dir, 
                f"{os.path.basename(args.ifc_file).split('.')[0]}_perf_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
            logger.info(f"Performance report saved to: {report_path}")
        
    except Exception as e:
        logger.error(f"Error processing IFC file: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main() 