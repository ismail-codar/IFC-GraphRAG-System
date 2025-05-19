#!/usr/bin/env python
"""
IFC Optimizer

This script optimizes IFC files by:
1. Removing duplicate geometry instances
2. Optimizing large files for better performance
3. Providing statistics on the IFC file content
"""

import os
import sys
import time
import argparse
import logging
from pathlib import Path
import ifcopenshell

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    from toposort import toposort_flatten as toposort
    TOPOSORT_AVAILABLE = True
except ImportError:
    logger.warning("toposort package not installed. Install with 'pip install toposort' for best optimization.")
    TOPOSORT_AVAILABLE = False

def get_entity_stats(ifc_file):
    """
    Get statistics on entity types in the IFC file.
    
    Args:
        ifc_file: The IFC file object
        
    Returns:
        Dictionary with entity types and their counts
    """
    types = set(i.is_a() for i in ifc_file)
    types_count = {t: len(ifc_file.by_type(t)) for t in types}
    return types_count

def print_entity_stats(stats, title="IFC Entity Statistics"):
    """
    Print statistics about entity types in a readable format.
    
    Args:
        stats: Dictionary with entity types and their counts
        title: Title for the statistics output
    """
    print(f"\n=== {title} ===")
    
    # Sort by count (descending)
    sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)
    
    # Print top 20 most common entities
    for entity_type, count in sorted_stats[:20]:
        print(f"{entity_type}: {count}")
    
    # Print total
    total = sum(stats.values())
    print(f"\nTotal entities: {total}")

def optimize_ifc(input_file, output_file=None, perform_topo_sort=True):
    """
    Optimize an IFC file by removing duplicate geometry instances.
    
    Args:
        input_file: Path to input IFC file
        output_file: Path to output optimized IFC file (if None, will use input_file_optimized.ifc)
        perform_topo_sort: Whether to perform topological sorting
        
    Returns:
        Dictionary with optimization statistics
    """
    if not output_file:
        input_path = Path(input_file)
        output_file = str(input_path.parent / f"{input_path.stem}_optimized{input_path.suffix}")
    
    logger.info(f"Optimizing IFC file: {input_file}")
    logger.info(f"Output will be saved to: {output_file}")
    
    start_time = time.time()
    
    # Open input file
    f = ifcopenshell.open(input_file)
    
    # Get initial statistics
    start_stats = get_entity_stats(f)
    start_file_size = os.path.getsize(input_file)
    
    # Create a new file with the same schema
    g = ifcopenshell.file(schema=f.schema)
    
    # Copy header
    g.wrapped_data.header = f.wrapped_data.header
    
    if TOPOSORT_AVAILABLE and perform_topo_sort:
        logger.info("Performing topological sort for optimal deduplication")
        optimize_with_toposort(f, g)
    else:
        logger.info("Performing simple optimization without topological sort")
        optimize_simple(f, g)
    
    # Write the optimized file
    g.write(output_file)
    
    # Get final statistics
    end_time = time.time()
    end_file_size = os.path.getsize(output_file)
    end_stats = get_entity_stats(g)
    
    # Prepare result statistics
    result = {
        "input_file": input_file,
        "output_file": output_file,
        "start_file_size": start_file_size,
        "end_file_size": end_file_size,
        "size_reduction": start_file_size - end_file_size,
        "size_reduction_percent": (1 - (end_file_size / start_file_size)) * 100,
        "start_entity_count": sum(start_stats.values()),
        "end_entity_count": sum(end_stats.values()),
        "entity_reduction": sum(start_stats.values()) - sum(end_stats.values()),
        "entity_reduction_percent": (1 - (sum(end_stats.values()) / sum(start_stats.values()))) * 100,
        "processing_time": end_time - start_time
    }
    
    return result, start_stats, end_stats

def generate_instances_and_references(ifc_file):
    """
    Generator which yields an entity id and the set of all of its references.
    """
    for inst in ifc_file:
        yield inst.id(), set(i.id() for i in ifc_file.traverse(inst)[1:] if i.id())

def map_value(v, g, instance_mapping):
    """
    Recursive function which replicates an entity instance, with 
    its attributes, mapping references to already registered instances.
    """
    if isinstance(v, (list, tuple)):
        # Lists are recursively traversed
        return type(v)(map(lambda x: map_value(x, g, instance_mapping), v))
    elif isinstance(v, ifcopenshell.entity_instance):
        if v.id() == 0:
            # Express simple types are not part of the toposort and just copied
            return g.create_entity(v.is_a(), v[0])
        
        return instance_mapping[v]
    else:
        # A plain python value can just be returned
        return v

def optimize_with_toposort(f, g):
    """
    Optimize IFC file using topological sort for better deduplication.
    
    Args:
        f: Input IFC file
        g: Output IFC file
    """
    info_to_id = {}
    instance_mapping = {}
    
    # Generate a dict of entity ID to referenced IDs
    instances_and_refs = dict(generate_instances_and_references(f))
    
    # Perform topological sort
    sorted_ids = toposort(instances_and_refs)
    logger.info(f"Topological sort completed. Processing {len(sorted_ids)} entities...")
    
    # Process entities in sorted order
    for i, id in enumerate(sorted_ids):
        if i % 5000 == 0:
            logger.info(f"Processed {i}/{len(sorted_ids)} entities...")
            
        inst = f[id]
        
        try:
            # Get entity info as a frozenset for comparisons
            info = inst.get_info(include_identifier=False, recursive=True, return_type=frozenset)
            
            # If we've seen this exact entity before, map to existing one
            if info in info_to_id:
                mapped = instance_mapping[inst] = instance_mapping[f[info_to_id[info]]]
            else:
                # Otherwise create a new entity
                info_to_id[info] = id
                instance_mapping[inst] = g.create_entity(
                    inst.is_a(),
                    *map(lambda x: map_value(x, g, instance_mapping), inst)
                )
        except Exception as e:
            logger.error(f"Error processing entity {id} of type {inst.is_a()}: {str(e)}")
            # Create entity anyway to maintain referential integrity
            try:
                instance_mapping[inst] = g.create_entity(
                    inst.is_a(),
                    *map(lambda x: map_value(x, g, instance_mapping), inst)
                )
            except Exception as e2:
                logger.error(f"Failed to create fallback entity: {str(e2)}")

