#!/usr/bin/env python3
"""
Main entry point for the IFC to Neo4j Knowledge Graph project.

This script provides a command-line interface for the various tools in the project.
"""

import sys
import os
import argparse
import logging

# Add the src directory to the Python path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
sys.path.insert(0, src_dir)

# Import CLI modules
from ifc_to_graph.cli.ifc_parser_cli import main as parser_main
from ifc_to_graph.cli.ifc_to_neo4j_cli import main as neo4j_main

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """
    Main entry point for the application.
    
    Uses subcommands to handle different operations:
    - parse: Parse an IFC file and extract information
    - graph: Convert an IFC file to a Neo4j graph database
    """
    parser = argparse.ArgumentParser(
        description="IFC to Neo4j Knowledge Graph - Tools for working with IFC files and Neo4j"
    )
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Parser subcommand
    parser_cmd = subparsers.add_parser("parse", help="Parse an IFC file and extract information")
    
    # Graph subcommand
    graph_cmd = subparsers.add_parser("graph", help="Convert an IFC file to a Neo4j graph database")
    
    # Parse arguments
    args, remaining_args = parser.parse_known_args()
    
    # Execute the appropriate command
    if args.command == "parse":
        # Forward to the parser CLI
        sys.argv = [sys.argv[0]] + remaining_args
        parser_main()
    elif args.command == "graph":
        # Forward to the Neo4j CLI
        sys.argv = [sys.argv[0]] + remaining_args
        neo4j_main()
    else:
        # No subcommand provided, show help
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main() 