#!/usr/bin/env python
"""
Performance Monitoring Example

This script demonstrates how to use the performance monitoring features
to track and analyze the performance of Neo4j operations.
"""

import os
import logging
import time
import sys

# Add project root to sys.path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector
from src.ifc_to_graph.database.performance_monitor import timing_decorator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Example IFC file path - replace with a valid path
SAMPLE_IFC_FILE = "data/samples/Duplex_A_20110907.ifc"

# Neo4j connection details
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "test1234"


@timing_decorator
def run_query_benchmark(connector: Neo4jConnector, count: int = 10, size: int = 100) -> None:
    """
    Run a benchmark with multiple queries.
    
    Args:
        connector: Neo4j connector instance
        count: Number of queries to run
        size: Size of the data to create
    """
    logger.info(f"Running query benchmark with {count} queries, size {size}")
    
    # First create test data
    connector.run_query(
        """
        UNWIND range(1, $size) AS i
        CREATE (n:BenchmarkNode {id: i, value: rand(), timestamp: timestamp()})
        RETURN count(n) AS created
        """,
        {"size": size}
    )
    
    # Run multiple queries
    for i in range(count):
        # Start timer for this query
        stop_timer = connector.performance_monitor.start_timer(
            "read_benchmark_query", 
            {"iteration": i, "total": count}
        )
        
        # Run query with random reads
        result = connector.run_query(
            """
            MATCH (n:BenchmarkNode)
            WHERE n.id % $mod = 0
            RETURN n.id, n.value
            ORDER BY n.value DESC
            LIMIT 10
            """,
            {"mod": i % 10 + 1}
        )
        
        # Stop timer
        stop_timer()
        
        # Log results
        logger.info(f"Query {i+1}/{count}: Retrieved {len(result)} records")
        
        # Add small delay
        time.sleep(0.1)


@timing_decorator
def run_batch_benchmark(connector: Neo4jConnector, batch_sizes: list = [10, 50, 100, 200]) -> None:
    """
    Run a benchmark testing different batch sizes.
    
    Args:
        connector: Neo4j connector instance
        batch_sizes: List of batch sizes to test
    """
    logger.info(f"Running batch size benchmark with sizes: {batch_sizes}")
    
    # Test each batch size
    for batch_size in batch_sizes:
        # Create batch data
        batch_data = [
            {"id": i, "value": i * 0.1} 
            for i in range(batch_size)
        ]
        
        # Start timer for this batch
        stop_timer = connector.performance_monitor.start_timer(
            "batch_operation", 
            {"batch_size": batch_size}
        )
        
        # Execute batch
        connector.execute_batch(
            """
            CREATE (n:BatchNode {id: $id, value: $value, created: timestamp()})
            """,
            batch_data
        )
        
        # Stop timer
        elapsed_ms = stop_timer()
        
        # Log results
        logger.info(f"Batch size {batch_size}: {elapsed_ms:.2f} ms ({elapsed_ms/batch_size:.2f} ms per item)")
        
        # Track memory
        connector.performance_monitor.measure_memory(
            "after_batch", 
            {"batch_size": batch_size}
        )


def cleanup(connector: Neo4jConnector) -> None:
    """
    Clean up test data.
    
    Args:
        connector: Neo4j connector instance
    """
    logger.info("Cleaning up test data")
    
    # Clean up benchmark nodes
    connector.run_query("MATCH (n:BenchmarkNode) DELETE n")
    
    # Clean up batch nodes
    connector.run_query("MATCH (n:BatchNode) DELETE n")
    
    logger.info("Test data cleaned up")


def main() -> None:
    """Main entry point for the example."""
    try:
        # Create output directory for performance reports
        os.makedirs("performance_reports", exist_ok=True)
        
        # Connect to Neo4j with performance monitoring enabled
        logger.info(f"Connecting to Neo4j at {NEO4J_URI}")
        connector = Neo4jConnector(
            uri=NEO4J_URI, 
            username=NEO4J_USERNAME, 
            password=NEO4J_PASSWORD,
            enable_monitoring=True
        )
        
        # Test connection
        if not connector.test_connection():
            logger.error("Failed to connect to Neo4j")
            return
            
        logger.info("Successfully connected to Neo4j")
        
        # Measure initial memory usage
        connector.performance_monitor.measure_memory("startup")
        
        # Run performance benchmarks
        run_query_benchmark(connector)
        run_batch_benchmark(connector)
        
        # Measure final memory usage
        connector.performance_monitor.measure_memory("completion")
        
        # Generate and print performance report
        print("\n" + "=" * 80)
        print("PERFORMANCE REPORT")
        print("=" * 80)
        print(connector.get_performance_report())
        
        # Export metrics
        metrics_data = connector.export_performance_metrics(
            "performance_reports/benchmark_metrics.json"
        )
        logger.info(f"Exported {len(metrics_data['metrics'])} metrics to performance_reports/benchmark_metrics.json")
        
        # Save report
        with open("performance_reports/benchmark_report.txt", "w") as report_file:
            report_file.write(connector.get_performance_report())
        logger.info("Saved performance report to performance_reports/benchmark_report.txt")
        
        # Clean up
        cleanup(connector)
        
        # Close connection
        connector.close()
        
    except Exception as e:
        logger.error(f"Error in performance monitoring example: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main() 