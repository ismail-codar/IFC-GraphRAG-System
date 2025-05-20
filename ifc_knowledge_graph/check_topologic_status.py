#!/usr/bin/env python3
"""
Check the status of the topological analyzer and try to run a simple analysis
to diagnose why relationships aren't being created.
"""

import os
import sys
import logging
import importlib

# Add parent directory to path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_topologic_import():
    """Check if TopologicPy can be imported"""
    print("Checking if TopologicPy is available...")
    try:
        import topologicpy
        from topologicpy.Topology import Topology
        print("✓ TopologicPy imported successfully!")
        return True
    except ImportError as e:
        print(f"✗ Failed to import TopologicPy: {e}")
        return False

def check_topologic_analyzer():
    """Check if the TopologicAnalyzer can be imported and instantiated"""
    print("\nChecking TopologicAnalyzer class...")
    try:
        # Try to find the module with the analyzer
        locations = [
            "src.ifc_to_graph.analyzer.topologic_analyzer",
            "src.ifc_to_graph.topology.topologic_analyzer",
        ]
        
        module = None
        for loc in locations:
            try:
                module = importlib.import_module(loc)
                break
            except ImportError:
                continue
        
        if not module:
            print("✗ Could not find TopologicAnalyzer module")
            return False
            
        # Check if TopologicAnalyzer exists in the module
        if not hasattr(module, "TopologicAnalyzer"):
            print("✗ TopologicAnalyzer class not found in module")
            return False
            
        print(f"✓ Found TopologicAnalyzer in module: {module.__name__}")
        return True
        
    except Exception as e:
        print(f"✗ Error checking TopologicAnalyzer: {e}")
        return False

def check_ifc_file():
    """Check if the IFC file exists and can be opened"""
    print("\nChecking IFC file access...")
    try:
        from src.ifc_to_graph.parser.ifc_parser import IfcParser
        
        ifc_files = []
        for root, _, files in os.walk('.'):
            for file in files:
                if file.lower().endswith('.ifc'):
                    ifc_files.append(os.path.join(root, file))
        
        if not ifc_files:
            print("✗ No IFC files found in the current directory or subdirectories")
            return False
            
        print(f"Found {len(ifc_files)} IFC files: {', '.join(ifc_files)}")
        
        # Try to open the first IFC file
        ifc_file = ifc_files[0]
        parser = IfcParser(ifc_file)
        elements = parser.get_elements()
        
        print(f"✓ Successfully opened IFC file {ifc_file} with {len(elements)} elements")
        return True
        
    except Exception as e:
        print(f"✗ Error checking IFC file: {e}")
        return False

def inspect_optimized_processor():
    """Inspect the topological analysis code in the optimized processor"""
    print("\nInspecting optimized processor's topological analysis code...")
    try:
        from optimized_processor import OptimizedIfcProcessor
        
        # Check if TOPOLOGICPY_AVAILABLE is set
        import inspect
        source = inspect.getsource(OptimizedIfcProcessor._run_topological_analysis)
        
        if "if not TOPOLOGICPY_AVAILABLE:" in source:
            print("✓ Processor checks for TOPOLOGICPY_AVAILABLE")
        else:
            print("✗ Processor does not check TOPOLOGICPY_AVAILABLE in _run_topological_analysis")
            
        if "try:" in source and "except Exception as e:" in source:
            print("✓ Processor has error handling in topological analysis")
        else:
            print("✗ Missing proper error handling in topological analysis")
            
        # Check the import path
        if "from src.ifc_to_graph.analyzer.topologic_analyzer import TopologicAnalyzer" in source:
            print("✗ Incorrect import path: src.ifc_to_graph.analyzer.topologic_analyzer")
        elif "from src.ifc_to_graph.topology.topologic_analyzer import TopologicAnalyzer" in source:
            print("✓ Correct import path: src.ifc_to_graph.topology.topologic_analyzer")
            
        # Print insights
        print("\nPotential issues in _run_topological_analysis method:")
        print("-----------------------------------------------------")
        if "src.ifc_to_graph.analyzer.topologic_analyzer" in source:
            print("1. Import path is incorrect - should be 'src.ifc_to_graph.topology.topologic_analyzer'")
            
        if "self.mapper.create_relationships_batch" in source:
            print("✓ Using batch relationship creation")
        else:
            print("2. Not using batch relationship creation method")
            
        return True
        
    except Exception as e:
        print(f"✗ Error inspecting optimized processor: {e}")
        return False

def main():
    """Run all checks"""
    print("==== Topological Analysis Diagnostic ====\n")
    
    topologic_available = check_topologic_import()
    analyzer_available = check_topologic_analyzer()
    ifc_file_accessible = check_ifc_file()
    processor_inspection = inspect_optimized_processor()
    
    print("\n==== Diagnostic Summary ====")
    print(f"TopologicPy available: {'✓' if topologic_available else '✗'}")
    print(f"TopologicAnalyzer available: {'✓' if analyzer_available else '✗'}")
    print(f"IFC file accessible: {'✓' if ifc_file_accessible else '✗'}")
    print(f"Processor inspection completed: {'✓' if processor_inspection else '✗'}")
    
    if not topologic_available:
        print("\nPrimary issue: TopologicPy is not available or cannot be imported")
        print("Solution: Ensure TopologicPy is properly installed and accessible")
    
    if not analyzer_available:
        print("\nIssue: TopologicAnalyzer class is not found or cannot be imported")
        print("Solution: Verify import paths in optimized_processor.py")
    
    print("\nPossible solutions:")
    print("1. Check the import path in optimized_processor.py for TopologicAnalyzer")
    print("2. Verify TopologicPy installation and configuration")
    print("3. Enable more detailed logging in the processor")
    
if __name__ == "__main__":
    main() 