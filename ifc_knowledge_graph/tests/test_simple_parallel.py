#!/usr/bin/env python
"""Simple test for parallel processing."""

import os
import time
import threading
import concurrent.futures

def main():
    """Test basic parallel processing functionality."""
    print("Testing basic parallel processing...")
    
    # Test 1: Create a thread pool executor
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        print(f"Created ThreadPoolExecutor with 2 workers")
        
        # Define a simple worker function
        def worker(n):
            """Simple worker function that sleeps and returns n."""
            print(f"Worker {n} started")
            time.sleep(0.1)
            print(f"Worker {n} finished")
            return n * 2
        
        # Submit some tasks
        print("Submitting tasks...")
        futures = [executor.submit(worker, i) for i in range(5)]
        
        # Collect results
        results = []
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"Got result: {result}")
        
        print(f"All results: {results}")
    
    print("Test completed successfully")
    return 0

if __name__ == "__main__":
    exit(main()) 