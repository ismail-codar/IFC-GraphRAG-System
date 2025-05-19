#!/usr/bin/env python
"""
Optimized Integration Tests for IFC to Neo4j Knowledge Graph

This module contains integration tests for the complete pipeline from
IFC file to Neo4j, validating the end-to-end functionality with 
improved performance and error handling.
"""

import os
import sys
import unittest
import logging
import tempfile
import time
import psutil
import json
import argparse
from datetime import datetime
from pathlib import Path

# Add the src directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ifc_to_graph.processor import IfcProcessor
from src.ifc_to_graph.parser import IfcParser
from src.ifc_to_graph.database import Neo4jConnector
from tools.ifc_optimize import optimize_ifc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global variables that can be set via command-line arguments
CLEAR_DATABASE = True  # Default: Clear database before running tests
BATCH_SIZE = 50  # Default batch size
RUN_SINGLE_TEST = None  # Default: Run all tests
OPTIMIZE_IFC = False  # Default: Don't optimize IFC files
PARALLEL_WORKERS = 4  # Default: Use 4 parallel workers

def set_parallel_workers(count):
    """Set the number of parallel workers to use."""
    global PARALLEL_WORKERS
    PARALLEL_WORKERS = count
    logger.info(f"Set parallel workers to {count}")

class TestIntegrationOptimized(unittest.TestCase):
    """
    Integration tests for the IFC to Neo4j Knowledge Graph.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures that should be reused across tests."""
        cls.ifc_file = "data/ifc_files/Duplex_A_20110907.ifc"
        
        # Optimize IFC file if enabled
        if OPTIMIZE_IFC:
            logger.info(f"Optimizing IFC file: {cls.ifc_file}")
            optimized_path = f"{cls.ifc_file}_optimized.ifc"
            
            # Check if optimized file already exists and is newer than the original
            if (Path(optimized_path).exists() and 
                Path(optimized_path).stat().st_mtime > Path(cls.ifc_file).stat().st_mtime):
                logger.info(f"Using existing optimized file: {optimized_path}")
                cls.ifc_file = optimized_path
            else:
                try:
                    # Import the optimizer and optimize the file
                    result, _, _ = optimize_ifc(cls.ifc_file, optimized_path)
                    logger.info(f"IFC optimization complete: {result['size_reduction_percent']:.1f}% size reduction")
                    cls.ifc_file = optimized_path
                except Exception as e:
                    logger.error(f"IFC optimization failed: {str(e)}")
                    logger.warning("Continuing with original file")
        
        # Initialize the parser
        cls.parser = IfcParser(cls.ifc_file)
        
        # Get the IFC schema version
        schema_version = cls.parser.get_schema_version()
        logger.info(f"Testing with IFC version: {schema_version}")
        
        # Initialize the processor
        cls.processor = IfcProcessor(
            ifc_file_path=cls.ifc_file,
            neo4j_uri="neo4j://localhost:7687",
            neo4j_username="neo4j",
            neo4j_password="test1234",
            parallel_processing=True,
            enable_monitoring=True
        )
        
        # Create temp directory for performance reports
        cls.temp_dir = tempfile.mkdtemp()
        
    @classmethod
    def tearDownClass(cls):
        """Tear down test fixtures after all tests are run."""
        # Clean up temp directory if it exists
        if hasattr(cls, 'temp_dir') and os.path.exists(cls.temp_dir):
            import shutil
            shutil.rmtree(cls.temp_dir)
            
    def setUp(self):
        """Set up test fixtures before each test."""
        pass
        
    def tearDown(self):
        """Tear down test fixtures after each test."""
        pass
        
    def get_memory_usage(self):
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
        
    def test_1_end_to_end_pipeline(self):
        """Test the complete processing pipeline from IFC to Neo4j."""
        # Record initial memory usage
        start_memory = self.get_memory_usage()
        logger.info(f"Initial memory usage: {start_memory:.2f} MB")
        
        try:
            # Process the IFC file with database reset config from command line
            # Use a larger batch size and parallel_batch_size for faster processing
            stats = self.processor.process(
                clear_existing=CLEAR_DATABASE,
                batch_size=BATCH_SIZE,
                parallel_batch_size=600,  # Even larger for speed
                save_performance_report=True,
                parallel_workers=PARALLEL_WORKERS,  # Use configured worker count
                optimize_memory=False  # Optimize for speed rather than memory
            )
            
            # Get final memory usage
            end_memory = self.get_memory_usage()
            logger.info(f"Final memory usage: {end_memory:.2f} MB")
            logger.info(f"Memory increase: {end_memory - start_memory:.2f} MB")
            
            # Verify that the processing completed successfully
            self.assertIsNotNone(stats, "Processing stats should not be None")
            self.assertIn("total_elements", stats, "Stats should include total_elements")
            self.assertIn("processing_time", stats, "Stats should include processing_time")
            
            # Log the processing statistics
            logger.info(f"Processed {stats['total_elements']} elements in {stats['processing_time']:.2f} seconds")
            logger.info(f"Processing rate: {stats['total_elements'] / stats['processing_time']:.2f} elements/second")
            
            # Save report with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = os.path.join(self.temp_dir, f"performance_report_{timestamp}.json")
            with open(report_path, 'w') as f:
                json.dump(stats, f, indent=2)
                
            logger.info(f"Performance report saved to {report_path}")
            
        except Exception as e:
            self.fail(f"End-to-end test failed with exception: {str(e)}")
            
    def test_2_database_statistics(self):
        """Test that the database contains the expected elements."""
        try:
            # Create a new connector directly
            connector = Neo4jConnector(
                uri="neo4j://localhost:7687",
                username="neo4j", 
                password="test1234"
            )
            
            # Verify connection
            self.assertTrue(connector.test_connection(), "Neo4j connection failed")
            
            # Test database statistics
            element_count = connector.run_query("MATCH (n:Element) RETURN COUNT(n) AS count")[0]['count']
            logger.info(f"Element count in database: {element_count}")
            self.assertGreater(element_count, 0, "Database should contain elements")
            
            # Check for specific element types
            wall_count = connector.run_query("MATCH (n:Element:Wall) RETURN COUNT(n) AS count")[0]['count']
            logger.info(f"Wall count in database: {wall_count}")
            self.assertGreater(wall_count, 0, "Database should contain walls")
            
            # Check for relationships
            contains_count = connector.run_query("MATCH ()-[r:CONTAINS]->() RETURN COUNT(r) AS count")[0]['count']
            logger.info(f"CONTAINS relationship count: {contains_count}")
            self.assertGreater(contains_count, 0, "Database should contain CONTAINS relationships")
            
            # Close the connection
            connector.close()
            
        except Exception as e:
            self.fail(f"Database statistics test failed with exception: {str(e)}")

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run integration tests for IFC to Neo4j Knowledge Graph")
    parser.add_argument("--no-clear", action="store_true", help="Don't clear the database before running tests")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for processing elements")
    parser.add_argument("--test", type=str, help="Run a specific test method")
    parser.add_argument("--optimize", action="store_true", help="Optimize IFC files before testing")
    
    args = parser.parse_args()
    
    # Set global variables based on command-line arguments
    global CLEAR_DATABASE, BATCH_SIZE, RUN_SINGLE_TEST, OPTIMIZE_IFC, PARALLEL_WORKERS
    CLEAR_DATABASE = not args.no_clear
    BATCH_SIZE = args.batch_size
    RUN_SINGLE_TEST = args.test
    OPTIMIZE_IFC = args.optimize
    
    return args

if __name__ == "__main__":
    # Parse command-line arguments
    args = parse_args()
    
    # Create a test suite
    test_suite = unittest.TestSuite()
    
    # Add specific test if requested, otherwise add all tests
    if RUN_SINGLE_TEST:
        test_suite.addTest(TestIntegrationOptimized(RUN_SINGLE_TEST))
    else:
        test_suite.addTest(unittest.makeSuite(TestIntegrationOptimized))
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite) 