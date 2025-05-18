 #!/usr/bin/env python
"""
Test script to check if the parallel processing module can be imported.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main function to test parallel processing imports."""
    try:
        logger.info("Attempting to import parallel_processor module...")
        
        # Try absolute import first
        try:
            from src.ifc_to_graph.utils.parallel_processor import ParallelProcessor
            logger.info("Successfully imported ParallelProcessor with absolute import")
            
            # Test creating an instance
            processor = ParallelProcessor(max_workers=2)
            logger.info(f"Created instance with {processor.max_workers} workers")
            
        except ImportError as e:
            logger.error(f"Error with absolute import: {str(e)}")
            
            # Try relative import
            sys.path.insert(0, os.path.abspath('.'))
            from ifc_knowledge_graph.src.ifc_to_graph.utils.parallel_processor import ParallelProcessor
            logger.info("Successfully imported ParallelProcessor with modified path")
        
        logger.info("Import test completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Error testing imports: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 