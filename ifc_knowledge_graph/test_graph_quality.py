#!/usr/bin/env python
"""
Graph Quality Analysis Test Script

This script demonstrates the use of the GraphQualityAnalyzer to validate,
clean, and report on the quality of the IFC Knowledge Graph in Neo4j.
"""

import os
import logging
import sys
import json
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the package to the path
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

try:
    # Import required modules
    from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector
    from src.ifc_to_graph.utils.graph_quality_analyzer import GraphQualityAnalyzer
    
    def main():
        """Main entry point for the graph quality analysis test."""
        try:
            # Initialize the Neo4j connector
            connector = Neo4jConnector(
                uri="bolt://localhost:7687",
                user="neo4j",
                password="test1234"  # Use your actual password
            )
            
            logger.info("Initializing Graph Quality Analyzer")
            
            # Initialize the GraphQualityAnalyzer
            analyzer = GraphQualityAnalyzer(connector)
            
            # 1. Validate the graph
            logger.info("Starting graph validation")
            validation_results = analyzer.validate_graph()
            
            print("\n===== VALIDATION RESULTS =====")
            print(f"Overall graph quality score: {validation_results.get('overall_score', 0):.2f}/100")
            
            for key, result in validation_results.items():
                if isinstance(result, dict) and key != "overall_score":
                    print(f"\n--- {key.replace('_', ' ').title()} ---")
                    print(f"Valid: {result.get('valid', False)}")
                    print(f"Score: {result.get('score', 0):.2f}/100")
                    
                    if result.get('issues'):
                        print("Issues:")
                        for issue in result.get('issues', []):
                            print(f"  - {issue}")
            
            # 2. Clean identified issues
            if validation_results.get('overall_score', 100) < 90:
                logger.info("Quality score below 90, cleaning graph issues")
                
                clean_options = {
                    "remove_orphans": True,
                    "fix_relationships": True,
                    "fix_properties": True,
                    "fix_topological": True
                }
                
                cleaning_results = analyzer.clean_graph_issues(clean_options)
                
                print("\n===== CLEANING RESULTS =====")
                print(f"Actions taken: {', '.join(cleaning_results.get('actions_taken', []))}")
                print(f"Nodes modified: {cleaning_results.get('nodes_modified', 0)}")
                print(f"Nodes deleted: {cleaning_results.get('nodes_deleted', 0)}")
                print(f"Relationships modified: {cleaning_results.get('relationships_modified', 0)}")
                print(f"Relationships deleted: {cleaning_results.get('relationships_deleted', 0)}")
                
                # Re-validate after cleaning
                logger.info("Re-validating graph after cleaning")
                new_validation_results = analyzer.validate_graph()
                print(f"\nNew quality score: {new_validation_results.get('overall_score', 0):.2f}/100")
            
            # 3. Generate comprehensive report
            logger.info("Generating comprehensive graph quality report")
            report = analyzer.generate_report(include_details=True)
            
            # Print graph statistics
            print("\n===== GRAPH STATISTICS =====")
            stats = report["graph_statistics"]
            
            print(f"Total nodes: {stats.get('totalNodes', 'N/A')}")
            print(f"Total relationships: {stats.get('totalRelationships', 'N/A')}")
            
            if "nodeCountsByLabel" in stats:
                print("\nNode counts by label:")
                for label, count in list(stats["nodeCountsByLabel"].items())[:5]:  # Show top 5
                    print(f"  {label}: {count}")
                
                if len(stats["nodeCountsByLabel"]) > 5:
                    print(f"  ... and {len(stats['nodeCountsByLabel']) - 5} more")
            
            if "relationshipCountsByType" in stats:
                print("\nRelationship counts by type:")
                for rel_type, count in list(stats["relationshipCountsByType"].items())[:5]:  # Show top 5
                    print(f"  {rel_type}: {count}")
                
                if len(stats["relationshipCountsByType"]) > 5:
                    print(f"  ... and {len(stats['relationshipCountsByType']) - 5} more")
            
            # 4. Export the report to a JSON file
            export_path = os.path.join(current_dir, "reports", "graph_quality_report.json")
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            
            if analyzer.export_report_to_json(export_path):
                logger.info(f"Report exported to {export_path}")
            
            # 5. Get detailed schema statistics
            logger.info("Getting detailed schema statistics")
            schema_stats = analyzer.get_schema_statistics()
            
            # Print schema constraints and indexes
            if "constraints" in schema_stats:
                print("\n===== SCHEMA CONSTRAINTS =====")
                for constraint in schema_stats["constraints"][:3]:  # Show first 3 constraints
                    print(f"  {constraint}")
                    
                if len(schema_stats["constraints"]) > 3:
                    print(f"  ... and {len(schema_stats['constraints']) - 3} more")
            
            if "indexes" in schema_stats:
                print("\n===== SCHEMA INDEXES =====")
                for index in schema_stats["indexes"][:3]:  # Show first 3 indexes
                    print(f"  {index}")
                    
                if len(schema_stats["indexes"]) > 3:
                    print(f"  ... and {len(schema_stats['indexes']) - 3} more")
            
            logger.info("Graph quality analysis completed successfully")
            return 0
            
        except Exception as e:
            logger.exception(f"Error in graph quality analysis: {str(e)}")
            return 1

    if __name__ == "__main__":
        sys.exit(main())
        
except Exception as e:
    print(f"Import error: {str(e)}")
    import traceback
    traceback.print_exc() 