#!/usr/bin/env python
"""
BIMConverse Multi-hop Reasoning Test

This script demonstrates the multi-hop reasoning capabilities
of the BIMConverse GraphRAG system.
"""

import os
import sys
import json
import logging
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

# Import BIMConverseRAG (fix the import path)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bimconverse.core import BIMConverseRAG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MultihopTest")

# Create a Rich console for pretty output
console = Console()

def print_header():
    """Print the test header."""
    console.print()
    console.print(Panel.fit(
        "[bold blue]BIMConverse Multi-hop Reasoning Test[/bold blue]",
        border_style="blue"
    ))
    console.print()

def print_query_results(query: str, result: dict, index: int):
    """Print a query and its results in a pretty format."""
    # Create a table for the query and result
    console.print(Panel(
        f"[bold]Test Query {index}:[/bold] {query}",
        border_style="blue"
    ))
    
    # Print the answer
    answer_md = Markdown(result["answer"])
    console.print(Panel(
        answer_md,
        title="[bold blue]Answer[/bold blue]",
        border_style="green"
    ))
    
    # Print retrieval strategy
    console.print(f"[bold]Retrieval Strategy:[/bold] {result['retrieval_strategy']}")
    
    # Print metadata based on retrieval strategy
    if result["retrieval_strategy"] == "multihop" and "metadata" in result and "sub_queries" in result["metadata"]:
        console.print("[bold]Multi-hop Reasoning Steps:[/bold]")
        for i, query in enumerate(result["metadata"]["sub_queries"]):
            console.print(f"  {i+1}. {query}")
        
        # Print intermediate results if available
        if "intermediate_results" in result["metadata"]:
            console.print("[bold]Intermediate Results:[/bold]")
            for i, intermediate in enumerate(result["metadata"]["intermediate_results"]):
                console.print(f"  Step {i+1}: {intermediate['sub_query']}")
                if "cypher_query" in intermediate:
                    console.print(f"  Cypher: {intermediate['cypher_query']}")
                if "results" in intermediate:
                    console.print(f"  Results: {len(intermediate['results'])} records")
    else:
        if "metadata" in result and "cypher_query" in result["metadata"]:
            console.print("[bold]Generated Cypher:[/bold]")
            console.print(f"  {result['metadata']['cypher_query']}")
    
    console.print("\n" + "-" * 80 + "\n")

def run_test_query(bimconverse: BIMConverseRAG, query: str, use_multihop: bool = None) -> dict:
    """Run a test query and return the result."""
    logger.info(f"Running query: '{query}' (multihop={use_multihop})")
    result = bimconverse.query(query, use_multihop=use_multihop)
    return result

def main():
    """Main test function."""
    print_header()
    
    # Check for OpenAI API key
    if "OPENAI_API_KEY" not in os.environ:
        console.print("[red]Error: OPENAI_API_KEY environment variable not set[/red]")
        sys.exit(1)
    
    # Check for config file path argument
    if len(sys.argv) < 2:
        console.print("[red]Error: Please specify a config file path[/red]")
        console.print("Usage: python test_multihop.py <config_file>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    # Initialize BIMConverseRAG
    try:
        console.print(f"Initializing BIMConverseRAG with config: {config_path}")
        bimconverse = BIMConverseRAG(config_path=config_path)
        
        # Enable multi-hop reasoning
        bimconverse.set_multihop_enabled(True)
        bimconverse.set_multihop_detection(True)
        
        # Test queries that require multi-hop reasoning
        test_queries = [
            "What materials are used in walls that are adjacent to the kitchen?",
            "How many windows are in spaces located on the second floor?",
            "Which rooms have doors that are made of wood?",
            "Find all spaces that are adjacent to rooms with more than 2 windows",
            "What is the total area of all spaces that contain wooden furniture?"
        ]
        
        # Run each query with auto-detection
        console.print("[bold]Running test queries with auto-detection...[/bold]")
        for i, query in enumerate(test_queries):
            result = run_test_query(bimconverse, query)
            print_query_results(query, result, i+1)
        
        # Close the connection
        bimconverse.close()
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main() 