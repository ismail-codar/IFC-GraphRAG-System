"""
BIMConverse Schema Module

This module provides utilities for validating and enhancing the schema mapping
between natural language queries and the Neo4j graph structure.
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from neo4j import Driver, GraphDatabase

logger = logging.getLogger(__name__)

class SchemaMapper:
    """
    A utility class for managing and validating the IFC schema in Neo4j.
    Helps ensure that queries correctly map to the actual database structure.
    """
    
    def __init__(self, driver: Driver):
        """
        Initialize the schema mapper with a Neo4j driver.
        
        Args:
            driver: Neo4j driver instance
        """
        self.driver = driver
        self.node_labels = set()
        self.relationship_types = set()
        self.property_keys = set()
        self.common_patterns = {}
        self.label_properties = {}
        self.relationship_properties = {}
        self.hierarchical_paths = []
        
    def refresh_schema(self) -> Dict[str, Any]:
        """
        Fetches and returns the current schema from the Neo4j database.
        
        Returns:
            Dictionary containing schema information
        """
        result = {
            "node_labels": [],
            "relationship_types": [],
            "property_keys": [],
            "label_counts": {},
            "relationship_counts": {},
            "hierarchical_paths": []
        }
        
        # Fetch node labels and counts
        with self.driver.session() as session:
            # Get all node labels
            label_query = """
            CALL db.labels() YIELD label
            RETURN collect(label) AS labels
            """
            label_result = session.run(label_query).single()
            if label_result:
                labels = label_result["labels"]
                result["node_labels"] = labels
                self.node_labels = set(labels)
            
            # Get counts for each label
            for label in self.node_labels:
                count_query = f"MATCH (n:{label}) RETURN count(n) AS count"
                count_result = session.run(count_query).single()
                if count_result:
                    result["label_counts"][label] = count_result["count"]
            
            # Get all relationship types
            rel_query = """
            CALL db.relationshipTypes() YIELD relationshipType
            RETURN collect(relationshipType) AS types
            """
            rel_result = session.run(rel_query).single()
            if rel_result:
                rel_types = rel_result["types"]
                result["relationship_types"] = rel_types
                self.relationship_types = set(rel_types)
            
            # Get counts for each relationship type
            for rel_type in self.relationship_types:
                count_query = f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS count"
                count_result = session.run(count_query).single()
                if count_result:
                    result["relationship_counts"][rel_type] = count_result["count"]
            
            # Get all property keys
            props_query = """
            CALL db.propertyKeys() YIELD propertyKey
            RETURN collect(propertyKey) AS keys
            """
            props_result = session.run(props_query).single()
            if props_result:
                prop_keys = props_result["keys"]
                result["property_keys"] = prop_keys
                self.property_keys = set(prop_keys)
                
            # Map properties to node labels
            for label in self.node_labels:
                props_query = f"""
                MATCH (n:{label})
                RETURN keys(n) AS properties
                LIMIT 1
                """
                props_result = session.run(props_query).single()
                if props_result and props_result["properties"]:
                    self.label_properties[label] = props_result["properties"]
            
            # Map properties to relationship types
            for rel_type in self.relationship_types:
                props_query = f"""
                MATCH ()-[r:{rel_type}]->()
                RETURN keys(r) AS properties
                LIMIT 1
                """
                props_result = session.run(props_query).single()
                if props_result and props_result["properties"]:
                    self.relationship_properties[rel_type] = props_result["properties"]
                    
            # Extract common hierarchical paths
            paths_query = """
            MATCH path = (a)-[r]->(b)
            WHERE labels(a) <> [] AND labels(b) <> []
            RETURN DISTINCT [labels(a)[0], type(r), labels(b)[0]] AS path_pattern,
                   count(*) AS frequency
            ORDER BY frequency DESC
            LIMIT 20
            """
            paths_result = session.run(paths_query)
            for record in paths_result:
                pattern = record["path_pattern"]
                frequency = record["frequency"]
                self.hierarchical_paths.append({
                    "source_label": pattern[0],
                    "relationship": pattern[1],
                    "target_label": pattern[2],
                    "frequency": frequency
                })
                result["hierarchical_paths"].append({
                    "source_label": pattern[0],
                    "relationship": pattern[1],
                    "target_label": pattern[2],
                    "frequency": frequency
                })
                
        return result
    
    def find_missing_relationships(self) -> List[Dict[str, Any]]:
        """
        Identifies potential missing relationships in the schema based on
        common IFC patterns that should exist.
        
        Returns:
            List of potentially missing relationships
        """
        expected_patterns = [
            # Essential IFC containment relationships
            {"source": "Building", "relationship": "CONTAINS", "target": "Storey"},
            {"source": "Storey", "relationship": "CONTAINS", "target": "Space"},
            {"source": "Space", "relationship": "CONTAINS", "target": "Element"},
            # Essential IFC boundary relationships
            {"source": "Space", "relationship": "BOUNDED_BY", "target": "Wall"},
            {"source": "Space", "relationship": "BOUNDED_BY", "target": "Window"},
            {"source": "Space", "relationship": "BOUNDED_BY", "target": "Door"},
            {"source": "Space", "relationship": "BOUNDED_BY", "target": "Slab"},
            {"source": "Space", "relationship": "BOUNDED_BY", "target": "Roof"},
            # Essential IFC element relationships
            {"source": "Wall", "relationship": "CONNECTED_TO", "target": "Wall"},
            {"source": "Wall", "relationship": "CONTAINS", "target": "Window"},
            {"source": "Wall", "relationship": "CONTAINS", "target": "Door"},
            {"source": "Roof", "relationship": "CONTAINS", "target": "Skylight"},
            # Material relationships
            {"source": "Element", "relationship": "IS_MADE_OF", "target": "Material"},
            {"source": "Wall", "relationship": "IS_MADE_OF", "target": "Material"},
            {"source": "Slab", "relationship": "IS_MADE_OF", "target": "Material"},
            {"source": "Roof", "relationship": "IS_MADE_OF", "target": "Material"}
        ]
        
        missing = []
        with self.driver.session() as session:
            for pattern in expected_patterns:
                query = f"""
                MATCH (a:{pattern['source']})-[r:{pattern['relationship']}]->(b:{pattern['target']})
                RETURN count(r) as count
                """
                result = session.run(query).single()
                if not result or result["count"] == 0:
                    missing.append(pattern)
        
        return missing
    
    def suggest_query_improvements(self, query: str) -> Dict[str, Any]:
        """
        Analyzes a Cypher query and suggests improvements based on the schema.
        
        Args:
            query: Cypher query to analyze
            
        Returns:
            Dictionary with query improvement suggestions
        """
        suggestions = {
            "missing_labels": [],
            "unknown_labels": [],
            "missing_relationships": [],
            "unknown_relationships": [],
            "alternative_paths": [],
            "fixed_query": None
        }
        
        # Extract labels from query
        query_labels = set()
        for label in self.node_labels:
            if f":{label}" in query:
                query_labels.add(label)
        
        # Check for missing essential labels
        essential_labels = {"Space", "Element", "Wall", "Storey", "Building", "Roof", "Slab"}
        for label in essential_labels:
            if label not in query_labels and label in self.node_labels:
                suggestions["missing_labels"].append(label)
        
        # Check for unknown labels
        for label in query_labels:
            if label not in self.node_labels:
                suggestions["unknown_labels"].append(label)
                # Suggest alternatives
                if label == "Skylight" and "Skylight" not in self.node_labels:
                    if "Opening" in self.node_labels:
                        suggestions["alternative_paths"].append({
                            "missing": "Skylight",
                            "alternative": "Roof-[:CONTAINS]->Opening"
                        })
        
        # Extract relationship types from query
        query_rels = set()
        for rel in self.relationship_types:
            if f":{rel}" in query:
                query_rels.add(rel)
        
        # Check for unknown relationships
        for rel in query_rels:
            if rel not in self.relationship_types:
                suggestions["unknown_relationships"].append(rel)
        
        # Suggest fixed query if possible
        if suggestions["unknown_labels"] or suggestions["unknown_relationships"]:
            fixed_query = query
            for unknown_label in suggestions["unknown_labels"]:
                if unknown_label == "Skylight" and "Opening" in self.node_labels:
                    fixed_query = fixed_query.replace(
                        f"(skylight:{unknown_label})", 
                        "(opening:Opening)"
                    )
                    fixed_query = fixed_query.replace(
                        "MATCH (roof:Roof)-[:CONTAINS]->(skylight:Skylight)",
                        "MATCH (roof:Roof)-[:CONTAINS]->(opening:Opening)"
                    )
            
            suggestions["fixed_query"] = fixed_query
        
        return suggestions
    
    def enhance_schema_prompt(self) -> str:
        """
        Generates an enhanced schema prompt with accurate relationship information
        for better LLM query formulation.
        
        Returns:
            Enhanced schema prompt string for the LLM
        """
        # Get the current schema
        schema_info = self.refresh_schema()
        
        # Build a more accurate schema prompt
        node_labels_str = "\n".join([
            f"{label} {{" + ", ".join([f"{prop}: STRING" for prop in self.label_properties.get(label, [])]) + "}"
            for label in sorted(self.node_labels)
        ])
        
        relationship_types_str = "\n".join([
            f"{rel_type} {{" + ", ".join([f"{prop}: STRING" for prop in self.relationship_properties.get(rel_type, [])]) + "}"
            for rel_type in sorted(self.relationship_types)
        ])
        
        # Generate relationship paths from actual data
        paths_str = "\n".join([
            f"(:{path['source_label']})-[:{path['relationship']}]->(:{path['target_label']})"
            for path in self.hierarchical_paths
        ])
        
        prompt = f"""
