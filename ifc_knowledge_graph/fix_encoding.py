#!/usr/bin/env python
"""
Fix encoding issue by removing null bytes from Python files
"""

import os
import sys
from pathlib import Path

def fix_file_encoding(file_path):
    """
    Remove null bytes from a file and save it with correct encoding.
    
    Args:
        file_path: Path to the file to fix
    """
    print(f"Checking encoding for: {file_path}")
    
    try:
        # Read the file in binary mode
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Remove null bytes (0x00)
        clean_content = content.replace(b'\x00', b'')
        
        # If file size changed, write back the cleaned content
        if len(content) != len(clean_content):
            with open(file_path, 'wb') as f:
                f.write(clean_content)
            print(f"Fixed encoding - removed {len(content) - len(clean_content)} null bytes")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error fixing file {file_path}: {str(e)}")
        return False

def scan_directory(directory):
    """
    Scan a directory for Python files and fix their encoding.
    
    Args:
        directory: Directory to scan
    """
    fixed_count = 0
    total_count = 0
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                total_count += 1
                if fix_file_encoding(file_path):
                    fixed_count += 1
    
    return fixed_count, total_count

def main():
    """Main entry point for the script."""
    # Path to the project directory
    project_dir = Path(".")
    
    print(f"Scanning for Python files with encoding issues...")
    fixed_count, total_count = scan_directory(project_dir)
    
    print(f"Fixed {fixed_count} out of {total_count} Python files")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 