"""
Topological Analysis Module

This module provides functionality to analyze topological relationships
between building elements using TopologicPy.
"""

import logging
import os
import tempfile
from typing import Dict, List, Set, Tuple, Optional, Any, Union

import ifcopenshell
import ifcopenshell.geom
import numpy as np

try:
    import topologicpy
    from topologicpy.Topology import Topology
    from topologicpy.Cell import Cell
    from topologicpy.CellComplex import CellComplex
    from topologicpy.Face import Face
    from topologicpy.Edge import Edge
    from topologicpy.Vertex import Vertex
    from topologicpy.Wire import Wire
    from topologicpy.Cluster import Cluster
    from topologicpy.Dictionary import Dictionary
    TOPOLOGICPY_AVAILABLE = True
except ImportError:
    TOPOLOGICPY_AVAILABLE = False
    logging.warning("TopologicPy is not available. Topological analysis capabilities will be limited.")

# Configure logging
logger = logging.getLogger(__name__)


class TopologicAnalyzer:
    """
    Analyzer class for extracting topological relationships from IFC models
    using TopologicPy.
    """
    
    def __init__(self, ifc_parser=None):
        """
        Initialize the topological analyzer.
        
        Args:
            ifc_parser: Optional IFC parser instance to use for getting IFC data
        """
        if not TOPOLOGICPY_AVAILABLE:
            logger.warning("TopologicPy is not available. Topological analysis will be limited.")
        
        self.ifc_parser = ifc_parser
        self.topologic_entities = {}  # Cache for topologic entities by GlobalId
        self._space_boundaries_cache = {}  # Cache for space boundary relationships
        self._adjacency_cache = {}  # Cache for adjacency relationships
        self._containment_cache = {}  # Cache for containment relationships
        
    def set_ifc_parser(self, ifc_parser) -> None:
        """
        Set the IFC parser instance.
        
        Args:
            ifc_parser: The IFC parser instance to use
        """
        self.ifc_parser = ifc_parser
        
    def _check_parser(self) -> None:
        """Check if the parser is available."""
        if self.ifc_parser is None:
            raise ValueError("IFC parser not set. Use set_ifc_parser() method first.")
            
    def _check_topologicpy(self) -> None:
        """Check if TopologicPy is available."""
        if not TOPOLOGICPY_AVAILABLE:
            raise ImportError("TopologicPy is not available. Cannot perform topological analysis.")
    
    def convert_ifc_to_topologic(self, ifc_element: Any) -> Optional[Any]:
        """
        Convert an IFC element to a TopologicPy entity.
        
        Args:
            ifc_element: The IFC element to convert
            
        Returns:
            TopologicPy entity if successful, None otherwise
        """
        self._check_topologicpy()
        
        # Check if already converted and cached
        if hasattr(ifc_element, "GlobalId") and ifc_element.GlobalId in self.topologic_entities:
            return self.topologic_entities[ifc_element.GlobalId]
        
        try:
            # Use IfcOpenShell's geometry settings
            settings = ifcopenshell.geom.settings()
            
            # Create the shape from the IFC element
            shape = ifcopenshell.geom.create_shape(settings, ifc_element)
            
            if shape:
                # Get geometry data from the shape
                verts = shape.geometry.verts
                faces = shape.geometry.faces
                
                # Reshape vertices into triplets (x, y, z)
                vertices = np.array(verts).reshape(-1, 3)
                
                # Process faces to create a topologic entity
                topologic_entity = None
                
                if ifc_element.is_a("IfcSpace"):
                    # Create a Cell for spaces
                    topologic_entity = self._create_topologic_cell(vertices, faces, ifc_element)
                    
                elif ifc_element.is_a("IfcWall") or ifc_element.is_a("IfcSlab") or ifc_element.is_a("IfcRoof"):
                    # Create a Face for walls, slabs, and roofs
                    topologic_entity = self._create_topologic_face(vertices, faces, ifc_element)
                    
                elif ifc_element.is_a("IfcBeam") or ifc_element.is_a("IfcColumn") or ifc_element.is_a("IfcMember"):
                    # Create an Edge for beams, columns, and members
                    topologic_entity = self._create_topologic_edge(vertices, faces, ifc_element)
                    
                elif ifc_element.is_a("IfcDoor") or ifc_element.is_a("IfcWindow"):
                    # Create a Face for doors and windows
                    topologic_entity = self._create_topologic_face(vertices, faces, ifc_element)
                    
                else:
                    # Default: try to create a Cell for 3D elements
                    topologic_entity = self._create_topologic_cell(vertices, faces, ifc_element)
                    
                    # Fallback to Face if Cell creation fails
                    if topologic_entity is None:
                        topologic_entity = self._create_topologic_face(vertices, faces, ifc_element)
                
                # Store in cache if successful
                if topologic_entity and hasattr(ifc_element, "GlobalId"):
                    # Add dictionary with IFC data to the topologic entity
                    if hasattr(ifc_element, "GlobalId"):
                        Dictionary.ByKeysValues(
                            topologic_entity,
                            ["GlobalId", "IFCType"], 
                            [ifc_element.GlobalId, ifc_element.is_a()]
                        )
                    
                    self.topologic_entities[ifc_element.GlobalId] = topologic_entity
                    
                return topologic_entity
                
        except Exception as e:
            logger.error(f"Error converting IFC element to TopologicPy entity: {str(e)}")
            
        return None
    
    def _create_topologic_cell(self, vertices: np.ndarray, faces: List[int], ifc_element: Any) -> Optional[Any]:
        """
        Create a TopologicPy Cell from IFC geometry data.
        
        Args:
            vertices: Array of vertex coordinates
            faces: List of face indices
            ifc_element: Original IFC element
            
        Returns:
            TopologicPy Cell if successful, None otherwise
        """
        try:
            # Create topologic vertices
            topologic_vertices = []
            for vertex in vertices:
                topologic_vertex = Vertex.ByCoordinates(vertex[0], vertex[1], vertex[2])
                topologic_vertices.append(topologic_vertex)
            
            # Create faces
            topologic_faces = []
            i = 0
            while i < len(faces):
                # Get number of vertices in this face
                num_vertices = faces[i]
                i += 1
                
                # Get the indices for this face
                face_indices = faces[i:i+num_vertices]
                i += num_vertices
                
                # Create wire from vertices
                wire_vertices = []
                for idx in face_indices:
                    wire_vertices.append(topologic_vertices[idx])
                
                # Add closing vertex if not already closed
                if face_indices[0] != face_indices[-1]:
                    wire_vertices.append(topologic_vertices[face_indices[0]])
                
                # Create wire and face
                wire = Wire.ByVertices(wire_vertices)
                if wire:
                    face = Face.ByWire(wire)
                    if face:
                        topologic_faces.append(face)
            
            # Create a cell from faces
            if topologic_faces:
                cell = Cell.ByFaces(topologic_faces, tolerance=0.0001)
                return cell
                
        except Exception as e:
            logger.error(f"Error creating TopologicPy Cell: {str(e)}")
            
        return None
    
    def _create_topologic_face(self, vertices: np.ndarray, faces: List[int], ifc_element: Any) -> Optional[Any]:
        """
        Create a TopologicPy Face from IFC geometry data.
        
        Args:
            vertices: Array of vertex coordinates
            faces: List of face indices
            ifc_element: Original IFC element
            
        Returns:
            TopologicPy Face if successful, None otherwise
        """
        try:
            # Create topologic vertices
            topologic_vertices = []
            for vertex in vertices:
                topologic_vertex = Vertex.ByCoordinates(vertex[0], vertex[1], vertex[2])
                topologic_vertices.append(topologic_vertex)
            
            # Create the first face (simplified approach)
            if len(faces) > 0:
                # Get number of vertices in the first face
                num_vertices = faces[0]
                
                # Get the indices for this face
                face_indices = faces[1:1+num_vertices]
                
                # Create wire from vertices
                wire_vertices = []
                for idx in face_indices:
                    wire_vertices.append(topologic_vertices[idx])
                
                # Add closing vertex if not already closed
                if face_indices[0] != face_indices[-1]:
                    wire_vertices.append(topologic_vertices[face_indices[0]])
                
                # Create wire and face
                wire = Wire.ByVertices(wire_vertices)
                if wire:
                    face = Face.ByWire(wire)
                    return face
                
        except Exception as e:
            logger.error(f"Error creating TopologicPy Face: {str(e)}")
            
        return None
    
    def _create_topologic_edge(self, vertices: np.ndarray, faces: List[int], ifc_element: Any) -> Optional[Any]:
        """
        Create a TopologicPy Edge from IFC geometry data.
        
        Args:
            vertices: Array of vertex coordinates
            faces: List of face indices
            ifc_element: Original IFC element
            
        Returns:
            TopologicPy Edge if successful, None otherwise
        """
        try:
            if len(vertices) >= 2:
                # Create start and end vertices
                start_vertex = Vertex.ByCoordinates(vertices[0][0], vertices[0][1], vertices[0][2])
                end_vertex = Vertex.ByCoordinates(vertices[-1][0], vertices[-1][1], vertices[-1][2])
                
                # Create edge
                edge = Edge.ByStartVertexEndVertex(start_vertex, end_vertex)
                return edge
                
        except Exception as e:
            logger.error(f"Error creating TopologicPy Edge: {str(e)}")
            
        return None 