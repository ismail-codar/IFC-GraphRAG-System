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

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the package to the path
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

try:
    # Import required modules
    import ifcopenshell
    from src.ifc_to_graph.topology.topologic_analyzer import TopologicAnalyzer
    from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector
    from src.ifc_to_graph.database.topologic_to_graph_mapper import TopologicToGraphMapper
    from src.ifc_to_graph.ifc_parser import IFCParser
    
    # Test IFC files - URLs to sample IFC files
    SAMPLE_IFC_URLS = {
        "simple_building": "https://raw.githubusercontent.com/buildingSMART/Sample-Test-Files/master/IFC%204.3/SpatialStructure/Grid-Placement-1/Grid-Placement-1.ifc",
        "duplex": "https://raw.githubusercontent.com/buildingSMART/Sample-Test-Files/master/IFC%202x3/Duplex%20Apartment/Duplex_A_20110907.ifc",
        "office": "https://raw.githubusercontent.com/buildingSMART/Sample-Test-Files/master/IFC%204.0/Schependomlaan/Schependomlaan.ifc"
    }

    class TopologicalFeaturesTester:
        """Test class for topological features of the IFC to Neo4j pipeline."""
        
        def __init__(self, neo4j_uri="bolt://localhost:7687", neo4j_user="neo4j", neo4j_password="test1234"):
            """
            Initialize the tester with Neo4j connection details.
            
            Args:
                neo4j_uri: URI for Neo4j connection
                neo4j_user: Neo4j username
                neo4j_password: Neo4j password
            """
            self.neo4j_uri = neo4j_uri
            self.neo4j_user = neo4j_user
            self.neo4j_password = neo4j_password
            
            self.test_files = {}
            self.connector = None
            self.ifc_model = None
            self.parser = None
            self.analyzer = None
            self.mapper = None
            
            # Create temporary directory for test files
            self.temp_dir = Path(tempfile.gettempdir()) / "ifc_topo_test"
            self.temp_dir.mkdir(exist_ok=True)
            
        def download_test_files(self) -> Dict[str, Path]:
            """
            Download test IFC files for the tests.
            
            Returns:
                Dictionary of file names and their paths
            """
            logger.info("Downloading test IFC files...")
            
            for name, url in SAMPLE_IFC_URLS.items():
                file_path = self.temp_dir / f"{name}.ifc"
                
                if not file_path.exists():
                    logger.info(f"Downloading {name} from {url}")
                    try:
                        urllib.request.urlretrieve(url, file_path)
                        logger.info(f"Downloaded {name} to {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to download {name}: {str(e)}")
                        continue
                
                self.test_files[name] = file_path
            
            return self.test_files
            
        def setup_neo4j_connection(self) -> bool:
            """
            Set up the Neo4j connection for the tests.
            
            Returns:
                True if successful, False otherwise
            """
            try:
                logger.info("Setting up Neo4j connection...")
                self.connector = Neo4jConnector(
                    uri=self.neo4j_uri,
                    user=self.neo4j_user,
                    password=self.neo4j_password
                )
                
                # Test connection
                result = self.connector.run_query("RETURN 1 AS test")
                
                if result and result[0]["test"] == 1:
                    logger.info("Neo4j connection successful")
                    return True
                else:
                    logger.error("Neo4j connection failed")
                    return False
                    
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
                
                # Load IFC model
                self.ifc_model = ifcopenshell.open(str(ifc_file))
                
                # Create parser
                self.parser = IFCParser(self.ifc_model)
                
                # Create analyzer
                self.analyzer = TopologicAnalyzer(self.parser)
                
                # Create mapper
                self.mapper = TopologicToGraphMapper(self.connector)
                
                logger.info("Test environment setup successful")
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
                all_elements = self.parser.get_all_building_elements()
                
                # Try to convert each element
                for element in all_elements:
                    element_type = element.is_a()
                    
                    if element_type not in results["element_types"]:
                        results["element_types"][element_type] = {
                            "total": 0,
                            "successful": 0,
                            "failed": 0
                        }
                    
                    results["element_types"][element_type]["total"] += 1
                    
                    # Convert to topologic
                    start_time = time.time()
                    topologic_entity = self.analyzer.convert_ifc_to_topologic(element)
                    end_time = time.time()
                    
                    if topologic_entity:
                        results["converted_elements"] += 1
                        results["element_types"][element_type]["successful"] += 1
                    else:
                        results["conversion_errors"] += 1
                        results["element_types"][element_type]["failed"] += 1
                
                if results["conversion_errors"] > 0:
                    results["success"] = False
                    
                return results
                
            except Exception as e:
                logger.error(f"Error in IFC to TopologicPy conversion test: {str(e)}")
                results["success"] = False
                return results
        
        def test_adjacency_extraction(self) -> Dict[str, Any]:
            """
            Test extraction of adjacency relationships.
            
            Returns:
                Dictionary with test results
            """
            logger.info("Testing adjacency relationship extraction...")
            
            results = {
                "success": True,
                "adjacency_count": 0,
                "extraction_time": 0
            }
            
            try:
                # Start timing
                start_time = time.time()
                
                # Extract adjacency relationships
                adjacency_map = self.analyzer.get_adjacency_relationships()
                
                # End timing
                end_time = time.time()
                
                # Count adjacency relationships
                total_adjacencies = sum(len(adjacent_ids) for adjacent_ids in adjacency_map.values())
                
                results["adjacency_count"] = total_adjacencies
                results["extraction_time"] = end_time - start_time
                
                return results
                
            except Exception as e:
                logger.error(f"Error in adjacency extraction test: {str(e)}")
                results["success"] = False
                return results
        
        def test_containment_extraction(self) -> Dict[str, Any]:
            """
            Test extraction of containment relationships.
            
            Returns:
                Dictionary with test results
            """
            logger.info("Testing containment relationship extraction...")
            
            results = {
                "success": True,
                "containment_count": 0,
                "extraction_time": 0
            }
            
            try:
                # Start timing
                start_time = time.time()
                
                # Extract containment relationships
                containment_map = self.analyzer.get_containment_relationships()
                
                # End timing
                end_time = time.time()
                
                # Count containment relationships
                total_containments = sum(len(contained_ids) for contained_ids in containment_map.values())
                
                results["containment_count"] = total_containments
                results["extraction_time"] = end_time - start_time
                
                return results
                
            except Exception as e:
                logger.error(f"Error in containment extraction test: {str(e)}")
                results["success"] = False
                return results
        
        def test_space_boundaries_extraction(self) -> Dict[str, Any]:
            """
            Test extraction of space boundary relationships.
            
            Returns:
                Dictionary with test results
            """
            logger.info("Testing space boundary extraction...")
            
            results = {
                "success": True,
                "space_boundary_count": 0,
                "extraction_time": 0
            }
            
            try:
                # Start timing
                start_time = time.time()
                
                # Extract space boundaries
                space_boundaries = self.analyzer.get_space_boundaries()
                
                # End timing
                end_time = time.time()
                
                # Count space boundaries
                total_boundaries = sum(len(boundary_ids) for boundary_ids in space_boundaries.values())
                
                results["space_boundary_count"] = total_boundaries
                results["extraction_time"] = end_time - start_time
                
                return results
                
            except Exception as e:
                logger.error(f"Error in space boundary extraction test: {str(e)}")
                results["success"] = False
                return results
            
        def test_connectivity_graph_generation(self) -> Dict[str, Any]:
            """
            Test generation of the connectivity graph.
            
            Returns:
                Dictionary with test results
            """
            logger.info("Testing connectivity graph generation...")
            
            results = {
                "success": True,
                "connectivity_count": 0,
                "relationship_types": {},
                "generation_time": 0
            }
            
            try:
                # Start timing
                start_time = time.time()
                
                # Generate connectivity graph
                connectivity_graph = self.analyzer.get_connectivity_graph()
                
                # End timing
                end_time = time.time()
                
                # Count connectivity relationships
                total_connections = 0
                relationship_types = {}
                
                for element_id, connections in connectivity_graph.items():
                    for rel_type, rel_connections in connections.items():
                        if rel_type not in relationship_types:
                            relationship_types[rel_type] = 0
                        
                        relationship_types[rel_type] += len(rel_connections)
                        total_connections += len(rel_connections)
                
                results["connectivity_count"] = total_connections
                results["relationship_types"] = relationship_types
                results["generation_time"] = end_time - start_time
                
                return results
                
            except Exception as e:
                logger.error(f"Error in connectivity graph generation test: {str(e)}")
                results["success"] = False
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
                spaces = self.parser.get_by_type("IfcSpace")
                walls = self.parser.get_by_type("IfcWall")
                
                if not spaces or not walls:
                    logger.warning("Not enough elements for path finding test")
                    results["success"] = False
                    return results
                
                # Try to find paths between various elements
                num_tests = min(5, len(spaces) * len(walls))
                test_count = 0
                
                total_time = 0
                paths_found = 0
                
                for space in spaces[:2]:  # Limit to first 2 spaces
                    for wall in walls[:3]:  # Limit to first 3 walls
                        if test_count >= num_tests:
                            break
                            
                        start_id = space.GlobalId
                        end_id = wall.GlobalId
                        
                        # Start timing
                        start_time = time.time()
                        
                        # Find path
                        path = self.analyzer.find_path(start_id, end_id)
                        
                        # End timing
                        end_time = time.time()
                        
                        total_time += (end_time - start_time)
                        test_count += 1
                        
                        if path:
                            paths_found += 1
                            results["path_lengths"].append(len(path))
                
                results["paths_found"] = paths_found
                results["path_finding_time"] = total_time
                
                return results
                
            except Exception as e:
                logger.error(f"Error in path finding test: {str(e)}")
                results["success"] = False
                return results
        
        def test_database_mapping(self) -> Dict[str, Any]:
            """
            Test mapping of topological relationships to the Neo4j database.
            
            Returns:
                Dictionary with test results
            """
            logger.info("Testing database mapping of topological relationships...")
            
            results = {
                "success": True,
                "total_relationships_created": 0,
                "relationship_types": {},
                "mapping_time": 0
            }
            
            try:
                # Make sure we have a valid Neo4j connection
                if not self.connector:
                    results["success"] = False
                    results["error"] = "Neo4j connector not initialized"
                    return results
                
                # Clear existing data for clean test
                self.connector.run_query("MATCH ()-[r]->() WHERE r.relationshipSource = 'topologicalAnalysis' DELETE r")
                
                # Analyze the building topology
                topology_results = self.analyzer.analyze_building_topology()
                
                # Start timing
                start_time = time.time()
                
                # Map results to Neo4j
                mapping_results = self.mapper.import_all_topological_relationships(topology_results)
                
                # End timing
                end_time = time.time()
                
                # Record results
                results["total_relationships_created"] = sum(mapping_results.values())
                results["relationship_types"] = mapping_results
                results["mapping_time"] = end_time - start_time
                
                return results
                
            except Exception as e:
                logger.error(f"Error in database mapping test: {str(e)}")
                results["success"] = False
                results["error"] = str(e)
                return results
                
        def test_topological_query(self) -> Dict[str, Any]:
            """
            Test running a topological query in Neo4j.
            
            Returns:
                Dictionary with test results
            """
            logger.info("Testing topological query execution...")
            
            results = {
                "success": True,
                "query_results": [],
                "query_time": 0
            }
            
            try:
                # Define a query to find adjacent elements
                query = """
                MATCH (a)-[r:ADJACENT]->(b)
                WHERE r.relationshipSource = 'topologicalAnalysis'
                RETURN a.GlobalId AS source, b.GlobalId AS target, r
                LIMIT 10
                """
                
                # Start timing
                start_time = time.time()
                
                # Execute query
                query_results = self.connector.run_query(query)
                
                # End timing
                end_time = time.time()
                
                # Record results
                results["query_results"] = [dict(record) for record in query_results]
                results["query_time"] = end_time - start_time
                
                return results
                
            except Exception as e:
                logger.error(f"Error in topological query test: {str(e)}")
                results["success"] = False
                results["error"] = str(e)
                return results
                
        def run_all_tests(self, ifc_file_name: str = "duplex") -> Dict[str, Any]:
            """
            Run all tests on a specified IFC file.
            
            Args:
                ifc_file_name: Name of the IFC file to test
                
            Returns:
                Dictionary with all test results
            """
            logger.info(f"Running all tests on {ifc_file_name}...")
            
            all_results = {
                "file_name": ifc_file_name,
                "success": True,
                "test_results": {},
                "total_time": 0
            }
            
            # Download test files if not already available
            if not self.test_files:
                self.download_test_files()
            
            if ifc_file_name not in self.test_files:
                logger.error(f"Test file {ifc_file_name} not available")
                all_results["success"] = False
                return all_results
            
            # Set up Neo4j connection
            if not self.setup_neo4j_connection():
                logger.error("Failed to set up Neo4j connection")
                all_results["success"] = False
                return all_results
            
            # Set up test environment with the specified IFC file
            if not self.setup_test_environment(self.test_files[ifc_file_name]):
                logger.error("Failed to set up test environment")
                all_results["success"] = False
                return all_results
            
            # Start timing
            start_time = time.time()
            
            # Run individual tests
            all_results["test_results"]["conversion"] = self.test_ifc_to_topologic_conversion()
            all_results["test_results"]["adjacency"] = self.test_adjacency_extraction()
            all_results["test_results"]["containment"] = self.test_containment_extraction()
            all_results["test_results"]["space_boundaries"] = self.test_space_boundaries_extraction()
            all_results["test_results"]["connectivity"] = self.test_connectivity_graph_generation()
            all_results["test_results"]["path_finding"] = self.test_path_finding()
            all_results["test_results"]["database_mapping"] = self.test_database_mapping()
            all_results["test_results"]["topological_query"] = self.test_topological_query()
            
            # End timing
            end_time = time.time()
            all_results["total_time"] = end_time - start_time
            
            # Check overall success
            all_results["success"] = all(
                result.get("success", False) 
                for result in all_results["test_results"].values()
            )
            
            return all_results


    def print_results(results: Dict[str, Any]) -> None:
        """
        Print test results in a formatted way.
        
        Args:
            results: Test results to print
        """
        print("\n==== TEST RESULTS ====")
        print(f"File: {results['file_name']}")
        print(f"Overall success: {results['success']}")
        print(f"Total time: {results['total_time']:.2f} seconds")
        
        for test_name, test_result in results["test_results"].items():
            print(f"\n--- {test_name.replace('_', ' ').title()} Test ---")
            print(f"Success: {test_result.get('success', False)}")
            
            for key, value in test_result.items():
                if key != "success" and not isinstance(value, dict) and not isinstance(value, list):
                    if isinstance(value, float):
                        print(f"{key.replace('_', ' ').title()}: {value:.3f}")
                    else:
                        print(f"{key.replace('_', ' ').title()}: {value}")
                        
            if "relationship_types" in test_result and isinstance(test_result["relationship_types"], dict):
                print("Relationship Types:")
                for rel_type, count in test_result["relationship_types"].items():
                    print(f"  - {rel_type}: {count}")
                    
            if "element_types" in test_result and isinstance(test_result["element_types"], dict):
                print("Element Types:")
                for elem_type, counts in list(test_result["element_types"].items())[:5]:  # Show top 5
                    success_rate = 0
                    if counts["total"] > 0:
                        success_rate = (counts["successful"] / counts["total"]) * 100
                    print(f"  - {elem_type}: {counts['successful']}/{counts['total']} ({success_rate:.1f}%)")
                
                if len(test_result["element_types"]) > 5:
                    print(f"  ... and {len(test_result['element_types']) - 5} more")


    def main():
        """Main entry point for testing topological features."""
        
        # Create tester
        tester = TopologicalFeaturesTester()
        
        # Set default test file - use "simple_building", "duplex", or "office"
        test_file = "simple_building"
        
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
        try:
            sys.exit(main())
        except Exception as e:
            logger.exception(f"Unhandled exception: {str(e)}")
            sys.exit(1)
            
except ImportError as e:
    print(f"Failed to import required modules: {str(e)}")
    print("Make sure all dependencies are installed.")
    sys.exit(1) 