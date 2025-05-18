"""
Parser module for extracting data from IFC files.

This module provides functionality to parse IFC files using IfcOpenShell,
extracting entities, relationships, attributes, and property sets.
"""

from .ifc_parser import IfcParser

__all__ = ["IfcParser"] 