#!/usr/bin/env python
"""
BIMConverse Multi-hop Reasoning and Visualization Demo

This script demonstrates the enhanced multi-hop reasoning capabilities 
and visualization features for spatial query results.
"""

import os
import sys
import json
import logging
from pathlib import Path
import argparse

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the parent directory to the path (if running from examples)
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from neo4j import GraphDatabase
    from bimconverse.core import BIMConverseRAG
    from bimconverse.retrievers import MultihopRetriever
    import bimconverse.visualization as viz

    # Check if visualization dependencies are installed
    viz_deps_available = True
    try:
        import plotly
        import networkx
    except ImportError:
        viz_deps_available = False
        logger.warning("Visualization dependencies not found. "
                      "Run tools/install_visualization_deps.py to install them.")
except ImportError as e:
    logger.error(f"Error importing required modules: {e}")
    logger.error("Make sure you have installed all required dependencies.")
    sys.exit(1)

def load_config(config_path):
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading config from {config_path}: {e}")
        return None

def create_bimconverse_rag(config):
    """Create a BIMConverseRAG instance with the provided configuration."""
    try:
        # Create connection to Neo4j
        uri = config.get("neo4j", {}).get("uri", "neo4j://localhost:7687")
        username = config.get("neo4j", {}).get("username", "neo4j")
        password = config.get("neo4j", {}).get("password", "password")
        
        # Set up OpenAI credentials if using OpenAI
        openai_api_key = config.get("openai", {}).get("api_key", None)
        
        # Create BIMConverseRAG instance with the correct parameters
        rag = BIMConverseRAG(
            neo4j_uri=uri,
            neo4j_username=username,
            neo4j_password=password,
            openai_api_key=openai_api_key
        )
        
        # Get Neo4j driver from the BIMConverseRAG instance
        driver = rag.driver
        
        return rag, driver
    except Exception as e:
        logger.error(f"Error creating BIMConverseRAG instance: {e}")
        return None, None

def demo_multihop_query(rag, driver, query):
    """
    Demonstrate multi-hop reasoning with visualization.
    
    Args:
        rag: BIMConverseRAG instance
        driver: Neo4j driver
        query: Query to process
    """
    try:
        # Create a MultihopRetriever instance
        from bimconverse.retrievers import MultihopRetriever
        
        # Get the LLM from the BIMConverseRAG instance
        llm = rag.llm
        
        # Create the MultihopRetriever
        multihop = MultihopRetriever(driver, llm)
        
        # Process the query
        logger.info(f"Processing multi-hop query: {query}")
        result = multihop.search(query)
        
        # Display the results
        print("\n" + "="*80)
        print(f"Query: {query}")
        print("="*80)
        
        # Show the decomposed sub-queries
        print(f"\nDecomposed into {len(result.sub_queries)} sub-queries:")
        for i, sub_query in enumerate(result.sub_queries):
            print(f"{i+1}. {sub_query}")
        
        # Show the accumulated context
        if hasattr(result, "accumulated_context") and result.accumulated_context:
            print("\nAccumulated Context:")
            print(result.accumulated_context)
        
        # Show the final answer
        print("\nFinal Answer:")
        print(result.answer)
        
        # Show visualization path if available
        if hasattr(result, "visualization_path") and result.visualization_path:
            print(f"\nVisualization available at: {result.visualization_path}")
            print(f"Open this file in a web browser to view the visualization.")
        
        return result
    except Exception as e:
        logger.error(f"Error in multi-hop reasoning demo: {e}")
        return None

def main():
    """Main entry point for the demo script."""
    parser = argparse.ArgumentParser(description="BIMConverse Multi-hop Reasoning and Visualization Demo")
    parser.add_argument("--config", default="config.json", help="Path to configuration file")
    parser.add_argument("--query", default=None, help="Query to process (if not provided, example queries will be used)")
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    if not config:
        logger.error("Failed to load configuration. Exiting.")
        sys.exit(1)
    
    # Create BIMConverseRAG instance
    rag, driver = create_bimconverse_rag(config)
    if not rag or not driver:
        logger.error("Failed to create BIMConverseRAG instance. Exiting.")
        sys.exit(1)
    
    try:
        # Use provided query or example queries
        if args.query:
            demo_multihop_query(rag, driver, args.query)
        else:
            # Example complex building queries that benefit from multi-hop reasoning
            example_queries = [
                "What materials are used in walls adjacent to spaces on the second floor?",
                "Find all doors that connect the kitchen to spaces with more than 2 windows",
                "Which rooms adjacent to the living room have furniture made of wood?",
                "What is the total area of spaces that contain at least one door connecting to a corridor?"
            ]
            
            for i, query in enumerate(example_queries):
                print(f"\n\nExample {i+1}:")
                demo_multihop_query(rag, driver, query)
                input("\nPress Enter to continue to the next example...")
    finally:
        # Close the driver
        if driver:
            driver.close()

if __name__ == "__main__":
    main()