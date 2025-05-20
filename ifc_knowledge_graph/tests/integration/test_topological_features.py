#!/usr/bin/env python
"""
Topological Features Test Script

This script tests the topological analysis features of the IFC to Neo4j Knowledge Graph
pipeline, including conversion of IFC elements to topological entities, extraction of
relationships, and proper mapping to the Neo4j graph.
"""

import os
import sys
import logging
import time
from pathlib import Path
import tempfile
import urllib.request
from typing import Dict, List, Any, Optional, Tuple
import pytest
from datetime import datetime

# Setup logging with more detailed formatting
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for development, INFO for production
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Output to console
        logging.FileHandler('topological_test.log')  # Also log to file
    ]
)
logger = logging.getLogger(__name__)

# Add the package to the path
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

try:
    # Import required modules
    import ifcopenshell
    from src.ifc_to_graph.topology.topologic_analyzer import TopologicAnalyzer, TOPOLOGICPY_AVAILABLE
    from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector
    from src.ifc_to_graph.database.topologic_to_graph_mapper import TopologicToGraphMapper
    from src.ifc_to_graph.parser.ifc_parser import IfcParser
    from src.ifc_to_graph.processor import IfcProcessor
    
    # Test IFC files - Local file paths instead of URLs
    LOCAL_IFC_FILES = {
        "duplex": str(Path(__file__).parent / "data" / "ifc_files" / "Duplex_A_20110907.ifc")
    }

    class TopologicalFeaturesTester:
        """Test class for topological features of the IFC to Neo4j pipeline."""
        
        def __init__(self, neo4j_uri="bolt://localhost:7687", neo4j_username="neo4j", neo4j_password="test1234"):
            """
            Initialize the tester with Neo4j connection details.
            
            Args:
                neo4j_uri: URI for Neo4j connection
                neo4j_username: Neo4j username
                neo4j_password: Neo4j password
            """
            self.neo4j_uri = neo4j_uri
            self.neo4j_username = neo4j_username
            self.neo4j_password = neo4j_password
            
            self.ifc_model = None
            self.parser = None
            self.analyzer = None
            self.connector = None
            self.mapper = None
            
            # Verify IFC files exist
            for name, path in LOCAL_IFC_FILES.items():
                ifc_path = Path(path)
                if not ifc_path.exists():
                    logger.error(f"IFC file {path} not found. Please ensure the file exists.")
                    sys.exit(1)
                logger.info(f"Found IFC file: {path}")

        def download_test_files(self) -> Dict[str, Path]:
            """
            Use local files instead of downloading.
            
            Returns:
                Dictionary mapping file names to paths
            """
            return {name: Path(path) for name, path in LOCAL_IFC_FILES.items()}
            
        def setup_neo4j_connection(self) -> bool:
            """
            Set up the Neo4j connection for the tests.
            
            Returns:
                True if successful, False otherwise
            """
            try:
                logger.info(f"Connecting to Neo4j at {self.neo4j_uri}")
                self.connector = Neo4jConnector(
                    uri=self.neo4j_uri,
                    username=self.neo4j_username,
                    password=self.neo4j_password
                )
                
                # Test connection
                logger.info("Testing Neo4j connection...")
                test_result = self.connector.test_connection()
                if test_result:
                    logger.info("Neo4j connection successful")
                else:
                    logger.error("Neo4j connection failed")
                    return False
                    
                return True
            except Exception as e:
                logger.error(f"Error setting up Neo4j connection: {str(e)}")
                return False
        
        def setup_test_environment(self, ifc_file: Path) -> bool:
            """
            Set up the test environment with an IFC file.
            
            Args:
                ifc_file: Path to the IFC file to use
                
            Returns:
                True if successful, False otherwise
            """
            try:
                logger.info(f"Setting up test environment with {ifc_file}")
                
                # Convert Path to string
                ifc_file_str = str(ifc_file)
                
                # Create parser with file path string
                self.parser = IfcParser(ifc_file_str)
                logger.debug(f"Created IfcParser: {type(self.parser).__name__}")
                
                # Get the loaded IFC model from the parser
                self.ifc_model = self.parser.file
                logger.debug(f"Loaded IFC model: {type(self.ifc_model).__name__}")
                
                # Create analyzer
                self.analyzer = TopologicAnalyzer(self.parser)
                logger.debug(f"Created TopologicAnalyzer: {type(self.analyzer).__name__}")
                
                # Set up the mapper
                if self.connector:
                    self.mapper = TopologicToGraphMapper(self.connector)
                    logger.debug(f"Created TopologicToGraphMapper: {type(self.mapper).__name__}")
                    
                return True
            except Exception as e:
                logger.error(f"Error setting up test environment: {str(e)}")
                return False
        
        def test_ifc_to_topologic_conversion(self) -> Dict[str, Any]:
            """
            Test conversion of IFC elements to TopologicPy entities.
            
            Returns:
                Dictionary with test results
            """
            logger.info("Testing IFC to TopologicPy conversion...")
            
            results = {
                "success": True,
                "converted_elements": 0,
                "conversion_errors": 0,
                "element_types": {}
            }
            
            try:
                # Get all elements from the IFC model
                all_elements = self.parser.get_elements()  # Use get_elements() instead of get_all_building_elements()
                logger.info(f"Found {len(all_elements)} elements to convert")
                
                # Try to convert each element
                for element in all_elements:
                    element_type = element.is_a()
                    
                    # Track element types
                    if element_type not in results["element_types"]:
                        results["element_types"][element_type] = {
                            "total": 0,
                            "converted": 0,
                            "failed": 0
                        }
                    
                    results["element_types"][element_type]["total"] += 1
                    
                    # Try to convert
                    start_time = time.time()
                    topologic_entity = self.analyzer.convert_ifc_to_topologic(element)
                    conversion_time = time.time() - start_time
                    
                    if topologic_entity:
                        results["converted_elements"] += 1
                        results["element_types"][element_type]["converted"] += 1
                        logger.debug(f"Converted {element_type} {element.GlobalId} in {conversion_time:.4f}s")
                    else:
                        results["conversion_errors"] += 1
                        results["element_types"][element_type]["failed"] += 1
                        logger.warning(f"Failed to convert {element_type} {element.GlobalId}")
                
                # Calculate success percentage
                total_elements = len(all_elements)
                if total_elements > 0:
                    conversion_rate = (results["converted_elements"] / total_elements) * 100
                    results["conversion_rate"] = conversion_rate
                    
                    # Overall success criteria: at least 60% conversion rate
                    results["success"] = conversion_rate >= 60
                    
                    logger.info(f"Converted {results['converted_elements']} of {total_elements} elements ({conversion_rate:.2f}%)")
                    
                    # Log element type statistics
                    for element_type, stats in results["element_types"].items():
                        if stats["total"] > 0:
                            convert_rate = (stats["converted"] / stats["total"]) * 100
                            logger.info(f"{element_type}: Converted {stats['converted']} of {stats['total']} ({convert_rate:.2f}%)")
                else:
                    results["success"] = False
                    logger.error("No elements found in the IFC model")
                    
            except Exception as e:
                results["success"] = False
                logger.error(f"Error in IFC to TopologicPy conversion test: {str(e)}")
                    
            return results
                
        def test_adjacency_relationships(self) -> Dict[str, Any]:
            """
            Test extraction of adjacency relationships.
            
            Returns:
                Dictionary with test results
            """
            logger.info("Testing adjacency relationship extraction...")
            
            results = {
                "success": True,
                "total_relationships": 0,
                "extraction_time": 0
            }
            
            try:
                # Extract adjacency relationships
                start_time = time.time()
                adjacency = self.analyzer.get_adjacency_relationships()
                results["extraction_time"] = time.time() - start_time
                
                # Count relationships
                for element_id, adjacent_ids in adjacency.items():
                    results["total_relationships"] += len(adjacent_ids)
                
                logger.info(f"Found {results['total_relationships']} adjacency relationships")
                logger.info(f"Extraction time: {results['extraction_time']:.4f}s")
                
                # Success criteria: should find at least some relationships
                results["success"] = results["total_relationships"] > 0
                
            except Exception as e:
                results["success"] = False
                logger.error(f"Error in adjacency relationship test: {str(e)}")
                
            return results
                
        def test_containment_relationships(self) -> Dict[str, Any]:
            """
            Test extraction of containment relationships.
            
            Returns:
                Dictionary with test results
            """
            logger.info("Testing containment relationship extraction...")
            
            results = {
                "success": True,
                "total_relationships": 0,
                "extraction_time": 0
            }
            
            try:
                # Extract containment relationships
                start_time = time.time()
                containment = self.analyzer.get_containment_relationships()
                results["extraction_time"] = time.time() - start_time
                
                # Count relationships
                for container_id, contained_ids in containment.items():
                    results["total_relationships"] += len(contained_ids)
                    
                logger.info(f"Found {results['total_relationships']} containment relationships")
                logger.info(f"Extraction time: {results['extraction_time']:.4f}s")
                
                # Success criteria: should find at least some relationships
                results["success"] = results["total_relationships"] > 0
                
            except Exception as e:
                results["success"] = False
                logger.error(f"Error in containment relationship test: {str(e)}")
                
            return results
                
        def test_space_boundaries(self) -> Dict[str, Any]:
            """
            Test extraction of space boundaries.
            
            Returns:
                Dictionary with test results
            """
            logger.info("Testing space boundary extraction...")
            
            results = {
                "success": True,
                "total_relationships": 0,
                "extraction_time": 0
            }
            
            try:
                # Extract space boundaries
                start_time = time.time()
                boundaries = self.analyzer.get_space_boundaries()
                results["extraction_time"] = time.time() - start_time
                
                # Count relationships
                for space_id, boundary_ids in boundaries.items():
                    results["total_relationships"] += len(boundary_ids)
                    
                logger.info(f"Found {results['total_relationships']} space boundary relationships")
                logger.info(f"Extraction time: {results['extraction_time']:.4f}s")
                
                # Success criteria: should find at least some relationships
                results["success"] = results["total_relationships"] > 0
                
            except Exception as e:
                results["success"] = False
                logger.error(f"Error in space boundary test: {str(e)}")
                
            return results
                
        def test_connectivity_graph(self) -> Dict[str, Any]:
            """
            Test generation of the connectivity graph.
            
            Returns:
                Dictionary with test results
            """
            logger.info("Testing connectivity graph generation...")
            
            results = {
                "success": True,
                "nodes": 0,
                "edges": 0,
                "generation_time": 0
            }
            
            try:
                # Generate connectivity graph
                start_time = time.time()
                graph = self.analyzer.get_connectivity_graph()
                results["generation_time"] = time.time() - start_time
                
                # Count nodes and edges in the dictionary structure
                if isinstance(graph, dict):
                    if "nodes" in graph:
                        results["nodes"] = len(graph["nodes"])
                    if "edges" in graph:
                        results["edges"] = len(graph["edges"])
                else:
                    # For backward compatibility with graph objects
                    try:
                        results["nodes"] = len(graph.nodes)
                        results["edges"] = len(graph.edges)
                    except AttributeError:
                        logger.error("Unsupported graph structure returned by get_connectivity_graph()")
                
                logger.info(f"Generated connectivity graph with {results['nodes']} nodes and {results['edges']} edges")
                logger.info(f"Generation time: {results['generation_time']:.4f}s")
                
                # Success criteria: should have nodes and edges
                results["success"] = results["nodes"] > 0 and results["edges"] > 0
                
            except Exception as e:
                results["success"] = False
                logger.error(f"Error in connectivity graph test: {str(e)}")
                
            return results
                
        def test_path_finding(self) -> Dict[str, Any]:
            """
            Test path finding between elements.
            
            Returns:
                Dictionary with test results
            """
            logger.info("Testing path finding...")
            
            results = {
                "success": True,
                "paths_found": 0,
                "path_lengths": [],
                "path_finding_time": 0
            }
            
            try:
                # Get some elements from the model for path finding
                spaces = self.parser.get_elements("IfcSpace")
                walls = self.parser.get_elements("IfcWall")
                
                if not spaces or not walls:
                    logger.warning("Not enough elements for path finding test")
                    results["success"] = False
                    return results
                
                # Try to find paths between elements
                start_time = time.time()
                
                # Try up to 5 space-wall combinations
                test_cases = 0
                max_test_cases = 5
                
                for space in spaces[:max_test_cases]:
                    for wall in walls[:max_test_cases]:
                        test_cases += 1
                        if test_cases > max_test_cases:
                            break
                            
                        # Find path between space and wall
                        path = self.analyzer.find_path(space.GlobalId, wall.GlobalId)
                        
                        if path:
                            results["paths_found"] += 1
                            results["path_lengths"].append(len(path))
                            logger.debug(f"Found path from {space.GlobalId} to {wall.GlobalId} with length {len(path)}")
                        else:
                            logger.debug(f"No path found from {space.GlobalId} to {wall.GlobalId}")
                
                results["path_finding_time"] = time.time() - start_time
                
                # Calculate average path length
                if results["paths_found"] > 0:
                    results["avg_path_length"] = sum(results["path_lengths"]) / results["paths_found"]
                    
                logger.info(f"Found {results['paths_found']} paths with average length {results.get('avg_path_length', 0):.2f}")
                logger.info(f"Path finding time: {results['path_finding_time']:.4f}s")
                
                # Success criteria: should find at least some paths
                results["success"] = results["paths_found"] > 0
                
            except Exception as e:
                results["success"] = False
                logger.error(f"Error in path finding test: {str(e)}")
                
            return results
                
        def test_topologic_to_graph_import(self) -> Dict[str, Any]:
            """
            Test importing topological relationships to Neo4j.
            
            Returns:
                Dictionary with test results
            """
            logger.info("Testing topological relationships import to Neo4j...")
            
            results = {
                "success": True,
                "adjacency_relationships": 0,
                "containment_relationships": 0,
                "space_boundary_relationships": 0,
                "import_time": 0
            }
            
            try:
                # Check if we have the mapper
                if not self.mapper:
                    logger.warning("No mapper available for Neo4j import test")
                    results["success"] = False
                    return results
                
                # Start import
                start_time = time.time()
                
                # Extract relationships
                adjacency = self.analyzer.get_adjacency_relationships()
                containment = self.analyzer.get_containment_relationships()
                space_boundaries = self.analyzer.get_space_boundaries()
                
                # Import to Neo4j
                # First clear existing relationships
                self.mapper.clear_topological_relationships()
                
                # Import adjacency relationships
                adjacency_count = self.mapper.import_adjacency_relationships(adjacency)
                results["adjacency_relationships"] = adjacency_count
                
                # Import containment relationships
                containment_count = self.mapper.import_containment_relationships(containment)
                results["containment_relationships"] = containment_count
                
                # Import space boundary relationships
                space_boundary_count = self.mapper.import_space_boundary_relationships(space_boundaries)
                results["space_boundary_relationships"] = space_boundary_count
                
                results["import_time"] = time.time() - start_time
                
                # Calculate total relationships
                total_relationships = (
                    results["adjacency_relationships"] +
                    results["containment_relationships"] +
                    results["space_boundary_relationships"]
                )
                
                logger.info(f"Imported {total_relationships} topological relationships to Neo4j")
                logger.info(f"Import time: {results['import_time']:.4f}s")
                
                # Success criteria: should import at least some relationships
                results["success"] = total_relationships > 0
                
            except Exception as e:
                results["success"] = False
                logger.error(f"Error in Neo4j import test: {str(e)}")
                
            return results
                
        def run_all_tests(self, ifc_file_name) -> Dict[str, Any]:
            """
            Run all topological feature tests.
            
            Args:
                ifc_file_name: Name of the IFC file to use
                
            Returns:
                Dictionary with test results
            """
            overall_results = {
                "success": True,
                "tests": {},
                "start_time": time.time()
            }
            
            try:
                # Get test files
                test_files = self.download_test_files()
                
                if ifc_file_name not in test_files:
                    logger.error(f"Test file '{ifc_file_name}' not found. Available files: {list(test_files.keys())}")
                    return {"success": False, "reason": "Test file not found"}
                
                # Setup Neo4j connection
                neo4j_success = self.setup_neo4j_connection()
                overall_results["tests"]["neo4j_connection"] = {"success": neo4j_success}
                
                if not neo4j_success:
                    overall_results["success"] = False
                    return overall_results
                
                # Setup test environment with the specified IFC file
                ifc_file = test_files[ifc_file_name]
                env_success = self.setup_test_environment(ifc_file)
                overall_results["tests"]["environment_setup"] = {"success": env_success}
                
                if not env_success:
                    overall_results["success"] = False
                    return overall_results
                
                # Run tests
                # IFC to TopologicPy conversion
                conversion_results = self.test_ifc_to_topologic_conversion()
                overall_results["tests"]["ifc_to_topologic_conversion"] = conversion_results
                
                # If conversion fails completely, skip remaining tests
                if conversion_results["converted_elements"] == 0:
                    logger.error("IFC to TopologicPy conversion failed completely, skipping remaining tests")
                    overall_results["success"] = False
                    overall_results["completed_time"] = time.time() - overall_results["start_time"]
                    return overall_results
                
                # Relationship extraction tests
                adjacency_results = self.test_adjacency_relationships()
                overall_results["tests"]["adjacency_relationships"] = adjacency_results
                
                containment_results = self.test_containment_relationships()
                overall_results["tests"]["containment_relationships"] = containment_results
                
                space_boundary_results = self.test_space_boundaries()
                overall_results["tests"]["space_boundaries"] = space_boundary_results
                
                # Graph generation and path finding
                graph_results = self.test_connectivity_graph()
                overall_results["tests"]["connectivity_graph"] = graph_results
                
                path_finding_results = self.test_path_finding()
                overall_results["tests"]["path_finding"] = path_finding_results
                
                # Neo4j import
                import_results = self.test_topologic_to_graph_import()
                overall_results["tests"]["neo4j_import"] = import_results
                
                # Check overall success
                for test_name, test_results in overall_results["tests"].items():
                    if not test_results.get("success", True):
                        overall_results["success"] = False
                        logger.warning(f"Test '{test_name}' failed")
                
                # Record total time
                overall_results["completed_time"] = time.time() - overall_results["start_time"]
                
                return overall_results
                
            except Exception as e:
                logger.error(f"Error running tests: {str(e)}")
                overall_results["success"] = False
                overall_results["error"] = str(e)
                return overall_results
    
    def print_results(results):
        """
        Print test results in a readable format.
        
        Args:
            results: Dictionary with test results
        """
        print("\n" + "="*80)
        print("TOPOLOGICAL FEATURES TEST RESULTS")
        print("="*80)
        
        if "completed_time" in results:
            print(f"Total test time: {results['completed_time']:.2f}s")
            
        print(f"Overall success: {'Yes' if results['success'] else 'No'}")
        print("-"*80)
        
        if "tests" in results:
            for test_name, test_results in results["tests"].items():
                success = test_results.get("success", False)
                print(f"{test_name}: {'✓' if success else '✗'}")
                
                # Print details based on test type
                if test_name == "ifc_to_topologic_conversion" and "converted_elements" in test_results:
                    print(f"  Converted {test_results['converted_elements']} elements")
                    if "conversion_rate" in test_results:
                        print(f"  Conversion rate: {test_results['conversion_rate']:.2f}%")
                    
                elif "total_relationships" in test_results:
                    print(f"  Found {test_results['total_relationships']} relationships")
                    if "extraction_time" in test_results:
                        print(f"  Extraction time: {test_results['extraction_time']:.4f}s")
                    
                elif test_name == "connectivity_graph" and "nodes" in test_results:
                    print(f"  Nodes: {test_results['nodes']}, Edges: {test_results['edges']}")
                    if "generation_time" in test_results:
                        print(f"  Generation time: {test_results['generation_time']:.4f}s")
                    
                elif test_name == "path_finding" and "paths_found" in test_results:
                    print(f"  Paths found: {test_results['paths_found']}")
                    if "avg_path_length" in test_results:
                        print(f"  Average path length: {test_results['avg_path_length']:.2f}")
                    
                elif test_name == "neo4j_import":
                    adjacency = test_results.get("adjacency_relationships", 0)
                    containment = test_results.get("containment_relationships", 0)
                    space_boundary = test_results.get("space_boundary_relationships", 0)
                    total = adjacency + containment + space_boundary
                    print(f"  Imported {total} relationships (A: {adjacency}, C: {containment}, SB: {space_boundary})")
                    
        print("="*80)
    
    def main():
        """Main entry point for testing topological features."""
        
        # Create tester
        tester = TopologicalFeaturesTester()
        
        # Set default test file
        test_file = "duplex"
        
        # Allow override from command line
        if len(sys.argv) > 1:
            test_file = sys.argv[1]
        
        # Run all tests
        results = tester.run_all_tests(test_file)
        
        # Print results
        print_results(results)
        
        # Return exit code based on success
        return 0 if results["success"] else 1
    
    if __name__ == "__main__":
        sys.exit(main())
    
