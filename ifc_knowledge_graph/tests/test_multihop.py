#!/usr/bin/env python
"""
Test script for multihop reasoning in BIMConverse.

This script specifically tests the multihop reasoning capabilities
implemented for complex building queries in the BIMConverse system.
"""

import os
import sys
import json
import logging
import time
from pathlib import Path
import argparse

# Add the parent directory to the path
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MultihopTest")

# Import BIMConverse components
try:
    from bimconverse.core import BIMConverseRAG
    from bimconverse.retrievers import MultihopRetriever
    from neo4j import GraphDatabase
except ImportError as e:
    logger.error(f"Error importing required modules: {e}")
    logger.error("Make sure you have installed all required dependencies.")
    sys.exit(1)

# Check if visualization is available
try:
    from bimconverse.visualization import enhance_multihop_result_with_visualization
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    logger.warning("Visualization module not available")

def load_config(config_path):
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading config from {config_path}: {e}")
        return None

def create_test_queries():
    """Create a set of test queries for multihop reasoning evaluation."""
    return [
        # Basic spatial queries
        {
            "category": "Spatial - Adjacency",
            "query": "What spaces are adjacent to the kitchen?",
            "complexity": "Simple"
        },
        {
            "category": "Spatial - Containment",
            "query": "List all elements contained in the living room",
            "complexity": "Simple"
        },
        {
            "category": "Spatial - Connectivity",
            "query": "Which rooms are connected to the hallway via doors?",
            "complexity": "Simple"
        },
        
        # Multi-hop spatial queries
        {
            "category": "Multi-hop - Adjacency",
            "query": "Which rooms are adjacent to spaces that contain more than 2 windows?",
            "complexity": "Medium"
        },
        {
            "category": "Multi-hop - Containment + Material",
            "query": "What materials are used in walls contained in the second floor?",
            "complexity": "Medium"
        },
        {
            "category": "Multi-hop - Connectivity + Elements",
            "query": "List all furniture in rooms that are connected to the kitchen",
            "complexity": "Medium"
        },
        
        # Complex multi-hop queries
        {
            "category": "Complex - Material + Adjacency + Containment",
            "query": "Find materials used in walls that are adjacent to spaces containing wooden furniture",
            "complexity": "Complex"
        },
        {
            "category": "Complex - Connectivity + Property + Adjacency",
            "query": "Which rooms with a floor area greater than 20m² are connected to spaces adjacent to the living room?",
            "complexity": "Complex"
        },
        {
            "category": "Complex - Spatial Reasoning",
            "query": "What is the total area of spaces that are both adjacent to the kitchen and contain at least one door connecting to the hallway?",
            "complexity": "Complex"
        }
    ]

def run_multihop_test(rag, driver, query_info, use_direct_retriever=False, output_dir=None):
    """
    Run a multihop reasoning test with the given query.
    
    Args:
        rag: BIMConverseRAG instance
        driver: Neo4j driver
        query_info: Dictionary with query information
        use_direct_retriever: Use MultihopRetriever directly instead of BIMConverseRAG
        output_dir: Directory to save visualization files
        
    Returns:
        Dictionary with test results
    """
    query = query_info["query"]
    category = query_info["category"]
    complexity = query_info["complexity"]
    
    logger.info(f"Testing query: {query}")
    logger.info(f"Category: {category}, Complexity: {complexity}")
    
    start_time = time.time()
    
    try:
        # Get multihop detection from RAG
        is_multihop = rag._detect_multihop_query(query)
        logger.info(f"Multihop detection: {is_multihop}")
        
        if use_direct_retriever:
            # Use MultihopRetriever directly
            logger.info("Using MultihopRetriever directly")
            retriever = MultihopRetriever(driver, rag.llm)
            result = retriever.search(query)
            
            # Add visualization if available
            if VISUALIZATION_AVAILABLE and output_dir:
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    result = enhance_multihop_result_with_visualization(result)
                    if hasattr(result, "visualization_path"):
                        logger.info(f"Visualization path: {result.visualization_path}")
                except Exception as e:
                    logger.error(f"Error adding visualization: {e}")
            
            # Process the result object
            answer = result.answer if hasattr(result, "answer") else "No answer"
            sub_queries = result.sub_queries if hasattr(result, "sub_queries") else []
            
            # Format test results
            test_results = {
                "query": query,
                "category": category,
                "complexity": complexity,
                "is_multihop_detected": is_multihop,
                "answer": answer,
                "num_steps": len(sub_queries),
                "sub_queries": sub_queries,
                "execution_time": time.time() - start_time,
                "visualization_path": getattr(result, "visualization_path", None)
            }
            
        else:
            # Use BIMConverseRAG query method
            logger.info("Using BIMConverseRAG query method")
            rag_result = rag.query(query, use_multihop=True)
            
            # Format test results
            test_results = {
                "query": query,
                "category": category,
                "complexity": complexity,
                "is_multihop_detected": is_multihop,
                "answer": rag_result.get("answer", "No answer"),
                "cypher_query": rag_result.get("cypher_query", ""),
                "execution_time": time.time() - start_time,
                "visualization_path": None
            }
        
        return test_results
        
    except Exception as e:
        logger.error(f"Error running multihop test: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        return {
            "query": query,
            "category": category,
            "complexity": complexity,
            "is_multihop_detected": False,
            "error": str(e),
            "execution_time": time.time() - start_time
        }

