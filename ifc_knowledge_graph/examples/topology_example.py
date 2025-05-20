#!/usr/bin/env python3
"""
Topology Analysis Example

This script demonstrates how to use the topology analysis feature to extract additional
relationship types from IFC models beyond the basic relationships defined in the IFC schema.

The topology analysis uses the TopologicPy library to analyze the 3D geometry of building
elements and extract implicit spatial relationships like adjacency, containment, etc.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Make sure the module is in the Python path
parent_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, parent_dir)

# Import required modules
from src.ifc_to_graph.processor import IfcProcessor
from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector


def check_topologic_availability():
    """Check if TopologicPy is available and properly installed."""
    try:
        from src.ifc_to_graph.topology.topologic_analyzer import TopologicAnalyzer, TOPOLOGICPY_AVAILABLE
        if not TOPOLOGICPY_AVAILABLE:
            logger.error("TopologicPy is not available. Please install it using: pip install topologicpy")
            return False
        return True
    except ImportError:
        logger.error("Could not import topology module. Please check your installation.")
        return False


def run_topology_example(
    ifc_file_path: str,
    neo4j_uri: str = "neo4j://localhost:7687",
    neo4j_username: str = "neo4j",
    neo4j_password: str = "test1234",
    neo4j_database: str = None,
    clear_existing: bool = True
):
    """
    Run an example processing of an IFC file with topology analysis enabled.
    
    Args:
        ifc_file_path: Path to the IFC file
        neo4j_uri: URI for Neo4j connection
        neo4j_username: Neo4j username
        neo4j_password: Neo4j password
        neo4j_database: Neo4j database name (optional)
        clear_existing: Whether to clear existing data in the database
    """
    if not os.path.exists(ifc_file_path):
        logger.error(f"IFC file not found: {ifc_file_path}")
        return
    
    # Check TopologicPy availability
    if not check_topologic_availability():
        logger.error("Topology analysis requires TopologicPy. Exiting.")
        return
    
    # Create and run processor WITH topology analysis
    logger.info("Processing IFC file WITH topology analysis enabled...")
    processor_with_topology = IfcProcessor(
        ifc_file_path=ifc_file_path,
        neo4j_uri=neo4j_uri,
        neo4j_username=neo4j_username,
        neo4j_password=neo4j_password,
        neo4j_database=neo4j_database,
        enable_topological_analysis=True  # <-- This is the key parameter!
    )
    
    # Process with clear_existing=True to start fresh
    stats_with_topology = processor_with_topology.process(clear_existing=clear_existing)
    processor_with_topology.close()
    
    logger.info("\n====================== PROCESSING RESULTS ======================")
    logger.info(f"IFC file: {os.path.basename(ifc_file_path)}")
    logger.info(f"Total nodes: {stats_with_topology.get('node_count', 0)}")
    logger.info(f"Total relationships: {stats_with_topology.get('relationship_count', 0)}")
    logger.info(f"Topological relationships: {stats_with_topology.get('topological_relationship_count', 0)}")
    logger.info("================================================================\n")
    
    # Connect to Neo4j to query relationship types
    connector = Neo4jConnector(
        uri=neo4j_uri,
        username=neo4j_username,
        password=neo4j_password,
        database=neo4j_database
    )
    
    # Query for relationship types
    query = """
    MATCH ()-[r]->()
    RETURN type(r) as type, count(r) as count
    ORDER BY count DESC
    """
    relationship_types = connector.run_query(query)
    
    if relationship_types:
        logger.info("Relationship types in the graph:")
        for rel in relationship_types:
            rel_type = rel["type"]
            count = rel["count"]
            logger.info(f"- {rel_type}: {count} relationships")
    
    # Query for topological relationships specifically
    topo_query = """
    MATCH ()-[r]->()
    WHERE r.relationshipSource = 'topologicalAnalysis'
    RETURN type(r) as type, count(r) as count
    ORDER BY count DESC
    """
    topo_relationships = connector.run_query(topo_query)
    
    if topo_relationships:
        logger.info("\nTopological relationship types:")
        for rel in topo_relationships:
            rel_type = rel["type"]
            count = rel["count"]
            logger.info(f"- {rel_type}: {count} relationships")
    
    connector.close()


def print_cli_examples():
    """Print examples of how to use the topology flag with the CLI."""
    print("\n" + "=" * 80)
    print("COMMAND-LINE EXAMPLES")
    print("=" * 80)
    print("To use the topology analysis feature with the command-line interface:")
    print("\n1. Basic usage with topology enabled:")
    print("   python main.py graph path/to/your/file.ifc --topology")
    print("\n2. With additional options:")
    print("   python main.py graph path/to/your/file.ifc --topology --clear --parallel")
    print("\n3. With database credentials:")
    print("   python main.py graph path/to/your/file.ifc --topology --uri neo4j://localhost:7687 --username neo4j --password test1234")
    print("\n4. With all options:")
    print("   python main.py graph path/to/your/file.ifc --topology --clear --parallel --batch-size 200 --uri neo4j://localhost:7687 --username neo4j --password test1234")
    print("\nNOTE: Without the --topology flag, only basic IFC relationships will be extracted.")
    print("=" * 80 + "\n")


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Demonstrate topology analysis feature for IFC to Neo4j conversion"
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
        "--database",
        default=None,
        help="Neo4j database name (default: None, uses the default database)"
    )
    
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Don't clear existing graph data before processing"
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the script."""
    args = parse_args()
    
    # Print examples for CLI usage
    print_cli_examples()
    
    # Run the example
    run_topology_example(
        ifc_file_path=args.ifc_file,
        neo4j_uri=args.uri,
        neo4j_username=args.username,
        neo4j_password=args.password,
        neo4j_database=args.database,
        clear_existing=not args.no_clear
    )


if __name__ == "__main__":
    main() 