except ImportError as e:
    logging.error(f"Import error: {str(e)}")
    print(f"ERROR: Required module not found - {str(e)}")
    sys.exit(1)
except Exception as e:
    logging.error(f"Unexpected error: {str(e)}")
    print(f"ERROR: {str(e)}")
    sys.exit(1)

# Test Topological Features

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test IFC file path
TEST_IFC_PATH = os.path.join("tests", "fixtures", "small_office.ifc")

# Neo4j connection details (use environment variables or defaults)
NEO4J_URI = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
NEO4J_USERNAME = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")


@pytest.mark.skipif(not TOPOLOGICPY_AVAILABLE, reason="TopologicPy not available")
@pytest.mark.integration
def test_topologic_analyzer_initialization():
    """Test if the TopologicAnalyzer can be initialized."""
    parser = IfcParser(TEST_IFC_PATH)
    analyzer = TopologicAnalyzer(parser)
    assert analyzer is not None
    assert analyzer._has_topologicpy == TOPOLOGICPY_AVAILABLE


@pytest.mark.skipif(not TOPOLOGICPY_AVAILABLE, reason="TopologicPy not available")
@pytest.mark.integration
def test_analyze_building_topology():
    """Test analyzing building topology using TopologicPy."""
    parser = IfcParser(TEST_IFC_PATH)
    analyzer = TopologicAnalyzer(parser)
    
    # Analyze topology
    results = analyzer.analyze_building_topology()
    
    # Verify results contains expected keys
    assert "adjacency" in results
    assert "containment" in results
    assert "space_boundaries" in results
    assert "connectivity" in results
    
    # Verify at least some relationships were found
    assert any(results.values()), "No topological relationships were extracted"


