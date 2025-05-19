#!/usr/bin/env python
"""
Debug script to inspect the Neo4jConnector's test_connection method
"""

import os
import sys
import inspect
from pathlib import Path

# Add the src directory to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.ifc_to_graph.database.neo4j_connector import Neo4jConnector

# Print the source code of the test_connection method
print("=== Neo4jConnector.test_connection source ===")
print(inspect.getsource(Neo4jConnector.test_connection))

# Print the file path where the method is defined
print("\n=== File location ===")
print(f"Module file: {inspect.getfile(Neo4jConnector)}")

# Also check for .pyc (cached) files
module_dir = Path(inspect.getfile(Neo4jConnector)).parent
pyc_files = list(module_dir.glob("*.pyc"))
print("\n=== Cached .pyc files in module directory ===")
for pyc in pyc_files:
    print(f"- {pyc}")

# Look for backup files
backup_files = list(module_dir.glob("*.bak"))
print("\n=== Backup files in module directory ===")
for bak in backup_files:
    print(f"- {bak}")

if __name__ == "__main__":
    print("\nDone.") 