#!/usr/bin/env python
"""
Standalone Parallel Processing Example

This script demonstrates the parallel processing functionality without relying on module imports.
"""

import os
import sys
import time
import logging
import threading
import concurrent.futures
from typing import List, Any, Optional, Callable

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskProcessor:
    """Simple parallel task processor."""
    
    def __init__(self, max_workers: Optional[int] = None):
        """Initialize with optional worker count."""
        self.max_workers = max_workers or os.cpu_count() or 4
        logger.info(f"Initialized TaskProcessor with {self.max_workers} workers")
    
    def process_items(self, items: List[Any], worker_func: Callable[[Any], Any]) -> List[Any]:
        """Process items in parallel."""
        if not items:
            return []
        
        logger.info(f"Processing {len(items)} items in parallel")
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit tasks
            futures = [executor.submit(worker_func, item) for item in items]
            
            # Collect results
            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error processing item: {str(e)}")
        
        elapsed = time.time() - start_time
        logger.info(f"Processing completed in {elapsed:.2f}s ({len(items)/elapsed:.2f} items/s)")
        
        return results

def demo_worker(n: int) -> int:
    """Demo worker function that waits and returns a value."""
    logger.info(f"Processing item {n}")
    time.sleep(0.2)  # Simulate work
    return n * 2

def main():
    """Main function for demonstration."""
    logger.info("Starting parallel processing demonstration")
    
    # Create some test data
    test_data = list(range(20))
    
    # Create processor
    processor = TaskProcessor(max_workers=4)
    
    # Process data in parallel
    results = processor.process_items(test_data, demo_worker)
    
    logger.info(f"Results: {results}")
    logger.info("Demonstration completed successfully")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 