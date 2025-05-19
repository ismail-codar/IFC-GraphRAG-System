#!/usr/bin/env python
"""
Debug script to examine IFC element data and format issues
"""

import os
import sys
import logging
import json
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)  # ifc_knowledge_graph directory
sys.path.insert(0, parent_dir)

try:
    from src.ifc_to_graph.parser.ifc_parser import IfcParser
    from src.ifc_to_graph.database.ifc_to_graph_mapper import IfcToGraphMapper
    from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector
    from src.ifc_to_graph.database.performance_monitor import PerformanceMonitor
    from src.ifc_to_graph.database.schema import format_property_value
    logger.info("Successfully imported modules")
except ImportError as e:
    logger.error(f"Error importing modules: {e}")
    sys.exit(1)

def debug_element_data():
    """
    Debug element data formatting issues
    """
    # IFC file path
    ifc_file_path = os.path.join(parent_dir, "data", "ifc_files", "Duplex_A_20110907.ifc")
    
    # Verify file exists
    if not os.path.exists(ifc_file_path):
        logger.error(f"Test IFC file not found: {ifc_file_path}")
        return False
    
    try:
        # Initialize parser
        parser = IfcParser(ifc_file_path)
        logger.info(f"IFC Parser initialized with file: {ifc_file_path}")
        
        # Initialize performance monitor
        perf_monitor = PerformanceMonitor(enabled=True)
        
        # Initialize Neo4j connector - no actual connection needed for debugging
        # Just create dummy objects for testing the format_property_value function
        class DummyConnector:
            def run_query(self, query, params):
                return None
        
        connector = DummyConnector()
        
        # Initialize mapper
        mapper = IfcToGraphMapper(connector)
        
        # Get all elements
        elements = parser.get_elements()
        logger.info(f"Found {len(elements)} elements in the IFC file")
        
        # Count elements by type
        element_types = {}
        for element in elements:
            element_type = element.is_a()
            if element_type not in element_types:
                element_types[element_type] = 0
            element_types[element_type] += 1
        
        logger.info("Element types in the IFC file:")
        for element_type, count in element_types.items():
            logger.info(f"  {element_type}: {count}")
        
        # Format issues counter
        format_issues = 0
        null_global_ids = 0
        elements_with_null_globalid = []
        
        # Debug element data formatting - now check all elements
        for idx, element in enumerate(elements):
            element_data = parser.get_element_attributes(element)
            
            # Check for missing GlobalId
            if "GlobalId" not in element_data or element_data["GlobalId"] is None:
                null_global_ids += 1
                elements_with_null_globalid.append({
                    "index": idx + 1,
                    "type": element.is_a(),
                    "name": element.Name if hasattr(element, "Name") else "Unnamed"
                })
                
                # Print raw element data (for the first few problematic elements)
                if null_global_ids <= 5:
                    logger.warning(f"Element {idx+1} missing GlobalId: Type={element.is_a()}, Name={element.Name if hasattr(element, 'Name') else 'Unnamed'}")
                    
                    # Try to get GlobalId directly
                    if hasattr(element, "GlobalId"):
                        direct_globalid = element.GlobalId
                        logger.info(f"  Direct GlobalId access: {direct_globalid}")
                        
                        # Try to format the GlobalId value
                        formatted_globalid = format_property_value(direct_globalid)
                        logger.info(f"  Formatted GlobalId: {formatted_globalid}")
            
            # Debug property formatting
            try:
                # Get properties in Neo4j format
                properties = {}
                for key, value in element_data.items():
                    try:
                        formatted_value = format_property_value(value)
                        properties[key] = formatted_value
                    except Exception as e:
                        format_issues += 1
                        if format_issues <= 5:  # Limit log output
                            logger.error(f"Error formatting property {key}: {str(e)}")
                
                # Test if element data can be represented as JSON
                try:
                    json_data = json.dumps(properties)
                except TypeError as e:
                    format_issues += 1
                    if format_issues <= 5:  # Limit log output
                        logger.error(f"Element {idx+1} data is not JSON serializable: {str(e)}")
                        
                        # Find problematic properties
                        for key, value in properties.items():
                            try:
                                json.dumps({key: value})
                            except TypeError as e:
                                logger.error(f"  Property {key} is not serializable: {str(e)}")
            except Exception as e:
                if format_issues <= 5:  # Limit log output
                    logger.error(f"Error processing element {idx+1}: {str(e)}")
        
        logger.info(f"Found {format_issues} formatting issues")
        logger.info(f"Found {null_global_ids} elements with null GlobalId")
        
        if null_global_ids > 0:
            logger.info("Elements with null GlobalId:")
            for i, element in enumerate(elements_with_null_globalid[:10]):  # Show first 10
                logger.info(f"  {i+1}. Type: {element['type']}, Name: {element['name']}, Index: {element['index']}")
            
            if len(elements_with_null_globalid) > 10:
                logger.info(f"  ... (and {len(elements_with_null_globalid) - 10} more)")
        
        return True
    except Exception as e:
        logger.error(f"Error debugging element data: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = debug_element_data()
    if success:
        logger.info("Element data debugging completed")
    else:
        logger.error("Element data debugging failed")
        sys.exit(1) 