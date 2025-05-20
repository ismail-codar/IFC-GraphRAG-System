#!/usr/bin/env python3
"""
Neo4j Performance Optimization for IFC Knowledge Graph

This script provides tools to optimize Neo4j performance for IFC processing:
1. Diagnoses slow queries by running EXPLAIN/PROFILE
2. Applies recommended indexes and optimizations
3. Tests and validates the performance improvements

Use this after running the performance_diagnostic.py to address specific Neo4j issues.
"""

import os
import sys
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Import required modules
from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector
from src.ifc_to_graph.database.schema import SchemaManager

def setup_indexes_and_constraints(uri="neo4j://localhost:7687", username="neo4j", password="test1234", database=None):
    """Setup recommended indexes and constraints for Neo4j"""
    logger.info("Setting up recommended indexes and constraints...")
    
    connector = Neo4jConnector(uri, username, password, database)
    
    # Ensure connection works
    if not connector.test_connection():
        logger.error("Could not connect to Neo4j")
        return False
    
    # Create element indexes
    element_indexes = [
        "CREATE INDEX IF NOT EXISTS FOR (e:Element) ON (e.Name)",
        "CREATE INDEX IF NOT EXISTS FOR (e:Element) ON (e.IFCType)",
        "CREATE INDEX IF NOT EXISTS FOR (e:Element) ON (e.GlobalId)"
    ]
    
    # Create property set indexes
    pset_indexes = [
        "CREATE INDEX IF NOT EXISTS FOR (ps:PropertySet) ON (ps.Name)",
        "CREATE INDEX IF NOT EXISTS FOR (ps:PropertySet) ON (ps.GlobalId)"
    ]
    
    # Create property indexes
    property_indexes = [
        "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.Name)",
        "CREATE INDEX IF NOT EXISTS FOR (p:Property) ON (p.NominalValue)"
    ]
    
    # Create material indexes
    material_indexes = [
        "CREATE INDEX IF NOT EXISTS FOR (m:Material) ON (m.Name)"
    ]
    
    # Combine all indexes
    all_indexes = element_indexes + pset_indexes + property_indexes + material_indexes
    
    # Create each index
    for idx_query in all_indexes:
        try:
            connector.run_query(idx_query)
            logger.info(f"Created index: {idx_query}")
        except Exception as e:
            logger.warning(f"Error creating index: {str(e)}")
    
    logger.info("Completed creating indexes and constraints")
    return True