You are a specialist in converting natural language questions about buildings into Cypher queries for Neo4j.
The database contains an IFC (Industry Foundation Classes) building model represented as a graph.

Node properties:
{node_labels_str}

Relationship properties:
{relationship_types_str}

The relationships:
{paths_str}

Important notes:
1. All node labels are case-sensitive
2. Some elements might be represented differently than in standard IFC:
   - Skylights may be represented as Opening elements contained within Roof elements
   - Some elements might use alternative terminology (e.g., Window vs. Opening)
3. Always check for alternative paths if a direct relationship doesn't exist
4. Use multiple variable-length path patterns for complex spatial queries
        """
        
        return prompt
    
    def validate_query_against_schema(self, query: str) -> Dict[str, Any]:
        """
        Validates a Cypher query against the actual database schema.
        
        Args:
            query: Cypher query to validate
            
        Returns:
            Validation results with warnings and suggestions
        """
        result = {
            "is_valid": True,
            "warnings": [],
            "suggestions": []
        }
        
        # Check for empty schema
        if not self.node_labels or not self.relationship_types:
            self.refresh_schema()
        
        # Analyze and validate the query
        suggestions = self.suggest_query_improvements(query)
        
        # Add warnings for unknown labels and relationships
        for label in suggestions["unknown_labels"]:
            result["warnings"].append(f"Unknown node label: {label}")
            result["is_valid"] = False
        
        for rel in suggestions["unknown_relationships"]:
            result["warnings"].append(f"Unknown relationship type: {rel}")
            result["is_valid"] = False
        
        # Add suggestions for missing labels and alternative paths
        for label in suggestions["missing_labels"]:
            result["suggestions"].append(f"Consider including {label} nodes in your query for more complete results")
        
        for path in suggestions["alternative_paths"]:
            result["suggestions"].append(
                f"'{path['missing']}' not found in schema. Use '{path['alternative']}' pattern instead"
            )
        
        # If we have a fixed query suggestion, include it
        if suggestions["fixed_query"]:
            result["fixed_query"] = suggestions["fixed_query"]
        
        return result
        
    def test_query(self, query: str) -> Dict[str, Any]:
        """
        Tests a Cypher query against the database and returns basic stats.
        
        Args:
            query: Cypher query to test
            
        Returns:
            Dictionary with query test results
        """
        result = {
            "executed": False,
            "error": None,
            "result_count": 0,
            "execution_time_ms": 0,
            "sample_results": []
        }
        
        try:
            # Validate against schema first
            validation = self.validate_query_against_schema(query)
            if not validation["is_valid"] and "fixed_query" in validation:
                query = validation["fixed_query"]
                result["used_fixed_query"] = True
                
            with self.driver.session() as session:
                # Use a timeout to prevent long-running queries
                query_result = session.run(f"PROFILE {query}")
                records = list(query_result)
                
                result["executed"] = True
                result["result_count"] = len(records)
                
                # Get execution plan summary
                summary = query_result.consume()
                result["execution_time_ms"] = summary.result_available_after
                
                # Add a sample of results
                if records:
                    sample_size = min(3, len(records))
                    for i in range(sample_size):
                        record_dict = dict(records[i])
                        # Convert Neo4j types to simple Python types
                        simplified = {}
                        for key, value in record_dict.items():
                            if hasattr(value, "items"):
                                simplified[key] = dict(value)
                            elif hasattr(value, "__iter__") and not isinstance(value, str):
                                simplified[key] = list(value)
                            else:
                                simplified[key] = value
                        result["sample_results"].append(simplified)
                
        except Exception as e:
            result["error"] = str(e)
            
        return result 