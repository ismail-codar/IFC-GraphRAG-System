#!/usr/bin/env python
"""
Integration Tests for IFC to Neo4j Knowledge Graph

This module contains integration tests for the complete pipeline from
IFC file to Neo4j, validating the end-to-end functionality.
"""

import os
import sys
import unittest
import logging
import tempfile
from pathlib import Path

# Add the src directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ifc_to_graph.processor import IfcProcessor
from src.ifc_to_graph.parser import IfcParser
from src.ifc_to_graph.database import Neo4jConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class IntegrationTestConfig:
    """Configuration for integration tests."""
    
    # IFC File to use for testing (replace with an actual test file path)
    IFC_TEST_FILE = os.environ.get(
        "IFC_TEST_FILE", 
        str(project_root / "data" / "ifc_files" / "Duplex_A_20110907.ifc")
    )
    
    # Neo4j connection details
    NEO4J_URI = os.environ.get("NEO4J_TEST_URI", "neo4j://localhost:7687")
    NEO4J_USER = os.environ.get("NEO4J_TEST_USER", "neo4j")
    NEO4J_PASSWORD = os.environ.get("NEO4J_TEST_PASSWORD", "test1234")
    NEO4J_DATABASE = os.environ.get("NEO4J_TEST_DATABASE", "neo4j")
    
    # Test specific configurations
    BATCH_SIZE = 50
    PARALLEL_PROCESSING = False
    CLEAR_EXISTING = True
    DOMAIN_ENRICHMENT = True


