#!/usr/bin/env python3
"""
Schema Analyzer Tool

This tool analyzes the Neo4j database schema for IFC building data and provides
recommendations to improve query accuracy and performance.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.append(str(Path(__file__).parent.parent))

from neo4j import GraphDatabase
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
        description="Analyze Neo4j schema for IFC building data and provide query recommendations"
    )
    parser.add_argument(
        "--uri", 
        default=os.environ.get("NEO4J_URI", "neo4j://localhost:7687"),
        help="Neo4j connection URI"
    )
    parser.add_argument(
        "--username", 
        default=os.environ.get("NEO4J_USERNAME", "neo4j"),
        help="Neo4j username"
    )
    parser.add_argument(
        "--password", 
        default=os.environ.get("NEO4J_PASSWORD", "test1234"),
        help="Neo4j password"
    )
    parser.add_argument(
        "--output",
        help="Output file for schema report (JSON format)",
        default="schema_report.json"
    )
    parser.add_argument(
        "--query",
        help="Test a specific Cypher query against the schema",
        default=None
    )
    parser.add_argument(
        "--generate-prompt",
        action="store_true",
        help="Generate an enhanced schema prompt for LLM"
    )
    parser.add_argument(
        "--verify-query",
        help="Verify a natural language query against the schema",
        default=None
    )
    return parser.parse_args()

def check_connectivity(uri, username, password):
    """Check connectivity to Neo4j database."""
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

def analyze_schema(driver, output_file):
    """Analyze the Neo4j schema and write report to file."""
    logger.info("Analyzing Neo4j schema...")
    
    # Initialize schema mapper
    mapper = SchemaMapper(driver)
    
    # Refresh schema information
    schema_info = mapper.refresh_schema()
    
    # Check for missing relationships
    missing_rels = mapper.find_missing_relationships()
    
    # Generate recommendations based on schema analysis
    recommendations = []
    
    # Check for node labels that should have relationships but don't
    if "Roof" in schema_info["node_labels"] and "Skylight" in schema_info["node_labels"]:
        roof_skylight_query = """
        MATCH (roof:Roof)-[:CONTAINS]->(skylight:Skylight)
        RETURN count(*) as count
        """
        with driver.session() as session:
            result = session.run(roof_skylight_query).single()
            if not result or result["count"] == 0:
                recommendations.append({
                    "type": "missing_relationship",
                    "description": "Roof-to-Skylight relationship missing",
                    "impact": "Queries about skylights on roofs will return no results",
                    "suggested_fix": "Ensure Roof nodes are properly connected to Skylight nodes with CONTAINS relationships"
                })
    
    # Check for potentially incorrect node labels
    if "Skylight" not in schema_info["node_labels"] and "Opening" in schema_info["node_labels"]:
        recommendations.append({
            "type": "label_terminology",
            "description": "Skylight elements may be represented as Opening nodes",
            "impact": "Queries for Skylight will return no results",
            "suggested_fix": "Use Opening labels instead of Skylight in queries, or check if roof openings should be labeled as skylights"
        })
    
    # Add general recommendations
    recommendations.append({
        "type": "query_pattern",
        "description": "Use variable-length paths for spatial relationship queries",
        "impact": "Improves recall for complex spatial queries",
        "example": "MATCH (space:Space)-[:BOUNDED_BY*1..2]->(element) RETURN element"
    })
    
    # Add missing relationship recommendations
    for rel in missing_rels:
        recommendations.append({
            "type": "missing_relationship",
            "description": f"Missing {rel['source']}-[:{rel['relationship']}]->{rel['target']} relationship",
            "impact": f"Queries traversing from {rel['source']} to {rel['target']} via {rel['relationship']} will return no results",
            "suggested_fix": f"Check if this relationship should exist in your IFC model"
        })
    
    # Create report dictionary
    report = {
        "schema_summary": {
            "node_labels": len(schema_info["node_labels"]),
            "relationship_types": len(schema_info["relationship_types"]),
            "property_keys": len(schema_info["property_keys"])
        },
        "node_labels": schema_info["node_labels"],
        "relationship_types": schema_info["relationship_types"],
        "label_counts": schema_info["label_counts"],
        "relationship_counts": schema_info["relationship_counts"],
        "hierarchical_paths": schema_info["hierarchical_paths"],
        "missing_relationships": missing_rels,
        "recommendations": recommendations
    }
    
    # Write report to file
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Schema analysis complete. Report written to {output_file}")
    
    return report, mapper

def test_query(mapper, query):
    """Test a specific Cypher query against the schema."""
    logger.info(f"Testing query: {query}")
    
    # Validate query against schema
    validation = mapper.validate_query_against_schema(query)
    
    # Test query execution if it's valid or has a fixed version
    test_results = None
    if validation["is_valid"] or "fixed_query" in validation:
        test_results = mapper.test_query(query)
    
    # Combine results
    results = {
        "query": query,
        "validation": validation,
        "execution_results": test_results
    }
    
    # Pretty print results
    print("\nQuery Test Results:")
    print(f"Original Query: {query}")
    
    if not validation["is_valid"]:
        print("\nValidation Warnings:")
        for warning in validation["warnings"]:
            print(f"  - {warning}")
    
    if validation["suggestions"]:
        print("\nSuggestions:")
        for suggestion in validation["suggestions"]:
            print(f"  - {suggestion}")
    
    if "fixed_query" in validation:
        print(f"\nSuggested Fixed Query: {validation['fixed_query']}")
    
    if test_results:
        print(f"\nQuery Execution: {'Successful' if test_results['executed'] else 'Failed'}")
        if test_results.get("error"):
            print(f"Error: {test_results['error']}")
        else:
            print(f"Result Count: {test_results['result_count']}")
            print(f"Execution Time: {test_results['execution_time_ms']} ms")
            
            if test_results.get("sample_results"):
                print("\nSample Results:")
                for i, result in enumerate(test_results["sample_results"]):
                    print(f"  Result {i+1}: {result}")
    
    return results

def generate_schema_prompt(mapper):
    """Generate an enhanced schema prompt for LLM."""
    prompt = mapper.enhance_schema_prompt()
    
    # Print to console
    print("\nEnhanced Schema Prompt for LLM:")
    print(prompt)
    
    # Save to file
    with open("schema_prompt.txt", "w") as f:
        f.write(prompt)
    
    logger.info("Enhanced schema prompt saved to schema_prompt.txt")
    
    return prompt

def main():
    """Main entry point for the script."""
    args = parse_args()
    
    # Check connectivity
    driver = check_connectivity(args.uri, args.username, args.password)
    
    try:
        # Analyze schema
        report, mapper = analyze_schema(driver, args.output)
        
        # Test a specific query if provided
        if args.query:
            test_query(mapper, args.query)
        
        # Generate enhanced schema prompt if requested
        if args.generate_prompt:
            generate_schema_prompt(mapper)
            
    finally:
        # Close the driver
        driver.close()

if __name__ == "__main__":
    main() 