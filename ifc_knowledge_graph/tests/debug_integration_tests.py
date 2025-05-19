#!/usr/bin/env python
"""
Debug Integration Tests

This script runs the integration tests with error capturing and provides a cleaner summary
of any issues that occur. It helps diagnose problems without sifting through massive logs.
"""

import os
import sys
import time
import logging
import importlib
import traceback
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import test classes (this way we can reload them if changed)
from tests.test_integration_optimized import TestIntegrationOptimized

def run_test_with_error_capture(test_name="test_1_end_to_end_pipeline", 
                                clear_db=False, batch_size=200):
    """
    Run a specific integration test with detailed error capturing.
    
    Args:
        test_name: Name of the test method to run
        clear_db: Whether to clear the database before running
        batch_size: Batch size for element processing
    """
    print(f"\n{'='*80}")
    print(f"RUNNING TEST: {test_name}")
    print(f"{'='*80}")
    
    # Import fresh instance of test module
    test_module = importlib.reload(sys.modules.get('tests.test_integration_optimized'))
    test_class = getattr(test_module, 'TestIntegrationOptimized')
    
    # Override global configuration with performance-optimized settings
    test_module.CLEAR_DATABASE = clear_db
    test_module.BATCH_SIZE = batch_size
    test_module.OPTIMIZE_IFC = True  # Always use optimization
    
    # Add custom module variable for parallel worker count if it exists
    if hasattr(test_module, 'set_parallel_workers'):
        # Use maximum available cores minus 1 (to keep system responsive)
        import multiprocessing
        worker_count = max(1, multiprocessing.cpu_count() - 1)
        test_module.set_parallel_workers(worker_count)
    
    # Setup class first to initialize class variables
    test_class.setUpClass()
    
    # Create test instance
    test_instance = test_class(test_name)
    test_instance.ifc_file = test_class.ifc_file
    test_instance.neo4j_uri = test_class.neo4j_uri if hasattr(test_class, 'neo4j_uri') else "neo4j://localhost:7687"
    test_instance.neo4j_username = test_class.neo4j_username if hasattr(test_class, 'neo4j_username') else "neo4j"
    test_instance.neo4j_password = test_class.neo4j_password if hasattr(test_class, 'neo4j_password') else "test1234"
    test_instance.temp_dir = test_class.temp_dir
    
    # Setup test
    test_instance.setUp()
    
    start_time = time.time()
    error_info = None
    
    try:
        # Run the test
        getattr(test_instance, test_name)()
        success = True
        print(f"\n✅ Test {test_name} PASSED!")
        
    except Exception as e:
        success = False
        error_info = {
            'exception_type': type(e).__name__,
            'message': str(e),
            'traceback': traceback.format_exc()
        }
        
        # Extract relevant context from error
        context = {}
        if 'mapper' in str(e):
            context['component'] = 'IfcToGraphMapper'
        elif 'parser' in str(e):
            context['component'] = 'IfcParser'
        elif 'connector' in str(e):
            context['component'] = 'Neo4jConnector'
        elif 'processor' in str(e):
            context['component'] = 'IfcProcessor'
            
        # Check for common errors
        if "no attribute" in str(e):
            context['error_type'] = 'Missing method or attribute'
            context['suggestion'] = f"Create missing {str(e).split('no attribute ')[-1].split('.')[0]}"
        elif "KeyError" in str(e):
            context['error_type'] = 'Missing key in dictionary'
        elif "TypeError" in str(e):
            context['error_type'] = 'Type mismatch'
            
        error_info['context'] = context
    
    finally:
        # Cleanup
        test_instance.tearDown()
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Print results
    print(f"\nTest completed in {duration:.2f} seconds")
    
    if not success:
        print(f"\n{'='*80}")
        print(f"ERROR REPORT FOR: {test_name}")
        print(f"{'='*80}")
        print(f"Exception Type: {error_info['exception_type']}")
        print(f"Message: {error_info['message']}")
        
        if 'context' in error_info:
            context = error_info['context']
            print("\nContext Analysis:")
            for key, value in context.items():
                print(f"  {key}: {value}")
        
        # Print simplified traceback (last 10 lines only)
        print("\nTraceback (most recent call last):")
        traceback_lines = error_info['traceback'].splitlines()
        if len(traceback_lines) > 10:
            print("  ...")
            for line in traceback_lines[-10:]:
                print(f"  {line}")
        else:
            for line in traceback_lines:
                print(f"  {line}")
    
    print(f"\n{'='*80}")
    return success

def run_all_tests():
    """Run all test methods in the integration test class."""
    # Find all test methods in the TestIntegrationOptimized class
    test_methods = [method for method in dir(TestIntegrationOptimized) 
                   if method.startswith('test_')]
    
    results = {}
    
    for method in test_methods:
        results[method] = run_test_with_error_capture(method, clear_db=False, batch_size=200)
    
    # Print summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    
    for method, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{method}: {status}")
    
    # Overall status
    if all(results.values()):
        print("\nAll tests passed successfully! 🎉")
    else:
        print(f"\n{results.values().count(False)} test(s) failed! 😭")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Debug integration tests with better error reporting")
    parser.add_argument("--test", type=str, default="test_1_end_to_end_pipeline", 
                      help="Name of test to run (default: test_1_end_to_end_pipeline)")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--clear", action="store_true", help="Clear database before running tests")
    parser.add_argument("--batch-size", type=int, default=200, help="Batch size for processing")
    
    args = parser.parse_args()
    
    if args.all:
        run_all_tests()
    else:
        run_test_with_error_capture(args.test, args.clear, args.batch_size) 