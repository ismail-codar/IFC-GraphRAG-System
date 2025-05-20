#!/usr/bin/env python3
"""
Performance Diagnostic for IFC to Knowledge Graph Pipeline

This script profiles the different components of the IFC to Knowledge Graph pipeline
to identify performance bottlenecks and provide recommendations for optimization.
"""

import os
import sys
import time
import logging
import cProfile
import pstats
import argparse
import traceback
from pathlib import Path
from datetime import datetime
import tracemalloc

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Import required modules
from src.ifc_to_graph.parser import IfcParser
from src.ifc_to_graph.processor import IfcProcessor
from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector
from src.ifc_to_graph.database.ifc_to_graph_mapper import IfcToGraphMapper
from src.ifc_to_graph.topology.topologic_analyzer import TopologicAnalyzer, TOPOLOGICPY_AVAILABLE

class PipelineProfiler:
    """Profiles each component of the IFC to Knowledge Graph pipeline."""
    
    def __init__(self, ifc_file_path, neo4j_uri="neo4j://localhost:7687", 
                 neo4j_username="neo4j", neo4j_password="test1234",
                 neo4j_database=None, use_topology=False):
        self.ifc_file_path = ifc_file_path
        self.neo4j_uri = neo4j_uri
        self.neo4j_username = neo4j_username
        self.neo4j_password = neo4j_password
        self.neo4j_database = neo4j_database
        self.use_topology = use_topology
        
        # Profiling data
        self.timings = {}
        self.memory_usage = {}
        self.query_stats = {}
        
        # Initialize components but don't run them yet
        self.neo4j = Neo4jConnector(
            uri=neo4j_uri,
            username=neo4j_username,
            password=neo4j_password,
            database=neo4j_database
        )
        
        self.parser = None
        self.processor = None
        
    def time_operation(self, operation_name, func, *args, **kwargs):
        """Time a specific operation and store the result."""
        logger.info(f"Starting {operation_name}...")
        
        # Start memory tracking
        tracemalloc.start()
        
        # Time execution
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        
        # Get memory stats
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Log results
        logger.info(f"Completed {operation_name} in {elapsed_time:.2f} seconds")
        logger.info(f"Memory usage: current={current / 1024 / 1024:.2f}MB, peak={peak / 1024 / 1024:.2f}MB")
        
        # Store results
        self.timings[operation_name] = elapsed_time
        self.memory_usage[operation_name] = {"current": current, "peak": peak}
        
        return result
    
    def profile_connection(self):
        """Profile the Neo4j connection setup."""
        def test_connection():
            return self.neo4j.test_connection()
        
        is_connected = self.time_operation("Neo4j connection", test_connection)
        if not is_connected:
            logger.error("Could not connect to Neo4j. Make sure it's running.")
            sys.exit(1)
            
    def profile_parsing(self):
        """Profile the IFC parsing step."""
        def parse_ifc():
            self.parser = IfcParser(self.ifc_file_path)
            # The parser doesn't have a parse method, it loads the file in __init__
            # Get all elements to ensure everything is loaded
            self.parser.get_elements()
            return self.parser
        
        self.time_operation("IFC parsing", parse_ifc)
        
        # Log some basic stats about the parsed model
        model_stats = {
            "total_entities": len(self.parser.get_elements()),
            "entity_types": len(set(element.is_a() for element in self.parser.get_elements())),
            "property_sets": len(self.parser.file.by_type("IfcPropertySet")),
            "materials": len(self.parser.file.by_type("IfcMaterial"))
        }
        
        logger.info(f"IFC Model Stats: {model_stats}")
    
    def profile_schema_setup(self):
        """Profile the Neo4j schema setup."""
        def setup_schema():
            processor = IfcProcessor(
                ifc_file_path=self.ifc_file_path,
                neo4j_uri=self.neo4j_uri,
                neo4j_username=self.neo4j_username,
                neo4j_password=self.neo4j_password,
                neo4j_database=self.neo4j_database,
                enable_monitoring=False,
                parallel_processing=False,
                enable_topological_analysis=False
            )
            processor.setup_database(clear_existing=True)
            return processor
        
        self.processor = self.time_operation("Schema setup", setup_schema)
    
    def profile_graph_mapper(self):
        """Profile the graph mapper operations to identify slow queries."""
        def create_element_sample():
            # Get a sample of 10 elements to test
            elements = self.parser.get_elements()[:10]
            mapper = IfcToGraphMapper(self.neo4j)
            
            # Track each element creation time
            query_times = []
            for element in elements:
                element_data = self.parser.get_element_attributes(element)
                start = time.time()
                mapper.create_node_from_element(element_data)
                query_times.append(time.time() - start)
            
            return {
                "avg_time": sum(query_times) / len(query_times),
                "max_time": max(query_times),
                "min_time": min(query_times),
                "total_time": sum(query_times)
            }
        
        element_stats = self.time_operation("Element creation (10 samples)", create_element_sample)
        self.query_stats["element_creation"] = element_stats
        
        # Profile property set creation
        def create_property_set_sample():
            # Get a sample of 5 property sets to test
            property_sets = self.parser.file.by_type("IfcPropertySet")[:5] 
            mapper = IfcToGraphMapper(self.neo4j)
            
            query_times = []
            for pset in property_sets:
                pset_data = {"Name": pset.Name, "GlobalId": pset.GlobalId}
                start = time.time()
                mapper.create_property_set(pset.Name, pset.GlobalId)
                query_times.append(time.time() - start)
            
            return {
                "avg_time": sum(query_times) / len(query_times) if query_times else 0,
                "max_time": max(query_times) if query_times else 0,
                "min_time": min(query_times) if query_times else 0,
                "total_time": sum(query_times)
            }
        
        pset_stats = self.time_operation("Property set creation (5 samples)", create_property_set_sample)
        self.query_stats["property_set_creation"] = pset_stats
        
        # Profile material creation
        def create_material_sample():
            # Get a sample of 5 materials to test
            materials = self.parser.file.by_type("IfcMaterial")[:5]
            mapper = IfcToGraphMapper(self.neo4j)
            
            query_times = []
            for material in materials:
                # Create proper material data dictionary
                material_data = {
                    "Name": material.Name,
                    "GlobalId": f"Material-{material.Name}"  # Materials don't have GlobalId, create one
                }
                start = time.time()
                mapper.create_material_node(material_data)
                query_times.append(time.time() - start)
            
            return {
                "avg_time": sum(query_times) / len(query_times) if query_times else 0,
                "max_time": max(query_times) if query_times else 0,
                "min_time": min(query_times) if query_times else 0,
                "total_time": sum(query_times)
            }
        
        material_stats = self.time_operation("Material creation (5 samples)", create_material_sample)
        self.query_stats["material_creation"] = material_stats
    
    def profile_topology_analysis(self):
        """Profile the topology analysis if enabled."""
        if not self.use_topology or not TOPOLOGICPY_AVAILABLE:
            logger.info("Skipping topology analysis profiling (not enabled or TopologicPy not available)")
            return
        
        def analyze_topology_sample():
            elements = self.parser.get_elements()[:10]
            analyzer = TopologicAnalyzer(self.ifc_file_path)
            
            # Profile topology analysis for a sample
            sample_elements = {element.GlobalId: element for element in elements}
            start = time.time()
            relationships = analyzer.analyze_elements(sample_elements)
            elapsed = time.time() - start
            
            return {
                "relationships_found": len(relationships),
                "time_per_element": elapsed / len(elements) if elements else 0,
                "total_time": elapsed
            }
        
        topo_stats = self.time_operation("Topology analysis (10 samples)", analyze_topology_sample)
        self.query_stats["topology_analysis"] = topo_stats
    
    def profile_batch_processing(self):
        """Profile the batch processing functionality."""
        def process_small_batch():
            # Get a small batch of 20 elements
            elements = self.parser.get_elements()[:20]
            batch_processor = IfcProcessor(
                ifc_file_path=self.ifc_file_path,
                neo4j_uri=self.neo4j_uri,
                neo4j_username=self.neo4j_username,
                neo4j_password=self.neo4j_password,
                neo4j_database=self.neo4j_database,
                enable_monitoring=False,
                parallel_processing=False,
                enable_topological_analysis=False
            )
            
            # Process just these elements
            start = time.time()
            # Access the private method using name mangling
            batch_processor._process_element_batch(elements)
            elapsed = time.time() - start
            
            return {
                "elements_processed": len(elements),
                "time_per_element": elapsed / len(elements) if elements else 0,
                "total_time": elapsed
            }
        
        batch_stats = self.time_operation("Batch processing (20 elements)", process_small_batch)
        self.query_stats["batch_processing"] = batch_stats
    
    def profile_neo4j_queries(self):
        """Profile common Neo4j queries to assess database performance."""
        def run_sample_queries():
            queries = [
                ("Count nodes", "MATCH (n) RETURN count(n) AS count"),
                ("Count relationships", "MATCH ()-[r]->() RETURN count(r) AS count"),
                ("Count by label", "MATCH (n) RETURN labels(n) AS label, count(*) AS count"),
                ("Get first 5 elements", "MATCH (e:Element) RETURN e.GlobalId, e.Name LIMIT 5"),
                ("Property lookup", "MATCH (ps:PropertySet)-[:HAS_PROPERTY]->(p:Property) WHERE p.Name = 'Name' RETURN ps.GlobalId, p.Value LIMIT 5")
            ]
            
            query_results = {}
            for name, query in queries:
                start = time.time()
                result = self.neo4j.run_query(query)
                elapsed = time.time() - start
                
                query_results[name] = {
                    "query": query,
                    "time": elapsed,
                    "result_count": len(result) if result else 0
                }
                
                logger.info(f"Query '{name}' took {elapsed:.4f} seconds")
            
            return query_results
        
        query_stats = self.time_operation("Sample Neo4j queries", run_sample_queries)
        self.query_stats["neo4j_queries"] = query_stats
    
    def profile_full_pipeline(self):
        """Do a short end-to-end test with a smaller subset of elements."""
        def process_mini_pipeline():
            # We'll process only the first 50 elements for this test
            mini_processor = IfcProcessor(
                ifc_file_path=self.ifc_file_path,
                neo4j_uri=self.neo4j_uri,
                neo4j_username=self.neo4j_username,
                neo4j_password=self.neo4j_password,
                neo4j_database=self.neo4j_database,
                enable_monitoring=False,
                parallel_processing=False,
                enable_topological_analysis=self.use_topology
            )
            
            # Only parse a subset of elements
            elements = self.parser.get_elements()[:50]
            
            # Process just these elements as a mini test
            start = time.time()
            # Access the private method using name mangling
            mini_processor._process_element_batch(elements)
            elapsed = time.time() - start
            
            return {
                "elements_processed": len(elements),
                "time_per_element": elapsed / len(elements) if elements else 0,
                "total_time": elapsed
            }
        
        mini_stats = self.time_operation("Mini end-to-end pipeline (50 elements)", process_mini_pipeline)
        self.query_stats["mini_pipeline"] = mini_stats
    
    def check_indexes(self):
        """Check the Neo4j indexes and constraints."""
        def get_db_stats():
            # Get index information
            index_query = "SHOW INDEXES"
            constraint_query = "SHOW CONSTRAINTS"
            
            indexes = self.neo4j.run_query(index_query)
            constraints = self.neo4j.run_query(constraint_query)
            
            return {
                "indexes": len(indexes),
                "constraints": len(constraints),
                "index_details": indexes,
                "constraint_details": constraints
            }
        
        db_stats = self.time_operation("Database index check", get_db_stats)
        self.query_stats["db_stats"] = db_stats
        
        # Log index details
        for idx in db_stats.get("index_details", []):
            if isinstance(idx, dict):
                logger.info(f"Index: {idx.get('name', 'unnamed')} - {idx.get('type', 'unknown type')} - {idx.get('state', 'unknown state')}")
    
    def run_full_profiling(self):
        """Run the full profiling suite."""
        try:
            # Create a mapper to use clear_graph method
            from src.ifc_to_graph.database.ifc_to_graph_mapper import IfcToGraphMapper
            
            # Clear the database first
            logger.info("Clearing existing database...")
            mapper = IfcToGraphMapper(self.neo4j)
            mapper.clear_graph()
            
            # Run the profiling tests
            self.profile_connection()
            self.profile_parsing()
            self.profile_schema_setup()
            self.profile_graph_mapper()
            
            if self.use_topology and TOPOLOGICPY_AVAILABLE:
                self.profile_topology_analysis()
                
            self.profile_batch_processing()
            self.profile_neo4j_queries()
            self.check_indexes()
            self.profile_full_pipeline()
            
            # Generate comprehensive report
            self.generate_report()
            
        except Exception as e:
            logger.error(f"Profiling failed: {str(e)}")
            logger.error(traceback.format_exc())
            
        finally:
            # Clean up
            if self.neo4j:
                self.neo4j.close()
    
    def generate_report(self):
        """Generate a comprehensive performance report with optimization recommendations."""
        report_path = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_path, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("IFC TO NEO4J KNOWLEDGE GRAPH PERFORMANCE REPORT\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"IFC File: {self.ifc_file_path}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Topology Analysis: {'Enabled' if self.use_topology else 'Disabled'}\n\n")
            
            f.write("-" * 80 + "\n")
            f.write("EXECUTION TIMES\n")
            f.write("-" * 80 + "\n\n")
            
            # Sort operations by execution time
            sorted_ops = sorted(self.timings.items(), key=lambda x: x[1], reverse=True)
            
            for operation, time_taken in sorted_ops:
                f.write(f"{operation}: {time_taken:.2f} seconds\n")
            
            f.write("\n")
            f.write("-" * 80 + "\n")
            f.write("MEMORY USAGE (MB)\n")
            f.write("-" * 80 + "\n\n")
            
            for operation, memory in self.memory_usage.items():
                peak_mb = memory["peak"] / 1024 / 1024
                current_mb = memory["current"] / 1024 / 1024
                f.write(f"{operation}: Current={current_mb:.2f}MB, Peak={peak_mb:.2f}MB\n")
            
            f.write("\n")
            f.write("-" * 80 + "\n")
            f.write("QUERY PERFORMANCE\n")
            f.write("-" * 80 + "\n\n")
            
            # Element creation stats
            if "element_creation" in self.query_stats:
                stats = self.query_stats["element_creation"]
                f.write(f"Element Creation (avg of 10 samples):\n")
                f.write(f"  Average time: {stats['avg_time']:.4f} seconds per element\n")
                f.write(f"  Maximum time: {stats['max_time']:.4f} seconds\n")
                f.write(f"  Minimum time: {stats['min_time']:.4f} seconds\n")
                f.write(f"  Projected time for all elements: {stats['avg_time'] * len(self.parser.get_elements()):.2f} seconds\n\n")
            
            # Property set creation stats
            if "property_set_creation" in self.query_stats:
                stats = self.query_stats["property_set_creation"]
                f.write(f"Property Set Creation (avg of 5 samples):\n")
                f.write(f"  Average time: {stats['avg_time']:.4f} seconds per property set\n")
                f.write(f"  Maximum time: {stats['max_time']:.4f} seconds\n")
                f.write(f"  Minimum time: {stats['min_time']:.4f} seconds\n")
                pset_count = len(self.parser.file.by_type("IfcPropertySet"))
                f.write(f"  Projected time for all property sets: {stats['avg_time'] * pset_count:.2f} seconds\n\n")
            
            # Material creation stats
            if "material_creation" in self.query_stats:
                stats = self.query_stats["material_creation"]
                f.write(f"Material Creation (avg of 5 samples):\n")
                f.write(f"  Average time: {stats['avg_time']:.4f} seconds per material\n")
                f.write(f"  Maximum time: {stats['max_time']:.4f} seconds\n")
                f.write(f"  Minimum time: {stats['min_time']:.4f} seconds\n")
                material_count = len(self.parser.file.by_type("IfcMaterial"))
                f.write(f"  Projected time for all materials: {stats['avg_time'] * material_count:.2f} seconds\n\n")
            
            # Topology analysis stats
            if "topology_analysis" in self.query_stats:
                stats = self.query_stats["topology_analysis"]
                f.write(f"Topology Analysis (10 samples):\n")
                f.write(f"  Relationships found: {stats['relationships_found']}\n")
                f.write(f"  Time per element: {stats['time_per_element']:.4f} seconds\n")
                f.write(f"  Projected time for all elements: {stats['time_per_element'] * len(self.parser.get_elements()):.2f} seconds\n\n")
            
            # Batch processing stats
            if "batch_processing" in self.query_stats:
                stats = self.query_stats["batch_processing"]
                f.write(f"Batch Processing (20 elements):\n")
                f.write(f"  Elements processed: {stats['elements_processed']}\n")
                f.write(f"  Time per element: {stats['time_per_element']:.4f} seconds\n")
                f.write(f"  Projected time for all elements: {stats['time_per_element'] * len(self.parser.get_elements()):.2f} seconds\n\n")
            
            # Mini pipeline stats
            if "mini_pipeline" in self.query_stats:
                stats = self.query_stats["mini_pipeline"]
                f.write(f"Mini End-to-End Pipeline (50 elements):\n")
                f.write(f"  Elements processed: {stats['elements_processed']}\n")
                f.write(f"  Time per element: {stats['time_per_element']:.4f} seconds\n")
                f.write(f"  Projected total time for all elements: {stats['time_per_element'] * len(self.parser.get_elements()):.2f} seconds\n\n")
            
            # Database stats
            if "db_stats" in self.query_stats:
                stats = self.query_stats["db_stats"]
                f.write(f"Database Statistics:\n")
                f.write(f"  Indexes: {stats.get('indexes', 'unknown')}\n")
                f.write(f"  Constraints: {stats.get('constraints', 'unknown')}\n\n")
            
            # Neo4j query stats
            if "neo4j_queries" in self.query_stats:
                f.write(f"Neo4j Query Performance:\n")
                for name, query_stat in self.query_stats["neo4j_queries"].items():
                    f.write(f"  {name}: {query_stat['time']:.4f} seconds\n")
                f.write("\n")
            
            # Calculate overall bottleneck
            if self.timings:
                slowest_op = max(self.timings.items(), key=lambda x: x[1])
                f.write(f"IDENTIFIED BOTTLENECK: {slowest_op[0]} taking {slowest_op[1]:.2f} seconds ({(slowest_op[1] / sum(self.timings.values())) * 100:.1f}% of total time)\n\n")
            
            # Recommendations
            f.write("-" * 80 + "\n")
            f.write("OPTIMIZATION RECOMMENDATIONS\n")
            f.write("-" * 80 + "\n\n")
            
            # Based on the slow query warning from the user (2 seconds per query)
            f.write("1. Database Query Optimization:\n")
            f.write("   - Ensure all required indexes are created and ONLINE\n")
            f.write("   - Consider increasing Neo4j memory settings (dbms.memory.heap.max_size)\n")
            f.write("   - Review and optimize Cypher queries in IfcToGraphMapper\n")
            f.write("   - Use EXPLAIN and PROFILE to identify slow queries\n\n")
            
            f.write("2. Batch Processing Optimization:\n")
            f.write("   - Tune batch size (currently the default is 100)\n")
            f.write("   - Experiment with different parallel worker counts\n")
            f.write("   - Consider implementing transaction batching\n\n")
            
            f.write("3. Topology Analysis Optimization:\n")
            f.write("   - Consider implementing a more efficient geometry calculation\n")
            f.write("   - Add options to limit topology analysis to specific element types\n")
            f.write("   - Implement caching for geometric calculations\n\n")
            
            f.write("4. Neo4j Configuration Recommendations:\n")
            f.write("   - Increase Java heap size: dbms.memory.heap.max_size=4G\n")
            f.write("   - Increase page cache: dbms.memory.pagecache.size=2G\n")
            f.write("   - Set appropriate transaction timeout: dbms.transaction.timeout=5m\n")
            f.write("   - Optimize for write performance: dbms.tx_state.memory_allocation=ON_HEAP\n\n")
            
            f.write("5. Code-Level Optimizations:\n")
            f.write("   - Optimize the material linking query which was identified as problematic\n")
            f.write("   - Consider using more efficient data structures for element lookup\n")
            f.write("   - Implement more granular transaction management\n")
            f.write("   - Add a query cache for repetitive operations\n\n")
            
            f.write("=" * 80 + "\n")
            f.write("PERFORMANCE REPORT COMPLETED\n")
            f.write("=" * 80 + "\n")
        
        logger.info(f"Performance report generated: {report_path}")
        return report_path

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Profile the IFC to Neo4j Knowledge Graph pipeline to identify bottlenecks"
    )
    
    parser.add_argument(
        "ifc_file",
        help="Path to the IFC file to process"
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
    
    parser.add_argument(
        "--topology",
        action="store_true",
        help="Include topology analysis in profiling"
    )
    
    return parser.parse_args()

def main():
    """Main entry point."""
    args = parse_args()
    
    logger.info(f"Starting performance profiling for {args.ifc_file}")
    
    if not os.path.exists(args.ifc_file):
        logger.error(f"IFC file not found: {args.ifc_file}")
        sys.exit(1)
    
    profiler = PipelineProfiler(
        ifc_file_path=args.ifc_file,
        neo4j_uri=args.uri,
        neo4j_username=args.username,
        neo4j_password=args.password,
        neo4j_database=args.database,
        use_topology=args.topology
    )
    
    profiler.run_full_profiling()

if __name__ == "__main__":
    main() 