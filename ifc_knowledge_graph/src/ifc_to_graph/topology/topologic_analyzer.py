"""
Topological Analysis Module

This module provides functionality to analyze topological relationships
between building elements using TopologicPy.
"""

import logging
import os
import tempfile
from typing import Dict, List, Set, Tuple, Optional, Any, Union
import collections

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
    
    def __init__(self, ifc_parser):
        """
        Initialize the TopologicAnalyzer with an IFC parser.
        
        Args:
            ifc_parser: IFC parser instance
        """
        self.ifc_parser = ifc_parser
        self.topologic_entities = {}
        self._adjacency_cache = {}
        self._containment_cache = {}
        self._space_boundaries_cache = None
        self._connectivity_graph_cache = None
        
        # Configure logging for more detailed output during testing
        self.logger = logging.getLogger(__name__)
        
        # Try to import TopologicPy
        try:
            global Cell, Face, Edge, Wire, Vertex, Dictionary, Cluster
            from topologicpy.Cell import Cell
            from topologicpy.Face import Face
            from topologicpy.Edge import Edge
            from topologicpy.Wire import Wire
            from topologicpy.Vertex import Vertex
            from topologicpy.Dictionary import Dictionary
            from topologicpy.Cluster import Cluster
            
            self._has_topologicpy = True
            self.logger.info("Successfully imported TopologicPy")
        except ImportError as e:
            self._has_topologicpy = False
            self.logger.error(f"Failed to import TopologicPy: {str(e)}")
        
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
        if not self._has_topologicpy:
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
            # Skip elements without representation
            if not hasattr(ifc_element, "Representation") or not ifc_element.Representation:
                logger.debug(f"Skipping element {ifc_element.GlobalId} - no representation")
                return None
                
            # Use IfcOpenShell's geometry settings
            settings = ifcopenshell.geom.settings()
            settings.set(settings.USE_WORLD_COORDS, True)
            
            # Try to use SEW_SHELLS setting if available in this version of IfcOpenShell
            try:
                settings.set(settings.SEW_SHELLS, True)
            except AttributeError:
                logger.warning("SEW_SHELLS setting not available in this version of IfcOpenShell, continuing without it")
                
            settings.set(settings.APPLY_DEFAULT_MATERIALS, True)
            
            try:
                # Create the shape from the IFC element
                shape = ifcopenshell.geom.create_shape(settings, ifc_element)
                
                if not shape:
                    logger.debug(f"Failed to create shape for {ifc_element.GlobalId}")
                    return None
                    
                # Get geometry data from the shape
                verts = shape.geometry.verts
                faces = shape.geometry.faces
                
                if len(verts) == 0 or len(faces) == 0:
                    logger.debug(f"Element {ifc_element.GlobalId} has empty geometry")
                    return None
                
                # Reshape vertices into triplets (x, y, z)
                vertices = np.array(verts).reshape(-1, 3)
                
                logger.debug(f"Processing element {ifc_element.GlobalId} of type {ifc_element.is_a()} with {len(vertices)} vertices and {len(faces)} face indices")
                
                # Process faces to create a topologic entity
                topologic_entity = None
                
                if ifc_element.is_a("IfcSpace"):
                    # Create a Cell for spaces
                    topologic_entity = self._create_topologic_cell(vertices, faces, ifc_element)
                    if not topologic_entity:
                        logger.debug(f"Failed to create Cell for space {ifc_element.GlobalId}, trying Face")
                        topologic_entity = self._create_topologic_face(vertices, faces, ifc_element)
                    
                elif ifc_element.is_a("IfcWall") or ifc_element.is_a("IfcSlab") or ifc_element.is_a("IfcRoof"):
                    # Create a Cell for walls, slabs, and roofs (they're 3D elements)
                    topologic_entity = self._create_topologic_cell(vertices, faces, ifc_element)
                    if not topologic_entity:
                        logger.debug(f"Failed to create Cell for {ifc_element.is_a()} {ifc_element.GlobalId}, trying Face")
                        topologic_entity = self._create_topologic_face(vertices, faces, ifc_element)
                    
                elif ifc_element.is_a("IfcBeam") or ifc_element.is_a("IfcColumn") or ifc_element.is_a("IfcMember"):
                    # Try Cell first, then Edge for beams, columns, and members
                    topologic_entity = self._create_topologic_cell(vertices, faces, ifc_element)
                    if not topologic_entity:
                        logger.debug(f"Failed to create Cell for {ifc_element.is_a()} {ifc_element.GlobalId}, trying Edge")
                        topologic_entity = self._create_topologic_edge(vertices, faces, ifc_element)
                    
                elif ifc_element.is_a("IfcDoor") or ifc_element.is_a("IfcWindow"):
                    # Create a Cell for doors and windows (they're 3D elements)
                    topologic_entity = self._create_topologic_cell(vertices, faces, ifc_element)
                    if not topologic_entity:
                        logger.debug(f"Failed to create Cell for {ifc_element.is_a()} {ifc_element.GlobalId}, trying Face")
                        topologic_entity = self._create_topologic_face(vertices, faces, ifc_element)
                    
                else:
                    # Default: try to create a Cell for 3D elements
                    topologic_entity = self._create_topologic_cell(vertices, faces, ifc_element)
                    
                    # Fallback to Face if Cell creation fails
                    if topologic_entity is None:
                        logger.debug(f"Failed to create Cell for {ifc_element.is_a()} {ifc_element.GlobalId}, trying Face")
                        topologic_entity = self._create_topologic_face(vertices, faces, ifc_element)
                
                # Store in cache if successful
                if topologic_entity and hasattr(ifc_element, "GlobalId"):
                    try:
                        # Add dictionary with IFC data to the topologic entity
                        # Create a dictionary object first with the key-value pairs
                        dict_keys = ["GlobalId", "IFCType"]
                        dict_values = [ifc_element.GlobalId, ifc_element.is_a()]
                        
                        # Fix: First verify if topologic_entity is a list or a single object
                        if isinstance(topologic_entity, list):
                            # For lists (like clusters), use the first item
                            if len(topologic_entity) > 0:
                                entity_to_use = topologic_entity[0]
                                try:
                                    # Try with dictionary as parameter
                                    dictionary = Dictionary.ByKeysValues(dict_keys, dict_values)
                                    entity_to_use.SetDictionary(dictionary)
                                except (AttributeError, TypeError):
                                    # Fallback to older API if needed
                                    Dictionary.ByKeysValues(entity_to_use, dict_keys, dict_values)
                        else:
                            # For single entities
                            try:
                                # Try with dictionary as parameter first (newer API)
                                dictionary = Dictionary.ByKeysValues(dict_keys, dict_values)
                                topologic_entity.SetDictionary(dictionary)
                            except (AttributeError, TypeError):
                                # Fallback to older API
                                Dictionary.ByKeysValues(topologic_entity, dict_keys, dict_values)
                        
                        logger.debug(f"Successfully converted {ifc_element.is_a()} {ifc_element.GlobalId} to Topologic entity")
                        self.topologic_entities[ifc_element.GlobalId] = topologic_entity
                    except Exception as dict_error:
                        logger.error(f"Error adding dictionary to topologic entity: {str(dict_error)}")
                else:
                    logger.warning(f"Failed to convert {ifc_element.is_a()} {ifc_element.GlobalId} to any Topologic entity")
                    
                return topologic_entity
                
            except RuntimeError as shape_error:
                # This is a common error when IfcOpenShell can't create a valid shape
                logger.warning(f"RuntimeError creating shape for {ifc_element.GlobalId}: {str(shape_error)}")
                return None
                
        except Exception as e:
            logger.error(f"Error converting {ifc_element.is_a()} {ifc_element.GlobalId} to TopologicPy entity: {str(e)}")
            
        return None
    
    def _create_topologic_cell(self, vertices: np.ndarray, faces: List[int], ifc_element: Any, max_retries: int = 3) -> Optional[Any]:
        """
        Create a TopologicPy Cell from IFC geometry data with improved error handling.
        
        Args:
            vertices: Array of vertex coordinates
            faces: List of face indices
            ifc_element: Original IFC element
            max_retries: Maximum number of retries with increasing tolerance (default: 3)
            
        Returns:
            TopologicPy Cell if successful, None otherwise
        """
        try:
            # Using increasing tolerance for multiple attempts
            for retry in range(max_retries):
                current_tolerance = 0.001 * (1 + retry)
                
                try:
                    # Create faces using the _create_topologic_face method
                    # This approach treats each face individually for better error handling
                    all_faces = []
                    
                    # Since we're breaking the face indices down differently, we'll process them in batches
                    # We first collect groups of face indices - this is based on how the IFC geometry is structured
                    face_groups = []
                    
                    # Group the faces, assuming the first number in each group is the face count
                    i = 0
                    while i < len(faces):
                        # Get the number of vertices in this face
                        try:
                            num_vertices = faces[i]
                            i += 1
                            
                            # Check if we have enough data left
                            if i + num_vertices <= len(faces):
                                face_indices = faces[i:i+num_vertices]
                                face_groups.append(face_indices)
                                i += num_vertices
                            else:
                                logger.warning(f"Face index out of range: i={i}, num_vertices={num_vertices}, len(faces)={len(faces)}")
                                break
                        except IndexError:
                            logger.warning(f"Index error while grouping faces at index {i}")
                            break
                    
                    # Process each face group to create faces
                    for face_indices in face_groups:
                        try:
                            # Create a wire for this face
                            wire_vertices = []
                            
                            # Check all indices are in range
                            if max(face_indices) >= len(vertices):
                                logger.warning(f"Invalid vertex index in face: max index={max(face_indices)}, len(vertices)={len(vertices)}")
                                continue
                    
                            # Get vertices for the face
                            for idx in face_indices:
                                wire_vertices.append(vertices[idx])
                                
                            # Create a topologic face from these vertices
                            # Force closing of the wire if needed
                            if not np.array_equal(wire_vertices[0], wire_vertices[-1]):
                                wire_vertices.append(wire_vertices[0])
                                
                            # Convert to Topologic vertices
                            topologic_vertices = []
                            for v in wire_vertices:
                                vertex = Vertex.ByCoordinates(float(v[0]), float(v[1]), float(v[2]))
                                topologic_vertices.append(vertex)
                                
                            # Create wire with explicit closure
                            try:
                                wire = Wire.ByVertices(topologic_vertices, close=True)
                            except Exception as wire_error:
                                logger.debug(f"Wire creation failed for face, trying alternative method: {str(wire_error)}")
                                
                                # Try alternative method - create edges and then wire
                                edges = []
                                for j in range(len(topologic_vertices) - 1):
                                    edge = Edge.ByStartVertexEndVertex(topologic_vertices[j], topologic_vertices[j+1])
                                    edges.append(edge)
                                    
                                # Create closing edge if needed
                                if not np.array_equal(wire_vertices[0], wire_vertices[-1]):
                                    edge = Edge.ByStartVertexEndVertex(topologic_vertices[-1], topologic_vertices[0])
                                    edges.append(edge)
                                    
                                wire = Wire.ByEdges(edges)
                            
                            # Check if wire is closed before creating face
                            if not wire.IsClosed():
                                logger.debug(f"Wire not closed for face in {ifc_element.GlobalId}, skipping")
                                continue
                                
                            # Create face from wire
                            face = Face.ByWire(wire)
                            
                            if face:
                                all_faces.append(face)
                            
                        except Exception as face_error:
                            logger.debug(f"Error creating face: {str(face_error)}")
                            continue
                    
                    # Check if we have enough faces to create a cell
                    if len(all_faces) < 4:  # A cell needs at least 4 faces (tetrahedron)
                        logger.debug(f"Not enough valid faces ({len(all_faces)}) to create a cell for {ifc_element.GlobalId}")
                        if retry < max_retries - 1:
                            logger.debug(f"Retrying with increased tolerance {current_tolerance}")
                            continue
                        return None
                    
                    # Try to create a cell from faces
                    try:
                        cell = Cell.ByFaces(all_faces, current_tolerance)
                        if cell:
                            logger.debug(f"Successfully created Cell with {len(all_faces)} faces for {ifc_element.GlobalId}")
                            return cell
                    except Exception as cell_error:
                        logger.debug(f"Error creating cell on attempt {retry+1}: {str(cell_error)}")
                        if retry < max_retries - 1:
                            continue
                        else:
                            logger.warning(f"Failed to create Cell from faces: {str(cell_error)}")
                            return None
                
                except Exception as attempt_error:
                    logger.debug(f"Error during attempt {retry+1}: {str(attempt_error)}")
                    if retry < max_retries - 1:
                        continue
                    raise
            
            logger.warning(f"Failed to create cell after {max_retries} attempts for {ifc_element.GlobalId}")
            return None
        
        except Exception as e:
            logger.error(f"Error in _create_topologic_cell for {ifc_element.GlobalId}: {str(e)}")
            return None
    
    def _create_topologic_face(self, vertices: np.ndarray, faces: List[int], ifc_element: Any, max_retries: int = 3, tolerance: float = 0.001) -> Optional[Any]:
        """
        Create a TopologicPy Face from IFC geometry data with improved error handling.
        
        Args:
            vertices: Array of vertex coordinates
            faces: List of face indices
            ifc_element: Original IFC element
            max_retries: Maximum number of retries with increasing tolerance (default: 3)
            tolerance: Initial tolerance value for geometry operations (default: 0.001)
            
        Returns:
            TopologicPy Face if successful, None otherwise
        """
        try:
            # Check if we have enough data
            if len(vertices) == 0 or len(faces) == 0:
                logger.debug(f"Element {ifc_element.GlobalId} has empty face geometry")
                return None
                
            # Try with increasing tolerance if needed
            for retry in range(max_retries):
                current_tolerance = tolerance * (1 + retry)
                
                try:
                    # Convert the indices to a list of vertices for the face
                    face_indices = faces
                    if len(face_indices) < 3:
                        logger.debug(f"Face for {ifc_element.GlobalId} has fewer than 3 vertices")
                        return None
                        
                    # Create a wire from the vertices
                    face_vertices = []
                    for i in range(len(face_indices)):
                        if i >= len(vertices):
                            logger.warning(f"Face index out of range: i={i}, num_vertices={len(vertices)}, len(faces)={len(faces)}")
                            return None
                            
                        vertex_index = face_indices[i]
                        if vertex_index >= len(vertices):
                            logger.warning(f"Vertex index out of range: index={vertex_index}, len(vertices)={len(vertices)}")
                            return None
                            
                        face_vertices.append(vertices[vertex_index])
                    
                    # Add the first vertex to the end to ensure the wire is closed
                    if len(face_vertices) > 0 and not np.array_equal(face_vertices[0], face_vertices[-1]):
                        face_vertices.append(face_vertices[0])
                    
                    # Create vertices
                    topologic_vertices = []
                    for v in face_vertices:
                        topologic_vertex = Vertex.ByCoordinates(float(v[0]), float(v[1]), float(v[2]))
                        topologic_vertices.append(topologic_vertex)
                    
                    # Create wire - with explicit closure check
                    try:
                        # First try regular creation
                        wire = Wire.ByVertices(topologic_vertices, close=True)
                    except Exception as wire_error:
                        logger.debug(f"Wire creation failed, trying alternative approach: {str(wire_error)}")
                        # Try an alternative approach - create separate edges and then a wire
                        edges = []
                        for i in range(len(topologic_vertices) - 1):
                            edge = Edge.ByStartVertexEndVertex(topologic_vertices[i], topologic_vertices[i+1])
                            edges.append(edge)
                        # Add closing edge if needed
                        if not np.array_equal(face_vertices[0], face_vertices[-1]):
                            edge = Edge.ByStartVertexEndVertex(topologic_vertices[-1], topologic_vertices[0])
                            edges.append(edge)
                        wire = Wire.ByEdges(edges)
                    
                    # Check if wire is closed
                    if not wire.IsClosed():
                        if retry < max_retries - 1:
                            logger.debug(f"Wire not closed, retrying with increased tolerance {current_tolerance}")
                            continue
                        else:
                            logger.warning(f"Wire not closed after {max_retries} attempts for {ifc_element.GlobalId}")
                            return None
                    
                    # Create face
                    face = Face.ByWire(wire)
                    
                    if face:
                        return face
                    else:
                        logger.debug(f"Face.ByWire returned None for {ifc_element.GlobalId}")
                        if retry < max_retries - 1:
                            continue
                        return None
                        
                except Exception as e:
                    logger.debug(f"Error creating face on attempt {retry+1}: {str(e)}")
                    if retry < max_retries - 1:
                        continue
                    raise
            
            logger.warning(f"Failed to create face after {max_retries} attempts for {ifc_element.GlobalId}")
            return None
            
        except Exception as e:
            logger.error(f"Error in _create_topologic_face for {ifc_element.GlobalId}: {str(e)}")
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
            # Check if we have enough data
            if len(vertices) < 2:  # Minimum for an edge
                logger.debug(f"Not enough vertices for Edge: {len(vertices)} vertices")
                return None
            
            # Create topologic vertices
            topologic_vertices = []
            for vertex in vertices:
                topologic_vertex = Vertex.ByCoordinates(vertex[0], vertex[1], vertex[2])
                topologic_vertices.append(topologic_vertex)
            
            # For linear elements, we can try to create an edge from the first two vertices
            if len(topologic_vertices) >= 2:
                try:
                    # Create an edge between first and last vertex to ensure largest span
                    edge = Edge.ByStartVertexEndVertex(
                        topologic_vertices[0], 
                        topologic_vertices[-1]
                    )
                    if edge:
                        logger.debug(f"Created Edge from first to last vertex")
                        return edge
                except Exception as edge_error:
                    logger.warning(f"Error creating edge from first to last vertex: {str(edge_error)}")
            
            # If we couldn't create an edge from first to last, try all pairs
            # This might be needed for elements with multiple disconnected edges
            edges = []
            for i in range(len(topologic_vertices) - 1):
                try:
                    edge = Edge.ByStartVertexEndVertex(
                        topologic_vertices[i],
                        topologic_vertices[i+1]
                    )
                    if edge:
                        edges.append(edge)
                except Exception:
                    pass
            
            if edges:
                # If we have multiple edges, create a cluster of edges
                if len(edges) > 1:
                    try:
                        cluster = Cluster.ByTopologies(edges)
                        logger.debug(f"Created Cluster of {len(edges)} edges")
                        return cluster
                    except Exception as cluster_error:
                        logger.warning(f"Error creating cluster: {str(cluster_error)}")
                
                # If we couldn't create a cluster or only have one edge, return the first edge
                logger.debug(f"Created a single Edge")
                return edges[0]
            
            # Try to use geometry faces to create a wire if available
            if len(faces) > 0:
                try:
                    i = 0
                    while i < len(faces):
                        # Get number of vertices in this face
                        num_vertices = faces[i]
                        i += 1
                        
                        # Check if we have enough data
                        if i + num_vertices > len(faces):
                            break
                        
                        # Get the indices for this face
                        face_indices = faces[i:i+num_vertices]
                        i += num_vertices
                        
                        # Create wire from the face
                        if len(face_indices) >= 2:
                            wire_vertices = []
                            
                            # Use only perimeter vertices
                            for idx in face_indices:
                                if idx < len(topologic_vertices):
                                    wire_vertices.append(topologic_vertices[idx])
                            
                            if len(wire_vertices) >= 2:
                                # Try to create a wire
                                wire = Wire.ByVertices(wire_vertices)
                                if wire:
                                    edges = wire.Edges()
                                    if edges and len(edges) > 0:
                                        logger.debug(f"Created Edge from Wire with {len(edges)} edges")
                                        return edges[0]  # Return the first edge
                except Exception as wire_error:
                    logger.warning(f"Error creating Edge from Wire: {str(wire_error)}")
            
            logger.debug("Could not create any valid Edge from geometry")
            
        except Exception as e:
            logger.error(f"Error creating TopologicPy Edge: {str(e)}")
            
        return None
    
    def get_adjacency_relationships(self, tolerance: float = 0.001) -> Dict[str, List[str]]:
        """
        Extract adjacency relationships between topological entities.
        
        Adjacency is defined as two elements sharing a face or edge.
        
        Args:
            tolerance: Tolerance for adjacency detection (distance in model units)
            
        Returns:
            Dictionary mapping GlobalIds to lists of adjacent GlobalIds
        """
        self._check_topologicpy()
        self._check_parser()
        
        # Return cached result if available
        if self._adjacency_cache and tolerance in self._adjacency_cache:
            return self._adjacency_cache[tolerance]
            
        adjacency_map = {}
        
        try:
            # Get all IFC elements from the parser - use robust method to get file
            ifc_model = self._get_ifc_model()
            all_elements = ifc_model.by_type("IfcElement")
            
            logger.info(f"Processing {len(all_elements)} elements for adjacency relationships")
            
            # Ensure all elements are converted to topologic entities
            for element in all_elements:
                if hasattr(element, "GlobalId") and element.GlobalId not in self.topologic_entities:
                    self.convert_ifc_to_topologic(element)
            
            # Get all GlobalIds that were successfully converted
            global_ids = list(self.topologic_entities.keys())
            logger.info(f"Found {len(global_ids)} successfully converted elements")
            
            # Create a list of entities with their GlobalIds
            entities_with_ids = [(gid, self.topologic_entities[gid]) for gid in global_ids]
            
            # Initialize adjacency map for all elements
            for gid in global_ids:
                adjacency_map[gid] = []
            
            # Fallback to IFC-based adjacency if very few entities have been converted
            if len(entities_with_ids) < 10:
                logger.warning("Few topologic entities available, using IFC-based adjacency")
                
                # Look at all walls and connected elements
                for element in all_elements:
                    if not hasattr(element, "GlobalId"):
                        continue
                    
                    # Consider elements that are likely to be adjacent
                    # Most common adjacency: Walls to other walls
                    if element.is_a("IfcWall") or element.is_a("IfcWallStandardCase"):
                        # Find other walls that might be connected
                        for other in all_elements:
                            if not hasattr(other, "GlobalId") or element.GlobalId == other.GlobalId:
                                continue
                                
                            if (other.is_a("IfcWall") or other.is_a("IfcWallStandardCase")):
                                # Walls sharing the same space boundary are adjacent
                                in_same_space = self._elements_share_space(element, other)
                                if in_same_space:
                                    if (element.GlobalId in adjacency_map and 
                                        other.GlobalId not in adjacency_map[element.GlobalId]):
                                        adjacency_map[element.GlobalId].append(other.GlobalId)
                                        
                                    if (other.GlobalId in adjacency_map and 
                                        element.GlobalId not in adjacency_map[other.GlobalId]):
                                        adjacency_map[other.GlobalId].append(element.GlobalId)
                                        
            else:
                # Use topologic entities for adjacency detection
                logger.info(f"Checking {len(entities_with_ids)} pairs of elements for adjacency")
                
                # Counter for logging
                checked_pairs = 0
                adjacent_found = 0
                
                # Check pairs of elements for adjacency
                for i in range(len(entities_with_ids)):
                    gid1, entity1 = entities_with_ids[i]
                    
                    for j in range(i+1, len(entities_with_ids)):
                        gid2, entity2 = entities_with_ids[j]
                        
                        checked_pairs += 1
                        if checked_pairs % 1000 == 0:
                            logger.info(f"Checked {checked_pairs} pairs, found {adjacent_found} adjacencies")
                        
                        # Skip if same element
                        if gid1 == gid2:
                            continue
                        
                        # Check adjacency based on topology type
                        is_adjacent = False
                        
                        # Handle the case where entity1 or entity2 is a list
                        entity1_list = [entity1] if not isinstance(entity1, list) else entity1
                        entity2_list = [entity2] if not isinstance(entity2, list) else entity2
                        
                        # Check each combination
                        for entity1_item in entity1_list:
                            if is_adjacent:
                                break
                                
                            for entity2_item in entity2_list:
                                try:
                                    if isinstance(entity1_item, Cell) and isinstance(entity2_item, Cell):
                                        # Two cells are adjacent if they share a face
                                        shared_faces = Topology.SharedFaces(entity1_item, entity2_item, tolerance)
                                        is_adjacent = shared_faces and len(shared_faces) > 0
                                        
                                    elif isinstance(entity1_item, Cell) and isinstance(entity2_item, Face):
                                        # A cell and face are adjacent if the face bounds the cell
                                        faces = Topology.Faces(entity1_item)
                                        for face in faces:
                                            if Topology.IsSame(face, entity2_item, tolerance):
                                                is_adjacent = True
                                                break
                                                
                                    elif isinstance(entity1_item, Face) and isinstance(entity2_item, Cell):
                                        # A face and cell are adjacent if the face bounds the cell
                                        faces = Topology.Faces(entity2_item)
                                        for face in faces:
                                            if Topology.IsSame(face, entity1_item, tolerance):
                                                is_adjacent = True
                                                break
                                                
                                    elif isinstance(entity1_item, Face) and isinstance(entity2_item, Face):
                                        # Two faces are adjacent if they share an edge
                                        shared_edges = Topology.SharedEdges(entity1_item, entity2_item, tolerance)
                                        is_adjacent = shared_edges and len(shared_edges) > 0
                                        
                                    elif isinstance(entity1_item, Edge) and isinstance(entity2_item, Edge):
                                        # Two edges are adjacent if they share a vertex
                                        shared_vertices = Topology.SharedVertices(entity1_item, entity2_item, tolerance)
                                        is_adjacent = shared_vertices and len(shared_vertices) > 0
                                        
                                    elif isinstance(entity1_item, Edge) and (isinstance(entity2_item, Face) or isinstance(entity2_item, Cell)):
                                        # An edge and face/cell are adjacent if the edge bounds the face/cell
                                        edges = Topology.Edges(entity2_item)
                                        for edge in edges:
                                            if Topology.IsSame(edge, entity1_item, tolerance):
                                                is_adjacent = True
                                                break
                                                
                                    elif isinstance(entity2_item, Edge) and (isinstance(entity1_item, Face) or isinstance(entity1_item, Cell)):
                                        # A face/cell and edge are adjacent if the edge bounds the face/cell
                                        edges = Topology.Edges(entity1_item)
                                        for edge in edges:
                                            if Topology.IsSame(edge, entity2_item, tolerance):
                                                is_adjacent = True
                                                break
                                                
                                    if is_adjacent:
                                        break
                                        
                                except Exception as adj_err:
                                    logger.debug(f"Error checking adjacency between {gid1} and {gid2}: {str(adj_err)}")
                                    continue
                        
                        # Add to adjacency map if adjacent
                        if is_adjacent:
                            adjacent_found += 1
                            adjacency_map[gid1].append(gid2)
                            adjacency_map[gid2].append(gid1)
                            logger.debug(f"Found adjacency between {gid1} and {gid2}")
                
                # Also check IFC relationships for adjacency (for elements like doors and windows)
                logger.info("Checking IFC relationships for adjacency")
                
                for element in all_elements:
                    if not hasattr(element, "GlobalId"):
                        continue
                        
                    # Doors and windows are adjacent to their containing walls
                    if element.is_a("IfcDoor") or element.is_a("IfcWindow"):
                        # Find the opening element
                        opening = self._get_opening_for_element(element)
                        if opening:
                            # Find the wall containing the opening
                            wall = self._get_element_for_opening(opening)
                            if wall and hasattr(wall, "GlobalId"):
                                # Add adjacency between door/window and wall
                                if (element.GlobalId in adjacency_map and 
                                    wall.GlobalId not in adjacency_map[element.GlobalId]):
                                    adjacency_map[element.GlobalId].append(wall.GlobalId)
                                    
                                if (wall.GlobalId in adjacency_map and 
                                    element.GlobalId not in adjacency_map[wall.GlobalId]):
                                    adjacency_map[wall.GlobalId].append(element.GlobalId)
                                    
                                logger.debug(f"Found IFC adjacency between {element.is_a()} {element.GlobalId} and {wall.is_a()} {wall.GlobalId}")
                
            # Cache the result
            self._adjacency_cache[tolerance] = adjacency_map
            
            # Log statistics
            adjacency_count = sum(len(adjacent_ids) for adjacent_ids in adjacency_map.values())
            logger.info(f"Found {adjacency_count} adjacency relationships between {len(adjacency_map)} elements")
            
        except Exception as e:
            logger.error(f"Error extracting adjacency relationships: {str(e)}")
            
        return adjacency_map
    
    def _elements_share_space(self, element1, element2) -> bool:
        """
        Check if two elements share the same space.
        
        Args:
            element1: First IFC element
            element2: Second IFC element
            
        Returns:
            True if they share at least one space, False otherwise
        """
        # Get spaces for element1
        spaces1 = set()
        for rel in element1.ContainedInStructure if hasattr(element1, "ContainedInStructure") else []:
            if hasattr(rel, "RelatingStructure") and rel.RelatingStructure.is_a("IfcSpace"):
                spaces1.add(rel.RelatingStructure.GlobalId)
                
        # Get spaces for element2
        spaces2 = set()
        for rel in element2.ContainedInStructure if hasattr(element2, "ContainedInStructure") else []:
            if hasattr(rel, "RelatingStructure") and rel.RelatingStructure.is_a("IfcSpace"):
                spaces2.add(rel.RelatingStructure.GlobalId)
                
        # Check if they share at least one space
        return bool(spaces1.intersection(spaces2))
        
    def _get_opening_for_element(self, element):
        """
        Get the opening element for a door or window.
        
        Args:
            element: IFC door or window element
            
        Returns:
            IFC opening element or None
        """
        if hasattr(element, "FillsVoids") and element.FillsVoids:
            for rel in element.FillsVoids:
                if hasattr(rel, "RelatingOpeningElement"):
                    return rel.RelatingOpeningElement
        return None
        
    def _get_element_for_opening(self, opening):
        """
        Get the element containing the opening.
        
        Args:
            opening: IFC opening element
            
        Returns:
            IFC element or None
        """
        if hasattr(opening, "VoidsElements") and opening.VoidsElements:
            for rel in opening.VoidsElements:
                if hasattr(rel, "RelatingBuildingElement"):
                    return rel.RelatingBuildingElement
        return None
    
    def get_containment_relationships(self, tolerance: float = 0.001) -> Dict[str, List[str]]:
        """
        Extract containment relationships between topological entities.
        
        Containment is defined as one element being fully inside another.
        
        Args:
            tolerance: Tolerance for containment detection (distance in model units)
            
        Returns:
            Dictionary mapping GlobalIds to lists of contained GlobalIds
        """
        self._check_topologicpy()
        self._check_parser()
        
        # Return cached result if available
        if self._containment_cache and tolerance in self._containment_cache:
            return self._containment_cache[tolerance]
            
        containment_map = {}
        
        try:
            # Get all IFC elements from the parser - use robust method to get file
            ifc_model = self._get_ifc_model()
            all_elements = ifc_model.by_type("IfcElement")
            
            logger.info(f"Processing {len(all_elements)} elements for containment relationships")
            
            # Ensure all elements are converted to topologic entities
            for element in all_elements:
                if hasattr(element, "GlobalId") and element.GlobalId not in self.topologic_entities:
                    self.convert_ifc_to_topologic(element)
            
            # Get all GlobalIds that were successfully converted
            global_ids = list(self.topologic_entities.keys())
            logger.info(f"Found {len(global_ids)} successfully converted elements")
            
            # Create a list of entities with their GlobalIds
            entities_with_ids = [(gid, self.topologic_entities[gid]) for gid in global_ids]
            
            # Initialize containment map for all elements
            for gid in global_ids:
                containment_map[gid] = []
            
            # Fallback to IFC-based containment if very few entities have been converted
            if len(entities_with_ids) < 10:
                logger.warning("Few topologic entities available, using IFC-based containment")
                
                # Look at all spaces and their contained elements
                for element in all_elements:
                    if not hasattr(element, "GlobalId"):
                        continue
                    
                    # Find spaces that elements are contained in
                    if element.is_a("IfcSpace"):
                        # Find elements contained in this space
                        for rel in element.ContainsElements if hasattr(element, "ContainsElements") else []:
                            if not hasattr(rel, "RelatedElements"):
                                continue
                            
                            for contained in rel.RelatedElements:
                                if not hasattr(contained, "GlobalId"):
                                    continue
                                
                                if contained.GlobalId in global_ids:
                                    containment_map[element.GlobalId].append(contained.GlobalId)
            
            else:
                # Use topologic entities for containment detection
                logger.info(f"Checking {len(entities_with_ids)} pairs of elements for containment")
                
                # Counter for logging
                checked_pairs = 0
                containment_found = 0
                
                # Check pairs of elements for containment
                for i in range(len(entities_with_ids)):
                    gid1, entity1 = entities_with_ids[i]
                    
                    for j in range(i+1, len(entities_with_ids)):
                        gid2, entity2 = entities_with_ids[j]
                        
                        checked_pairs += 1
                        if checked_pairs % 1000 == 0:
                            logger.info(f"Checked {checked_pairs} pairs, found {containment_found} containments")
                        
                        # Skip if same element
                        if gid1 == gid2:
                            continue
                            
                        # Check containment based on topology type
                        is_contained = False
                        
                        # Handle the case where entity1 or entity2 is a list
                        entity1_list = [entity1] if not isinstance(entity1, list) else entity1
                        entity2_list = [entity2] if not isinstance(entity2, list) else entity2
                        
                        # Check each combination
                        for entity1_item in entity1_list:
                            if is_contained:
                                break
                                
                            for entity2_item in entity2_list:
                                try:
                                    if isinstance(entity1_item, Cell) and isinstance(entity2_item, Cell):
                                        # Two cells are contained if entity1 is inside entity2
                                        is_contained = Topology.Contains(entity1_item, entity2_item, tolerance)
                                        
                                    elif isinstance(entity1_item, Cell) and isinstance(entity2_item, Face):
                                        # A cell is contained if it is inside the face
                                        faces = Topology.Faces(entity2_item)
                                        for face in faces:
                                            if Topology.Contains(entity1_item, face, tolerance):
                                                is_contained = True
                                                break
                                                
                                    elif isinstance(entity1_item, Face) and isinstance(entity2_item, Cell):
                                        # A face is contained if it is inside the cell
                                        faces = Topology.Faces(entity1_item)
                                        for face in faces:
                                            if Topology.Contains(face, entity2_item, tolerance):
                                                is_contained = True
                                                break
                                                
                                    elif isinstance(entity1_item, Face) and isinstance(entity2_item, Face):
                                        # Two faces are contained if entity1 is inside entity2
                                        is_contained = Topology.Contains(entity1_item, entity2_item, tolerance)
                                        
                                    elif isinstance(entity1_item, Edge) and isinstance(entity2_item, Edge):
                                        # Two edges are contained if entity1 is inside entity2
                                        is_contained = Topology.Contains(entity1_item, entity2_item, tolerance)
                                        
                                    elif isinstance(entity1_item, Edge) and (isinstance(entity2_item, Face) or isinstance(entity2_item, Cell)):
                                        # An edge is contained if it is inside the face/cell
                                        edges = Topology.Edges(entity2_item)
                                        for edge in edges:
                                            if Topology.Contains(entity1_item, edge, tolerance):
                                                is_contained = True
                                                break
                                                
                                    elif isinstance(entity2_item, Edge) and (isinstance(entity1_item, Face) or isinstance(entity1_item, Cell)):
                                        # A face/cell is contained if it is inside the edge
                                        edges = Topology.Edges(entity1_item)
                                        for edge in edges:
                                            if Topology.Contains(edge, entity2_item, tolerance):
                                                is_contained = True
                                                break
                                                
                                    if is_contained:
                                        break
                                        
                                except Exception as cont_err:
                                    logger.debug(f"Error checking containment between {gid1} and {gid2}: {str(cont_err)}")
                        continue
                        
                        # Add to containment map if contained
                        if is_contained:
                            containment_found += 1
                            containment_map[gid1].append(gid2)
                            logger.debug(f"Found containment between {gid1} and {gid2}")
            
            # Cache the result
            self._containment_cache[tolerance] = containment_map
            
            # Log statistics
            containment_count = sum(len(contained) for contained in containment_map.values())
            logger.info(f"Found {containment_count} containment relationships between {len(containment_map)} elements")
            
        except Exception as e:
            logger.error(f"Error extracting containment relationships: {str(e)}")
            
        return containment_map
        
    def _get_ifc_model(self):
        """
        Get the IFC model from the parser in a robust way that handles different parser implementations.
            
        Returns:
            The IFC model object
        """
        # Try different known attributes and methods to get the IFC model
        if hasattr(self.ifc_parser, 'file'):
            return self.ifc_parser.file
        elif hasattr(self.ifc_parser, 'get_model') and callable(getattr(self.ifc_parser, 'get_model')):
            return self.ifc_parser.get_model()
        elif hasattr(self.ifc_parser, 'ifc_file'):
            return self.ifc_parser.ifc_file
        elif hasattr(self.ifc_parser, 'model'):
            return self.ifc_parser.model
        else:
            # As a fallback, check if the parser itself is the file object or has the necessary methods
            if hasattr(self.ifc_parser, 'by_type') and callable(getattr(self.ifc_parser, 'by_type')):
                return self.ifc_parser
            
            # If we get here, we couldn't find a valid model
            raise ValueError("Could not retrieve IFC model from parser. Please ensure the parser has a 'file', 'ifc_file', or 'model' attribute, or implements 'get_model()' method.")
    
    def get_space_boundaries(self) -> Dict[str, List[str]]:
        """
        Extract space boundary relationships.
        
        Space boundaries are defined as elements (walls, doors, etc.) that bound spaces.
        
        Returns:
            Dictionary mapping space GlobalIds to lists of bounding element GlobalIds
        """
        self._check_parser()
        
        # Return cached result if available
        if self._space_boundaries_cache is not None:
            return self._space_boundaries_cache
            
        space_boundaries = {}
        
        try:
            # Get all spaces from the IFC model - use robust method to get file
            ifc_model = self._get_ifc_model()
            all_spaces = ifc_model.by_type("IfcSpace")
            
            logger.info(f"Found {len(all_spaces)} spaces in the IFC model")
            
            # Process each space
            for space in all_spaces:
                # Skip if GlobalId is missing
                if not hasattr(space, "GlobalId"):
                    continue
                    
                # Initialize space entry if not exists
                if space.GlobalId not in space_boundaries:
                    space_boundaries[space.GlobalId] = []
                
                # Get space boundaries from IFC
                space_boundaries[space.GlobalId].extend(self._get_space_boundaries_from_ifc(space))
            
            # Try to find boundaries topologically if not many were found in IFC relationships
            if self._check_topologic_available() and sum(len(b) for b in space_boundaries.values()) < 10:
                logger.info("Few space boundaries found in IFC data, attempting to detect topologically")
                
                # Get all potential boundary elements
                boundary_elements = []
                for element_type in ["IfcWall", "IfcSlab", "IfcRoof", "IfcDoor", "IfcWindow"]:
                    boundary_elements.extend(ifc_model.by_type(element_type))
                
                # Convert spaces and boundary elements to topologic entities
                for space in all_spaces:
                    if not hasattr(space, "GlobalId"):
                        continue
                        
                    space_entity = self.convert_ifc_to_topologic(space)
                    if not space_entity:
                        continue
                        
                    # Initialize space entry if not exists
                    if space.GlobalId not in space_boundaries:
                        space_boundaries[space.GlobalId] = []
                    
                    # Check each boundary element
                    for element in boundary_elements:
                        if not hasattr(element, "GlobalId"):
                            continue
                            
                        element_entity = self.convert_ifc_to_topologic(element)
                        if not element_entity:
                            continue
                            
                        # Check if the element is adjacent to the space
                        try:
                            # For Cell-Cell detection
                            if isinstance(space_entity, Cell) and isinstance(element_entity, Cell):
                                shared_faces = Topology.SharedFaces(space_entity, element_entity, 0.001)
                                if shared_faces and len(shared_faces) > 0:
                                    if element.GlobalId not in space_boundaries[space.GlobalId]:
                                        space_boundaries[space.GlobalId].append(element.GlobalId)
                            
                            # For Cell-Face detection (most common case)
                            elif isinstance(space_entity, Cell) and isinstance(element_entity, Face):
                                faces = Topology.Faces(space_entity)
                                for face in faces:
                                    if Topology.IsSame(face, element_entity, 0.001):
                                        if element.GlobalId not in space_boundaries[space.GlobalId]:
                                            space_boundaries[space.GlobalId].append(element.GlobalId)
                                        break
                        except Exception as e:
                            logger.warning(f"Error checking topological space boundary: {str(e)}")
        
            # Cache the result
            self._space_boundaries_cache = space_boundaries
            
        except Exception as e:
            logger.error(f"Error extracting space boundary relationships: {str(e)}")
            
        return space_boundaries
    
    def _check_topologic_available(self) -> bool:
        """
        Check if TopologicPy is available without raising an exception.
        
        Returns:
            True if TopologicPy is available, False otherwise
        """
        return self._has_topologicpy
    
    def get_connectivity_graph(self) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        Generate a comprehensive connectivity graph of the building model.
        
        This includes adjacency, containment, and space boundary relationships.
        
        Returns:
            Dictionary with "nodes" and "edges" keys for representing the building connectivity network
        """
        self._check_parser()
        
        # Return cached result if available
        if self._connectivity_graph_cache:
            return self._connectivity_graph_cache
        
        # Initialize the connectivity graph
        connectivity_graph = {
            "nodes": {},
            "edges": []
        }
        
        try:
            # Get all elements from the IFC model
            ifc_model = self._get_ifc_model()
            all_elements = []
            
            # Get elements by type
            for element_type in ["IfcWall", "IfcSlab", "IfcBeam", "IfcColumn", "IfcDoor", 
                                "IfcWindow", "IfcRoof", "IfcSpace", "IfcBuildingStorey"]:
                all_elements.extend(ifc_model.by_type(element_type))
            
            # Add nodes to the graph (all IFC elements)
            for element in all_elements:
                if not hasattr(element, "GlobalId"):
                    continue
                    
                entity_id = element.GlobalId
                entity_type = element.is_a()
                
                # Get basic properties
                properties = {
                    "type": entity_type,
                    "GlobalId": entity_id
                }
                
                # Add name if available
                if hasattr(element, "Name") and element.Name:
                    properties["Name"] = element.Name
                
                # Add the node
                connectivity_graph["nodes"][entity_id] = properties
            
            # Add relationships
            # 1. Adjacency relationships
            adjacency_map = self.get_adjacency_relationships()
            for source_id, target_ids in adjacency_map.items():
                for target_id in target_ids:
                    if source_id in connectivity_graph["nodes"] and target_id in connectivity_graph["nodes"]:
                        edge = {
                            "source": source_id,
                            "target": target_id,
                            "type": "ADJACENT_TO",
                            "properties": {
                                "relationshipType": "adjacency",
                                "relationshipSource": "topologicalAnalysis"
                            }
                        }
                        connectivity_graph["edges"].append(edge)
            
            # 2. Containment relationships
            containment_map = self.get_containment_relationships()
            for container_id, contained_ids in containment_map.items():
                for contained_id in contained_ids:
                    if container_id in connectivity_graph["nodes"] and contained_id in connectivity_graph["nodes"]:
                        # Container to contained
                        edge = {
                            "source": container_id,
                            "target": contained_id,
                            "type": "CONTAINS",
                            "properties": {
                                "relationshipType": "containment",
                                "relationshipSource": "topologicalAnalysis"
                            }
                        }
                        connectivity_graph["edges"].append(edge)
                        
                        # Contained to container (inverse)
                        edge = {
                            "source": contained_id,
                            "target": container_id,
                            "type": "CONTAINED_BY",
                            "properties": {
                                "relationshipType": "containment",
                                "relationshipSource": "topologicalAnalysis"
                            }
                        }
                        connectivity_graph["edges"].append(edge)
            
            # 3. Space boundary relationships
            boundary_map = self.get_space_boundaries()
            for space_id, boundary_ids in boundary_map.items():
                for boundary_id in boundary_ids:
                    if space_id in connectivity_graph["nodes"] and boundary_id in connectivity_graph["nodes"]:
                        # Space to boundary
                        edge = {
                            "source": space_id,
                            "target": boundary_id,
                            "type": "IS_BOUNDED_BY",
                            "properties": {
                                "relationshipType": "spaceBoundary",
                                "boundaryType": "physical", 
                                "relationshipSource": "topologicalAnalysis"
                            }
                        }
                        connectivity_graph["edges"].append(edge)
                        
                        # Boundary to space (inverse)
                        edge = {
                            "source": boundary_id,
                            "target": space_id,
                            "type": "BOUNDS",
                            "properties": {
                                "relationshipType": "spaceBoundary",
                                "boundaryType": "physical",
                                "relationshipSource": "topologicalAnalysis"
                            }
                        }
                        connectivity_graph["edges"].append(edge)
            
            # Cache the result
            self._connectivity_graph_cache = connectivity_graph
            
            # Log statistics
            logger.info(f"Created connectivity graph with {len(connectivity_graph['nodes'])} nodes and {len(connectivity_graph['edges'])} edges")
            
        except Exception as e:
            logger.error(f"Error creating connectivity graph: {str(e)}")
            
        return connectivity_graph
    
    def find_path(
        self, 
        start_id: str, 
        end_id: str,
        relationship_types: List[str] = None,
        max_depth: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find a path between two elements in the building model.
        
        Args:
            start_id: GlobalId of the start element
            end_id: GlobalId of the end element
            relationship_types: List of relationship types to consider
                                (default: ADJACENT_TO, CONTAINS, CONTAINED_BY)
            max_depth: Maximum search depth
            
        Returns:
            List of elements in the path, or empty list if no path was found
        """
        # Get the connectivity graph
        graph = self.get_connectivity_graph()
        
        # Check if both start and end elements exist in the graph
        if (start_id not in graph["nodes"] or end_id not in graph["nodes"]):
            logger.warning(f"Start or end element not found in graph: {start_id}, {end_id}")
            return []
            
        # Default relationship types if not provided
        if not relationship_types:
            relationship_types = ["ADJACENT_TO", "CONTAINS", "CONTAINED_BY", "IS_BOUNDED_BY", "BOUNDS"]
            
        # Build an adjacency list from the connectivity graph for BFS
        adjacency_list = {}
        
        # Initialize adjacency list for all nodes
        for node_id in graph["nodes"]:
            adjacency_list[node_id] = []
        
        # Add connections based on edges with matching relationship types
        for edge in graph["edges"]:
            if edge["type"] in relationship_types:
                source_id = edge["source"]
                target_id = edge["target"]
                
                # Add connection with relationship info
                if source_id in adjacency_list:
                    adjacency_list[source_id].append({
                        "id": target_id,
                        "relationship": edge["type"],
                        "properties": edge.get("properties", {})
                    })
        
        # Breadth-first search to find the shortest path
        visited = {start_id: None}  # Maps node to its predecessor in the path
        queue = [(start_id, 0)]  # (node_id, depth)
        
        while queue:
            current_id, depth = queue.pop(0)
            
            # Check depth limit
            if depth >= max_depth:
                break
                
            # Check if we reached the target
            if current_id == end_id:
                break
                
            # Explore neighbors
            for neighbor in adjacency_list[current_id]:
                neighbor_id = neighbor["id"]
                
                if neighbor_id not in visited:
                    visited[neighbor_id] = (current_id, neighbor["relationship"])
                    queue.append((neighbor_id, depth + 1))
        
        # If end node was not reached, no path exists
        if end_id not in visited:
            return []
            
        # Reconstruct the path
        path = []
        current_id = end_id
        
        while current_id != start_id:
            # Get node data
            node_data = graph["nodes"][current_id].copy()
            
            # Add the id to the data
            node_data["id"] = current_id
            
            # Get the relationship from the predecessor
            predecessor_info = visited[current_id]
            if predecessor_info:
                predecessor_id, relationship = predecessor_info
                node_data["relationship_from_previous"] = relationship
            
            # Add to path (in reverse order)
            path.append(node_data)
            
            # Move to predecessor
            current_id = predecessor_info[0]
        
        # Add the start node
        start_node_data = graph["nodes"][start_id].copy()
        start_node_data["id"] = start_id
        path.append(start_node_data)
        
        # Reverse to get path from start to end
        path.reverse()
        
        return path
    
    def analyze_building_topology(self) -> Dict[str, Any]:
        """
        High-level method to analyze all topological relationships in the building.
        
        Returns:
            Dictionary containing all topological analysis results
        """
        self._check_parser()
        
        results = {}
        
        try:
            # Get the IFC model - use robust method to get file
            ifc_model = self._get_ifc_model()
        
            # Extract adjacency relationships
            try:
                adjacency_map = self.get_adjacency_relationships()
                results["adjacency"] = adjacency_map
            except Exception as e:
                logger.error(f"Error extracting adjacency relationships: {str(e)}")
        
            # Extract containment relationships
            try:
                containment_map = self.get_containment_relationships()
                results["containment"] = containment_map
            except Exception as e:
                logger.error(f"Error extracting containment relationships: {str(e)}")
            
            # Extract space boundary relationships
            try:
                space_boundaries = self.get_space_boundaries()
                results["space_boundaries"] = space_boundaries
            except Exception as e:
                logger.error(f"Error extracting space boundary relationships: {str(e)}")
            
            # Generate connectivity graph
            try:
                connectivity_graph = self.get_connectivity_graph()
                results["connectivity"] = connectivity_graph
            except Exception as e:
                logger.error(f"Error generating connectivity graph: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error analyzing building topology: {str(e)}")
        
        return results

    def _get_space_boundaries_from_ifc(self, space) -> List[str]:
        """
        Get space boundaries from IFC relationships.
        
        Args:
            space: The IFC space element
        
        Returns:
            List of GlobalIds of boundary elements
        """
        boundary_ids = []
        
        try:
            # Get space boundary relationships
            ifc_model = self._get_ifc_model()
            all_space_boundaries = ifc_model.by_type("IfcRelSpaceBoundary")
            
            # Filter relationships for this space
            for rel in all_space_boundaries:
                # Check if this relationship relates to the given space
                if not hasattr(rel, "RelatingSpace") or rel.RelatingSpace is None:
                    continue
                    
                if rel.RelatingSpace.GlobalId != space.GlobalId:
                    continue
                    
                # Get the related building element
                if not hasattr(rel, "RelatedBuildingElement") or rel.RelatedBuildingElement is None:
                    continue
                    
                element = rel.RelatedBuildingElement
                if not hasattr(element, "GlobalId"):
                    continue
                    
                # Add to boundary list if not already there
                if element.GlobalId not in boundary_ids:
                    boundary_ids.append(element.GlobalId)
                    
        except Exception as e:
            logger.error(f"Error getting space boundaries from IFC: {str(e)}")
            
        return boundary_ids 

    def _get_topologic_entities(self) -> List[Dict[str, Any]]:
        """
        Get all topologic entities with their metadata.
        
        Returns:
            List of dictionaries containing entity data:
            - id: GlobalId
            - topology: TopologicPy entity
            - type: IFC type
            - properties: Dictionary of properties
        """
        self._check_parser()
        
        entities = []
        
        try:
            # Get all IFC elements from the parser
            ifc_model = self._get_ifc_model()
            all_elements = ifc_model.by_type("IfcElement")
            spaces = ifc_model.by_type("IfcSpace")
            
            # Combine elements and spaces
            all_elements.extend(spaces)
            
            # Ensure all elements are converted to topologic entities
            for element in all_elements:
                if not hasattr(element, "GlobalId"):
                    continue
                    
                element_id = element.GlobalId
                
                # Convert to topologic entity if not already converted
                if element_id not in self.topologic_entities:
                    self.convert_ifc_to_topologic(element)
                
                # Add to entities list if conversion was successful
                if element_id in self.topologic_entities:
                    entity_type = element.is_a()
                    
                    # Get basic properties
                    properties = {
                        "GlobalId": element_id,
                        "IFCType": entity_type
                    }
                    
                    # Add name if available
                    if hasattr(element, "Name") and element.Name:
                        properties["Name"] = element.Name
                    
                    entities.append({
                        "id": element_id,
                        "topology": self.topologic_entities[element_id],
                        "type": entity_type,
                        "properties": properties
                    })
            
            logger.info(f"Found {len(entities)} topologic entities")
            
        except Exception as e:
            logger.error(f"Error getting topologic entities: {str(e)}")
            
        return entities 

    def analyze_elements(self, elements_dict: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Analyze the topology of the given elements and extract spatial relationships.
        
        Args:
            elements_dict: Dictionary of elements to analyze, keyed by GlobalId
            
        Returns:
            List of relationship dictionaries in format:
            {'source_id': str, 'target_id': str, 'relationship_type': str}
        """
        logger.info(f"Analyzing topology of {len(elements_dict)} elements")
        
        if not self._has_topologicpy:
            logger.error("TopologicPy is not available for analysis")
            return []
            
        relationships = []
        
        try:
            # Setup the parser if not already done
            if not hasattr(self, "ifc_parser") or self.ifc_parser is None:
                logger.info(f"Setting up IFC parser from file path: {self.ifc_file_path}")
                self.ifc_parser = ifcopenshell.open(self.ifc_file_path)
                
            # Convert all elements to topological entities
            logger.info("Converting elements to topological entities...")
            for global_id, element in elements_dict.items():
                if global_id not in self.topologic_entities:
                    logger.debug(f"Converting element {global_id} to topological entity")
                    self.convert_ifc_to_topologic(element)
            
            # 1. Extract adjacency relationships
            logger.info("Extracting adjacency relationships...")
            adjacency_map = self.get_adjacency_relationships()
            
            adjacency_count = 0
            for source_id, targets in adjacency_map.items():
                for target_id in targets:
                    # Only include relationships between the provided elements
                    if source_id in elements_dict and target_id in elements_dict:
                        relationships.append({
                            'source_id': source_id,
                            'target_id': target_id,
                            'relationship_type': 'ADJACENT_TO'
                        })
                        adjacency_count += 1
                        
            logger.info(f"Found {adjacency_count} adjacency relationships")
            
            # 2. Extract containment relationships
            logger.info("Extracting containment relationships...")
            containment_map = self.get_containment_relationships()
            
            containment_count = 0
            for container_id, contents in containment_map.items():
                for content_id in contents:
                    # Only include relationships between the provided elements
                    if container_id in elements_dict and content_id in elements_dict:
                        relationships.append({
                            'source_id': container_id,
                            'target_id': content_id,
                            'relationship_type': 'CONTAINS_SPATIALLY'
                        })
                        
                        # Add inverse relationship too
                        relationships.append({
                            'source_id': content_id,
                            'target_id': container_id,
                            'relationship_type': 'CONTAINED_IN'
                        })
                        containment_count += 2
                        
            logger.info(f"Found {containment_count} containment relationships")
            
            # 3. Extract space boundary relationships
            logger.info("Extracting space boundary relationships...")
            space_boundaries = self.get_space_boundaries()
            
            boundary_count = 0
            for space_id, boundaries in space_boundaries.items():
                for boundary_id in boundaries:
                    # Only include relationships between the provided elements
                    if space_id in elements_dict and boundary_id in elements_dict:
                        relationships.append({
                            'source_id': space_id,
                            'target_id': boundary_id,
                            'relationship_type': 'BOUNDED_BY'
                        })
                        
                        # Add inverse relationship too
                        relationships.append({
                            'source_id': boundary_id,
                            'target_id': space_id,
                            'relationship_type': 'BOUNDS_SPACE'
                        })
                        boundary_count += 2
                        
            logger.info(f"Found {boundary_count} space boundary relationships")
            
            # 4. Add fallback relationships if no topological relationships are found
            if not relationships:
                logger.warning("No topological relationships found, adding fallback relationships based on IFC data")
                relationships.extend(self._get_ifc_relationships(elements_dict))
            
            logger.info(f"Found total of {len(relationships)} topological relationships")
            
        except Exception as e:
            logger.error(f"Error analyzing elements: {str(e)}", exc_info=True)
        
        return relationships
        
    def _get_ifc_relationships(self, elements_dict: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Get relationships directly from IFC model as a fallback.
        
        Args:
            elements_dict: Dictionary of elements to analyze
            
        Returns:
            List of relationships
        """
        relationships = []
        
        try:
            # Get IFC model
            ifc_model = self._get_ifc_model()
            
            # Process relationship for walls, windows and doors
            for global_id, element in elements_dict.items():
                # Find windows and doors in walls
                if element.is_a("IfcWall") or element.is_a("IfcWallStandardCase"):
                    # Find openings in this wall
                    if hasattr(element, "HasOpenings"):
                        for rel in element.HasOpenings:
                            if hasattr(rel, "RelatedOpeningElement"):
                                opening = rel.RelatedOpeningElement
                                if not hasattr(opening, "GlobalId"):
                                    continue
                                    
                                # Record wall-opening relationship
                                if opening.GlobalId in elements_dict:
                                    relationships.append({
                                        'source_id': global_id,
                                        'target_id': opening.GlobalId,
                                        'relationship_type': 'HAS_OPENING'
                                    })
                                    
                                    # Find elements in this opening (doors, windows)
                                    if hasattr(opening, "HasFillings"):
                                        for filling_rel in opening.HasFillings:
                                            if hasattr(filling_rel, "RelatedBuildingElement"):
                                                filling = filling_rel.RelatedBuildingElement
                                                if not hasattr(filling, "GlobalId"):
                                                    continue
                                                    
                                                # Record opening-element and wall-element relationships
                                                if filling.GlobalId in elements_dict:
                                                    relationships.append({
                                                        'source_id': opening.GlobalId,
                                                        'target_id': filling.GlobalId,
                                                        'relationship_type': 'HAS_FILLING'
                                                    })
                                                    
                                                    relationships.append({
                                                        'source_id': global_id,
                                                        'target_id': filling.GlobalId,
                                                        'relationship_type': 'HOSTS'
                                                    })
                                                    
                                                    relationships.append({
                                                        'source_id': filling.GlobalId,
                                                        'target_id': global_id,
                                                        'relationship_type': 'HOSTED_BY'
                                                    })
                
                # Find spaces that elements are related to
                if hasattr(element, "ContainedInStructure"):
                    for rel in element.ContainedInStructure:
                        if hasattr(rel, "RelatingStructure"):
                            structure = rel.RelatingStructure
                            if not hasattr(structure, "GlobalId"):
                                continue
                                
                            if structure.GlobalId in elements_dict:
                                relationships.append({
                                    'source_id': structure.GlobalId,
                                    'target_id': global_id,
                                    'relationship_type': 'CONTAINS'
                                })
                                
                                relationships.append({
                                    'source_id': global_id,
                                    'target_id': structure.GlobalId,
                                    'relationship_type': 'CONTAINED_IN'
                                })
            
            logger.info(f"Found {len(relationships)} fallback relationships from IFC data")
            
        except Exception as e:
            logger.error(f"Error getting IFC relationships: {str(e)}")
            
        return relationships 

    def get_space_boundary_relationships(self) -> List[Dict[str, str]]:
        """
        Get space boundary relationships formatted as a list of relationship dictionaries.
        
        This method reformats the dictionary output from get_space_boundaries() into a list
        of dictionaries compatible with adjacency and containment relationship processing.
        
        Returns:
            List of dictionaries, where each dictionary contains 'source_id', 'target_id', 
            and 'relationship_type' keys.
        """
        self._check_parser()
        
        # Get space boundaries as a dictionary
        space_boundaries_dict = self.get_space_boundaries()
        
        # Convert to list of relationship dictionaries
        relationships = []
        for space_id, boundary_element_ids in space_boundaries_dict.items():
            for element_id in boundary_element_ids:
                relationships.append({
                    'source_id': space_id,
                    'target_id': element_id,
                    'relationship_type': 'BOUNDS_SPACE'
                })
        
        return relationships 