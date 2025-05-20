from src.ifc_to_graph.parser.ifc_parser import IfcParser
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Debug the spatial structure output from the parser"""
    # Path to the IFC file - corrected path
    ifc_file_path = r"data/ifc_files/Duplex_A_20110907.ifc"
    
    # Initialize the parser
    logger.info(f"Initializing IFC parser with file: {ifc_file_path}")
    parser = IfcParser(ifc_file_path)
    
    # Get the spatial structure
    logger.info("Retrieving spatial structure...")
    spatial_structure = parser.get_spatial_structure()
    
    # Print structure for debugging
    logger.info(f"Spatial structure contains: "
              f"{len(spatial_structure.get('sites', []))} sites, "
              f"{len(spatial_structure.get('buildings', []))} buildings, "
              f"{len(spatial_structure.get('storeys', []))} storeys, "
              f"{len(spatial_structure.get('spaces', []))} spaces")
    
    # Show project info
    if 'project' in spatial_structure and spatial_structure['project']:
        project = spatial_structure['project']
        logger.info(f"Project: {project.get('GlobalId')} - {project.get('Name')}")
        print(f"Project details: {json.dumps(project, indent=2)}")
    else:
        logger.warning("No project information found")
    
    # Show site info
    if 'sites' in spatial_structure and spatial_structure['sites']:
        for i, site in enumerate(spatial_structure['sites']):
            logger.info(f"Site {i+1}: {site.get('GlobalId')} - {site.get('Name')}")
            print(f"Site {i+1} details: {json.dumps(site, indent=2)}")
    else:
        logger.warning("No sites found")
    
    # Show building info
    if 'buildings' in spatial_structure and spatial_structure['buildings']:
        for i, building in enumerate(spatial_structure['buildings']):
            logger.info(f"Building {i+1}: {building.get('GlobalId')} - {building.get('Name')}")
            print(f"Building {i+1} details: {json.dumps(building, indent=2)}")
    else:
        logger.warning("No buildings found")
    
    # Show storey info
    if 'storeys' in spatial_structure and spatial_structure['storeys']:
        for i, storey in enumerate(spatial_structure['storeys']):
            logger.info(f"Storey {i+1}: {storey.get('GlobalId')} - {storey.get('Name')}")
            print(f"Storey {i+1} details: {json.dumps(storey, indent=2)}")
    else:
        logger.warning("No storeys found")
    
    # Show space info
    if 'spaces' in spatial_structure and spatial_structure['spaces']:
        for i, space in enumerate(spatial_structure['spaces'][:2]):  # Just show first 2 spaces
            logger.info(f"Space {i+1}: {space.get('GlobalId')} - {space.get('Name')}")
            print(f"Space {i+1} details: {json.dumps(space, indent=2)}")
        logger.info(f"... and {len(spatial_structure['spaces']) - 2} more spaces")
    else:
        logger.warning("No spaces found")

if __name__ == "__main__":
    main() 