#!/usr/bin/env python
"""
Optimize all IFC files in the data directory

This script scans the data directory for IFC files and optimizes them
using the IFC optimizer to remove duplicate geometry instances and reduce file size.
"""

import os
import sys
import time
import argparse
import logging
from pathlib import Path
import concurrent.futures
from tqdm import tqdm

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.ifc_optimize import optimize_ifc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def optimize_single_file(file_path, force=False, verbose=False):
    """
    Optimize a single IFC file.
    
    Args:
        file_path: Path to the IFC file
        force: Whether to optimize even if an optimized file already exists
        verbose: Whether to print detailed information
        
    Returns:
        Dictionary with optimization results or None if skipped
    """
    input_path = Path(file_path)
    output_path = input_path.parent / f"{input_path.stem}_optimized{input_path.suffix}"
    
    # Skip if output already exists and force is False
    if output_path.exists() and not force:
        if verbose:
            logger.info(f"Skipping {file_path} - optimized file already exists")
        return None
    
    try:
        result, _, _ = optimize_ifc(str(input_path), str(output_path))
        return result
    except Exception as e:
        logger.error(f"Failed to optimize {file_path}: {str(e)}")
        return None

def find_ifc_files(directory):
    """
    Find all IFC files in the given directory and its subdirectories.
    
    Args:
        directory: Path to search for IFC files
        
    Returns:
        List of paths to IFC files
    """
    directory = Path(directory)
    ifc_files = []
    
    for path in directory.glob('**/*.ifc'):
        # Skip already optimized files
        if "_optimized.ifc" not in path.name:
            ifc_files.append(path)
    
    return ifc_files

def optimize_all_ifcs(data_dir, force=False, parallel=True, max_workers=None, verbose=False):
    """
    Optimize all IFC files in the data directory.
    
    Args:
        data_dir: Directory to search for IFC files
        force: Whether to optimize even if an optimized file already exists
        parallel: Whether to use parallel processing
        max_workers: Maximum number of worker processes
        verbose: Whether to print detailed information
        
    Returns:
        Dictionary with optimization statistics
    """
    start_time = time.time()
    
    # Find all IFC files
    ifc_files = find_ifc_files(data_dir)
    logger.info(f"Found {len(ifc_files)} IFC files to optimize")
    
    # Track optimization results
    results = []
    total_size_before = 0
    total_size_after = 0
    
    if parallel and len(ifc_files) > 1:
        # Determine number of workers
        if max_workers is None:
            max_workers = min(os.cpu_count() or 1, 4)  # Limit to 4 workers by default
        
        logger.info(f"Optimizing files using {max_workers} parallel workers")
        
        # Process files in parallel
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(optimize_single_file, str(file_path), force, verbose): file_path 
                      for file_path in ifc_files}
            
            # Show progress bar
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures),
                              desc="Optimizing IFC files"):
                file_path = futures[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        total_size_before += result["start_file_size"]
                        total_size_after += result["end_file_size"]
                except Exception as e:
                    logger.error(f"Error optimizing {file_path}: {str(e)}")
    else:
        # Process files sequentially
        logger.info("Optimizing files sequentially")
        
        # Show progress bar
        for file_path in tqdm(ifc_files, desc="Optimizing IFC files"):
            result = optimize_single_file(str(file_path), force, verbose)
            if result:
                results.append(result)
                total_size_before += result["start_file_size"]
                total_size_after += result["end_file_size"]
    
    # Calculate overall statistics
    end_time = time.time()
    
    if not results:
        logger.info("No files were optimized. All files may already have optimized versions.")
        return None
    
    # Prepare summary statistics
    stats = {
        "files_processed": len(results),
        "total_size_before": total_size_before,
        "total_size_after": total_size_after,
        "total_size_reduction": total_size_before - total_size_after,
        "total_size_reduction_percent": (1 - (total_size_after / total_size_before)) * 100 if total_size_before > 0 else 0,
        "average_size_reduction_percent": sum(r["size_reduction_percent"] for r in results) / len(results),
        "processing_time": end_time - start_time
    }
    
    return stats

def print_optimization_summary(stats):
    """
    Print a summary of the optimization results.
    
    Args:
        stats: Dictionary with optimization statistics
    """
    if not stats:
        return
    
    print("\n=== Optimization Summary ===")
    print(f"Files processed: {stats['files_processed']}")
    print(f"Total size before: {stats['total_size_before']/1024/1024:.2f} MB")
    print(f"Total size after: {stats['total_size_after']/1024/1024:.2f} MB")
    print(f"Total size reduction: {stats['total_size_reduction']/1024/1024:.2f} MB ({stats['total_size_reduction_percent']:.2f}%)")
    print(f"Average size reduction: {stats['average_size_reduction_percent']:.2f}%")
    print(f"Total processing time: {stats['processing_time']:.2f} seconds")

def main():
    parser = argparse.ArgumentParser(description="Optimize all IFC files in the data directory")
    parser.add_argument("--data-dir", default=str(project_root / "data" / "ifc_files"),
                       help="Directory containing IFC files to optimize")
    parser.add_argument("--force", action="store_true",
                       help="Force optimization even if optimized file already exists")
    parser.add_argument("--sequential", action="store_true",
                       help="Process files sequentially instead of in parallel")
    parser.add_argument("--max-workers", type=int, default=None,
                       help="Maximum number of worker processes for parallel optimization")
    parser.add_argument("--verbose", action="store_true",
                       help="Print detailed information during optimization")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check if data directory exists
    if not os.path.exists(args.data_dir):
        logger.error(f"Data directory not found: {args.data_dir}")
        return 1
    
    try:
        stats = optimize_all_ifcs(
            args.data_dir,
            force=args.force,
            parallel=not args.sequential,
            max_workers=args.max_workers,
            verbose=args.verbose
        )
        
        print_optimization_summary(stats)
        
        return 0
    except Exception as e:
        logger.error(f"Error during optimization: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 