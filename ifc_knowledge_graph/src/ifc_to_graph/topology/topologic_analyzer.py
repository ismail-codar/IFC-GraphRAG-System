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
                        
                        # Check API compatibility based on parameter count
                        try:
                            # Try with 3 parameters (entity, keys, values) - older API
                            Dictionary.ByKeysValues(
                                topologic_entity,
                                dict_keys, 
                                dict_values
                            )
                        except TypeError:
                            # Try with 2 parameters (keys, values) - newer API
                            dictionary = Dictionary.ByKeysValues(dict_keys, dict_values)
                            # Then set the dictionary to the entity
                            topologic_entity.SetDictionary(dictionary)
                        
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
            # Check if we have enough data to create a Cell
            if len(vertices) < 4 or len(faces) < 4:  # Minimum for a tetrahedron
                logger.debug(f"Not enough vertices/faces for Cell: {len(vertices)} vertices, {len(faces)} face indices")
                return None
            
            # Create topologic vertices
            topologic_vertices = []
            for vertex in vertices:
                topologic_vertex = Vertex.ByCoordinates(vertex[0], vertex[1], vertex[2])
                topologic_vertices.append(topologic_vertex)
            
            # Create faces
            topologic_faces = []
            i = 0
            face_count = 0
            
            while i < len(faces):
                try:
                    # Get number of vertices in this face
                    num_vertices = faces[i]
                    i += 1
                    
                    # Check if we have enough data remaining
                    if i + num_vertices > len(faces):
                        logger.warning(f"Face index out of range: i={i}, num_vertices={num_vertices}, len(faces)={len(faces)}")
                        break
                    
                    # Get the indices for this face
                    face_indices = faces[i:i+num_vertices]
                    i += num_vertices
                    
                    # Skip faces with too few vertices
                    if len(face_indices) < 3:
                        logger.debug("Skipping face with fewer than 3 vertices")
                        continue
                    
                    # Check if indices are in valid range
                    if max(face_indices) >= len(topologic_vertices) or min(face_indices) < 0:
                        logger.warning(f"Invalid vertex index in face: {face_indices}")
                        continue
                    
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
                            face_count += 1
                            
                except Exception as face_error:
                    logger.warning(f"Error processing face: {str(face_error)}")
                    # Skip to the next face
                    i += 1
            
            # Create a cell from faces if we have enough
            if topologic_faces and len(topologic_faces) >= 4:  # Need at least 4 faces for a tetrahedron
                try:
                    # Try using a higher tolerance if needed
                    cell = Cell.ByFaces(topologic_faces, tolerance=0.001)
                    logger.debug(f"Created Cell with {face_count} faces")
                    return cell
                except Exception as cell_error:
                    logger.warning(f"Failed to create Cell from faces: {str(cell_error)}")
                    return None
            else:
                logger.debug(f"Not enough faces to create Cell: {len(topologic_faces)}")
                
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
            # Check if we have enough data
            if len(vertices) < 3 or len(faces) < 3:  # Minimum for a triangle
                logger.debug(f"Not enough vertices/faces for Face: {len(vertices)} vertices, {len(faces)} face indices")
                return None
                
            # Create topologic vertices
            topologic_vertices = []
            for vertex in vertices:
                topologic_vertex = Vertex.ByCoordinates(vertex[0], vertex[1], vertex[2])
                topologic_vertices.append(topologic_vertex)
            
            # Try to create at least one valid face
            i = 0
            while i < len(faces):
                try:
                    # Get number of vertices in this face
                    num_vertices = faces[i]
                    i += 1
                    
                    # Check if we have enough data remaining
                    if i + num_vertices > len(faces):
                        logger.warning(f"Face index out of range: i={i}, num_vertices={num_vertices}, len(faces)={len(faces)}")
                        break
                    
                    # Get the indices for this face
                    face_indices = faces[i:i+num_vertices]
                    i += num_vertices
                    
                    # Skip faces with too few vertices
                    if len(face_indices) < 3:
                        logger.debug("Skipping face with fewer than 3 vertices")
                        continue
                    
                    # Check if indices are in valid range
                    if max(face_indices) >= len(topologic_vertices) or min(face_indices) < 0:
                        logger.warning(f"Invalid vertex index in face: {face_indices}")
                        continue
                        
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
                            logger.debug(f"Created Face with {len(wire_vertices)} vertices")
                            return face
                            
                except Exception as face_error:
                    logger.warning(f"Error processing face: {str(face_error)}")
                    # Continue to the next face
                    continue
            
            # If we get here, we couldn't create any valid faces
            logger.debug("Could not create any valid Face from geometry")
            
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
            # Get all IFC elements from the parser
            ifc_model = self.ifc_parser.file  # Use file attribute instead of get_model()
            all_elements = ifc_model.by_type("IfcElement")
            
            # Ensure all elements are converted to topologic entities
            for element in all_elements:
                if hasattr(element, "GlobalId") and element.GlobalId not in self.topologic_entities:
                    self.convert_ifc_to_topologic(element)
            
            # Get all GlobalIds that were successfully converted
            global_ids = list(self.topologic_entities.keys())
            
            # Create a list of entities with their GlobalIds
            entities_with_ids = [(gid, self.topologic_entities[gid]) for gid in global_ids]
            
            # Initialize adjacency map for all elements
            for gid in global_ids:
                adjacency_map[gid] = []
            
            # Check pairs of elements for adjacency
            for i in range(len(entities_with_ids)):
                gid1, entity1 = entities_with_ids[i]
                
                for j in range(i+1, len(entities_with_ids)):
                    gid2, entity2 = entities_with_ids[j]
                    
                    # Skip if same element
                    if gid1 == gid2:
                        continue
                    
                    # Check adjacency based on topology type
                    is_adjacent = False
                    
                    if isinstance(entity1, Cell) and isinstance(entity2, Cell):
                        # Two cells are adjacent if they share a face
                        shared_faces = Topology.SharedFaces(entity1, entity2, tolerance)
                        is_adjacent = len(shared_faces) > 0
                        
                    elif isinstance(entity1, Cell) and isinstance(entity2, Face):
                        # A cell and face are adjacent if the face bounds the cell
                        faces = Topology.Faces(entity1)
                        for face in faces:
                            if Topology.IsSame(face, entity2, tolerance):
                                is_adjacent = True
                                break
                                
                    elif isinstance(entity1, Face) and isinstance(entity2, Cell):
                        # A face and cell are adjacent if the face bounds the cell
                        faces = Topology.Faces(entity2)
                        for face in faces:
                            if Topology.IsSame(face, entity1, tolerance):
                                is_adjacent = True
                                break
                                
                    elif isinstance(entity1, Face) and isinstance(entity2, Face):
                        # Two faces are adjacent if they share an edge
                        shared_edges = Topology.SharedEdges(entity1, entity2, tolerance)
                        is_adjacent = len(shared_edges) > 0
                        
                    elif isinstance(entity1, Edge) and isinstance(entity2, Edge):
                        # Two edges are adjacent if they share a vertex
                        shared_vertices = Topology.SharedVertices(entity1, entity2, tolerance)
                        is_adjacent = len(shared_vertices) > 0
                        
                    elif isinstance(entity1, Edge) and (isinstance(entity2, Face) or isinstance(entity2, Cell)):
                        # An edge and face/cell are adjacent if the edge bounds the face/cell
                        edges = Topology.Edges(entity2)
                        for edge in edges:
                            if Topology.IsSame(edge, entity1, tolerance):
                                is_adjacent = True
                                break
                                
                    elif isinstance(entity2, Edge) and (isinstance(entity1, Face) or isinstance(entity1, Cell)):
                        # A face/cell and edge are adjacent if the edge bounds the face/cell
                        edges = Topology.Edges(entity1)
                        for edge in edges:
                            if Topology.IsSame(edge, entity2, tolerance):
                                is_adjacent = True
                                break
                    
                    # Add to adjacency map if adjacent
                    if is_adjacent:
                        adjacency_map[gid1].append(gid2)
                        adjacency_map[gid2].append(gid1)
                        
            # Cache the result
            self._adjacency_cache[tolerance] = adjacency_map
            
        except Exception as e:
            logger.error(f"Error extracting adjacency relationships: {str(e)}")
            
        return adjacency_map
    
    def get_containment_relationships(self, tolerance: float = 0.001) -> Dict[str, List[str]]:
        """
        Extract containment relationships between topological entities.
        
        Containment is defined as one element being fully contained within another.
        
        Args:
            tolerance: Tolerance for containment detection (distance in model units)
            
        Returns:
            Dictionary mapping container GlobalIds to lists of contained GlobalIds
        """
        self._check_topologicpy()
        self._check_parser()
        
        # Return cached result if available
        if self._containment_cache and tolerance in self._containment_cache:
            return self._containment_cache[tolerance]
            
        containment_map = {}
        
        try:
            # Get all IFC elements from the parser
            ifc_model = self.ifc_parser.file  # Use file attribute instead of get_model()
            all_elements = ifc_model.by_type("IfcElement")
            
            # Ensure all elements are converted to topologic entities
            for element in all_elements:
                if hasattr(element, "GlobalId") and element.GlobalId not in self.topologic_entities:
                    self.convert_ifc_to_topologic(element)
            
            # Get all GlobalIds that were successfully converted
            global_ids = list(self.topologic_entities.keys())
            
            # Create a list of entities with their GlobalIds
            entities_with_ids = [(gid, self.topologic_entities[gid]) for gid in global_ids]
            
            # Initialize containment map for all elements
            for gid in global_ids:
                containment_map[gid] = []
            
            # Only cells can contain other entities
            cell_entities = [(gid, entity) for gid, entity in entities_with_ids if isinstance(entity, Cell)]
            
            # Check pairs of elements for containment
            for gid1, cell in cell_entities:
                for gid2, entity in entities_with_ids:
                    # Skip if same element
                    if gid1 == gid2:
                        continue
                    
                    # Check containment based on topology type
                    is_contained = False
                    
                    if isinstance(entity, Cell):
                        # A cell contains another cell if it's completely inside
                        try:
                            is_contained = Cell.Contains(cell, entity, tolerance)
                        except Exception as e:
                            logger.warning(f"Error checking if Cell contains Cell: {str(e)}")
                            
                    elif isinstance(entity, Face):
                        # A cell contains a face if the face is inside the cell
                        try:
                            is_contained = Cell.Contains(cell, entity, tolerance)
                        except Exception as e:
                            logger.warning(f"Error checking if Cell contains Face: {str(e)}")
                            
                    elif isinstance(entity, Edge):
                        # A cell contains an edge if the edge is inside the cell
                        try:
                            is_contained = Cell.Contains(cell, entity, tolerance)
                        except Exception as e:
                            logger.warning(f"Error checking if Cell contains Edge: {str(e)}")
                    
                    # Add to containment map if contained
                    if is_contained:
                        containment_map[gid1].append(gid2)
            
            # Also check IFC containment relationships
            for element in all_elements:
                if not hasattr(element, "GlobalId"):
                    continue
                
                # Check for spatial containment in IFC
                container = None
                try:
                    # Try to find the direct container
                    if hasattr(element, "ContainedInStructure") and element.ContainedInStructure:
                        container = element.ContainedInStructure[0].RelatingStructure
                    
                    # If we found a container with a GlobalId
                    if container and hasattr(container, "GlobalId"):
                        # Add IFC containment relationship if both elements are converted to topologic entities
                        if (container.GlobalId in self.topologic_entities and 
                            element.GlobalId in self.topologic_entities):
                            if element.GlobalId not in containment_map[container.GlobalId]:
                                containment_map[container.GlobalId].append(element.GlobalId)
                except Exception as e:
                    logger.warning(f"Error checking IFC containment for {element.GlobalId}: {str(e)}")
                
            # Cache the result
            self._containment_cache[tolerance] = containment_map
            
        except Exception as e:
            logger.error(f"Error extracting containment relationships: {str(e)}")
            
        return containment_map
    
    def get_space_boundaries(self) -> Dict[str, List[str]]:
        """
        Extract space boundary relationships between spaces and building elements.
        
        Uses both IFC relationships and topological analysis.
        
        Returns:
            Dictionary mapping space GlobalIds to lists of boundary element GlobalIds
        """
        self._check_parser()
        
        # Return cached result if available
        if self._space_boundaries_cache:
            return self._space_boundaries_cache
            
        space_boundaries = {}
        
        try:
            # Get all IFC elements from the parser
            ifc_model = self.ifc_parser.file  # Use file attribute instead of get_model()
            spaces = ifc_model.by_type("IfcSpace")
            
            logger.info(f"Found {len(spaces)} spaces in the IFC model")
            
            # Process each space
            for space in spaces:
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
                for space in spaces:
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
            Dictionary mapping GlobalIds to dictionaries of relationship types,
            each containing lists of connected element data.
        """
        self._check_parser()
        
        # Initialize the connectivity graph
        connectivity_graph = {}
        
        try:
            # Get all IFC elements
            ifc_model = self.ifc_parser.file  # Use file attribute instead of get_model()
            all_elements = ifc_model.by_type("IfcElement")
            
            # Initialize the connectivity graph for each element
            for element in all_elements:
                if not hasattr(element, "GlobalId"):
                    continue
                    
                element_id = element.GlobalId
                
                if element_id not in connectivity_graph:
                    connectivity_graph[element_id] = {
                        "adjacent": [],
                        "contains": [],
                        "contained_by": [],
                        "bounds_space": [],
                        "bounded_by": []
                    }
            
            # Get all necessary relationship maps
            adjacency_map = self.get_adjacency_relationships()
            containment_map = self.get_containment_relationships()
            space_boundaries = self.get_space_boundaries()
            
            # Add adjacency relationships
            for element_id, adjacent_ids in adjacency_map.items():
                if element_id not in connectivity_graph:
                    continue
                    
                for adjacent_id in adjacent_ids:
                    if adjacent_id not in connectivity_graph:
                        continue
                        
                    # Get the element type
                    adjacent_element = self.ifc_parser.get_element_by_id(adjacent_id)
                    if not adjacent_element:
                        continue
                        
                    element_type = adjacent_element.is_a()
                    
                    # Add to connectivity graph
                    connectivity_graph[element_id]["adjacent"].append({
                        "id": adjacent_id,
                        "type": element_type
                    })
            
            # Add containment relationships
            for container_id, contained_ids in containment_map.items():
                if container_id not in connectivity_graph:
                    continue
                    
                for contained_id in contained_ids:
                    if contained_id not in connectivity_graph:
                        continue
                        
                    # Get the element type
                    contained_element = self.ifc_parser.get_element_by_id(contained_id)
                    if not contained_element:
                        continue
                        
                    element_type = contained_element.is_a()
                    
                    # Add to connectivity graph (container -> contained)
                    connectivity_graph[container_id]["contains"].append({
                        "id": contained_id,
                        "type": element_type
                    })
                    
                    # Add to connectivity graph (contained -> container)
                    container_element = self.ifc_parser.get_element_by_id(container_id)
                    if not container_element:
                        continue
                        
                    container_type = container_element.is_a()
                    
                    connectivity_graph[contained_id]["contained_by"].append({
                        "id": container_id,
                        "type": container_type
                    })
            
            # Add space boundary relationships
            for space_id, boundary_ids in space_boundaries.items():
                if space_id not in connectivity_graph:
                    continue
                    
                for boundary_id in boundary_ids:
                    if boundary_id not in connectivity_graph:
                        continue
                        
                    # Get the element types
                    space = self.ifc_parser.get_element_by_id(space_id)
                    boundary = self.ifc_parser.get_element_by_id(boundary_id)
                    
                    if not space or not boundary:
                        continue
                        
                    space_type = space.is_a()
                    boundary_type = boundary.is_a()
                    
                    # Add to connectivity graph (space -> boundary)
                    connectivity_graph[space_id]["bounded_by"].append({
                        "id": boundary_id,
                        "type": boundary_type
                    })
                    
                    # Add to connectivity graph (boundary -> space)
                    connectivity_graph[boundary_id]["bounds_space"].append({
                        "id": space_id,
                        "type": space_type
                    })
            
            # Add direct connectivity through openings (doors, windows)
            for element in all_elements:
                if (not hasattr(element, "GlobalId") or 
                    not element.is_a("IfcDoor") and not element.is_a("IfcWindow")):
                    continue
                    
                element_id = element.GlobalId
                
                # Find spaces connected by this opening
                connected_spaces = []
                
                for space_id, boundary_ids in space_boundaries.items():
                    if element_id in boundary_ids:
                        connected_spaces.append(space_id)
                
                # If this opening connects two spaces, add a direct connection between them
                if len(connected_spaces) >= 2:
                    for i in range(len(connected_spaces)):
                        for j in range(i+1, len(connected_spaces)):
                            space1_id = connected_spaces[i]
                            space2_id = connected_spaces[j]
                            
                            if space1_id not in connectivity_graph or space2_id not in connectivity_graph:
                                continue
                                
                            space1 = self.ifc_parser.get_element_by_id(space1_id)
                            space2 = self.ifc_parser.get_element_by_id(space2_id)
                            
                            if not space1 or not space2:
                                continue
                                
                            # Add connection in both directions
                            # Space 1 -> Space 2
                            connectivity_graph[space1_id]["adjacent"].append({
                                "id": space2_id,
                                "type": space2.is_a(),
                                "via": element_id,
                                "via_type": element.is_a()
                            })
                            
                            # Space 2 -> Space 1
                            connectivity_graph[space2_id]["adjacent"].append({
                                "id": space1_id,
                                "type": space1.is_a(),
                                "via": element_id,
                                "via_type": element.is_a()
                            })
        
        except Exception as e:
            logger.error(f"Error generating connectivity graph: {str(e)}")
            
        return connectivity_graph
    
    def find_path(self, start_id: str, end_id: str, 
                  relationship_types: List[str] = None) -> List[Dict[str, Any]]:
        """
        Find a path between two elements in the building model.
        
        Args:
            start_id: GlobalId of the starting element
            end_id: GlobalId of the target element
            relationship_types: List of relationship types to consider
                               ["adjacent", "contains", "contained_by", "bounds_space", "bounded_by"]
                               If None, all types are considered.
                               
        Returns:
            A list of elements in the path, with their connections, or empty list if no path exists
        """
        # Default to all relationship types if none specified
        if relationship_types is None:
            relationship_types = ["adjacent", "contains", "contained_by", "bounds_space", "bounded_by"]
            
        # Get the connectivity graph
        connectivity_graph = self.get_connectivity_graph()
        
        # Check if start and end elements exist
        if start_id not in connectivity_graph or end_id not in connectivity_graph:
            return []
            
        # Breadth-first search
        queue = [(start_id, [])]  # (current_node, path)
        visited = set()
        
        while queue:
            current_id, path = queue.pop(0)
            
            # Skip if already visited
            if current_id in visited:
                continue
                
            # Mark as visited
            visited.add(current_id)
            
            # Add to path
            current_path = path + [current_id]
            
            # Check if reached target
            if current_id == end_id:
                # Convert path of IDs to path of elements with connections
                detailed_path = []
                for i in range(len(current_path) - 1):
                    from_id = current_path[i]
                    to_id = current_path[i + 1]
                    
                    # Find the connection type
                    connection_type = None
                    connection_details = None
                    
                    for rel_type in relationship_types:
                        for connection in connectivity_graph[from_id][rel_type]:
                            if connection["id"] == to_id:
                                connection_type = rel_type
                                connection_details = connection
                                break
                                
                        if connection_type:
                            break
                    
                    # Get element details
                    from_element = self.ifc_parser.get_element_by_id(from_id)
                    from_type = from_element.is_a() if from_element else "Unknown"
                    
                    # Add to detailed path
                    detailed_path.append({
                        "id": from_id,
                        "type": from_type,
                        "connection": connection_type,
                        "to": connection_details
                    })
                
                # Add the final element
                to_element = self.ifc_parser.get_element_by_id(end_id)
                to_type = to_element.is_a() if to_element else "Unknown"
                
                detailed_path.append({
                    "id": end_id,
                    "type": to_type,
                    "connection": None,
                    "to": None
                })
                
                return detailed_path
            
            # Add neighbors to queue
            for rel_type in relationship_types:
                for connection in connectivity_graph[current_id][rel_type]:
                    neighbor_id = connection["id"]
                    if neighbor_id not in visited:
                        queue.append((neighbor_id, current_path))
        
        # No path found
        return []
    
    def analyze_building_topology(self) -> Dict[str, Any]:
        """
        Perform full topological analysis of the building model.
        
        Returns:
            Dictionary with topological analysis results including:
            - adjacency: Adjacency relationships
            - containment: Containment relationships
            - space_boundaries: Space boundary relationships
            - connectivity: Overall connectivity graph
        """
        self._check_parser()
        
        analysis_results = {
            "adjacency": {},
            "containment": {},
            "space_boundaries": {},
            "connectivity": {}
        }
        
        # Extract adjacency relationships
        try:
            adjacency_map = self.get_adjacency_relationships()
            analysis_results["adjacency"] = adjacency_map
        except Exception as e:
            logger.error(f"Error extracting adjacency relationships: {str(e)}")
        
        # Extract containment relationships
        try:
            containment_map = self.get_containment_relationships()
            analysis_results["containment"] = containment_map
        except Exception as e:
            logger.error(f"Error extracting containment relationships: {str(e)}")
            
        # Extract space boundary relationships
        try:
            space_boundaries = self.get_space_boundaries()
            analysis_results["space_boundaries"] = space_boundaries
        except Exception as e:
            logger.error(f"Error extracting space boundary relationships: {str(e)}")
            
        # Generate connectivity graph
        try:
            connectivity_graph = self.get_connectivity_graph()
            analysis_results["connectivity"] = connectivity_graph
        except Exception as e:
            logger.error(f"Error generating connectivity graph: {str(e)}")
        
        return analysis_results 

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
            ifc_model = self.ifc_parser.file
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