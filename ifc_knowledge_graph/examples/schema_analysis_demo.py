#!/usr/bin/env python3
"""
Schema Analysis Demo

This script demonstrates how to use the schema analysis tools
to improve query accuracy in BIMConverse GraphRAG.
"""

import os
import sys
import argparse
import json
import logging
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.append(str(Path(__file__).parent.parent))

from neo4j import GraphDatabase
from bimconverse.core import BIMConverseRAG
from bimconverse.schema import SchemaMapper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Demo for schema analysis and query improvement"
    )
    parser.add_argument(
        "--config", 
        default="config.json",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--query",
        default="Does the roof have skylights?",
        help="Natural language query to test"
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only analyze schema without running a query"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare results with and without schema validation"
    )
    return parser.parse_args()

def load_config(config_path):
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading config from {config_path}: {e}")
        sys.exit(1)

def connect_to_neo4j(config):
    """Establish connection to Neo4j database."""
    uri = config["neo4j"]["uri"]
    username = config["neo4j"]["username"]
    password = config["neo4j"]["password"]
    
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        with driver.session() as session:
            result = session.run("RETURN 1 as test").single()
            if result and result["test"] == 1:
                logger.info("Successfully connected to Neo4j")
                return driver
            else:
                logger.error("Connection test failed")
                sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        sys.exit(1)

def analyze_schema(driver):
    """Analyze the Neo4j schema."""
    logger.info("Analyzing schema...")
    
    # Initialize schema mapper
    mapper = SchemaMapper(driver)
    
    # Get schema information
    schema_info = mapper.refresh_schema()
    
    # Print schema summary
    logger.info(f"Found {len(schema_info['node_labels'])} node labels")
    logger.info(f"Found {len(schema_info['relationship_types'])} relationship types")
    
    # Check for specific IFC elements
    if "Roof" in schema_info["node_labels"]:
        logger.info("Roof elements are present in the schema")
    else:
        logger.warning("No Roof elements found in the schema")
    
    if "Skylight" in schema_info["node_labels"]:
        logger.info("Skylight elements are present in the schema")
    else:
        logger.warning("No Skylight elements found in the schema")
        if "Opening" in schema_info["node_labels"]:
            logger.info("Opening elements found - might represent skylights")
    
    # Check for missing relationships
    missing_rels = mapper.find_missing_relationships()
    if missing_rels:
        logger.warning(f"Found {len(missing_rels)} missing expected relationships")
        for rel in missing_rels:
            logger.warning(f"Missing: ({rel['source']})-[:{rel['relationship']}]->({rel['target']})")
    else:
        logger.info("No missing relationships found")
    
    # Generate enhanced schema prompt
    enhanced_prompt = mapper.enhance_schema_prompt()
    with open("enhanced_schema_prompt.txt", "w") as f:
        f.write(enhanced_prompt)
    logger.info("Enhanced schema prompt saved to enhanced_schema_prompt.txt")
    
    return mapper

def test_query_with_schema_validation(rag, query, schema_mapper=None):
    """Test a query with schema validation."""
    logger.info(f"Testing query with schema validation: {query}")
    
    # Save original system prompt
    original_prompt = None
    if hasattr(rag.llm, "system_prompt"):
        original_prompt = rag.llm.system_prompt
    
    # Set enhanced schema prompt if available
    if schema_mapper:
        enhanced_prompt = schema_mapper.enhance_schema_prompt()
        if hasattr(rag.llm, "system_prompt"):
            rag.llm.system_prompt = enhanced_prompt
            logger.info("Set enhanced schema prompt")
    
    # Configure multihop retriever to use schema validation
    if hasattr(rag, "multihop_retriever") and rag.multihop_retriever:
        rag.multihop_retriever.schema_mapper = schema_mapper
    
    # Run the query
    result = rag.query(query)
    
    # Restore original prompt
    if original_prompt is not None and hasattr(rag.llm, "system_prompt"):
        rag.llm.system_prompt = original_prompt
    
    return result

def test_query_without_schema_validation(rag, query):
    """Test a query without schema validation."""
    logger.info(f"Testing query without schema validation: {query}")
    
    # Disable schema validation for multihop retriever
    if hasattr(rag, "multihop_retriever") and rag.multihop_retriever:
        rag.multihop_retriever.schema_mapper = None
    
    # Run the query
    result = rag.query(query)
    
    return result

def compare_query_results(result1, result2):
    """Compare results with and without schema validation."""
    print("\n=== QUERY RESULTS COMPARISON ===")
    
    # Extract key information from results
    def extract_info(result):
        if hasattr(result, "answer"):
            answer = result.answer
        elif isinstance(result, dict) and "result_text" in result:
            answer = result["result_text"]
        elif isinstance(result, dict) and "final_answer" in result:
            answer = result["final_answer"]
        else:
            answer = str(result)
            
        if isinstance(result, dict) and "cypher" in result:
            cypher = result["cypher"]
        elif hasattr(result, "metadata") and "cypher" in result.metadata:
            cypher = result.metadata["cypher"]
        else:
            cypher = "No Cypher query found"
            
        return {"answer": answer, "cypher": cypher}
    
    info1 = extract_info(result1)
    info2 = extract_info(result2)
    
    print("\n--- Without Schema Validation ---")
    print(f"Cypher: {info1['cypher']}")
    print(f"Answer: {info1['answer']}")
    
    print("\n--- With Schema Validation ---")
    print(f"Cypher: {info2['cypher']}")
    print(f"Answer: {info2['answer']}")
    
    return

def main():
    """Main entry point for the script."""
    args = parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Connect to Neo4j
    driver = connect_to_neo4j(config)
    
    try:
        # Analyze schema
        schema_mapper = analyze_schema(driver)
        
        # Exit early if only analyzing schema
        if args.analyze_only:
            logger.info("Schema analysis complete")
            return
        
        # Initialize BIMConverseRAG
        rag = BIMConverseRAG(
            config_path=args.config,
            neo4j_driver=driver
        )
        
        # Prepare API key for OpenAI
        if "openai" in config and "api_key" in config["openai"]:
            os.environ["OPENAI_API_KEY"] = config["openai"]["api_key"]
        
        # Test query
        if args.compare:
            # Run without schema validation
            result_without = test_query_without_schema_validation(rag, args.query)
            
            # Run with schema validation
            result_with = test_query_with_schema_validation(rag, args.query, schema_mapper)
            
            # Compare results
            compare_query_results(result_without, result_with)
        else:
            # Run with schema validation
            result = test_query_with_schema_validation(rag, args.query, schema_mapper)
            
            # Display result
            if hasattr(result, "answer"):
                print(f"\nQuery: {args.query}")
                print(f"Answer: {result.answer}")
            elif isinstance(result, dict):
                print(f"\nQuery: {args.query}")
                if "result_text" in result:
                    print(f"Answer: {result['result_text']}")
                elif "final_answer" in result:
                    print(f"Answer: {result['final_answer']}")
                else:
                    print(f"Result: {json.dumps(result, indent=2, default=str)}")
            else:
                print(f"\nResult: {result}")
                
    finally:
        # Close the driver
        driver.close()

if __name__ == "__main__":
    main() 