#!/usr/bin/env python
"""
Parallel Processing Example

This script demonstrates the performance benefits of parallel processing
when converting IFC files to Neo4j. It compares sequential vs parallel execution.
"""

import os
import logging
import time
import sys
import argparse
from datetime import datetime

# Add project root to sys.path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.ifc_to_graph.processor import IfcProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Default settings - update as needed
DEFAULT_IFC_FILE = "data/samples/Duplex_A_20110907.ifc"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "test1234"
BATCH_SIZES = [50, 100, 200]


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Compare parallel vs sequential processing performance."
    )
    
    parser.add_argument(
        "--ifc-file", "-f",
        default=DEFAULT_IFC_FILE,
        help=f"Path to IFC file (default: {DEFAULT_IFC_FILE})"
    )
    
    parser.add_argument(
        "--uri",
        default=NEO4J_URI,
        help=f"Neo4j connection URI (default: {NEO4J_URI})"
    )
    
    parser.add_argument(
        "--username",
        default=NEO4J_USERNAME,
        help=f"Neo4j username (default: {NEO4J_USERNAME})"
    )
    
    parser.add_argument(
        "--password",
        default=NEO4J_PASSWORD,
        help=f"Neo4j password (default: {NEO4J_PASSWORD})"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of workers for parallel processing (default: CPU count)"
    )
    
    return parser.parse_args()


def run_sequential_test(args, batch_size):
    """Run test with sequential processing."""
    logger.info(f"Running SEQUENTIAL test with batch size {batch_size}")
    start_time = time.time()
    
    # Create processor with sequential processing
    processor = IfcProcessor(
        ifc_file_path=args.ifc_file,
        neo4j_uri=args.uri,
        neo4j_username=args.username,
        neo4j_password=args.password,
        enable_monitoring=True,
        monitoring_output_dir="performance_reports",
        parallel_processing=False
    )
    
    # Process the file
    try:
        stats = processor.process(
            clear_existing=True,
            batch_size=batch_size,
            save_performance_report=True
        )
        
        # Close connections
        processor.close()
        
        # Calculate timing
        elapsed = time.time() - start_time
        
        return {
            "mode": "sequential",
            "batch_size": batch_size,
            "time": elapsed,
            "elements": stats["element_count"],
            "nodes": stats["node_count"],
            "relationships": stats["relationship_count"],
            "elements_per_second": stats["element_count"] / elapsed
        }
    
    except Exception as e:
        logger.error(f"Error in sequential processing: {str(e)}")
        processor.close()
        return None


def run_parallel_test(args, batch_size):
    """Run test with parallel processing."""
    logger.info(f"Running PARALLEL test with batch size {batch_size}")
    start_time = time.time()
    
    # Create processor with parallel processing
    processor = IfcProcessor(
        ifc_file_path=args.ifc_file,
        neo4j_uri=args.uri,
        neo4j_username=args.username,
        neo4j_password=args.password,
        enable_monitoring=True,
        monitoring_output_dir="performance_reports",
        parallel_processing=True,
        max_workers=args.workers
    )
    
    # Process the file
    try:
        stats = processor.process(
            clear_existing=True,
            batch_size=batch_size,
            save_performance_report=True
        )
        
        # Close connections
        processor.close()
        
        # Calculate timing
        elapsed = time.time() - start_time
        
        return {
            "mode": "parallel",
            "batch_size": batch_size,
            "workers": stats.get("parallel_workers", 0),
            "time": elapsed,
            "elements": stats["element_count"],
            "nodes": stats["node_count"],
            "relationships": stats["relationship_count"],
            "elements_per_second": stats["element_count"] / elapsed
        }
    
    except Exception as e:
        logger.error(f"Error in parallel processing: {str(e)}")
        processor.close()
        return None


def format_results(results):
    """Format results for display."""
    output = []
    output.append("\n" + "=" * 80)
    output.append("PERFORMANCE COMPARISON: SEQUENTIAL VS PARALLEL PROCESSING")
    output.append("=" * 80)
    
    # Group by batch size
    by_batch = {}
    for result in results:
        if result:
            batch_size = result["batch_size"]
            if batch_size not in by_batch:
                by_batch[batch_size] = []
            by_batch[batch_size].append(result)
    
    for batch_size, batch_results in sorted(by_batch.items()):
        output.append(f"\nBatch Size: {batch_size}")
        output.append("-" * 40)
        
        for result in sorted(batch_results, key=lambda x: x["mode"]):
            mode = result["mode"].upper()
            workers = result.get("workers", "N/A")
            time_taken = result["time"]
            elements = result["elements"]
            elements_per_second = result["elements_per_second"]
            
            if mode == "PARALLEL":
                output.append(f"{mode} (workers={workers}):")
            else:
                output.append(f"{mode}:")
                
            output.append(f"  Time: {time_taken:.2f} seconds")
            output.append(f"  Elements: {elements}")
            output.append(f"  Elements/second: {elements_per_second:.2f}")
        
        # If we have both sequential and parallel, calculate speedup
        modes = [r["mode"] for r in batch_results]
        if "sequential" in modes and "parallel" in modes:
            seq_time = next(r["time"] for r in batch_results if r["mode"] == "sequential")
            par_time = next(r["time"] for r in batch_results if r["mode"] == "parallel")
            speedup = seq_time / par_time if par_time > 0 else 0
            output.append(f"  Speedup factor: {speedup:.2f}x")
    
    output.append("\n" + "=" * 80)
    return "\n".join(output)


def save_results(results, filename="parallel_benchmark_results.txt"):
    """Save results to file."""
    report_dir = "performance_reports"
    os.makedirs(report_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(report_dir, f"{timestamp}_{filename}")
    
    with open(filepath, "w") as f:
        f.write(format_results(results))
        
    logger.info(f"Saved benchmark results to {filepath}")
    return filepath


def main():
    """Main entry point for the example."""
    args = parse_args()
    
    # Check if IFC file exists
    if not os.path.exists(args.ifc_file):
        logger.error(f"IFC file not found: {args.ifc_file}")
        sys.exit(1)
    
    # Create performance reports directory
    os.makedirs("performance_reports", exist_ok=True)
    
    # Run tests for different batch sizes
    results = []
    
    try:
        for batch_size in BATCH_SIZES:
            # Sequential test
            seq_result = run_sequential_test(args, batch_size)
            if seq_result:
                results.append(seq_result)
            
            # Parallel test
            par_result = run_parallel_test(args, batch_size)
            if par_result:
                results.append(par_result)
    
        # Display and save results
        print(format_results(results))
        results_file = save_results(results)
        logger.info(f"Completed performance comparison")
        
    except Exception as e:
        logger.error(f"Error running performance comparison: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main() 