class Neo4jOptimizer:
    """Optimizes Neo4j database performance for IFC knowledge graph processing."""
    
    def __init__(self, uri="neo4j://localhost:7687", username="neo4j", password="test1234", database=None):
        self.neo4j = Neo4jConnector(
            uri=uri,
            username=username,
            password=password,
            database=database
        )
        
        self.schema_manager = SchemaManager(self.neo4j)
        
        # List of slow queries identified from the IFC to Neo4j pipeline
        self.slow_queries = {
            "Element Creation": "MERGE (e:Element {GlobalId: $GlobalId}) SET e.Name = $Name, e.Description = $Description, e.type = $type, e.Tag = $Tag RETURN e",
            "Property Set Link": "MATCH (e:Element {GlobalId: $element_id}) MATCH (ps:PropertySet {GlobalId: $pset_id}) MERGE (e)-[r:HAS_PROPERTY_SET]->(ps) RETURN type(r)",
            "Material Link": "MATCH (e:Element {GlobalId: $element_id}) MATCH (m:Material {Name: $material_name}) MERGE (e)-[r:HAS_MATERIAL]->(m) RETURN type(r)",
            "Type Hierarchy": "MATCH (e:Element {GlobalId: $child_id}) MATCH (p:Element {GlobalId: $parent_id}) MERGE (p)-[r:CONTAINS]->(e) RETURN type(r)",
            "Property Creation": "MERGE (p:Property {GlobalId: $GlobalId}) SET p.Name = $Name, p.Description = $Description, p.NominalValue = $NominalValue, p.PropertyType = $PropertyType RETURN p"
        }
        
        # Recommended index additions beyond the basic schema
        self.recommended_indexes = [
            # Element indexes
            {"label": "Element", "properties": ["Name", "type"]},
            
            # Material indexes
            {"label": "Material", "properties": ["Name"]},
            
            # Property indexes
            {"label": "Property", "properties": ["Name", "PropertyType"]},
            
            # PropertySet indexes
            {"label": "PropertySet", "properties": ["Name"]}
        ]
        
    def test_connection(self):
        """Test the Neo4j connection."""
        if not self.neo4j.test_connection():
            logger.error("Could not connect to Neo4j. Make sure it's running.")
            return False
        logger.info("Successfully connected to Neo4j")
        return True
    
    def check_existing_indexes(self):
        """Check existing indexes in the database."""
        logger.info("Checking existing indexes...")
        result = self.neo4j.execute_query("SHOW INDEXES")
        
        indexes = []
        for idx in result:
            if isinstance(idx, dict):
                index_info = {
                    "name": idx.get("name", "unnamed"),
                    "type": idx.get("type", "unknown"),
                    "state": idx.get("state", "unknown"),
                    "populationPercent": idx.get("populationPercent", 0),
                    "labelsOrTypes": idx.get("labelsOrTypes", []),
                    "properties": idx.get("properties", [])
                }
                indexes.append(index_info)
                logger.info(f"Found index: {index_info['name']} - {index_info['state']} - {index_info['properties']}")
        
        return indexes
    
    def create_recommended_indexes(self):
        """Create recommended additional indexes for better performance."""
        logger.info("Creating recommended indexes...")
        
        existing_indexes = self.check_existing_indexes()
        existing_index_keys = []
        
        # Extract existing index keys
        for idx in existing_indexes:
            if idx["labelsOrTypes"] and idx["properties"]:
                key = (tuple(idx["labelsOrTypes"]), tuple(idx["properties"]))
                existing_index_keys.append(key)
        
        # Create missing recommended indexes
        for index in self.recommended_indexes:
            label = index["label"]
            properties = index["properties"]
            
            key = ((label,), tuple(properties))
            if key not in existing_index_keys:
                for prop in properties:
                    index_name = f"idx_{label}_{prop}".lower()
                    query = f"CREATE INDEX {index_name} FOR (n:{label}) ON (n.{prop})"
                    
                    logger.info(f"Creating index: {query}")
                    self.neo4j.execute_query(query)
                    logger.info(f"Created index {index_name}")
            else:
                logger.info(f"Index for {label} on {properties} already exists")
    
    def analyze_slow_queries(self):
        """Analyze slow queries using EXPLAIN and PROFILE."""
        logger.info("Analyzing slow queries...")
        
        query_improvements = {}
        
        # Sample parameters for testing queries
        params = {
            "GlobalId": "test_global_id",
            "Name": "test_name",
            "Description": "test_description",
            "type": "IfcWall",
            "Tag": "test_tag",
            "element_id": "test_element_id",
            "pset_id": "test_pset_id",
            "material_name": "test_material_name",
            "child_id": "test_child_id",
            "parent_id": "test_parent_id",
            "NominalValue": "test_value",
            "PropertyType": "test_property_type"
        }
        
        for name, query in self.slow_queries.items():
            logger.info(f"Analyzing query: {name}")
            
            # Run EXPLAIN
            explain_query = f"EXPLAIN {query}"
            start_time = time.time()
            explain_result = self.neo4j.execute_query(explain_query, params)
            explain_time = time.time() - start_time
            
            # Run PROFILE
            profile_query = f"PROFILE {query}"
            start_time = time.time()
            profile_result = self.neo4j.execute_query(profile_query, params)
            profile_time = time.time() - start_time
            
            # Store results
            query_improvements[name] = {
                "original_query": query,
                "explain_time": explain_time,
                "profile_time": profile_time,
                "has_index_scan": self._check_index_usage(explain_result),
                "has_eager_operator": self._check_eager_operators(explain_result)
            }
            
            # Log findings
            logger.info(f"  Query time (EXPLAIN): {explain_time:.4f}s")
            logger.info(f"  Query time (PROFILE): {profile_time:.4f}s")
            logger.info(f"  Uses indexes: {query_improvements[name]['has_index_scan']}")
            if query_improvements[name]['has_eager_operator']:
                logger.info("  ⚠️ Query uses eager operators that may cause performance issues")
        
        return query_improvements
    
    def _check_index_usage(self, explain_result):
        """Check if the query plan uses index scans."""
        # Simple check - in real implementation this would parse the query plan properly
        return "IndexSeek" in str(explain_result) or "NodeIndexSeek" in str(explain_result)
    
    def _check_eager_operators(self, explain_result):
        """Check if the query plan has eager operators which can cause memory issues."""
        return "Eager" in str(explain_result)
    
    def optimize_queries(self, query_improvements):
        """Suggest optimized versions of slow queries."""
        logger.info("Optimizing slow queries...")
        
        optimized_queries = {}
        
        # Optimization strategies for each query type
        optimizations = {
            "Element Creation": {
                "original": self.slow_queries["Element Creation"],
                "optimized": "MERGE (e:Element {GlobalId: $GlobalId}) ON CREATE SET e.Name = $Name, e.Description = $Description, e.type = $type, e.Tag = $Tag RETURN e",
                "explanation": "Use ON CREATE to only set properties when creating new nodes, reducing write operations"
            },
            "Property Set Link": {
                "original": self.slow_queries["Property Set Link"],
                "optimized": "MATCH (e:Element {GlobalId: $element_id}) MATCH (ps:PropertySet {GlobalId: $pset_id}) WITH e, ps LIMIT 1 MERGE (e)-[r:HAS_PROPERTY_SET]->(ps) RETURN type(r)",
                "explanation": "Added LIMIT 1 to ensure only one relationship is created, reducing processing time"
            },
            "Material Link": {
                "original": self.slow_queries["Material Link"],
                "optimized": "MATCH (e:Element {GlobalId: $element_id}) MATCH (m:Material {Name: $material_name}) WITH e, m LIMIT 1 MERGE (e)-[r:HAS_MATERIAL]->(m) RETURN type(r)",
                "explanation": "Added LIMIT 1 to ensure only one relationship is created, improving performance"
            },
            "Type Hierarchy": {
                "original": self.slow_queries["Type Hierarchy"],
                "optimized": "MATCH (e:Element {GlobalId: $child_id}) MATCH (p:Element {GlobalId: $parent_id}) WITH e, p LIMIT 1 MERGE (p)-[r:CONTAINS]->(e) RETURN type(r)",
                "explanation": "Added LIMIT 1 to prevent creating multiple relationships"
            },
            "Property Creation": {
                "original": self.slow_queries["Property Creation"],
                "optimized": "MERGE (p:Property {GlobalId: $GlobalId}) ON CREATE SET p.Name = $Name, p.Description = $Description, p.NominalValue = $NominalValue, p.PropertyType = $PropertyType RETURN p",
                "explanation": "Use ON CREATE to only set properties when creating new nodes"
            }
        }
        
        for name, optimization in optimizations.items():
            original = optimization["original"]
            optimized = optimization["optimized"]
            explanation = optimization["explanation"]
            
            # Test optimized query
            params = {
                "GlobalId": "test_global_id",
                "Name": "test_name",
                "Description": "test_description", 
                "type": "IfcWall",
                "Tag": "test_tag",
                "element_id": "test_element_id",
                "pset_id": "test_pset_id",
                "material_name": "test_material_name",
                "child_id": "test_child_id", 
                "parent_id": "test_parent_id",
                "NominalValue": "test_value",
                "PropertyType": "test_property_type"
            }
            
            # Measure optimized query performance
            start_time = time.time()
            self.neo4j.execute_query(optimized, params)
            optimized_time = time.time() - start_time
            
            # Measure original query performance
            start_time = time.time()
            self.neo4j.execute_query(original, params)
            original_time = time.time() - start_time
            
            # Calculate improvement
            improvement = ((original_time - optimized_time) / original_time) * 100
            
            optimized_queries[name] = {
                "original": original,
                "optimized": optimized,
                "explanation": explanation,
                "original_time": original_time,
                "optimized_time": optimized_time,
                "improvement": improvement
            }
            
            logger.info(f"Optimized {name}:")
            logger.info(f"  Original time: {original_time:.4f}s")
            logger.info(f"  Optimized time: {optimized_time:.4f}s")
            logger.info(f"  Improvement: {improvement:.2f}%")
            logger.info(f"  Explanation: {explanation}")
        
        return optimized_queries
    
    def recommend_db_configuration(self):
        """Provide Neo4j configuration recommendations for improved performance."""
        logger.info("Generating Neo4j configuration recommendations...")
        
        # Get current system info
        try:
            result = self.neo4j.execute_query("CALL dbms.listConfig()")
            current_config = {}
            for config in result:
                if isinstance(config, dict) and "name" in config and "value" in config:
                    current_config[config["name"]] = config["value"]
        except Exception as e:
            logger.error(f"Error fetching Neo4j configuration: {str(e)}")
            current_config = {}
        
        # Generate recommendations
        recommendations = {
            "Memory Settings": [
                {
                    "setting": "dbms.memory.heap.initial_size",
                    "recommended": "2G",
                    "current": current_config.get("dbms.memory.heap.initial_size", "unknown"),
                    "explanation": "Initial Java heap size - increase for better initial performance"
                },
                {
                    "setting": "dbms.memory.heap.max_size", 
                    "recommended": "4G",
                    "current": current_config.get("dbms.memory.heap.max_size", "unknown"),
                    "explanation": "Maximum Java heap size - critical for large operations"
                },
                {
                    "setting": "dbms.memory.pagecache.size",
                    "recommended": "2G",
                    "current": current_config.get("dbms.memory.pagecache.size", "unknown"),
                    "explanation": "Page cache size - important for large graph databases"
                }
            ],
            "Transaction Settings": [
                {
                    "setting": "dbms.transaction.timeout",
                    "recommended": "5m",
                    "current": current_config.get("dbms.transaction.timeout", "unknown"),
                    "explanation": "Transaction timeout - prevent long-running queries from timing out"
                },
                {
                    "setting": "dbms.transaction.concurrent.maximum", 
                    "recommended": "100", 
                    "current": current_config.get("dbms.transaction.concurrent.maximum", "unknown"),
                    "explanation": "Maximum concurrent transactions - increase for parallel processing"
                }
            ],
            "Performance Settings": [
                {
                    "setting": "dbms.tx_state.memory_allocation",
                    "recommended": "ON_HEAP",
                    "current": current_config.get("dbms.tx_state.memory_allocation", "unknown"),
                    "explanation": "Transaction state memory allocation - ON_HEAP can be faster"
                },
                {
                    "setting": "dbms.index.default_schema_provider",
                    "recommended": "native-btree-1.0",
                    "current": current_config.get("dbms.index.default_schema_provider", "unknown"), 
                    "explanation": "Default index provider - native-btree-1.0 is recommended for most use cases"
                }
            ]
        }
        
        return recommendations
    
    def generate_neo4j_conf(self, recommendations):
        """Generate a neo4j.conf file with performance optimizations."""
        logger.info("Generating optimized neo4j.conf file...")
        
        conf_path = "neo4j_optimized.conf"
        
        with open(conf_path, "w") as f:
            f.write("# Neo4j Optimized Configuration for IFC Knowledge Graph Processing\n")
            f.write("# Generated on " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
            
            # Write memory settings
            f.write("# Memory Settings\n")
            for rec in recommendations["Memory Settings"]:
                f.write(f"# {rec['explanation']}\n")
                f.write(f"{rec['setting']}={rec['recommended']}\n\n")
            
            # Write transaction settings
            f.write("# Transaction Settings\n")
            for rec in recommendations["Transaction Settings"]:
                f.write(f"# {rec['explanation']}\n")
                f.write(f"{rec['setting']}={rec['recommended']}\n\n")
            
            # Write performance settings
            f.write("# Performance Settings\n")
            for rec in recommendations["Performance Settings"]:
                f.write(f"# {rec['explanation']}\n")
                f.write(f"{rec['setting']}={rec['recommended']}\n\n")
            
            # Additional optimizations
            f.write("# Additional Optimizations\n")
            f.write("# Enable query cache for faster repeated queries\n")
            f.write("dbms.query_cache_size=100MB\n\n")
            
            f.write("# Reduce transaction logs for bulk imports\n")
            f.write("dbms.checkpoint.interval.time=10m\n\n")
            
            f.write("# Enable parallelism for query execution\n")
            f.write("dbms.threads.worker_count=4\n\n")
        
        logger.info(f"Generated optimized configuration: {conf_path}")
        return conf_path
    
    def generate_implementation_guide(self, optimized_queries):
        """Generate implementation guide with code changes needed."""
        logger.info("Generating implementation guide...")
        
        guide_path = "neo4j_optimization_guide.md"
        
        with open(guide_path, "w") as f:
            f.write("# Neo4j Performance Optimization Guide for IFC Knowledge Graph\n\n")
            f.write("This guide contains specific code changes to improve Neo4j performance in the IFC Knowledge Graph pipeline.\n\n")
            
            # Query optimizations
            f.write("## Query Optimizations\n\n")
            f.write("Replace the following slow queries in the codebase with their optimized versions:\n\n")
            
            for name, data in optimized_queries.items():
                f.write(f"### {name}\n\n")
                f.write(f"**Improvement: {data['improvement']:.2f}%**\n\n")
                f.write(f"**Explanation: {data['explanation']}**\n\n")
                f.write("Original query:\n```cypher\n")
                f.write(data["original"])
                f.write("\n```\n\n")
                f.write("Optimized query:\n```cypher\n")
                f.write(data["optimized"])
                f.write("\n```\n\n")
                
                # Provide Python code example
                f.write("Implementation example:\n\n")
                f.write("```python\n")
                if name == "Element Creation":
                    f.write("def create_element(self, element):\n")
                    f.write("    params = {\n")
                    f.write("        \"GlobalId\": element.guid,\n")
                    f.write("        \"Name\": element.name,\n")
                    f.write("        \"Description\": element.description,\n")
                    f.write("        \"type\": element.type,\n")
                    f.write("        \"Tag\": element.tag\n")
                    f.write("    }\n")
                    f.write("    query = \"MERGE (e:Element {GlobalId: $GlobalId}) ON CREATE SET e.Name = $Name, e.Description = $Description, e.type = $type, e.Tag = $Tag RETURN e\"\n")
                    f.write("    result = self.neo4j.execute_query(query, params)\n")
                    f.write("    return result[0]['e']['GlobalId'] if result else None\n")
                
                elif name == "Material Link":
                    f.write("def link_element_to_material(self, element_id, material_name):\n")
                    f.write("    params = {\n")
                    f.write("        \"element_id\": element_id,\n")
                    f.write("        \"material_name\": material_name\n")
                    f.write("    }\n")
                    f.write("    query = \"MATCH (e:Element {GlobalId: $element_id}) MATCH (m:Material {Name: $material_name}) WITH e, m LIMIT 1 MERGE (e)-[r:HAS_MATERIAL]->(m) RETURN type(r)\"\n")
                    f.write("    result = self.neo4j.execute_query(query, params)\n")
                    f.write("    return len(result) > 0\n")
                
                elif name == "Property Set Link":
                    f.write("def link_element_to_property_set(self, element_id, pset_id):\n")
                    f.write("    params = {\n")
                    f.write("        \"element_id\": element_id,\n")
                    f.write("        \"pset_id\": pset_id\n")
                    f.write("    }\n")
                    f.write("    query = \"MATCH (e:Element {GlobalId: $element_id}) MATCH (ps:PropertySet {GlobalId: $pset_id}) WITH e, ps LIMIT 1 MERGE (e)-[r:HAS_PROPERTY_SET]->(ps) RETURN type(r)\"\n")
                    f.write("    result = self.neo4j.execute_query(query, params)\n")
                    f.write("    return len(result) > 0\n")
                
                f.write("```\n\n")
            
            # General recommendations
            f.write("## Code Structure Recommendations\n\n")
            
            f.write("### 1. Add Query Caching\n\n")
            f.write("Implement a query cache to avoid redundant database operations:\n\n")
            f.write("```python\n")
            f.write("class QueryCache:\n")
            f.write("    def __init__(self, max_size=1000):\n")
            f.write("        self.cache = {}\n")
            f.write("        self.max_size = max_size\n")
            f.write("\n")
            f.write("    def get(self, key):\n")
            f.write("        return self.cache.get(key)\n")
            f.write("\n")
            f.write("    def set(self, key, value):\n")
            f.write("        if len(self.cache) >= self.max_size:\n")
            f.write("            # Simple LRU: just clear half the cache when full\n")
            f.write("            keys = list(self.cache.keys())[:self.max_size//2]\n")
            f.write("            for k in keys:\n")
            f.write("                del self.cache[k]\n")
            f.write("        self.cache[key] = value\n")
            f.write("\n")
            f.write("# Usage in IfcToGraphMapper:\n")
            f.write("self.query_cache = QueryCache()\n")
            f.write("\n")
            f.write("def element_exists(self, global_id):\n")
            f.write("    cache_key = f\"element_exists_{global_id}\"\n")
            f.write("    cached = self.query_cache.get(cache_key)\n")
            f.write("    if cached is not None:\n")
            f.write("        return cached\n")
            f.write("\n")
            f.write("    result = self.neo4j.execute_query(\"MATCH (e:Element {GlobalId: $GlobalId}) RETURN e\", {\"GlobalId\": global_id})\n")
            f.write("    exists = len(result) > 0\n")
            f.write("    self.query_cache.set(cache_key, exists)\n")
            f.write("    return exists\n")
            f.write("```\n\n")
            
            f.write("### 2. Optimize Batch Processing\n\n")
            f.write("Modify the batch processing to use more efficient transactions:\n\n")
            f.write("```python\n")
            f.write("def process_batch(self, elements, batch_size=100):\n")
            f.write("    # Group elements by type to optimize similar operations\n")
            f.write("    elements_by_type = {}\n")
            f.write("    for element in elements:\n")
            f.write("        if element.type not in elements_by_type:\n")
            f.write("            elements_by_type[element.type] = []\n")
            f.write("        elements_by_type[element.type].append(element)\n")
            f.write("\n")
            f.write("    # Process each type group separately\n")
            f.write("    for element_type, type_elements in elements_by_type.items():\n")
            f.write("        # Further split into batches\n")
            f.write("        for i in range(0, len(type_elements), batch_size):\n")
            f.write("            batch = type_elements[i:i+batch_size]\n")
            f.write("            \n")
            f.write("            # Begin transaction for the batch\n")
            f.write("            transaction = self.neo4j.begin_transaction()\n")
            f.write("            \n")
            f.write("            try:\n")
            f.write("                # First create all elements\n")
            f.write("                for element in batch:\n")
            f.write("                    self.create_element_in_transaction(transaction, element)\n")
            f.write("                \n")
            f.write("                # Then create relationships between them\n")
            f.write("                for element in batch:\n")
            f.write("                    self.create_element_relationships_in_transaction(transaction, element)\n")
            f.write("                \n")
            f.write("                # Commit the entire batch\n")
            f.write("                transaction.commit()\n")
            f.write("            except Exception as e:\n")
            f.write("                transaction.rollback()\n")
            f.write("                logger.error(f\"Error processing batch: {str(e)}\")\n")
            f.write("```\n\n")
            
            f.write("### 3. Conditional Topology Analysis\n\n")
            f.write("Modify the topology analysis to only process relevant elements:\n\n")
            f.write("```python\n")
            f.write("def process_topology(self, elements, relevant_types=None):\n")
            f.write("    \"\"\"Process topology only for relevant element types.\"\"\"\n")
            f.write("    if not TOPOLOGICPY_AVAILABLE:\n")
            f.write("        logger.warning(\"TopologicPy not available. Skipping topology analysis.\")\n")
            f.write("        return\n")
            f.write("        \n")
            f.write("    # Filter elements by type if types provided\n")
            f.write("    if relevant_types:\n")
            f.write("        filtered_elements = {guid: elem for guid, elem in elements.items() \n")
            f.write("                            if elem.type in relevant_types}\n")
            f.write("    else:\n")
            f.write("        filtered_elements = elements\n")
            f.write("    \n")
            f.write("    # Skip if no relevant elements\n")
            f.write("    if not filtered_elements:\n")
            f.write("        return\n")
            f.write("        \n")
            f.write("    # Perform topology analysis on filtered elements\n")
            f.write("    analyzer = TopologicAnalyzer(self.ifc_file_path)\n")
            f.write("    relationships = analyzer.analyze_elements(filtered_elements)\n")
            f.write("    \n")
            f.write("    # Process relationships in batches\n")
            f.write("    mapper = TopologicToGraphMapper(self.neo4j_connector)\n")
            f.write("    mapper.create_topologic_relationships(relationships, batch_size=500)\n")
            f.write("```\n\n")
            
            # Configuration instructions
            f.write("## Neo4j Configuration\n\n")
            f.write("To apply the optimized Neo4j configuration:\n\n")
            f.write("1. Locate your Neo4j configuration file (typically `neo4j.conf` in the Neo4j installation's `conf` directory)\n\n")
            f.write("2. Back up your existing configuration\n\n")
            f.write("3. Add or update the settings from the generated `neo4j_optimized.conf` file\n\n")
            f.write("4. Restart Neo4j to apply changes\n\n")
            
            # Implementation plan
            f.write("## Implementation Plan\n\n")
            f.write("1. Apply the query optimizations to `ifc_to_graph_mapper.py`\n\n")
            f.write("2. Implement the query cache class\n\n")
            f.write("3. Update the batch processing in `processor.py`\n\n")
            f.write("4. Make the topology analysis more selective\n\n")
            f.write("5. Configure Neo4j with the optimized settings\n\n")
            f.write("6. Re-run performance tests to validate improvements\n\n")
        
        logger.info(f"Generated implementation guide: {guide_path}")
        return guide_path
    
    def run_full_optimization(self):
        """Run the full optimization process and generate all recommendations."""
        if not self.test_connection():
            return
        
        # Check existing indexes
        self.check_existing_indexes()
        
        # Create recommended indexes
        self.create_recommended_indexes()
        
        # Analyze slow queries
        query_improvements = self.analyze_slow_queries()
        
        # Optimize queries
        optimized_queries = self.optimize_queries(query_improvements)
        
        # Get configuration recommendations
        recommendations = self.recommend_db_configuration()
        
        # Generate configuration file
        self.generate_neo4j_conf(recommendations)
        
        # Generate implementation guide
        self.generate_implementation_guide(optimized_queries)
        
        logger.info("Optimization process completed successfully")

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Optimize Neo4j for IFC Knowledge Graph processing"
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
        help="Neo4j database name (default: None)"
    )
    
    return parser.parse_args()

def main():
    """Main entry point."""
    args = parse_args()
    
    logger.info("Starting Neo4j optimization...")
    
    optimizer = Neo4jOptimizer(
        uri=args.uri,
        username=args.username,
        password=args.password,
        database=args.database
    )
    
    optimizer.run_full_optimization()
    
    logger.info("Optimization completed. See the generated files for implementation details.")

if __name__ == "__main__":
    main() 