import os
import sys
import logging
import ifcopenshell

# Add the src directory to the Python path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
sys.path.insert(0, src_dir)

from ifc_to_graph.topology import TopologyProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="topological_test.log",
    filemode="w"
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

logger = logging.getLogger(__name__)

# Test file paths
TEST_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "01_Duplex_A.ifc")
SMALL_TEST_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "small_test.ifc")

def test_topology_basic():
    """Test basic topology functions."""
    logger.info("Testing basic topology functions")
    
    # Load IFC file
    if os.path.exists(SMALL_TEST_FILE_PATH):
        ifc_file = ifcopenshell.open(SMALL_TEST_FILE_PATH)
        logger.info(f"Loaded small test file with {len(ifc_file.by_type('IfcProduct'))} products")
    else:
        logger.info(f"Small test file not found at {SMALL_TEST_FILE_PATH}, using main test file")
        ifc_file = ifcopenshell.open(TEST_FILE_PATH)
        logger.info(f"Loaded test file with {len(ifc_file.by_type('IfcProduct'))} products")
    
    # Create topology processor
    processor = TopologyProcessor(ifc_file)
    
    # Test basic functions
    logger.info("Testing get_all_products")
    products = processor.get_all_products()
    logger.info(f"Found {len(products)} products")
    
    # Check a few products
    logger.info("Checking first few products:")
    for i, product in enumerate(products[:5]):
        logger.info(f"  {i+1}. {product}")
    
    return True

def test_element_relationships():
    """Test element relationship functions."""
    logger.info("Testing element relationship functions")
    
    # Load IFC file
    ifc_file = ifcopenshell.open(TEST_FILE_PATH)
    
    # Create topology processor
    processor = TopologyProcessor(ifc_file)
    
    # Get all walls
    walls = ifc_file.by_type("IfcWall")
    if walls:
        # Test with first wall
        wall = walls[0]
        logger.info(f"Testing with wall: {wall}")
        
        # Get related elements
        logger.info("Getting related elements")
        related = processor.get_related_elements(wall)
        logger.info(f"Found {len(related)} related elements")
        
        # Log first few related elements
        for i, rel in enumerate(related[:5] if len(related) > 5 else related):
            logger.info(f"  {i+1}. {rel}")
    else:
        logger.warning("No walls found in test file")
    
    return True

def test_spatial_structure():
    """Test spatial structure functions."""
    logger.info("Testing spatial structure functions")
    
    # Load IFC file
    ifc_file = ifcopenshell.open(TEST_FILE_PATH)
    
    # Create topology processor
    processor = TopologyProcessor(ifc_file)
    
    # Get spatial structure
    logger.info("Getting spatial structure")
    structure = processor.get_spatial_structure()
    
    # Print the structure
    logger.info("Spatial structure:")
    for level, elements in structure.items():
        logger.info(f"  Level {level}: {len(elements)} elements")
        # Print first few elements
        for i, element in enumerate(elements[:3]):
            logger.info(f"    {i+1}. {element}")
    
    return True

def test_containment():
    """Test containment functions."""
    logger.info("Testing containment functions")
    
    # Load IFC file
    ifc_file = ifcopenshell.open(TEST_FILE_PATH)
    
    # Create topology processor
    processor = TopologyProcessor(ifc_file)
    
    # Get all storeys
    storeys = ifc_file.by_type("IfcBuildingStorey")
    if storeys:
        # Test with first storey
        storey = storeys[0]
        logger.info(f"Testing with storey: {storey}")
        
        # Get contained elements
        logger.info("Getting contained elements")
        contained = processor.get_contained_elements(storey)
        logger.info(f"Found {len(contained)} contained elements")
        
        # Group by type
        by_type = {}
        for elem in contained:
            elem_type = elem.is_a()
            if elem_type not in by_type:
                by_type[elem_type] = []
            by_type[elem_type].append(elem)
        
        # Log counts by type
        logger.info("Contained elements by type:")
        for elem_type, elements in by_type.items():
            logger.info(f"  {elem_type}: {len(elements)}")
    else:
        logger.warning("No building storeys found in test file")
    
    return True

def run_tests():
    """Run all tests."""
    logger.info("Running topology tests")
    
    results = {}
    
    try:
        logger.info("=== Basic topology test ===")
        results["Basic Topology"] = test_topology_basic()
    except Exception as e:
        logger.error(f"Basic topology test failed: {str(e)}")
        results["Basic Topology"] = False
    
    try:
        logger.info("\n=== Element relationships test ===")
        results["Element Relationships"] = test_element_relationships()
    except Exception as e:
        logger.error(f"Element relationships test failed: {str(e)}")
        results["Element Relationships"] = False
    
    try:
        logger.info("\n=== Spatial structure test ===")
        results["Spatial Structure"] = test_spatial_structure()
    except Exception as e:
        logger.error(f"Spatial structure test failed: {str(e)}")
        results["Spatial Structure"] = False
    
    try:
        logger.info("\n=== Containment test ===")
        results["Containment"] = test_containment()
    except Exception as e:
        logger.error(f"Containment test failed: {str(e)}")
        results["Containment"] = False
    
    # Print summary
    logger.info("\n=== Test summary ===")
    for test_name, result in results.items():
        logger.info(f"{test_name}: {'PASSED' if result else 'FAILED'}")
    
    # Overall result
    return all(results.values())

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 