def optimize_simple(f, g):
    """
    Simple optimization without topological sort.
    
    Args:
        f: Input IFC file
        g: Output IFC file
    """
    info_to_inst = {}
    instance_mapping = {}
    
    # First pass: Find duplicate entities and build mapping
    logger.info("First pass: Identifying duplicate entities...")
    for i, inst in enumerate(f):
        if i % 5000 == 0:
            logger.info(f"Processed {i}/{len(f)} entities in first pass...")
            
        try:
            entity_type = inst.is_a()
            
            # For entities that commonly have duplicates, check if we've seen it before
            if entity_type in ("IfcCartesianPoint", "IfcDirection", "IfcVector", 
                               "IfcPolyline", "IfcCompositeCurve", "IfcTrimmedCurve"):
                # Create a simplified info tuple for comparison
                if entity_type == "IfcCartesianPoint":
                    info = (entity_type, tuple(inst.Coordinates))
                elif entity_type == "IfcDirection":
                    info = (entity_type, tuple(inst.DirectionRatios))
                elif entity_type in ("IfcPolyline", "IfcCompositeCurve"):
                    # These are harder to compare, so just keep track of the instances
                    info = id(inst)
                else:
                    # For other types, just use their type as key
                    info = entity_type
                
                if info in info_to_inst:
                    instance_mapping[inst] = info_to_inst[info]
                else:
                    info_to_inst[info] = inst
            else:
                # For other entities, keep track of them individually
                instance_mapping[inst] = inst
        except Exception as e:
            logger.error(f"Error in first pass processing entity {inst.id()} of type {inst.is_a()}: {str(e)}")
            instance_mapping[inst] = inst
    
    # Second pass: Create new entities in the output file
    logger.info("Second pass: Creating optimized entities...")
    created_instances = {}
    
    for i, inst in enumerate(f):
        if i % 5000 == 0:
            logger.info(f"Processed {i}/{len(f)} entities in second pass...")
            
        # If this instance maps to itself (not a duplicate), create it
        if instance_mapping[inst] is inst:
            try:
                mapped_attrs = []
                for j, attr in enumerate(inst):
                    if isinstance(attr, ifcopenshell.entity_instance):
                        # Look up mapped instance
                        mapped_attr = instance_mapping.get(attr, attr)
                        if mapped_attr in created_instances:
                            mapped_attrs.append(created_instances[mapped_attr])
                        else:
                            # If not created yet, use the original
                            mapped_attrs.append(attr)
                    elif isinstance(attr, (list, tuple)):
                        # Handle lists/tuples of instances
                        mapped_list = []
                        for item in attr:
                            if isinstance(item, ifcopenshell.entity_instance):
                                mapped_item = instance_mapping.get(item, item)
                                if mapped_item in created_instances:
                                    mapped_list.append(created_instances[mapped_item])
                                else:
                                    mapped_list.append(item)
                            else:
                                mapped_list.append(item)
                        mapped_attrs.append(type(attr)(mapped_list))
                    else:
                        # Pass through regular attributes
                        mapped_attrs.append(attr)
                
                # Create the new entity
                created = g.create_entity(inst.is_a(), *mapped_attrs)
                created_instances[inst] = created
            except Exception as e:
                logger.error(f"Error in second pass creating entity {inst.id()} of type {inst.is_a()}: {str(e)}")

def print_optimization_results(result):
    """
    Print optimization results in a readable format.
    
    Args:
        result: Dictionary with optimization statistics
    """
    print("\n=== Optimization Results ===")
    print(f"Input file: {result['input_file']}")
    print(f"Output file: {result['output_file']}")
    print(f"File size: {result['start_file_size']/1024:.1f} KB -> {result['end_file_size']/1024:.1f} KB")
    print(f"Size reduction: {result['size_reduction']/1024:.1f} KB ({result['size_reduction_percent']:.1f}%)")
    print(f"Entity count: {result['start_entity_count']} -> {result['end_entity_count']}")
    print(f"Entity reduction: {result['entity_reduction']} ({result['entity_reduction_percent']:.1f}%)")
    print(f"Processing time: {result['processing_time']:.2f} seconds")

def main():
    parser = argparse.ArgumentParser(description="Optimize IFC files by removing duplicate geometry instances")
    parser.add_argument("input_file", help="Input IFC file path")
    parser.add_argument("-o", "--output", help="Output IFC file path (default: input_file_optimized.ifc)")
    parser.add_argument("--no-topo-sort", action="store_true", help="Disable topological sorting (faster but less effective)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not os.path.exists(args.input_file):
        logger.error(f"Input file not found: {args.input_file}")
        return 1
    
    try:
        # Perform optimization
        result, start_stats, end_stats = optimize_ifc(
            args.input_file, 
            args.output, 
            not args.no_topo_sort
        )
        
        # Print results
        print_optimization_results(result)
        print_entity_stats(start_stats, "Original IFC Entities")
        print_entity_stats(end_stats, "Optimized IFC Entities")
        
        logger.info(f"Optimization complete. Optimized file saved to: {result['output_file']}")
        return 0
        
    except Exception as e:
        logger.error(f"Error during optimization: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 