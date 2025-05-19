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
from neo4j_graphrag.retrievers import KnowledgeGraphRetriever, VectorRetriever, HybridRetriever

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
                    
                # Apply conversation settings if provided
                if "conversation" in config:
                    self.max_history_length = config["conversation"].get("max_history_length", 10)
                    self.context_enabled = config["conversation"].get("enabled", False)
                    
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
            
            # Create the retriever
            self.retriever = KnowledgeGraphRetriever(
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
            raise Exception(f"GraphRAG initialization failed: {e}")
    
    def query(self, question: str, include_sources: bool = True, use_context: Optional[bool] = None) -> Dict[str, Any]:
        """
        Query the IFC knowledge graph using natural language.
        
        Args:
            question: Natural language question about the building
            include_sources: Whether to include source information in the response
            use_context: Whether to use conversation context (overrides default setting)
            
        Returns:
            Dictionary containing the answer and optional metadata
        """
        try:
            # Determine whether to use context for this query
            using_context = self.context_enabled if use_context is None else use_context
            
            # Configure retrieval parameters
            retriever_config = {
                "node_labels": self.config["graph_schema"]["node_labels"],
                "relationship_types": self.config["graph_schema"]["relationship_types"],
                "include_graph_context": self.config["retrieval"]["include_graph_context"],
                "top_k": self.config["retrieval"]["top_k"]
            }
            
            # Prepare context if enabled
            if using_context and self.conversation_history:
                # Format conversation history for context
                context = self._format_context_for_query()
                query_with_context = f"{context}\n\nNew question: {question}"
                logger.debug(f"Using context with query. Context length: {len(context)}")
            else:
                query_with_context = question
            
            # Execute the RAG pipeline
            response = self.rag.search(
                query_text=query_with_context,
                retriever_config=retriever_config
            )
            
            # Format the response
            result = {
                "answer": response.answer,
                "question": question,
                "context_used": using_context
            }
            
            if include_sources:
                result["sources"] = response.sources
                result["cypher"] = response.cypher_query
            
            # Add to conversation history
            if using_context:
                self.add_to_conversation_history(question, response.answer)
            
            return result
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "answer": f"I encountered an error while processing your query: {e}",
                "question": question,
                "error": str(e)
            }
    
    def _format_context_for_query(self) -> str:
        """Format conversation history as context for the next query."""
        context = "Previous conversation:\n"
        for i, (q, a) in enumerate(self.conversation_history):
            context += f"User: {q}\nAssistant: {a}\n\n"
        return context
    
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
    
    def get_conversation_history(self) -> List[Tuple[str, str]]:
        """
        Get the current conversation history.
        
        Returns:
            List of (question, answer) tuples
        """
        return self.conversation_history
    
    def clear_conversation_history(self) -> None:
        """Clear the conversation history."""
        self.conversation_history = []
        logger.info("Conversation history cleared")
    
    def set_context_enabled(self, enabled: bool) -> None:
        """
        Enable or disable conversation context.
        
        Args:
            enabled: Whether to enable conversation context
        """
        self.context_enabled = enabled
        logger.info(f"Conversation context {'enabled' if enabled else 'disabled'}")
    
    def set_max_history_length(self, length: int) -> None:
        """
        Set the maximum number of exchanges to keep in conversation history.
        
        Args:
            length: Maximum number of exchanges to keep
        """
        if length < 1:
            raise ValueError("History length must be at least 1")
        
        self.max_history_length = length
        
        # Trim history if it exceeds the new maximum length
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]
            
        logger.info(f"Max conversation history length set to {length}")
    
    def get_conversation_settings(self) -> Dict[str, Any]:
        """
        Get the current conversation settings.
        
        Returns:
            Dictionary containing conversation settings
        """
        return {
            "enabled": self.context_enabled,
            "max_history_length": self.max_history_length,
            "current_history_length": len(self.conversation_history)
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current Neo4j database.
        
        Returns:
            Dictionary containing database statistics
        """
        try:
            with self.driver.session() as session:
                # Get node counts by label
                labels_query = """
                MATCH (n)
                RETURN labels(n) AS label, count(*) AS count
                ORDER BY count DESC
                """
                labels_result = session.run(labels_query)
                labels_stats = {str(record["label"]): record["count"] for record in labels_result}
                
                # Get relationship counts by type
                rels_query = """
                MATCH ()-[r]->()
                RETURN type(r) AS type, count(*) AS count
                ORDER BY count DESC
                """
                rels_result = session.run(rels_query)
                rels_stats = {record["type"]: record["count"] for record in rels_result}
                
                # Get total counts
                totals_query = """
                MATCH (n)
                OPTIONAL MATCH (n)-[r]->()
                RETURN count(DISTINCT n) AS nodes, count(DISTINCT r) AS relationships
                """
                totals_result = session.run(totals_query).single()
                
                return {
                    "nodes": totals_result["nodes"],
                    "relationships": totals_result["relationships"],
                    "labels": labels_stats,
                    "relationship_types": rels_stats
                }
        except Exception as e:
            logger.error(f"Error getting database statistics: {e}")
            return {"error": str(e)}
    
    def close(self):
        """Close the Neo4j connection."""
        if hasattr(self, 'driver'):
            self.driver.close()
            logger.info("Neo4j connection closed")

def create_config_file(
    output_path: str, 
    neo4j_uri: str, 
    neo4j_username: str, 
    neo4j_password: str,
    openai_api_key: str = "",
    project_name: str = "IFC Building Project"
) -> str:
    """
    Create a configuration file for BIMConverse.
    
    Args:
        output_path: Path to save the configuration file
        neo4j_uri: Neo4j connection URI
        neo4j_username: Neo4j username
        neo4j_password: Neo4j password
        openai_api_key: OpenAI API key
        project_name: Name of the project
        
    Returns:
        Path to the created configuration file
    """
    config = {
        "project_name": project_name,
        "description": f"Configuration for {project_name}",
        
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
        },
        
        "ui": {
            "title": project_name,
            "description": "Query your building model using natural language",
            "theme": "default",
            "example_queries": [
                "What spaces are on the ground floor?",
                "Show me all doors between the kitchen and dining room",
                "Which walls use concrete as a material?",
                "What is the total area of all bedrooms?",
                "How many windows are in the north-facing walls?"
            ]
        }
    }
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Write configuration to file
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"Created configuration file at {output_path}")
    return output_path

if __name__ == "__main__":
    # Example usage
    print("BIMConverse Core Module")
    print("This module is not meant to be run directly.")
    print("Import and use the BIMConverseRAG class in your application.") 