def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(description="Test multihop reasoning capabilities in BIMConverse")
    parser.add_argument("--config", default="config.json", help="Path to configuration file")
    parser.add_argument("--output", default="test_results", help="Directory to save test results")
    parser.add_argument("--direct", action="store_true", help="Use MultihopRetriever directly")
    parser.add_argument("--query", default=None, help="Run a specific query instead of test set")
    parser.add_argument("--category", default=None, help="Filter test queries by category")
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    if not config:
        logger.error("Failed to load configuration. Exiting.")
        sys.exit(1)
    
    # Check for OpenAI API key
    if not config.get("openai", {}).get("api_key") and not os.environ.get("OPENAI_API_KEY"):
        logger.error("OpenAI API key not found in config or environment.")
        logger.error("Please set OPENAI_API_KEY environment variable or add it to config.json")
        sys.exit(1)
    
    # Create output directory for test results
    os.makedirs(args.output, exist_ok=True)
    
    try:
        # Initialize BIMConverseRAG
        neo4j_uri = config.get("neo4j", {}).get("uri", "neo4j://localhost:7687")
        neo4j_username = config.get("neo4j", {}).get("username", "neo4j")
        neo4j_password = config.get("neo4j", {}).get("password", "test1234")
        openai_api_key = config.get("openai", {}).get("api_key", os.environ.get("OPENAI_API_KEY"))
        
        rag = BIMConverseRAG(
            neo4j_uri=neo4j_uri,
            neo4j_username=neo4j_username,
            neo4j_password=neo4j_password,
            openai_api_key=openai_api_key
        )
        
        # Enable multihop functionality
        rag.set_multihop_enabled(True)
        rag.set_multihop_detection(True)
        
        # Get the Neo4j driver from RAG
        driver = rag.driver
        
        # Get database statistics
        try:
            stats = rag.get_stats()
            logger.info("Knowledge Graph Statistics:")
            logger.info(f"  Nodes: {stats.get('nodes', 'N/A')}")
            logger.info(f"  Relationships: {stats.get('relationships', 'N/A')}")
        except Exception as e:
            logger.warning(f"Could not retrieve database statistics: {e}")
        
        # Create directory for visualizations
        viz_dir = os.path.join(args.output, "visualizations")
        os.makedirs(viz_dir, exist_ok=True)
        
        # Run test(s)
        results = []
        
        if args.query:
            # Test a specific query
            query_info = {
                "query": args.query,
                "category": "Custom",
                "complexity": "Unknown"
            }
            result = run_multihop_test(rag, driver, query_info, args.direct, viz_dir)
            results.append(result)
            
            # Print detailed results for single query
            print("\n" + "="*80)
            print(f"Query: {args.query}")
            print("="*80)
            
            if "error" in result:
                print(f"Error: {result['error']}")
            else:
                print(f"Multihop detected: {result['is_multihop_detected']}")
                print(f"Answer: {result['answer']}")
                
                if "num_steps" in result:
                    print(f"Steps: {result['num_steps']}")
                    print("\nSub-queries:")
                    for i, sub_query in enumerate(result['sub_queries']):
                        print(f"{i+1}. {sub_query}")
                
                if result.get("visualization_path"):
                    print(f"\nVisualization: {result['visualization_path']}")
                
                print(f"\nExecution time: {result['execution_time']:.2f} seconds")
        else:
            # Run the standard test set
            queries = create_test_queries()
            
            # Filter by category if specified
            if args.category:
                queries = [q for q in queries if args.category.lower() in q["category"].lower()]
                
            if not queries:
                logger.error(f"No queries found for category: {args.category}")
                sys.exit(1)
                
            logger.info(f"Running {len(queries)} test queries")
            
            # Run each test query
            for i, query_info in enumerate(queries):
                logger.info(f"Test {i+1}/{len(queries)}")
                result = run_multihop_test(rag, driver, query_info, args.direct, viz_dir)
                results.append(result)
            
            # Save the test results
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            result_path = os.path.join(args.output, f"multihop_test_results_{timestamp}.json")
            
            with open(result_path, 'w') as f:
                json.dump(results, f, indent=2)
                
            logger.info(f"Test results saved to {result_path}")
            
            # Print summary
            print("\n" + "="*80)
            print("Multihop Reasoning Test Summary")
            print("="*80)
            print(f"Total queries: {len(results)}")
            
            # Count successes and failures
            successes = len([r for r in results if "error" not in r])
            failures = len(results) - successes
            
            print(f"Successful tests: {successes}")
            print(f"Failed tests: {failures}")
            
            # Summary by complexity
            by_complexity = {}
            for result in results:
                complexity = result.get("complexity", "Unknown")
                if complexity not in by_complexity:
                    by_complexity[complexity] = {"total": 0, "success": 0}
                by_complexity[complexity]["total"] += 1
                if "error" not in result:
                    by_complexity[complexity]["success"] += 1
            
            print("\nBy Complexity:")
            for complexity, stats in by_complexity.items():
                success_rate = (stats["success"] / stats["total"]) * 100
                print(f"  {complexity}: {stats['success']}/{stats['total']} ({success_rate:.1f}%)")
            
            # Average execution time
            avg_time = sum(r.get("execution_time", 0) for r in results) / len(results)
            print(f"\nAverage execution time: {avg_time:.2f} seconds")
            
            # Multihop detection accuracy
            multihop_queries = len([q for q in queries if q["complexity"] != "Simple"])
            correct_detection = sum(1 for r in results 
                                if (r.get("complexity") != "Simple" and r.get("is_multihop_detected", False)) or
                                   (r.get("complexity") == "Simple" and not r.get("is_multihop_detected", False)))
            
            detection_accuracy = (correct_detection / len(results)) * 100
            print(f"Multihop detection accuracy: {detection_accuracy:.1f}%")
        
    except Exception as e:
        logger.error(f"Error running tests: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # Clean up
        if 'rag' in locals():
            rag.close()

if __name__ == "__main__":
    main() 