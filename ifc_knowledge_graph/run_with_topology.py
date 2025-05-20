#!/usr/bin/env python3
"""
Run IFC Processing with Topology Analysis

This script processes an IFC file with topology analysis enabled to generate
a richer knowledge graph with additional relationship types.
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import required modules
from src.ifc_to_graph.processor import IfcProcessor
from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector
from src.ifc_to_graph.topology.topologic_analyzer import TOPOLOGICPY_AVAILABLE

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Process IFC file with topology analysis enabled"
    )
    
    parser.add_argument(
        "ifc_file",
        help="Path to the IFC file to process"
    )
    
    parser.add_argument(
        "--uri",
        default="neo4j://localhost:7687",
        help="Neo4j connection URI (default: neo4j://localhost:7687)"
    )
    
    parser.add_argument(
        "--username",
        default="neo4j",
        help="Neo4j username (default: neo4j)"
    )
    
    parser.add_argument(
        "--password",
        default="test1234",
        help="Neo4j password (default: test1234)"
    )
    
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing graph data before processing"
    )
    
    return parser.parse_args()

def main():
    """Main entry point for the script."""
    args = parse_args()
    
    # Check if file exists
    if not os.path.exists(args.ifc_file):
        logger.error(f"IFC file not found: {args.ifc_file}")
        return
    
    # Check TopologicPy availability
    if not TOPOLOGICPY_AVAILABLE:
        logger.error("TopologicPy is not available. Please install it using: pip install topologicpy")
        return
    
    # Process the IFC file with topology analysis enabled
    logger.info(f"Processing {args.ifc_file} with topology analysis enabled...")
    processor = IfcProcessor(
        ifc_file_path=args.ifc_file,
        neo4j_uri=args.uri,
        neo4j_username=args.username,
        neo4j_password=args.password,
        enable_topological_analysis=True  # This enables the topology analysis
    )
    
    # Process the file
    stats = processor.process(clear_existing=args.clear)
    processor.close()
    
    # Print results
    logger.info("Processing complete!")
    logger.info(f"Nodes created: {stats.get('node_count', 0)}")
    logger.info(f"Relationships created: {stats.get('relationship_count', 0)}")
    logger.info(f"Topological relationships: {stats.get('topological_relationship_count', 0)}")
    
    # Connect to the database to verify relationship types
    connector = Neo4jConnector(
        uri=args.uri,
        username=args.username,
        password=args.password
    )
    
    # Query for relationship types
    rel_types = connector.run_query(
        "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC"
    )
    
    if rel_types:
        logger.info("\nRelationship types in the graph:")
        for rel in rel_types:
            logger.info(f"  - {rel['type']}: {rel['count']} relationships")
    
    connector.close()
    
    logger.info("\nTo verify the topological relationships in Neo4j, run this Cypher query:")
    logger.info("""
    MATCH ()-[r]->() 
    WHERE r.relationshipSource = 'topologicalAnalysis'
    RETURN type(r) as type, count(r) as count 
    ORDER BY count DESC
    """)

if __name__ == "__main__":
    main() 