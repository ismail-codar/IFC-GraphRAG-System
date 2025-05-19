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
from neo4j_graphrag.retrievers import VectorRetriever, HybridRetriever, Text2CypherRetriever

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BIMConverse")

class BIMConverseRAG:
    """
    BIMConverse core class for interacting with IFC knowledge graphs using natural language.
    
    This class integrates Neo4j GraphRAG to enable querying of building models stored
    in Neo4j using conversational language.
    """
    
    def __init__(
        self, 
        config_path: Optional[str] = None,
        neo4j_uri: Optional[str] = None,
        neo4j_username: Optional[str] = None,
        neo4j_password: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        """
        Initialize the BIMConverseRAG instance.
        
        Args:
            config_path: Path to the configuration file
            neo4j_uri: Neo4j connection URI (overrides config)
            neo4j_username: Neo4j username (overrides config)
            neo4j_password: Neo4j password (overrides config)
            openai_api_key: OpenAI API key (overrides config)
        """
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Override config with explicit parameters if provided
        if neo4j_uri:
            self.config["neo4j"]["uri"] = neo4j_uri
        if neo4j_username:
            self.config["neo4j"]["username"] = neo4j_username
        if neo4j_password:
            self.config["neo4j"]["password"] = neo4j_password
        if openai_api_key:
            self.config["openai"]["api_key"] = openai_api_key
            
        # Set OpenAI API key in environment
        if self.config["openai"]["api_key"]:
            os.environ["OPENAI_API_KEY"] = self.config["openai"]["api_key"]
        
        # Initialize Neo4j connection
        self._initialize_connection()
        
        # Initialize RAG components
        self._initialize_rag()
        
        # Initialize conversation context
        self.conversation_history = []
        self.max_history_length = 10  # Default history length
        self.context_enabled = False  # Context is disabled by default
        
        # Apply conversation settings from config if provided
        if "conversation" in self.config:
            self.max_history_length = self.config["conversation"].get("max_history_length", 10)
            self.context_enabled = self.config["conversation"].get("enabled", False)
        
        logger.info(f"BIMConverse initialized with Neo4j connection: {self.config['neo4j']['uri']}")
        
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        Load configuration from file or use defaults.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Dictionary containing the configuration
        """
        default_config = {
            "neo4j": {
                "uri": "neo4j://localhost:7687",
                "username": "neo4j",
                "password": "test1234",
                "database": "neo4j"
            },
            "openai": {
                "api_key": os.environ.get("OPENAI_API_KEY", ""),
                "embedding_model": "text-embedding-3-large",
                "llm_model": "gpt-4o",
                "temperature": 0.1
            },
            "graph_schema": {
                "node_labels": [
                    "Project", "Building", "Storey", "Space", "Element", 
                    "Wall", "Window", "Door", "Material"
                ],
                "relationship_types": [
                    "CONTAINS", "ADJACENT", "IS_MADE_OF", "CONNECTED_TO"
                ]
            },
            "retrieval": {
                "top_k": 5,
                "similarity_threshold": 0.7,
                "include_graph_context": True
            },
            "conversation": {
                "enabled": False,
                "max_history_length": 10
            }
        }
        
        if not config_path:
            logger.info("No configuration file provided, using defaults")
            return default_config
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                logger.info(f"Loaded configuration from {config_path}")
                
                # Merge with defaults to ensure all required fields exist
                if "neo4j" not in config:
                    config["neo4j"] = default_config["neo4j"]
                if "openai" not in config:
                    config["openai"] = default_config["openai"]
                if "graph_schema" not in config:
                    config["graph_schema"] = default_config["graph_schema"]
                if "retrieval" not in config:
                    config["retrieval"] = default_config["retrieval"]
                if "conversation" not in config:
                    config["conversation"] = default_config["conversation"]
                    
                return config
        except Exception as e:
            logger.warning(f"Failed to load configuration from {config_path}: {e}")
            logger.warning("Using default configuration")
            return default_config
    
    def _initialize_connection(self):
        """Initialize the Neo4j database connection."""
        try:
            self.driver = GraphDatabase.driver(
                self.config["neo4j"]["uri"],
                auth=(self.config["neo4j"]["username"], self.config["neo4j"]["password"])
            )
            
            # Test connection
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                test_value = result.single()["test"]
                if test_value != 1:
                    raise Exception("Connection test failed")
                
            logger.info("Successfully connected to Neo4j database")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise ConnectionError(f"Could not connect to Neo4j: {e}")
    
    def _initialize_rag(self):
        """Initialize the GraphRAG components."""
        try:
            # Create embeddings provider
            self.embedder = OpenAIEmbeddings(
                model=self.config["openai"]["embedding_model"]
            )
            
            # Create the LLM for generation
            self.llm = OpenAILLM(
                model_name=self.config["openai"]["llm_model"],
                model_params={"temperature": self.config["openai"]["temperature"]}
            )
            
            # Create the retriever based on configuration
            # Use Text2CypherRetriever that can generate Cypher queries based on natural language
            self.retriever = Text2CypherRetriever(
                driver=self.driver,
                embedder=self.embedder,
                llm=self.llm
            )

            # Create the RAG pipeline
            self.rag = GraphRAG(
                retriever=self.retriever,
                llm=self.llm
            )
            
            logger.info("Successfully initialized GraphRAG components")
        except Exception as e:
            logger.error(f"Failed to initialize GraphRAG components: {e}")
            raise RuntimeError(f"Could not initialize GraphRAG components: {e}")
    
    def query(self, question: str, include_sources: bool = True, use_context: Optional[bool] = None) -> Dict[str, Any]:
        """
        Execute a natural language query against the knowledge graph.
        
        Args:
            question: The natural language query
            include_sources: Whether to include source information in the response
            use_context: Override the instance's context_enabled setting
            
        Returns:
            Dictionary containing the query results
        """
        try:
            # Determine if context should be used
            use_context_for_query = self.context_enabled
            if use_context is not None:
                use_context_for_query = use_context
                
            # Format conversation context if needed
            context = ""
            if use_context_for_query and self.conversation_history:
                context = self._format_context_for_query()
                logger.info("Using conversation context for query")
            
            # Set retriever config
            retriever_config = {
                "top_k": self.config["retrieval"].get("top_k", 5)
            }
            
            # Prepend context if available
            query_with_context = question
            if context:
                query_with_context = f"{context}\n\nCurrent question: {question}"
            
            # Execute the query
            response = self.rag.search(
                query_text=query_with_context,
                retriever_config=retriever_config
            )
            
            # Format the response
            result = {
                "question": question,
                "answer": response.answer,
                "context_used": use_context_for_query,
            }
            
            # Include sources if requested
            if include_sources:
                result["sources"] = [str(source) for source in response.context]
                result["cypher"] = response.cypher if hasattr(response, "cypher") else ""
            
            # Add to conversation history if context is enabled
            if use_context_for_query:
                self.add_to_conversation_history(question, response.answer)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return {
                "question": question,
                "answer": f"Error: {str(e)}",
                "error": True
            }
    
    def _format_context_for_query(self) -> str:
        """Format conversation history as context for the next query."""
        context_parts = ["Previous conversation:"]
        for q, a in self.conversation_history:
            context_parts.append(f"Question: {q}")
            context_parts.append(f"Answer: {a}")
        return "\n".join(context_parts)
    
    def add_to_conversation_history(self, question: str, answer: str) -> None:
        """
        Add a question-answer pair to the conversation history.
        
        Args:
            question: The user's question
            answer: The system's answer
        """
        self.conversation_history.append((question, answer))
        
        # Trim history if it exceeds the maximum length
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]
        
        logger.debug(f"Added to conversation history (total: {len(self.conversation_history)})")
    
    def get_conversation_history(self) -> List[Tuple[str, str]]:
        """Get the current conversation history."""
        return self.conversation_history
    
    def clear_conversation_history(self) -> None:
        """Clear the conversation history."""
        self.conversation_history = []
        logger.info("Conversation history cleared")
    
    def set_context_enabled(self, enabled: bool) -> None:
        """
        Enable or disable conversation context.
        
        Args:
            enabled: Whether conversation context should be enabled
        """
        self.context_enabled = enabled
        logger.info(f"Conversation context {'enabled' if enabled else 'disabled'}")
    
    def set_max_history_length(self, length: int) -> None:
        """
        Set the maximum conversation history length.
        
        Args:
            length: Maximum number of conversation exchanges to keep
            
        Raises:
            ValueError: If length is not a positive integer
        """
        if not isinstance(length, int) or length <= 0:
            raise ValueError("Maximum history length must be a positive integer")
        
        self.max_history_length = length
        
        # Trim history if necessary
        if len(self.conversation_history) > length:
            self.conversation_history = self.conversation_history[-length:]
            
        logger.info(f"Maximum history length set to {length}")
    
    def get_conversation_settings(self) -> Dict[str, Any]:
        """Get the current conversation context settings."""
        return {
            "enabled": self.context_enabled,
            "max_history_length": self.max_history_length,
            "current_history_length": len(self.conversation_history)
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge graph.
        
        Returns:
            Dictionary containing node and relationship statistics
        """
        try:
            with self.driver.session() as session:
                # Count total nodes
                result = session.run("MATCH (n) RETURN count(n) as count")
                nodes_count = result.single()["count"]
                
                # Count total relationships
                result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                relationships_count = result.single()["count"]
                
                # Count nodes by label
                result = session.run("""
                    CALL db.labels() YIELD label
                    MATCH (n:`${label}`)
                    RETURN label, count(n) as count
                    ORDER BY label
                """)
                labels = {record["label"]: record["count"] for record in result}
                
                # Count relationships by type
                result = session.run("""
                    CALL db.relationshipTypes() YIELD relationshipType
                    MATCH ()-[r:`${relationshipType}`]->()
                    RETURN relationshipType, count(r) as count
                    ORDER BY relationshipType
                """)
                relationship_types = {record["relationshipType"]: record["count"] for record in result}
                
                return {
                    "nodes": nodes_count,
                    "relationships": relationships_count,
                    "labels": labels,
                    "relationship_types": relationship_types
                }
        except Exception as e:
            logger.error(f"Error getting database statistics: {e}")
            return {
                "error": str(e),
                "nodes": 0,
                "relationships": 0,
                "labels": {},
                "relationship_types": {}
            }
    
    def close(self):
        """Close the database connection."""
        if hasattr(self, 'driver'):
            self.driver.close()
            logger.info("Database connection closed")

def create_config_file(
    output_path: str, 
    neo4j_uri: str, 
    neo4j_username: str, 
    neo4j_password: str,
    openai_api_key: str = "",
    project_name: str = "IFC Building Project",
    context_enabled: bool = False,
    max_history_length: int = 10
) -> str:
    """
    Create a configuration file for BIMConverseRAG.
    
    Args:
        output_path: Path to save the configuration file
        neo4j_uri: Neo4j connection URI
        neo4j_username: Neo4j username
        neo4j_password: Neo4j password
        openai_api_key: OpenAI API key
        project_name: Name of the project
        context_enabled: Whether conversation context is enabled by default
        max_history_length: Maximum conversation history length
        
    Returns:
        Path to the created configuration file
    """
    config = {
        "project_name": project_name,
        "neo4j": {
            "uri": neo4j_uri,
            "username": neo4j_username,
            "password": neo4j_password,
            "database": "neo4j"
        },
        "openai": {
            "api_key": openai_api_key,
            "embedding_model": "text-embedding-3-large",
            "llm_model": "gpt-4o",
            "temperature": 0.1
        },
        "retrieval": {
            "top_k": 5,
            "similarity_threshold": 0.7,
            "include_graph_context": True
        },
        "conversation": {
            "enabled": context_enabled,
            "max_history_length": max_history_length
        }
    }
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Write configuration to file
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"Configuration file created at {output_path}")
    return output_path 