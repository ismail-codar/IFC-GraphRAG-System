#!/usr/bin/env python3
"""
Fix the import issue in optimized_processor.py for topologic_analyzer
"""

import os
import re
import sys
import shutil
from datetime import datetime

def backup_file(file_path):
    """Create a backup of the file"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_path = f"{file_path}.{timestamp}.bak"
    shutil.copy2(file_path, backup_path)
    print(f"Created backup: {backup_path}")
    return backup_path

def fix_imports(file_path):
    """Fix the import path for TopologicAnalyzer in the processor file"""
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Make a backup
    backup_file(file_path)
    
    # Check if the incorrect import exists
    incorrect_import = "from src.ifc_to_graph.analyzer.topologic_analyzer import TopologicAnalyzer"
    correct_import = "from src.ifc_to_graph.topology.topologic_analyzer import TopologicAnalyzer"
    
    if incorrect_import in content:
        # Replace the incorrect import
        updated_content = content.replace(incorrect_import, correct_import)
        print(f"Found and replaced incorrect import path")
        
        # Write the updated content
        with open(file_path, 'w') as f:
            f.write(updated_content)
        
        print(f"Fixed import path in {file_path}")
        return True
    elif "try:" in content and "from src.ifc_to_graph." in content and "TopologicAnalyzer" in content:
        # There might be a try/except block with the import
        print("Found import inside a try/except block. Checking for issues...")
        
        # Use regex to find the import line
        pattern = r"from src\.ifc_to_graph\.([a-zA-Z_.]+)\.topologic_analyzer import TopologicAnalyzer"
        match = re.search(pattern, content)
        
        if match and match.group(1) != "topology":
            # Found incorrect path within a try/except
            updated_content = re.sub(
                pattern,
                "from src.ifc_to_graph.topology.topologic_analyzer import TopologicAnalyzer",
                content
            )
            
            # Write the updated content
            with open(file_path, 'w') as f:
                f.write(updated_content)
            
            print(f"Fixed import path within try/except block in {file_path}")
            return True
        else:
            print("Import path appears to be correct or using a different pattern")
    else:
        # Import line not found directly, try to find TOPOLOGICPY_AVAILABLE check
        topologic_import_check = re.search(
            r"try:\s+from\s+([^\s]+)\s+import\s+TopologicAnalyzer\s+TOPOLOGICPY_AVAILABLE\s+=\s+True",
            content, re.DOTALL
        )
        
        if topologic_import_check:
            module_path = topologic_import_check.group(1)
            if module_path != "src.ifc_to_graph.topology.topologic_analyzer":
                # Replace the module path
                updated_content = content.replace(
                    f"from {module_path} import TopologicAnalyzer",
                    "from src.ifc_to_graph.topology.topologic_analyzer import TopologicAnalyzer"
                )
                
                # Write the updated content
                with open(file_path, 'w') as f:
                    f.write(updated_content)
                
                print(f"Fixed import path in TOPOLOGICPY_AVAILABLE check block")
                return True
            else:
                print("Import path in TOPOLOGICPY_AVAILABLE check is already correct")
        else:
            print("Could not find the import statement in the file")
    
    return False

def verify_topologic_import():
    """Check if TopologicAnalyzer can be imported correctly"""
    try:
        # Try to import from the correct path
        from src.ifc_to_graph.topology.topologic_analyzer import TopologicAnalyzer
        print("✓ Successfully verified TopologicAnalyzer import")
        return True
    except ImportError as e:
        print(f"✗ Failed to import TopologicAnalyzer: {e}")
        return False

def main():
    """Fix the import issue in optimized_processor.py"""
    file_path = "optimized_processor.py"
    
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        return False
    
    print(f"Checking {file_path} for import issues...")
    
    # Fix imports
    fixed = fix_imports(file_path)
    
    if fixed:
        print("\nFixed import issues in the processor file.")
        print("\nVerifying if TopologicAnalyzer can be imported correctly...")
        verify_topologic_import()
        
        print("\nNow run the following to verify all fixes:")
        print("$ python check_topologic_status.py")
    else:
        print("\nNo import issues were found or fixed.")
        print("\nOther possible issues to check:")
        print("1. Make sure TopologicPy is installed and working")
        print("2. Check that the IFC file has valid geometry")
        print("3. Enable more detailed logging in _run_topological_analysis")
    
    return True

if __name__ == "__main__":
    main() 