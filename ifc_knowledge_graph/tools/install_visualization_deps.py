#!/usr/bin/env python
"""
Installation script for BIMConverse visualization dependencies.

This script installs the required Python packages for the visualization capabilities
of the BIMConverse GraphRAG system, specifically for spatial query results visualization.
"""

import subprocess
import sys
import platform
import os

# Define the required packages
REQUIRED_PACKAGES = [
    "plotly",
    "networkx",
    "pandas",  # Often helpful for data manipulation
    "kaleido"  # For static image export with plotly
]

def install_packages(packages):
    """
    Install the specified packages using pip.
    
    Args:
        packages: List of package names to install
    """
    print(f"Installing required packages: {', '.join(packages)}")
    
    # Check if we're in a virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    if not in_venv:
        print("WARNING: It is recommended to install packages in a virtual environment.")
        response = input("Continue with installation? (y/n): ")
        if response.lower() != 'y':
            print("Installation aborted.")
            return
    
    # Install each package
    for package in packages:
        print(f"Installing {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"Successfully installed {package}")
        except subprocess.CalledProcessError as e:
            print(f"Error installing {package}: {e}")
            
    print("\nAll packages installed. Verifying installations...")
    
    # Verify installations
    for package in packages:
        try:
            __import__(package)
            print(f"✓ {package} is installed correctly")
        except ImportError:
            print(f"✗ {package} could not be imported. It may not have installed correctly.")

def main():
    """Main entry point for the script."""
    print("BIMConverse Visualization Dependencies Installer")
    print("===============================================")
    print("This script will install the required packages for BIMConverse visualization capabilities.")
    print(f"Python version: {platform.python_version()}")
    print(f"Platform: {platform.platform()}")
    print()
    
    # Ask for confirmation
    response = input("Would you like to install the visualization dependencies? (y/n): ")
    if response.lower() != 'y':
        print("Installation aborted.")
        return
    
    # Install the packages
    install_packages(REQUIRED_PACKAGES)
    
    print("\nInstallation complete!")
    print("\nTo use the visualization capabilities, import the visualization module:")
    print("from bimconverse.visualization import SpatialVisualizer")
    print("\nExample usage:")
    print("visualizer = SpatialVisualizer()")
    print("filepath = visualizer.visualize_graph(nodes, relationships, 'My Building Graph')")
    print("print(f'Visualization saved to {filepath}')")

if __name__ == "__main__":
    main() 