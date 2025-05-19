#!/usr/bin/env python
"""
BIMConverse Core Module

This module implements the core functionality for BIMConverse, a GraphRAG system
for interacting with IFC knowledge graphs stored in Neo4j using natural language.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple

from neo4j import GraphDatabase
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.retrievers import Text2CypherRetriever

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BIMConverse")

class BIMConverseRAG:
    """
    BIMConverse RAG implementation for IFC Knowledge Graphs.
    Uses Text2CypherRetriever to enable natural language querying of building information models.
    """

    def __init__(self, config_path: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the BIMConverseRAG system.

        Args:
            config_path: Path to configuration file
            config: Configuration dictionary (alternative to config_path)
        """
        self.config = config if config else self._load_config(config_path)
        self.driver = self._initialize_neo4j_connection()
        self.llm = self._initialize_llm()
        self.retriever = self._initialize_retriever()
        self.rag = self._initialize_rag()
        
        # Initialize conversation context
        self.context_enabled = self.config.get("context_enabled", False)
        self.max_history_length = self.config.get("max_history", 10)
        self.conversation_history = []

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file or environment variables."""
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        
        # Fallback to environment variables if no config file
        return {
            "neo4j_uri": os.environ.get("NEO4J_URI", "neo4j://localhost:7687"),
            "neo4j_username": os.environ.get("NEO4J_USERNAME", "neo4j"),
            "neo4j_password": os.environ.get("NEO4J_PASSWORD", "password"),
            "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
            "context_enabled": os.environ.get("CONTEXT_ENABLED", "false").lower() == "true",
            "max_history": int(os.environ.get("MAX_HISTORY", "10")),
        }

    def _initialize_neo4j_connection(self):
        """Initialize connection to Neo4j database."""
        uri = self.config.get("neo4j_uri")
        username = self.config.get("neo4j_username")
        password = self.config.get("neo4j_password")
        
        if not all([uri, username, password]):
            raise ValueError("Missing Neo4j connection details in configuration")
        
        logger.info(f"Connecting to Neo4j at {uri}")
        return GraphDatabase.driver(uri, auth=(username, password))

    def _initialize_llm(self):
        """Initialize the LLM for Text2Cypher generation."""
        api_key = self.config.get("openai_api_key")
        if not api_key:
            raise ValueError("Missing OpenAI API key in configuration")
        
        # Set the API key in environment variable for OpenAI
        os.environ["OPENAI_API_KEY"] = api_key
        
        logger.info("Initializing OpenAI LLM")
        return OpenAILLM(
            model_name="gpt-4o",  # Using GPT-4o for best performance
            model_params={"temperature": 0}  # Low temperature for more deterministic outputs
        )

    def _initialize_retriever(self):
        """Initialize the Text2CypherRetriever."""
        # Define IFC schema for Text2Cypher - this helps the model understand the graph structure
        ifc_schema = """
        Node properties:
        IfcProduct {GlobalId: STRING, Name: STRING, Description: STRING, ObjectType: STRING}
        IfcElement {GlobalId: STRING, Name: STRING, Description: STRING, ObjectType: STRING}
        IfcSpatialElement {GlobalId: STRING, Name: STRING, Description: STRING, ObjectType: STRING}
        IfcBuilding {GlobalId: STRING, Name: STRING, Description: STRING, ObjectType: STRING}
        IfcSpace {GlobalId: STRING, Name: STRING, Description: STRING, ObjectType: STRING}
        IfcMaterial {Name: STRING, Description: STRING}
        IfcPropertySet {GlobalId: STRING, Name: STRING, Description: STRING}
        IfcProperty {Name: STRING, Description: STRING, NominalValue: STRING}

        Relationship properties:
        HAS_PROPERTIES {}
        HAS_PROPERTY {}
        CONTAINS {}
        DEFINES {}
        HAS_MATERIAL {}
        CONNECTED_TO {}

        The relationships:
        (:IfcProduct)-[:HAS_PROPERTIES]->(:IfcPropertySet)
        (:IfcPropertySet)-[:HAS_PROPERTY]->(:IfcProperty)
        (:IfcSpatialElement)-[:CONTAINS]->(:IfcElement)
        (:IfcBuilding)-[:CONTAINS]->(:IfcSpace)
        (:IfcSpace)-[:CONTAINS]->(:IfcElement)
        (:IfcElement)-[:HAS_MATERIAL]->(:IfcMaterial)
        (:IfcElement)-[:CONNECTED_TO]->(:IfcElement)
        """
        
        # Example queries to help the model understand common queries
        examples = [
            "USER INPUT: 'What are all the spaces in the building?' QUERY: MATCH (s:IfcSpace)<-[:CONTAINS]-(b:IfcBuilding) RETURN s.Name as SpaceName, s.Description as Description",
            "USER INPUT: 'Show me walls with concrete material' QUERY: MATCH (w:IfcElement)-[:HAS_MATERIAL]->(m:IfcMaterial) WHERE w.ObjectType = 'Wall' AND m.Name CONTAINS 'Concrete' RETURN w.Name as WallName, m.Name as MaterialName",
            "USER INPUT: 'What properties does the main entrance door have?' QUERY: MATCH (d:IfcElement)-[:HAS_PROPERTIES]->(ps:IfcPropertySet)-[:HAS_PROPERTY]->(p:IfcProperty) WHERE d.ObjectType = 'Door' AND d.Name CONTAINS 'Entrance' RETURN d.Name as DoorName, ps.Name as PropertySetName, p.Name as PropertyName, p.NominalValue as PropertyValue"
        ]
        
        logger.info("Initializing Text2CypherRetriever")
        return Text2CypherRetriever(
            driver=self.driver,
            llm=self.llm,
            neo4j_schema=ifc_schema,
            examples=examples
        )

    def _initialize_rag(self):
        """Initialize the GraphRAG pipeline."""
        logger.info("Initializing GraphRAG pipeline")
        return GraphRAG(
            retriever=self.retriever,
            llm=self.llm
        )

    def query(self, query_text: str) -> Dict[str, Any]:
        """
        Execute a natural language query against the IFC knowledge graph.
        
        Args:
            query_text: The natural language query
            
        Returns:
            Dict containing answer, sources, and query details
        """
        logger.info(f"Processing query: {query_text}")
        
        # Apply conversation context if enabled
        if self.context_enabled and self.conversation_history:
            # Extract previous exchanges for context
            chat_history = [
                (q, a["answer"]) for q, a in self.conversation_history[-self.max_history_length:]
            ]
            # Execute search with chat history for context
            response = self.rag.search(
                query_text=query_text,
                chat_history=chat_history
            )
        else:
            # Execute search without context
            response = self.rag.search(query_text=query_text)
        
        # Extract generated Cypher query from metadata
        cypher_query = response.metadata.get("cypher", "No Cypher query generated")
        
        # Prepare result
        result = {
            "answer": response.answer,
            "query": query_text,
            "cypher_query": cypher_query,
            "sources": [],
            "timestamp": response.metadata.get("timestamp", ""),
        }
        
        # Extract sources from retriever results if available
        if hasattr(response, "retriever_result") and response.retriever_result:
            result["sources"] = [
                {"content": item.content, "metadata": item.metadata}
                for item in response.retriever_result.items
            ]
        
        # Update conversation history if context is enabled
        if self.context_enabled:
            self.conversation_history.append((query_text, result))
            # Trim history if needed
            if len(self.conversation_history) > self.max_history_length:
                self.conversation_history = self.conversation_history[-self.max_history_length:]
        
        return result

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the knowledge graph."""
        stats = {}
        
        with self.driver.session() as session:
            # Get total node count
            result = session.run("MATCH (n) RETURN count(n) as count")
            stats["nodes"] = result.single()["count"]
            
            # Get total relationship count
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            stats["relationships"] = result.single()["count"]
            
            # Get node label counts
            result = session.run("""
                CALL apoc.meta.stats()
                YIELD labels
                RETURN labels
            """)
            record = result.single()
            if record:
                stats["labels"] = record["labels"]
            else:
                # Fallback method if APOC is not available
                result = session.run("""
                    MATCH (n)
                    WITH labels(n) AS labels, count(*) AS count
                    UNWIND labels AS label
                    RETURN label, sum(count) AS count
                """)
                stats["labels"] = {row["label"]: row["count"] for row in result}
            
            # Get relationship type counts
            result = session.run("""
                MATCH ()-[r]->()
                WITH type(r) AS type, count(*) AS count
                RETURN type, count
                ORDER BY count DESC
            """)
            stats["relationship_types"] = {row["type"]: row["count"] for row in result}
        
        return stats

    def get_context_settings(self) -> Dict[str, Any]:
        """Get the current conversation context settings."""
        return {
            "enabled": self.context_enabled,
            "max_history_length": self.max_history_length,
            "current_history_length": len(self.conversation_history)
        }

    def set_context_enabled(self, enabled: bool):
        """Enable or disable conversation context."""
        self.context_enabled = enabled
        logger.info(f"Conversation context {'enabled' if enabled else 'disabled'}")

    def set_context_history_length(self, length: int):
        """Set the maximum conversation history length."""
        if length < 1:
            raise ValueError("History length must be at least 1")
        self.max_history_length = length
        logger.info(f"Maximum conversation history length set to {length}")

    def clear_context_history(self):
        """Clear the conversation history."""
        self.conversation_history = []
        logger.info("Conversation history cleared")

    def close(self):
        """Close database connections and resources."""
        if self.driver:
            self.driver.close()
        logger.info("BIMConverseRAG resources released")


def create_config_file(config: Dict[str, Any]) -> str:
    """
    Create a configuration file from the provided configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Path to the created configuration file
    """
    # Extract the output path or use default
    output_path = config.pop("output_path", "config.json")
    
    # Ensure the directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Write the configuration
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"Configuration file created at: {output_path}")
    return output_path