@pytest.mark.skipif(not TOPOLOGICPY_AVAILABLE, reason="TopologicPy not available")
@pytest.mark.integration
def test_processor_with_topological_analysis_enabled():
    """Test that the IfcProcessor creates topological relationships when enabled."""
    # Create a unique database name to avoid conflicts with other tests
    test_db_name = f"topology_test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    try:
        # Initialize processor with topological analysis enabled
        processor = IfcProcessor(
            ifc_file_path=TEST_IFC_PATH,
            neo4j_uri=NEO4J_URI,
            neo4j_username=NEO4J_USERNAME,
            neo4j_password=NEO4J_PASSWORD,
            neo4j_database=test_db_name,
            enable_topological_analysis=True
        )
        
        # Process the IFC file
        stats = processor.process(clear_existing=True)
        
        # Verify topological relationships were created
        assert stats.get("topological_relationship_count", 0) > 0, "No topological relationships were created"
        
        # Query the database to count topological relationship types
        connector = Neo4jConnector(
            uri=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD,
            database=test_db_name
        )
        
        # Count relationship types
        query = """
        MATCH ()-[r]->() 
        WHERE r.relationshipSource = 'topologicalAnalysis'
        RETURN type(r) as relType, count(r) as count
        """
        results = connector.run_query(query)
        
        # Verify topological relationships exist
        assert results, "No topological relationships found in the database"
        
        # Verify at least one relationship of each expected type exists
        rel_types = [result["relType"] for result in results]
        expected_types = ["ADJACENT", "CONTAINS_TOPOLOGICALLY", "BOUNDED_BY"]
        
        for expected in expected_types:
            assert any(expected in rel_type for rel_type in rel_types), f"No {expected} relationships found"
        
        # Clean up
        processor.close()
    finally:
        # Clean up - drop the test database
        cleanup_connector = Neo4jConnector(
            uri=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD
        )
        try:
            # Drop the database if it exists
            cleanup_connector.run_query(f"DROP DATABASE {test_db_name} IF EXISTS")
        except Exception as e:
            logger.warning(f"Failed to drop test database: {str(e)}")
        finally:
            cleanup_connector.close()


