"""
Graph Quality Analyzer

This module provides functionality for analyzing, validating, and cleaning
the quality of the IFC Knowledge Graph in Neo4j.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple, Set
import networkx as nx
from collections import Counter, defaultdict

# Configure logging
logger = logging.getLogger(__name__)


class GraphQualityAnalyzer:
    """
    Analyzes the quality of the Neo4j graph database and provides methods
    for validation, cleaning, and reporting on the graph structure.
    """
    
    def __init__(self, connector):
        """
        Initialize the GraphQualityAnalyzer with a Neo4j connector.
        
        Args:
            connector: Neo4jConnector instance
        """
        self.connector = connector
        self.validation_results = {}
        self.report_data = {}
    
    # --- VALIDATION METHODS ---
    
    def validate_graph(self) -> Dict[str, Any]:
        """
        Perform a comprehensive validation of the graph database.
        
        Returns:
            Dictionary with validation results
        """
        logger.info("Starting comprehensive graph validation")
        
        # Reset validation results
        self.validation_results = {}
        
        # Run individual validations
        self.validation_results["schema_consistency"] = self.validate_schema_consistency()
        self.validation_results["relationship_integrity"] = self.validate_relationship_integrity()
        self.validation_results["orphan_nodes"] = self.find_orphan_nodes()
        self.validation_results["property_completeness"] = self.validate_property_completeness()
        self.validation_results["ifc_reference_integrity"] = self.validate_ifc_references()
        self.validation_results["topological_consistency"] = self.validate_topological_consistency()
        
        # Calculate overall quality score
        scores = [result.get("score", 0) for result in self.validation_results.values() 
                 if isinstance(result, dict) and "score" in result]
        
        if scores:
            self.validation_results["overall_score"] = sum(scores) / len(scores)
        else:
            self.validation_results["overall_score"] = 0
            
        logger.info(f"Graph validation completed with overall score: {self.validation_results['overall_score']}")
        
        return self.validation_results
    
    def validate_schema_consistency(self) -> Dict[str, Any]:
        """
        Validate the consistency of the graph schema.
        Checks for correct node labels, relationship types, and property existence.
        
        Returns:
            Dictionary with validation results
        """
        logger.info("Validating schema consistency")
        
        result = {
            "valid": True,
            "score": 100,
            "issues": [],
            "details": {}
        }
        
        try:
            # Check node label consistency
            node_label_query = """
            MATCH (n)
            WITH labels(n) AS nodeLabels, count(*) AS count
            RETURN nodeLabels, count
            ORDER BY count DESC
            """
            
            node_labels = self.connector.run_query(node_label_query)
            
            # Check relationship type consistency
            rel_type_query = """
            MATCH ()-[r]->()
            WITH type(r) AS relType, count(*) AS count
            RETURN relType, count
            ORDER BY count DESC
            """
            
            rel_types = self.connector.run_query(rel_type_query)
            
            # Check required property existence (GlobalId is required for elements)
            missing_globalid_query = """
            MATCH (n:Element)
            WHERE NOT EXISTS(n.GlobalId)
            RETURN count(n) AS missingGlobalIdCount
            """
            
            missing_globalid = self.connector.run_query(missing_globalid_query)
            
            if missing_globalid and missing_globalid[0]["missingGlobalIdCount"] > 0:
                result["valid"] = False
                result["score"] -= min(50, missing_globalid[0]["missingGlobalIdCount"])
                result["issues"].append(f"Found {missing_globalid[0]['missingGlobalIdCount']} nodes missing required GlobalId property")
            
            # Store details for reporting
            result["details"]["nodeLabels"] = node_labels
            result["details"]["relationshipTypes"] = rel_types
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating schema consistency: {str(e)}")
            result["valid"] = False
            result["score"] = 0
            result["issues"].append(f"Error during validation: {str(e)}")
            return result
    
    def validate_relationship_integrity(self) -> Dict[str, Any]:
        """
        Validate the integrity of relationships in the graph.
        Checks for relationship consistency and correctness.
        
        Returns:
            Dictionary with validation results
        """
        logger.info("Validating relationship integrity")
        
        result = {
            "valid": True,
            "score": 100,
            "issues": [],
            "details": {}
        }
        
        try:
            # Check for dangling relationships (uncommon in Neo4j but good to verify)
            dangling_rel_query = """
            MATCH ()-[r]->()
            WHERE NOT EXISTS(startNode(r)) OR NOT EXISTS(endNode(r))
            RETURN count(r) AS danglingRelCount
            """
            
            dangling_rels = self.connector.run_query(dangling_rel_query)
            
            if dangling_rels and dangling_rels[0]["danglingRelCount"] > 0:
                result["valid"] = False
                result["score"] -= min(50, dangling_rels[0]["danglingRelCount"] * 10)
                result["issues"].append(f"Found {dangling_rels[0]['danglingRelCount']} dangling relationships")
            
            # Check for invalid relationship types between specific node labels
            invalid_rel_query = """
            MATCH (a:Space)-[r:CONTAINS]->(b:Space)
            RETURN count(r) AS invalidContainsCount
            """
            
            invalid_rels = self.connector.run_query(invalid_rel_query)
            
            if invalid_rels and invalid_rels[0]["invalidContainsCount"] > 0:
                result["valid"] = False
                result["score"] -= min(20, invalid_rels[0]["invalidContainsCount"] * 5)
                result["issues"].append(f"Found {invalid_rels[0]['invalidContainsCount']} invalid CONTAINS relationships between Space nodes")
            
            # Check relationship cardinality for IFC hierarchy
            hierarchy_query = """
            MATCH (s:Storey)<-[:CONTAINS]-(b)
            WITH s, count(b) AS buildingCount
            WHERE buildingCount > 1
            RETURN count(s) AS multipleParentStoreys
            """
            
            hierarchy_issues = self.connector.run_query(hierarchy_query)
            
            if hierarchy_issues and hierarchy_issues[0]["multipleParentStoreys"] > 0:
                result["valid"] = False
                result["score"] -= min(30, hierarchy_issues[0]["multipleParentStoreys"] * 5)
                result["issues"].append(f"Found {hierarchy_issues[0]['multipleParentStoreys']} Storey nodes with multiple parent buildings")
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating relationship integrity: {str(e)}")
            result["valid"] = False
            result["score"] = 0
            result["issues"].append(f"Error during validation: {str(e)}")
            return result
    
    def find_orphan_nodes(self) -> Dict[str, Any]:
        """
        Find nodes without any relationships (orphan nodes).
        
        Returns:
            Dictionary with validation results
        """
        logger.info("Finding orphan nodes")
        
        result = {
            "valid": True,
            "score": 100,
            "issues": [],
            "details": {}
        }
        
        try:
            # Find nodes without any relationships
            orphan_query = """
            MATCH (n)
            WHERE NOT (n)--()
            RETURN labels(n) AS nodeLabels, count(*) AS count
            ORDER BY count DESC
            """
            
            orphans = self.connector.run_query(orphan_query)
            
            total_orphans = sum(record["count"] for record in orphans)
            
            if total_orphans > 0:
                # Only consider it an issue if there are significant orphans
                if total_orphans > 10:
                    result["valid"] = False
                    result["score"] -= min(50, total_orphans)
                    result["issues"].append(f"Found {total_orphans} orphan nodes with no relationships")
                
                # Store detailed breakdown by node label
                result["details"]["orphansByLabel"] = orphans
            
            return result
            
        except Exception as e:
            logger.error(f"Error finding orphan nodes: {str(e)}")
            result["valid"] = False
            result["score"] = 0
            result["issues"].append(f"Error during validation: {str(e)}")
            return result
    
    def validate_property_completeness(self) -> Dict[str, Any]:
        """
        Validate the completeness of properties on nodes.
        Checks for missing required properties and property value consistency.
        
        Returns:
            Dictionary with validation results
        """
        logger.info("Validating property completeness")
        
        result = {
            "valid": True,
            "score": 100,
            "issues": [],
            "details": {}
        }
        
        try:
            # Define required properties for each node label
            required_properties = {
                "Element": ["GlobalId", "Name"],
                "Space": ["GlobalId", "Name"],
                "Storey": ["GlobalId", "Name", "Elevation"],
                "Building": ["GlobalId", "Name"],
                "Site": ["GlobalId", "Name"]
            }
            
            property_issues = []
            
            # Check each node type for missing required properties
            for label, properties in required_properties.items():
                for prop in properties:
                    missing_prop_query = f"""
                    MATCH (n:{label})
                    WHERE NOT EXISTS(n.{prop}) OR n.{prop} IS NULL
                    RETURN count(n) AS missingCount
                    """
                    
                    missing_prop = self.connector.run_query(missing_prop_query)
                    
                    if missing_prop and missing_prop[0]["missingCount"] > 0:
                        property_issues.append({
                            "label": label,
                            "property": prop,
                            "missingCount": missing_prop[0]["missingCount"]
                        })
            
            # Calculate score reduction based on missing properties
            total_missing = sum(issue["missingCount"] for issue in property_issues)
            
            if total_missing > 0:
                result["valid"] = False
                result["score"] -= min(70, total_missing)
                result["issues"].append(f"Found {total_missing} nodes with missing required properties")
                result["details"]["missingProperties"] = property_issues
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating property completeness: {str(e)}")
            result["valid"] = False
            result["score"] = 0
            result["issues"].append(f"Error during validation: {str(e)}")
            return result
    
    def validate_ifc_references(self) -> Dict[str, Any]:
        """
        Validate the integrity of IFC references in the graph.
        Checks if IFC entities referenced by GlobalId exist and are consistent.
        
        Returns:
            Dictionary with validation results
        """
        logger.info("Validating IFC references")
        
        result = {
            "valid": True,
            "score": 100,
            "issues": [],
            "details": {}
        }
        
        try:
            # Check for duplicate GlobalIds (should be unique)
            duplicate_globalid_query = """
            MATCH (n) 
            WHERE EXISTS(n.GlobalId)
            WITH n.GlobalId AS gid, collect(n) AS nodes
            WHERE size(nodes) > 1
            RETURN gid, size(nodes) AS dupeCount
            LIMIT 100
            """
            
            duplicate_globalids = self.connector.run_query(duplicate_globalid_query)
            
            if duplicate_globalids:
                dup_count = len(duplicate_globalids)
                result["valid"] = False
                result["score"] -= min(50, dup_count * 10)
                result["issues"].append(f"Found {dup_count} GlobalIds with duplicate nodes")
                result["details"]["duplicateGlobalIds"] = duplicate_globalids
            
            # Check for invalid GlobalId format
            invalid_globalid_query = """
            MATCH (n) 
            WHERE EXISTS(n.GlobalId) AND 
                  n.GlobalId IS NOT NULL AND
                  size(n.GlobalId) < 22
            RETURN count(n) AS invalidGlobalIdCount
            """
            
            invalid_globalids = self.connector.run_query(invalid_globalid_query)
            
            if invalid_globalids and invalid_globalids[0]["invalidGlobalIdCount"] > 0:
                result["valid"] = False
                result["score"] -= min(30, invalid_globalids[0]["invalidGlobalIdCount"])
                result["issues"].append(f"Found {invalid_globalids[0]['invalidGlobalIdCount']} nodes with invalid GlobalId format")
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating IFC references: {str(e)}")
            result["valid"] = False
            result["score"] = 0
            result["issues"].append(f"Error during validation: {str(e)}")
            return result
    
    def validate_topological_consistency(self) -> Dict[str, Any]:
        """
        Validate the consistency of topological relationships.
        Checks if topological relationships are correctly defined.
        
        Returns:
            Dictionary with validation results
        """
        logger.info("Validating topological consistency")
        
        result = {
            "valid": True,
            "score": 100,
            "issues": [],
            "details": {}
        }
        
        try:
            # Check for consistency between ADJACENT and ADJACENT_TO relationships
            adjacency_query = """
            MATCH (a)-[r:ADJACENT]->(b)
            WHERE NOT (a)-[:ADJACENT_TO]-(b)
            RETURN count(r) AS inconsistentCount
            """
            
            inconsistent_adjacency = self.connector.run_query(adjacency_query)
            
            if inconsistent_adjacency and inconsistent_adjacency[0]["inconsistentCount"] > 0:
                inc_count = inconsistent_adjacency[0]["inconsistentCount"]
                result["valid"] = False
                result["score"] -= min(40, inc_count)
                result["issues"].append(f"Found {inc_count} inconsistent ADJACENT relationships without corresponding ADJACENT_TO")
            
            # Check for bidirectional consistency in containment relationships
            containment_query = """
            MATCH (a)-[r:CONTAINS_TOPOLOGICALLY]->(b)
            WHERE NOT (b)-[:IS_CONTAINED_IN]->(a)
            RETURN count(r) AS inconsistentCount
            """
            
            inconsistent_containment = self.connector.run_query(containment_query)
            
            if inconsistent_containment and inconsistent_containment[0]["inconsistentCount"] > 0:
                inc_count = inconsistent_containment[0]["inconsistentCount"]
                result["valid"] = False
                result["score"] -= min(40, inc_count)
                result["issues"].append(f"Found {inc_count} inconsistent containment relationships missing inverse IS_CONTAINED_IN")
            
            # Check for self-relationships
            self_rel_query = """
            MATCH (a)-[r]->(a)
            RETURN type(r) AS relType, count(r) AS count
            ORDER BY count DESC
            """
            
            self_relationships = self.connector.run_query(self_rel_query)
            
            if self_relationships and sum(record["count"] for record in self_relationships) > 0:
                total_self_rels = sum(record["count"] for record in self_relationships)
                result["valid"] = False
                result["score"] -= min(20, total_self_rels * 2)
                result["issues"].append(f"Found {total_self_rels} self-relationships (node relating to itself)")
                result["details"]["selfRelationships"] = self_relationships
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating topological consistency: {str(e)}")
            result["valid"] = False
            result["score"] = 0
            result["issues"].append(f"Error during validation: {str(e)}")
            return result
    
    # --- DATA CLEANING METHODS ---
    
    def clean_graph_issues(self, clean_options: Dict[str, bool] = None) -> Dict[str, Any]:
        """
        Clean issues found in the graph based on validation results.
        
        Args:
            clean_options: Dictionary of cleaning options to enable/disable specific cleaners
            
        Returns:
            Dictionary with cleaning results
        """
        logger.info("Starting graph data cleaning")
        
        if clean_options is None:
            clean_options = {
                "remove_orphans": True,
                "fix_relationships": True,
                "fix_properties": True,
                "fix_topological": True
            }
        
        # Validate the graph first if not already validated
        if not self.validation_results:
            self.validate_graph()
        
        cleaning_results = {
            "actions_taken": [],
            "nodes_modified": 0,
            "relationships_modified": 0,
            "nodes_deleted": 0,
            "relationships_deleted": 0
        }
        
        # Clean orphan nodes if enabled
        if clean_options.get("remove_orphans", True):
            orphan_results = self.clean_orphan_nodes()
            cleaning_results["actions_taken"].append("Cleaned orphan nodes")
            cleaning_results["nodes_deleted"] += orphan_results.get("nodes_deleted", 0)
        
        # Fix relationship issues if enabled
        if clean_options.get("fix_relationships", True):
            rel_results = self.fix_relationship_issues()
            cleaning_results["actions_taken"].append("Fixed relationship issues")
            cleaning_results["relationships_modified"] += rel_results.get("relationships_modified", 0)
            cleaning_results["relationships_deleted"] += rel_results.get("relationships_deleted", 0)
        
        # Fix property issues if enabled
        if clean_options.get("fix_properties", True):
            prop_results = self.fix_property_issues()
            cleaning_results["actions_taken"].append("Fixed property issues")
            cleaning_results["nodes_modified"] += prop_results.get("nodes_modified", 0)
        
        # Fix topological consistency issues if enabled
        if clean_options.get("fix_topological", True):
            topo_results = self.fix_topological_issues()
            cleaning_results["actions_taken"].append("Fixed topological consistency issues")
            cleaning_results["relationships_modified"] += topo_results.get("relationships_modified", 0)
            cleaning_results["relationships_created"] = topo_results.get("relationships_created", 0)
        
        logger.info(f"Graph cleaning completed: {cleaning_results}")
        return cleaning_results
    
    def clean_orphan_nodes(self) -> Dict[str, int]:
        """
        Remove orphan nodes from the graph.
        
        Returns:
            Dictionary with cleaning results
        """
        logger.info("Cleaning orphan nodes")
        
        results = {
            "nodes_deleted": 0
        }
        
        try:
            # Delete orphan nodes
            delete_query = """
            MATCH (n)
            WHERE NOT (n)--()
            WITH n, labels(n) AS labels
            // Don't delete certain types of nodes even if orphaned
            WHERE NOT any(label IN labels WHERE label IN ['Project', 'Site', 'Building'])
            DELETE n
            RETURN count(n) AS deletedCount
            """
            
            deleted = self.connector.run_query(delete_query)
            
            if deleted:
                results["nodes_deleted"] = deleted[0]["deletedCount"]
                logger.info(f"Deleted {results['nodes_deleted']} orphan nodes")
                
            return results
            
        except Exception as e:
            logger.error(f"Error cleaning orphan nodes: {str(e)}")
            return results
    
    def fix_relationship_issues(self) -> Dict[str, int]:
        """
        Fix relationship issues in the graph.
        
        Returns:
            Dictionary with cleaning results
        """
        logger.info("Fixing relationship issues")
        
        results = {
            "relationships_modified": 0,
            "relationships_deleted": 0
        }
        
        try:
            # Delete invalid space to space containment relationships
            delete_query = """
            MATCH (a:Space)-[r:CONTAINS]->(b:Space)
            DELETE r
            RETURN count(r) AS deletedCount
            """
            
            deleted = self.connector.run_query(delete_query)
            
            if deleted:
                results["relationships_deleted"] += deleted[0]["deletedCount"]
                logger.info(f"Deleted {deleted[0]['deletedCount']} invalid space-to-space CONTAINS relationships")
            
            # Remove duplicate relationships
            dedup_query = """
            MATCH (a)-[r1:CONNECTED_TO]->(b)
            WITH a, b, collect(r1) as rels
            WHERE size(rels) > 1
            WITH a, b, rels[0] as r1, rels[1..] as duplicates
            UNWIND duplicates as r2
            DELETE r2
            RETURN count(r2) AS deletedCount
            """
            
            deduped = self.connector.run_query(dedup_query)
            
            if deduped:
                results["relationships_deleted"] += deduped[0]["deletedCount"]
                logger.info(f"Deleted {deduped[0]['deletedCount']} duplicate CONNECTED_TO relationships")
            
            return results
            
        except Exception as e:
            logger.error(f"Error fixing relationship issues: {str(e)}")
            return results
    
    def fix_property_issues(self) -> Dict[str, int]:
        """
        Fix property issues in the graph.
        
        Returns:
            Dictionary with cleaning results
        """
        logger.info("Fixing property issues")
        
        results = {
            "nodes_modified": 0
        }
        
        try:
            # Add missing Name property (use GlobalId as fallback)
            missing_name_query = """
            MATCH (n)
            WHERE EXISTS(n.GlobalId) AND (NOT EXISTS(n.Name) OR n.Name IS NULL)
            SET n.Name = 'Unnamed_' + n.GlobalId
            RETURN count(n) AS modifiedCount
            """
            
            fixed_names = self.connector.run_query(missing_name_query)
            
            if fixed_names:
                results["nodes_modified"] += fixed_names[0]["modifiedCount"]
                logger.info(f"Added missing Name property to {fixed_names[0]['modifiedCount']} nodes")
            
            # Fix property value consistency (e.g., ensure string type for names)
            fix_types_query = """
            MATCH (n)
            WHERE EXISTS(n.Name) AND NOT n.Name IS STRING
            SET n.Name = toString(n.Name)
            RETURN count(n) AS modifiedCount
            """
            
            fixed_types = self.connector.run_query(fix_types_query)
            
            if fixed_types:
                results["nodes_modified"] += fixed_types[0]["modifiedCount"]
                logger.info(f"Fixed Name property type for {fixed_types[0]['modifiedCount']} nodes")
            
            return results
            
        except Exception as e:
            logger.error(f"Error fixing property issues: {str(e)}")
            return results
    
    def fix_topological_issues(self) -> Dict[str, int]:
        """
        Fix topological consistency issues in the graph.
        
        Returns:
            Dictionary with cleaning results
        """
        logger.info("Fixing topological consistency issues")
        
        results = {
            "relationships_modified": 0,
            "relationships_created": 0
        }
        
        try:
            # Create missing IS_CONTAINED_IN relationships for existing CONTAINS_TOPOLOGICALLY
            containment_query = """
            MATCH (a)-[r:CONTAINS_TOPOLOGICALLY]->(b)
            WHERE NOT (b)-[:IS_CONTAINED_IN]->(a)
            CREATE (b)-[r2:IS_CONTAINED_IN {relationshipSource: r.relationshipSource}]->(a)
            RETURN count(r2) AS createdCount
            """
            
            created = self.connector.run_query(containment_query)
            
            if created:
                results["relationships_created"] += created[0]["createdCount"]
                logger.info(f"Created {created[0]['createdCount']} missing IS_CONTAINED_IN relationships")
            
            # Make ADJACENT relationships symmetric where needed
            adjacency_query = """
            MATCH (a)-[r:ADJACENT]->(b)
            WHERE NOT (b)-[:ADJACENT]->(a)
            CREATE (b)-[r2:ADJACENT {
                relationshipSource: r.relationshipSource,
                distanceTolerance: r.distanceTolerance
            }]->(a)
            RETURN count(r2) AS createdCount
            """
            
            created_adj = self.connector.run_query(adjacency_query)
            
            if created_adj:
                results["relationships_created"] += created_adj[0]["createdCount"]
                logger.info(f"Created {created_adj[0]['createdCount']} missing symmetric ADJACENT relationships")
            
            return results
            
        except Exception as e:
            logger.error(f"Error fixing topological issues: {str(e)}")
            return results
    
    # --- REPORTING METHODS ---
    
    def generate_report(self, include_details: bool = False) -> Dict[str, Any]:
        """
        Generate a comprehensive report on the graph database.
        
        Args:
            include_details: Whether to include detailed statistics in the report
            
        Returns:
            Dictionary with the report data
        """
        logger.info("Generating graph quality report")
        
        # Run validation if not already performed
        if not self.validation_results:
            self.validate_graph()
        
        report = {
            "summary": {
                "graph_quality_score": self.validation_results.get("overall_score", 0),
                "issues_found": sum(len(result.get("issues", [])) for result in self.validation_results.values() 
                                   if isinstance(result, dict) and "issues" in result),
                "timestamp": self.get_timestamp()
            },
            "validation_results": {
                key: {"valid": value.get("valid", False), "score": value.get("score", 0), "issues": value.get("issues", [])}
                for key, value in self.validation_results.items()
                if isinstance(value, dict) and key != "overall_score"
            },
            "graph_statistics": self.get_graph_statistics()
        }
        
        # Include detailed information if requested
        if include_details:
            for key, value in self.validation_results.items():
                if isinstance(value, dict) and "details" in value:
                    report["validation_results"][key]["details"] = value["details"]
        
        # Store report for future reference
        self.report_data = report
        
        logger.info("Graph quality report generated successfully")
        return report
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the graph database.
        
        Returns:
            Dictionary with graph statistics
        """
        stats = {}
        
        try:
            # Get node counts by label
            node_count_query = """
            CALL db.labels() YIELD label
            CALL apoc.cypher.run('MATCH (n:' + $label + ') RETURN count(n) as count', {label: label}) YIELD value
            RETURN label, value.count AS count
            ORDER BY count DESC
            """
            
            node_counts = self.connector.run_query(node_count_query)
            
            if node_counts:
                stats["nodeCountsByLabel"] = {row["label"]: row["count"] for row in node_counts}
                stats["totalNodes"] = sum(row["count"] for row in node_counts)
            
            # Get relationship counts by type
            rel_count_query = """
            CALL db.relationshipTypes() YIELD relationshipType
            CALL apoc.cypher.run('MATCH ()-[r:' + $type + ']->() RETURN count(r) as count', {type: relationshipType}) YIELD value
            RETURN relationshipType, value.count AS count
            ORDER BY count DESC
            """
            
            rel_counts = self.connector.run_query(rel_count_query)
            
            if rel_counts:
                stats["relationshipCountsByType"] = {row["relationshipType"]: row["count"] for row in rel_counts}
                stats["totalRelationships"] = sum(row["count"] for row in rel_counts)
            
            # Get property statistics
            property_query = """
            MATCH (n)
            UNWIND keys(n) AS property
            RETURN property, count(*) AS count
            ORDER BY count DESC
            LIMIT 20
            """
            
            property_stats = self.connector.run_query(property_query)
            
            if property_stats:
                stats["topNodeProperties"] = {row["property"]: row["count"] for row in property_stats}
            
            # Get density metrics
            density_query = """
            MATCH (n)
            WITH count(n) AS nodeCount
            MATCH ()-[r]->()
            RETURN nodeCount, count(r) AS relationshipCount,
                   toFloat(count(r)) / (nodeCount * (nodeCount - 1)) AS graphDensity
            """
            
            density = self.connector.run_query(density_query)
            
            if density:
                stats["graphDensity"] = density[0]["graphDensity"]
            
            # Get topological relationship metrics
            topo_query = """
            MATCH ()-[r]->()
            WHERE r.relationshipSource = 'topologicalAnalysis'
            RETURN type(r) AS relType, count(r) AS count
            ORDER BY count DESC
            """
            
            topo_stats = self.connector.run_query(topo_query)
            
            if topo_stats:
                stats["topologicalRelationships"] = {row["relType"]: row["count"] for row in topo_stats}
                stats["totalTopologicalRelationships"] = sum(row["count"] for row in topo_stats)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting graph statistics: {str(e)}")
            return {"error": str(e)}
    
    def get_schema_statistics(self) -> Dict[str, Any]:
        """
        Get detailed statistics about the graph schema.
        
        Returns:
            Dictionary with schema statistics
        """
        logger.info("Retrieving schema statistics")
        
        try:
            # Use APOC if available for schema information
            schema_query = """
            CALL apoc.meta.schema()
            YIELD value
            RETURN value
            """
            
            schema_stats = {}
            
            try:
                result = self.connector.run_query(schema_query)
                if result and len(result) > 0:
                    schema_stats["schema"] = result[0]["value"]
            except Exception:
                # APOC might not be available, fall back to manual schema analysis
                logger.info("APOC not available, falling back to manual schema analysis")
                
                # Get node labels and their counts
                labels_query = """
                CALL db.labels() YIELD label
                CALL apoc.cypher.run('MATCH (n:' + $label + ') RETURN count(n) as count', {label: label}) YIELD value
                RETURN label, value.count AS count
                ORDER BY count DESC
                """
                
                labels = self.connector.run_query(labels_query)
                
                if labels:
                    schema_stats["labels"] = {row["label"]: row["count"] for row in labels}
                
                # Get relationship types and their counts
                rels_query = """
                CALL db.relationshipTypes() YIELD relationshipType
                CALL apoc.cypher.run('MATCH ()-[r:' + $type + ']->() RETURN count(r) as count', {type: relationshipType}) YIELD value
                RETURN relationshipType, value.count AS count
                ORDER BY count DESC
                """
                
                rels = self.connector.run_query(rels_query)
                
                if rels:
                    schema_stats["relationshipTypes"] = {row["relationshipType"]: row["count"] for row in rels}
            
            # Get property key distribution by label
            prop_query = """
            MATCH (n)
            WITH labels(n) AS nodeLabels, keys(n) AS nodeProperties
            UNWIND nodeLabels AS label
            UNWIND nodeProperties AS property
            RETURN label, property, count(*) AS frequency
            ORDER BY label, frequency DESC
            """
            
            props = self.connector.run_query(prop_query)
            
            if props:
                # Organize properties by label
                schema_stats["propertyKeysByLabel"] = {}
                
                for row in props:
                    label = row["label"]
                    prop = row["property"]
                    freq = row["frequency"]
                    
                    if label not in schema_stats["propertyKeysByLabel"]:
                        schema_stats["propertyKeysByLabel"][label] = {}
                    
                    schema_stats["propertyKeysByLabel"][label][prop] = freq
            
            # Get constraints and indexes
            constraints_query = "SHOW CONSTRAINTS"
            indexes_query = "SHOW INDEXES"
            
            try:
                constraints = self.connector.run_query(constraints_query)
                indexes = self.connector.run_query(indexes_query)
                
                if constraints:
                    schema_stats["constraints"] = [dict(constraint) for constraint in constraints]
                
                if indexes:
                    schema_stats["indexes"] = [dict(index) for index in indexes]
            except Exception as e:
                logger.warning(f"Error retrieving constraints and indexes: {str(e)}")
            
            return schema_stats
            
        except Exception as e:
            logger.error(f"Error getting schema statistics: {str(e)}")
            return {"error": str(e)}
    
    def export_report_to_json(self, filepath: str) -> bool:
        """
        Export the graph quality report to a JSON file.
        
        Args:
            filepath: Path to save the JSON report
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate report if not already available
            if not self.report_data:
                self.generate_report(include_details=True)
            
            # Write report to file
            with open(filepath, 'w') as f:
                json.dump(self.report_data, f, indent=2)
            
            logger.info(f"Graph quality report exported to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting report to JSON: {str(e)}")
            return False
    
    # --- UTILITY METHODS ---
    
    def get_timestamp(self) -> str:
        """
        Get the current timestamp as a string.
        
        Returns:
            Current timestamp
        """
        from datetime import datetime
        return datetime.now().isoformat() 