"""
Command-line interface for parsing IFC files and exploring their content.
"""

import argparse
import json
import os
import sys
import logging
from typing import Dict, List, Any, Optional

# Add parent directory to sys.path to ensure imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ifc_to_graph.parser.ifc_parser import IfcParser

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def setup_parser() -> argparse.ArgumentParser:
    """Set up the argument parser."""
    parser = argparse.ArgumentParser(description="Parse IFC files and explore their content")
    
    parser.add_argument("ifc_file", help="Path to the IFC file to parse")
    
    # Create a subparser for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Parser for the "project" command
    project_parser = subparsers.add_parser("project", help="Get project information")
    
    # Parser for the "elements" command
    elements_parser = subparsers.add_parser("elements", help="Get elements from the IFC file")
    elements_parser.add_argument("--type", help="Filter elements by type (e.g., IfcWall)")
    elements_parser.add_argument("--limit", type=int, default=10, help="Limit the number of elements returned")
    elements_parser.add_argument("--count", action="store_true", help="Only show count of elements")
    
    # Parser for the "element" command to get a specific element by ID
    element_parser = subparsers.add_parser("element", help="Get information about a specific element")
    element_parser.add_argument("global_id", help="GlobalId of the element")
    element_parser.add_argument("--with-properties", action="store_true", help="Include property sets")
    element_parser.add_argument("--with-relationships", action="store_true", help="Include relationships")
    element_parser.add_argument("--with-materials", action="store_true", help="Include material information")
    
    # Parser for the "spatial" command
    spatial_parser = subparsers.add_parser("spatial", help="Get the spatial structure of the building")
    
    # Parser for the "property-sets" command
    prop_sets_parser = subparsers.add_parser("property-sets", help="Get property sets for an element")
    prop_sets_parser.add_argument("global_id", help="GlobalId of the element")
    
    # Parser for the "relationships" command
    relationships_parser = subparsers.add_parser("relationships", help="Get relationships for an element")
    relationships_parser.add_argument("global_id", help="GlobalId of the element")
    relationships_parser.add_argument("--type", help="Filter relationships by type")
    
    # Parser for the "materials" command
    materials_parser = subparsers.add_parser("materials", help="Get material information for an element")
    materials_parser.add_argument("global_id", help="GlobalId of the element")
    
    return parser


def format_and_print_json(data: Any) -> None:
    """Format and print JSON data."""
    # Handle objects that can't be directly serialized to JSON
    def json_serializer(obj):
        if hasattr(obj, "id"):
            return f"#{obj.id()}"
        return str(obj)
    
    # Convert the data to JSON and print it
    json_str = json.dumps(data, indent=2, default=json_serializer)
    print(json_str)


def handle_project_command(parser: IfcParser) -> None:
    """Handle the "project" command."""
    project_info = parser.get_project_info()
    format_and_print_json(project_info)


def handle_elements_command(parser: IfcParser, args: argparse.Namespace) -> None:
    """Handle the "elements" command."""
    elements = parser.get_elements(args.type)
    
    if args.count:
        print(f"Count: {len(elements)}")
        return
    
    # Limit the number of elements
    limited_elements = elements[:args.limit]
    
    # Format the elements
    formatted_elements = []
    for element in limited_elements:
        formatted_element = parser.get_element_attributes(element)
        formatted_elements.append(formatted_element)
    
    # Add a message if the output was limited
    if len(elements) > args.limit:
        print(f"Showing {args.limit} of {len(elements)} elements. Use --limit to show more.")
    
    format_and_print_json(formatted_elements)


def handle_element_command(parser: IfcParser, args: argparse.Namespace) -> None:
    """Handle the "element" command."""
    element = parser.get_element_by_id(args.global_id)
    
    if not element:
        print(f"Element with GlobalId {args.global_id} not found.")
        return
    
    # Get basic element attributes
    element_data = parser.get_element_attributes(element)
    
    # Include property sets if requested
    if args.with_properties:
        element_data["PropertySets"] = parser.get_property_sets(element)
    
    # Include relationships if requested
    if args.with_relationships:
        element_data["Relationships"] = parser.get_relationships(element)
    
    # Include material information if requested
    if args.with_materials:
        element_data["Materials"] = parser.extract_material_info(element)
    
    format_and_print_json(element_data)


def handle_spatial_command(parser: IfcParser) -> None:
    """Handle the "spatial" command."""
    spatial_structure = parser.get_spatial_structure()
    format_and_print_json(spatial_structure)


def handle_property_sets_command(parser: IfcParser, args: argparse.Namespace) -> None:
    """Handle the "property-sets" command."""
    element = parser.get_element_by_id(args.global_id)
    
    if not element:
        print(f"Element with GlobalId {args.global_id} not found.")
        return
    
    property_sets = parser.get_property_sets(element)
    format_and_print_json(property_sets)


def handle_relationships_command(parser: IfcParser, args: argparse.Namespace) -> None:
    """Handle the "relationships" command."""
    element = parser.get_element_by_id(args.global_id)
    
    if not element:
        print(f"Element with GlobalId {args.global_id} not found.")
        return
    
    relationships = parser.get_relationships(element)
    
    # Filter relationships by type if requested
    if args.type and args.type in relationships:
        relationships = {args.type: relationships[args.type]}
    
    format_and_print_json(relationships)


def handle_materials_command(parser: IfcParser, args: argparse.Namespace) -> None:
    """Handle the "materials" command."""
    element = parser.get_element_by_id(args.global_id)
    
    if not element:
        print(f"Element with GlobalId {args.global_id} not found.")
        return
    
    materials = parser.extract_material_info(element)
    format_and_print_json(materials)


def main() -> None:
    """Main entry point for the CLI."""
    # Parse arguments
    arg_parser = setup_parser()
    args = arg_parser.parse_args()
    
    # Ensure an IFC file was provided
    if not args.ifc_file:
        arg_parser.print_help()
        sys.exit(1)
    
    # Ensure a command was provided
    if not args.command:
        print("Error: Please provide a command.")
        arg_parser.print_help()
        sys.exit(1)
    
    try:
        # Create an IFC parser
        parser = IfcParser(args.ifc_file)
        
        # Handle the command
        if args.command == "project":
            handle_project_command(parser)
        elif args.command == "elements":
            handle_elements_command(parser, args)
        elif args.command == "element":
            handle_element_command(parser, args)
        elif args.command == "spatial":
            handle_spatial_command(parser)
        elif args.command == "property-sets":
            handle_property_sets_command(parser, args)
        elif args.command == "relationships":
            handle_relationships_command(parser, args)
        elif args.command == "materials":
            handle_materials_command(parser, args)
        else:
            print(f"Unknown command: {args.command}")
            arg_parser.print_help()
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 