@pytest.mark.skipif(not TOPOLOGICPY_AVAILABLE, reason="TopologicPy not available")
@pytest.mark.integration
def test_processor_with_topological_analysis_disabled():
    """Test that the IfcProcessor does not create topological relationships when disabled."""
    # Create a unique database name to avoid conflicts with other tests
    test_db_name = f"no_topology_test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    try:
        # Initialize processor with topological analysis disabled
        processor = IfcProcessor(
            ifc_file_path=TEST_IFC_PATH,
            neo4j_uri=NEO4J_URI,
            neo4j_username=NEO4J_USERNAME,
            neo4j_password=NEO4J_PASSWORD,
            neo4j_database=test_db_name,
            enable_topological_analysis=False
        )
        
        # Process the IFC file
        stats = processor.process(clear_existing=True)
        
        # Verify no topological relationships were created
        assert "topological_relationship_count" not in stats or stats["topological_relationship_count"] == 0
        
        # Query the database to check for topological relationships
        connector = Neo4jConnector(
            uri=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD,
            database=test_db_name
        )
        
        # Count topological relationships
        query = """
        MATCH ()-[r]->() 
        WHERE r.relationshipSource = 'topologicalAnalysis'
        RETURN count(r) as count
        """
        results = connector.run_query(query)
        
        # Verify no topological relationships exist
        assert results[0]["count"] == 0, "Topological relationships found despite being disabled"
        
        # Clean up
        processor.close()
    finally:
        # Clean up - drop the test database
        cleanup_connector = Neo4jConnector(
            uri=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD
        )
        try:
            # Drop the database if it exists
            cleanup_connector.run_query(f"DROP DATABASE {test_db_name} IF EXISTS")
        except Exception as e:
            logger.warning(f"Failed to drop test database: {str(e)}")
        finally:
            cleanup_connector.close()


