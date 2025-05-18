#!/usr/bin/env python
"""
Fix null bytes in the topologic_analyzer.py file
"""

import os
import sys
from pathlib import Path

def fix_file_null_bytes(file_path):
    """
    Fix file with null bytes by reading line by line and skipping null bytes.
    
    Args:
        file_path: Path to the file to fix
    """
    try:
        print(f"Fixing null bytes in: {file_path}")
        
        # Read the file in binary mode
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Remove null bytes
        clean_content = content.replace(b'\x00', b'')
        
        # Write back the clean content
        with open(file_path, 'wb') as f:
            f.write(clean_content)
            
        print(f"Removed {len(content) - len(clean_content)} null bytes")
        return True
        
    except Exception as e:
        print(f"Error fixing file: {str(e)}")
        return False

def main():
    """Main entry point for the script."""
    # Path to the problematic file
    file_path = "src/ifc_to_graph/topology/topologic_analyzer.py"
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found")
        return 1
    
    # Fix the file
    success = fix_file_null_bytes(file_path)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 