#!/usr/bin/env python
"""
Fix file encoding issues by converting files to proper UTF-8 encoding.
This script handles:
1. UTF-16 encoded files (both BE and LE)
2. Files with null bytes
3. Files with BOM markers
"""

import os
import sys
import codecs
from pathlib import Path


def detect_encoding(file_path):
    """
    Detect file encoding by checking BOM markers and content patterns.
    
    Args:
        file_path: Path to the file
    
    Returns:
        tuple: (encoding, has_bom)
    """
    # Read the first 4 bytes to check for BOM
    with open(file_path, 'rb') as f:
        raw_data = f.read(4)
        if not raw_data:
            return 'utf-8', False
        
        # Check for BOM markers
        if raw_data.startswith(codecs.BOM_UTF8):
            return 'utf-8-sig', True
        elif raw_data.startswith(codecs.BOM_UTF16_LE):
            return 'utf-16-le', True
        elif raw_data.startswith(codecs.BOM_UTF16_BE):
            return 'utf-16-be', True
        elif raw_data.startswith(codecs.BOM_UTF32_LE):
            return 'utf-32-le', True
        elif raw_data.startswith(codecs.BOM_UTF32_BE):
            return 'utf-32-be', True
        
        # Read more content to check for null bytes
        f.seek(0)
        content = f.read(4096)
        
        # Check for UTF-16 patterns (null bytes in alternating positions)
        if b'\x00\x00\x00\x00' in content:
            # Probably binary file
            return None, False
        
        # Check for null bytes in even positions (UTF-16-LE)
        even_nulls = sum(1 for i in range(0, len(content), 2) if i < len(content) and content[i] == 0)
        odd_nulls = sum(1 for i in range(1, len(content), 2) if i < len(content) and content[i] == 0)
        
        if even_nulls > len(content) // 8 and odd_nulls < even_nulls // 8:
            return 'utf-16-le', False
        elif odd_nulls > len(content) // 8 and even_nulls < odd_nulls // 8:
            return 'utf-16-be', False
        
        # Try UTF-8
        try:
            content.decode('utf-8')
            return 'utf-8', False
        except UnicodeDecodeError:
            pass
        
        # Default to system default encoding
        return 'cp1252', False  # Common Windows default


def fix_file_encoding(file_path, target_encoding='utf-8', add_bom=False):
    """
    Fix file encoding by converting to the target encoding.
    
    Args:
        file_path: Path to the file
        target_encoding: Target encoding (default: utf-8)
        add_bom: Whether to add a BOM marker
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        source_encoding, has_bom = detect_encoding(file_path)
        if source_encoding is None:
            print(f"Skipping {file_path}: appears to be a binary file")
            return False
        
        print(f"Converting {file_path}: {source_encoding} -> {target_encoding}")
        
        # Read content with detected encoding
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Decode with source encoding
        if source_encoding == 'utf-8-sig':
            text = content.decode('utf-8-sig')
        elif source_encoding:
            text = content.decode(source_encoding, errors='replace')
        else:
            print(f"Skipping {file_path}: could not determine encoding")
            return False
        
        # Write with target encoding
        target_encoding_for_write = target_encoding + '-sig' if add_bom else target_encoding
        with open(file_path, 'wb') as f:
            f.write(text.encode(target_encoding_for_write))
        
        return True
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def fix_directory(directory, file_extensions=None, target_encoding='utf-8', add_bom=False):
    """
    Fix encoding for all files in a directory.
    
    Args:
        directory: Directory to process
        file_extensions: List of file extensions to process (default: ['.py'])
        target_encoding: Target encoding (default: utf-8)
        add_bom: Whether to add a BOM marker
    """
    if file_extensions is None:
        file_extensions = ['.py']
    
    base_dir = Path(directory)
    total_files = 0
    fixed_files = 0
    
    for ext in file_extensions:
        for file_path in base_dir.glob(f"**/*{ext}"):
            total_files += 1
            if fix_file_encoding(file_path, target_encoding, add_bom):
                fixed_files += 1
    
    print(f"Processed {total_files} files, fixed {fixed_files} files")


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python fix_file_encoding.py <directory> [file_extensions]")
        print("Example: python fix_file_encoding.py src/ifc_to_graph/topology .py")
        return
    
    directory = sys.argv[1]
    file_extensions = ['.py'] if len(sys.argv) < 3 else [f".{ext.lstrip('.')}" for ext in sys.argv[2:]]
    
    print(f"Processing directory: {directory}")
    print(f"File extensions: {', '.join(file_extensions)}")
    
    fix_directory(directory, file_extensions)


if __name__ == "__main__":
    main() 