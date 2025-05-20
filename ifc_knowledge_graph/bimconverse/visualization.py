"""
BIMConverse Visualization Module

This module provides visualization capabilities for spatial query results,
enabling graphical representation of building elements, spaces, and their relationships.
"""

import logging
import os
import json
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
import uuid

# Optional imports for different visualization libraries
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

logger = logging.getLogger(__name__)

class SpatialVisualizer:
    """
    Creates visualizations for spatial query results from the Neo4j knowledge graph.
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the spatial visualizer.
        
        Args:
            output_dir: Directory to save visualization files
        """
        self.output_dir = output_dir or os.path.join(os.getcwd(), "visualizations")
        
        # Ensure the output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Check if required visualization libraries are available
        if not PLOTLY_AVAILABLE:
            logger.warning("Plotly is not installed. Install with 'pip install plotly'")
        
        if not NETWORKX_AVAILABLE:
            logger.warning("NetworkX is not installed. Install with 'pip install networkx'")
            
        logger.info(f"Initialized SpatialVisualizer with output directory: {self.output_dir}")
    
    def visualize_graph(self, 
                        nodes: List[Dict[str, Any]], 
                        relationships: List[Dict[str, Any]],
                        title: str = "Building Element Graph") -> Optional[str]:
        """
        Create a graph visualization of building elements and their relationships.
        
        Args:
            nodes: List of node data from Neo4j 
            relationships: List of relationship data from Neo4j
            title: Title for the visualization
            
        Returns:
            Path to the saved visualization file or None if visualization failed
        """
        if not NETWORKX_AVAILABLE or not PLOTLY_AVAILABLE:
            logger.error("Cannot create graph visualization: required libraries not installed")
            return None
            
        try:
            # Create a NetworkX graph
            G = nx.Graph()
            
            # Add nodes
            for node in nodes:
                # Use GlobalId as node identifier if available
                node_id = node.get("GlobalId", node.get("id", str(uuid.uuid4())))
                
                # Get node label from keys that might contain type information
                node_label = None
                for key in ["Name", "IFCType", "label", "type"]:
                    if key in node and node[key]:
                        node_label = node[key]
                        break
                        
                # Add node with properties
                G.add_node(node_id, 
                           label=node_label or "Unknown", 
                           properties=node)
            
            # Add edges
            for rel in relationships:
                # Extract source and target node IDs
                source_id = rel.get("startNode", rel.get("source", ""))
                target_id = rel.get("endNode", rel.get("target", ""))
                
                # Get relationship type
                rel_type = rel.get("type", rel.get("relationshipType", "RELATED_TO"))
                
                # Add edge with properties
                if source_id and target_id:
                    G.add_edge(source_id, target_id, 
                               label=rel_type,
                               properties=rel)
            
            # Create a Plotly figure
            pos = nx.spring_layout(G, seed=42)
            
            # Create edge trace
            edge_x = []
            edge_y = []
            edge_text = []
            
            for edge in G.edges():
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])
                
                # Add edge label for hover text
                edge_data = G.edges[edge]
                edge_text.append(edge_data.get("label", ""))
            
            edge_trace = go.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=1, color='#888'),
                hoverinfo='text',
                text=edge_text,
                mode='lines')
            
            # Create node trace
            node_x = []
            node_y = []
            node_text = []
            node_color = []
            
            # Define colors for different node types
            color_map = {
                "Space": "#6929c4",
                "Wall": "#1192e8",
                "Door": "#005d5d",
                "Window": "#9ef0f0",
                "Slab": "#fa4d56",
                "Beam": "#570408",
                "Column": "#198038",
                "Storey": "#002d9c",
                "Building": "#ee538b"
            }
            
            for node in G.nodes():
                x, y = pos[node]
                node_x.append(x)
                node_y.append(y)
                
                # Create hover text with node properties
                node_data = G.nodes[node]
                properties = node_data.get("properties", {})
                node_label = node_data.get("label", "Unknown")
                
                # Format properties for hover text
                hover_text = f"Type: {node_label}<br>"
                for key, value in properties.items():
                    if key not in ["GlobalId", "id"] and value:
                        hover_text += f"{key}: {value}<br>"
                        
                node_text.append(hover_text)
                
                # Determine node color based on type
                for node_type, color in color_map.items():
                    if node_type.lower() in node_label.lower():
                        node_color.append(color)
                        break
                else:
                    node_color.append("#a56eff")  # Default color
            
            node_trace = go.Scatter(
                x=node_x, y=node_y,
                mode='markers',
                hoverinfo='text',
                text=node_text,
                marker=dict(
                    showscale=False,
                    color=node_color,
                    size=10,
                    line_width=2))
            
            # Create the figure
            fig = go.Figure(data=[edge_trace, node_trace],
                           layout=go.Layout(
                               title=title,
                               titlefont_size=16,
                               showlegend=False,
                               hovermode='closest',
                               margin=dict(b=20, l=5, r=5, t=40),
                               xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                               yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)))
            
            # Save the figure to HTML file
            filename = f"spatial_graph_{uuid.uuid4().hex[:8]}.html"
            filepath = os.path.join(self.output_dir, filename)
            fig.write_html(filepath)
            
            logger.info(f"Created graph visualization at {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error creating graph visualization: {e}")
            return None
    
    def visualize_spatial_relationships(self, 
                                        query_results: Dict[str, Any],
                                        query_type: str = "adjacency") -> Optional[str]:
        """
        Create a specialized visualization for spatial relationships.
        
        Args:
            query_results: Results from a spatial relationship query
            query_type: Type of spatial relationship (adjacency, containment, connectivity)
            
        Returns:
            Path to the saved visualization file or None if visualization failed
        """
        if not PLOTLY_AVAILABLE:
            logger.error("Cannot create spatial visualization: Plotly not installed")
            return None
            
        try:
            # Extract nodes and relationships from query results
            nodes = []
            relationships = []
            
            # Process based on query type
            if query_type == "adjacency":
                # For adjacency queries, typically Space-Space relationships
                fig = self._create_adjacency_visualization(query_results)
            elif query_type == "containment":
                # For containment queries (hierarchical)
                fig = self._create_containment_visualization(query_results)
            elif query_type == "connectivity":
                # For connectivity queries (typically showing paths)
                fig = self._create_connectivity_visualization(query_results)
            else:
                # Generic graph visualization as fallback
                # Extract nodes and relationships from results first
                if "results" in query_results:
                    nodes, relationships = self._extract_graph_data(query_results["results"])
                return self.visualize_graph(nodes, relationships, f"Spatial {query_type.title()} Visualization")
            
            # Save the figure
            if fig:
                filename = f"spatial_{query_type}_{uuid.uuid4().hex[:8]}.html"
                filepath = os.path.join(self.output_dir, filename)
                fig.write_html(filepath)
                logger.info(f"Created {query_type} visualization at {filepath}")
                return filepath
                
            return None
            
        except Exception as e:
            logger.error(f"Error creating spatial visualization: {e}")
            return None
    
    def _create_adjacency_visualization(self, query_results: Dict[str, Any]) -> Optional[go.Figure]:
        """
        Create a specialized visualization for space adjacency relationships.
        
        Args:
            query_results: Results from a space adjacency query
            
        Returns:
            Plotly Figure object or None if visualization failed
        """
        # Extract adjacency data
        spaces = set()
        adjacencies = []
        
        # Process results to find spaces and their adjacencies
        if "results" in query_results:
            for record in query_results["results"]:
                # Looking for space nodes and ADJACENT_TO relationships
                for key, value in record.items():
                    if isinstance(value, dict) and "Name" in value:
                        spaces.add(value["Name"])
                    
                    # If this is a pair of adjacent spaces
                    if "space1" in record and "space2" in record:
                        space1 = record["space1"].get("Name", "Unknown")
                        space2 = record["space2"].get("Name", "Unknown")
                        adjacencies.append((space1, space2))
        
        if not spaces:
            logger.warning("No spaces found in adjacency query results")
            return None
            
        # Create a NetworkX graph for the adjacency network
        G = nx.Graph()
        for space in spaces:
            G.add_node(space)
            
        for s1, s2 in adjacencies:
            G.add_edge(s1, s2)
            
        # Layout the graph
        pos = nx.spring_layout(G, seed=42)
        
        # Create the figure
        fig = go.Figure()
        
        # Add edges
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            fig.add_trace(
                go.Scatter(
                    x=[x0, x1, None],
                    y=[y0, y1, None],
                    mode='lines',
                    line=dict(width=1, color='#888'),
                    hoverinfo='none'
                )
            )
        
        # Add nodes
        node_x = []
        node_y = []
        node_text = []
        
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(f"Space: {node}<br>Adjacent to: {', '.join(list(G.neighbors(node)))}")
        
        fig.add_trace(
            go.Scatter(
                x=node_x,
                y=node_y,
                mode='markers+text',
                marker=dict(size=15, color='#6929c4'),
                text=[node.split(' ')[0] if ' ' in node else node for node in G.nodes()],
                textposition="top center",
                hoverinfo='text',
                hovertext=node_text
            )
        )
        
        # Update layout
        fig.update_layout(
            title="Space Adjacency Diagram",
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='#fff'
        )
        
        return fig
    
    def _create_containment_visualization(self, query_results: Dict[str, Any]) -> Optional[go.Figure]:
        """
        Create a visualization showing containment hierarchies (e.g., Building → Storey → Space → Element).
        
        Args:
            query_results: Results from a containment query
            
        Returns:
            Plotly Figure object or None if visualization failed
        """
        # This could be implemented as a sunburst chart for hierarchical data
        containment_data = []
        
        # Process results to find containment relationships
        if "results" in query_results:
            for record in query_results["results"]:
                # Look for containment paths
                container = None
                contained = None
                
                # Try to identify container and contained elements
                for key, value in record.items():
                    if isinstance(value, dict):
                        if any(k in key.lower() for k in ["building", "storey", "parent", "container"]):
                            container = value.get("Name", "Unknown")
                        elif any(k in key.lower() for k in ["space", "element", "child", "contained"]):
                            contained = value.get("Name", "Unknown")
                
                if container and contained:
                    containment_data.append({"container": container, "contained": contained})
        
        if not containment_data:
            logger.warning("No containment relationships found in query results")
            return None
            
        # Build hierarchical data for sunburst chart
        hierarchy = {}
        
        # Create hierarchy dictionary
        for item in containment_data:
            container = item["container"]
            contained = item["contained"]
            
            if container not in hierarchy:
                hierarchy[container] = []
                
            hierarchy[container].append(contained)
        
        # Create sunburst data
        labels = []
        parents = []
        
        # Add root nodes (containers)
        for container in hierarchy:
            labels.append(container)
            parents.append("")  # No parent for root nodes
            
            # Add children
            for contained in hierarchy[container]:
                labels.append(contained)
                parents.append(container)
        
        # Create the figure
        fig = go.Figure(go.Sunburst(
            labels=labels,
            parents=parents,
            insidetextorientation='radial',
            branchvalues='total'
        ))
        
        # Update layout
        fig.update_layout(
            title="Building Element Containment Hierarchy",
            margin=dict(t=30, b=10, r=10, l=10)
        )
        
        return fig
    
    def _create_connectivity_visualization(self, query_results: Dict[str, Any]) -> Optional[go.Figure]:
        """
        Create a visualization showing connectivity between spaces (e.g., doors connecting rooms).
        
        Args:
            query_results: Results from a connectivity query
            
        Returns:
            Plotly Figure object or None if visualization failed
        """
        # Extract connectivity data - typical pattern: (Space)-[CONNECTED_TO]-(Space)
        spaces = set()
        connections = []
        connecting_elements = {}  # To track what connects spaces (doors, openings)
        
        # Process results to find connected spaces
        if "results" in query_results:
            for record in query_results["results"]:
                space1 = None
                space2 = None
                connector = None
                
                # Try to identify connected spaces and connector
                for key, value in record.items():
                    if isinstance(value, dict):
                        if "Space" in value.get("IFCType", ""):
                            if space1 is None:
                                space1 = value.get("Name", "Unknown Space")
                            else:
                                space2 = value.get("Name", "Unknown Space")
                        elif any(t in value.get("IFCType", "") for t in ["Door", "Opening", "Window"]):
                            connector = value.get("Name", value.get("IFCType", "Connection"))
                
                if space1 and space2:
                    spaces.update([space1, space2])
                    connections.append((space1, space2))
                    
                    # Store the connecting element if available
                    if connector:
                        connections_key = tuple(sorted([space1, space2]))
                        connecting_elements[connections_key] = connector
        
        if not spaces:
            logger.warning("No connected spaces found in connectivity query results")
            return None
            
        # Create a NetworkX graph for the connectivity network
        G = nx.Graph()
        for space in spaces:
            G.add_node(space)
            
        for s1, s2 in connections:
            G.add_edge(s1, s2)
            
        # Layout the graph
        pos = nx.spring_layout(G, seed=42)
        
        # Create the figure
        fig = go.Figure()
        
        # Add edges with connector information
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            
            # Get connector if available
            connection_key = tuple(sorted(edge))
            connector = connecting_elements.get(connection_key, "Connected")
            
            fig.add_trace(
                go.Scatter(
                    x=[x0, (x0+x1)/2, x1, None],
                    y=[y0, (y0+y1)/2, y1, None],
                    mode='lines+markers+text',
                    line=dict(width=1, color='#888'),
                    marker=dict(
                        size=[0, 8, 0, 0],
                        color='#1192e8',
                    ),
                    text=["", connector, "", ""],
                    textposition="top center",
                    hoverinfo='text',
                    hovertext=f"Connection: {connector}"
                )
            )
        
        # Add nodes (spaces)
        for node in G.nodes():
            x, y = pos[node]
            
            # Count connections for this space
            connections_count = len(list(G.neighbors(node)))
            
            fig.add_trace(
                go.Scatter(
                    x=[x],
                    y=[y],
                    mode='markers+text',
                    marker=dict(size=20, color='#6929c4'),
                    text=[node],
                    textposition="bottom center",
                    hoverinfo='text',
                    hovertext=f"Space: {node}<br>Connections: {connections_count}"
                )
            )
        
        # Update layout
        fig.update_layout(
            title="Space Connectivity Diagram",
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='#fff'
        )
        
        return fig
    
    def _extract_graph_data(self, results: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Extract nodes and relationships from query results.
        
        Args:
            results: List of query result records
            
        Returns:
            Tuple of (nodes, relationships)
        """
        nodes = []
        relationships = []
        nodes_seen = set()
        
        for record in results:
            # Process each field in the record
            for key, value in record.items():
                # Check if this is a node
                if isinstance(value, dict) and ("GlobalId" in value or "Name" in value):
                    # Use GlobalId as unique identifier if available
                    node_id = value.get("GlobalId", value.get("id", str(uuid.uuid4())))
                    
                    if node_id not in nodes_seen:
                        nodes.append(value)
                        nodes_seen.add(node_id)
                        
                # Check if this is a relationship
                elif key.lower() in ["relationship", "rel"] or (
                    isinstance(value, dict) and "type" in value and 
                    "startNode" in value and "endNode" in value
                ):
                    relationships.append(value)
        
        return nodes, relationships


def visualize_multihop_results(results: Dict[str, Any], output_dir: Optional[str] = None) -> Optional[str]:
    """
    Create a visualization of multihop query results.
    
    Args:
        results: Results from a multihop query
        output_dir: Directory to save the visualization
        
    Returns:
        Path to the saved visualization file or None if visualization failed
    """
    visualizer = SpatialVisualizer(output_dir)
    
    # Find all nodes and relationships from intermediate results
    all_nodes = []
    all_relationships = []
    nodes_seen = set()
    
    # Process each intermediate result
    for step in results.get("intermediate_results", []):
        step_results = step.get("results", [])
        
        # Extract nodes and relationships
        nodes, relationships = visualizer._extract_graph_data(step_results)
        
        # Add unique nodes
        for node in nodes:
            node_id = node.get("GlobalId", node.get("id", str(uuid.uuid4())))
            if node_id not in nodes_seen:
                all_nodes.append(node)
                nodes_seen.add(node_id)
                
        # Add relationships
        all_relationships.extend(relationships)
    
    # Create a visualization of the combined graph
    title = f"Multihop Query: {results.get('query', 'Complex Query')}"
    return visualizer.visualize_graph(all_nodes, all_relationships, title)


def enhance_multihop_result_with_visualization(multihop_result: Any) -> Any:
    """
    Enhance a MultihopResult with visualization capabilities.
    
    Args:
        multihop_result: The MultihopResult object
        
    Returns:
        The enhanced MultihopResult object
    """
    # Extract the results dictionary
    if hasattr(multihop_result, "intermediate_results"):
        results = {
            "query": getattr(multihop_result, "query", ""),
            "sub_queries": getattr(multihop_result, "sub_queries", []),
            "intermediate_results": getattr(multihop_result, "intermediate_results", []),
            "accumulated_context": getattr(multihop_result, "accumulated_context", "")
        }
        
        # Create visualization
        viz_path = visualize_multihop_results(results)
        
        # Enhance the result with visualization path
        if viz_path:
            multihop_result.visualization_path = viz_path
            # Update metadata field if it exists
            if hasattr(multihop_result, "metadata"):
                multihop_result.metadata["has_visualization"] = True
                multihop_result.metadata["visualization_path"] = viz_path
                
            # Update answer if it exists
            if hasattr(multihop_result, "answer"):
                multihop_result.answer += f" Visualization available at: {viz_path}"
    
    return multihop_result 