@pytest.mark.skipif(not TOPOLOGICPY_AVAILABLE, reason="TopologicPy not available")
@pytest.mark.integration
def test_topological_relationship_properties():
    """Test that the topological relationships have the expected properties."""
    # Create a unique database name to avoid conflicts with other tests
    test_db_name = f"topo_props_test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    try:
        # Initialize processor with topological analysis enabled
        processor = IfcProcessor(
            ifc_file_path=TEST_IFC_PATH,
            neo4j_uri=NEO4J_URI,
            neo4j_username=NEO4J_USERNAME,
            neo4j_password=NEO4J_PASSWORD,
            neo4j_database=test_db_name,
            enable_topological_analysis=True
        )
        
        # Process the IFC file
        processor.process(clear_existing=True)
        
        # Query the database to check relationship properties
        connector = Neo4jConnector(
            uri=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD,
            database=test_db_name
        )
        
        # Check properties of adjacency relationships
        query = """
        MATCH ()-[r:ADJACENT]->()
        RETURN r.relationshipSource, r.relationshipType, r.distanceTolerance
        LIMIT 1
        """
        results = connector.run_query(query)
        
        if results:
            # Verify properties exist
            assert results[0]["r.relationshipSource"] == "topologicalAnalysis"
            assert results[0]["r.relationshipType"] == "adjacency"
            assert results[0]["r.distanceTolerance"] is not None
        
        # Clean up
        processor.close()
    finally:
        # Clean up - drop the test database
        cleanup_connector = Neo4jConnector(
            uri=NEO4J_URI,
            username=NEO4J_USERNAME,
            password=NEO4J_PASSWORD
        )
        try:
            # Drop the database if it exists
            cleanup_connector.run_query(f"DROP DATABASE {test_db_name} IF EXISTS")
        except Exception as e:
            logger.warning(f"Failed to drop test database: {str(e)}")
        finally:
            cleanup_connector.close() 