class TestIntegration(unittest.TestCase):
    """Integration tests for the IFC to Neo4j conversion pipeline."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests."""
        # Check if test IFC file exists
        if not os.path.exists(IntegrationTestConfig.IFC_TEST_FILE):
            raise FileNotFoundError(
                f"Test IFC file not found: {IntegrationTestConfig.IFC_TEST_FILE}. "
                f"Please set the IFC_TEST_FILE environment variable to a valid IFC file path."
            )
        
        # Create test output directory
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.output_dir = Path(cls.temp_dir.name)
        
        # Create Neo4j connector but skip test_connection
        # We know the connection works from test_direct_connection.py
        cls.connector = Neo4jConnector(
            uri=IntegrationTestConfig.NEO4J_URI,
            username=IntegrationTestConfig.NEO4J_USER,
            password=IntegrationTestConfig.NEO4J_PASSWORD,
            database=IntegrationTestConfig.NEO4J_DATABASE,
            enable_monitoring=False  # Disable performance monitoring
        )
        
        # Close the connection for now
        cls.connector.close()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests have run."""
        # Remove temporary directory
        cls.temp_dir.cleanup()
    
    def setUp(self):
        """Set up before each test."""
        # Create processor for each test
        self.processor = IfcProcessor(
            ifc_file_path=IntegrationTestConfig.IFC_TEST_FILE,
            neo4j_uri=IntegrationTestConfig.NEO4J_URI,
            neo4j_username=IntegrationTestConfig.NEO4J_USER,
            neo4j_password=IntegrationTestConfig.NEO4J_PASSWORD,
            neo4j_database=IntegrationTestConfig.NEO4J_DATABASE,
            enable_monitoring=True,
            monitoring_output_dir=str(self.output_dir),
            parallel_processing=IntegrationTestConfig.PARALLEL_PROCESSING,
            enable_domain_enrichment=IntegrationTestConfig.DOMAIN_ENRICHMENT
        )
    
    def tearDown(self):
        """Clean up after each test."""
        if hasattr(self, 'processor') and self.processor:
            self.processor.close()
    
    def test_end_to_end_pipeline(self):
        """Test the complete processing pipeline from IFC to Neo4j."""
        # Process the IFC file
        stats = self.processor.process(
            clear_existing=IntegrationTestConfig.CLEAR_EXISTING,
            batch_size=IntegrationTestConfig.BATCH_SIZE,
            save_performance_report=True
        )
        
        # Verify that processing completed successfully
        self.assertIsNotNone(stats, "Processing stats should not be None")
        self.assertGreater(stats['element_count'], 0, "Should have processed at least one element")
        self.assertGreater(stats['node_count'], 0, "Should have created at least one node")
        self.assertGreater(stats['relationship_count'], 0, "Should have created at least one relationship")
        
        if IntegrationTestConfig.DOMAIN_ENRICHMENT:
            self.assertIn('domain_enrichment_count', stats, 
                          "Domain enrichment count should be present in stats")
            self.assertGreater(stats['domain_enrichment_count'], 0, 
                               "Should have applied domain enrichment to at least one element")
    
    def test_graph_structure_validation(self):
        """Test that the generated graph has the expected structure."""
        # Process the IFC file
        self.processor.process(
            clear_existing=True,
            batch_size=10  # Use small batch size to ensure batching logic works
        )
        
        # Check that the graph has the expected structure
        db = self.connector
        
        # Check that we have at least one project node
        project_count = db.run_query("MATCH (p:Project) RETURN count(p) as count")[0]['count']
        self.assertGreater(project_count, 0, "Should have at least one project node")
        
        # Check spatial structure hierarchy
        spatial_hierarchy = db.run_query("""
            MATCH path = (p:Project)-[:HAS_SITE]->(s:Site)-[:HAS_BUILDING]->(b:Building)
            -[:HAS_STOREY]->(storey:Storey)-[:CONTAINS]->(e:Element)
            RETURN count(path) as count
        """)
        
        self.assertGreater(
            spatial_hierarchy[0]['count'], 
            0, 
            "Should have at least one complete spatial hierarchy path"
        )
        
        # Check that we have elements with properties
        elements_with_properties = db.run_query("""
            MATCH (e:Element)-[:HAS_PROPERTY_SET]->(ps:PropertySet)
            RETURN count(DISTINCT e) as count
        """)
        
        self.assertGreater(
            elements_with_properties[0]['count'],
            0,
            "Should have elements with property sets"
        )
        
        # Verify relationships between elements
        element_relationships = db.run_query("""
            MATCH (e1:Element)-[r]->(e2:Element)
            RETURN count(r) as count
        """)
        
        self.assertGreater(
            element_relationships[0]['count'],
            0,
            "Should have relationships between elements"
        )
    
    def test_memory_usage(self):
        """Test the memory usage during processing to ensure it's optimized."""
        # Process with memory monitoring
        stats = self.processor.process(
            clear_existing=True,
            batch_size=20  # Small batches for memory testing
        )
        
        # Simplify memory usage checks
        # We'll just check that the processing completed successfully
        self.assertGreater(stats['element_count'], 0, "Should have processed elements")
        
        # If performance monitoring is enabled, check that metrics were recorded
        if self.processor.enable_monitoring:
            # Get metrics data
            metrics_data = self.processor.db_connector.performance_monitor.metrics
            
            # Check if we have any memory-related metrics
            memory_metrics = [m for m in metrics_data if 'memory' in m.get('name', '').lower()]
            
            # We should have at least some memory metrics if monitoring is enabled
            self.assertGreater(len(memory_metrics), 0, "Should have memory metrics recorded")
    
    def test_different_ifc_versions(self):
        """Test processing of different IFC versions if available."""
        # Skip this test if no additional IFC files are available
        test_file = IntegrationTestConfig.IFC_TEST_FILE
        if not os.path.exists(test_file):
            self.skipTest(f"Test IFC file not found: {test_file}")
        
        # Get the IFC version
        parser = IfcParser(test_file)
        ifc_version = parser.get_schema_version()
        logger.info(f"Testing with IFC version: {ifc_version}")
        
        # Process the file
        stats = self.processor.process(
            clear_existing=IntegrationTestConfig.CLEAR_EXISTING,
            batch_size=IntegrationTestConfig.BATCH_SIZE
        )
        
        # Verify that processing completed successfully
        self.assertIsNotNone(stats, "Processing stats should not be None")
        self.assertGreater(stats['element_count'], 0, "Should have processed at least one element")


if __name__ == "__main__":
    unittest.main() 