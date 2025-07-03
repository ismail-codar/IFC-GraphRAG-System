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
from neo4j_graphrag.llm import OpenAILLM, OllamaLLM
from neo4j_graphrag.retrievers import VectorRetriever, HybridRetriever, Text2CypherRetriever

# Import custom retrievers
import bimconverse.retrievers as retrievers
from bimconverse.retrievers import MultihopRetriever

logger = logging.getLogger(__name__)

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
                "include_graph_context": True,
                "multihop_enabled": False,  # Flag to enable multihop reasoning
                "multihop_detection": True  # Automatically detect when to use multihop
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
            # Create the LLM for generation
            model_params = {
                "temperature": self.config["openai"]["temperature"]
            }
            if "base_url" in self.config["openai"]:
                model_params["base_url"] = self.config["openai"]["base_url"]
                os.environ.setdefault("OPENAI_BASE_URL", self.config["openai"]["base_url"])
            if "api_key" in self.config["openai"]:
                model_params["api_key"] = self.config["openai"]["api_key"]
                os.environ.setdefault("OPENAI_API_KEY", self.config["openai"]["api_key"])
            self.llm = OpenAILLM(
                model_name=self.config["openai"]["llm_model"],
                model_params=model_params
            )
            
            # delete self.llm.model_params
            if "base_url" in self.llm.model_params:
                del self.llm.model_params["base_url"]
            if "api_key" in self.llm.model_params:
                del self.llm.model_params["api_key"]
                
            # self.llm = OllamaLLM(
            #     model_name=self.config["openai"]["llm_model"],
            #     model_params=model_params
            # )
            
            # Create the retrievers
            self.text2cypher_retriever = self._initialize_text2cypher_retriever()
            
            # Initialize MultihopRetriever if enabled
            self.multihop_retriever = self._initialize_multihop_retriever()
            
            # Set the default retriever
            self.retriever = self.text2cypher_retriever
            
            # Create the RAG pipeline with the default retriever
            self.rag = GraphRAG(
                retriever=self.retriever,
                llm=self.llm
            )
            
            logger.info("Successfully initialized GraphRAG components")
        except Exception as e:
            logger.error(f"Failed to initialize GraphRAG components: {e}")
            raise RuntimeError(f"Could not initialize GraphRAG components: {e}")
    
    def _initialize_text2cypher_retriever(self):
        """Initialize the Text2CypherRetriever."""
        # Define schema based on actual database labels found in schema.py
        building_schema = """
        Node properties:
        Project {GlobalId: STRING, Name: STRING, Description: STRING}
        Site {GlobalId: STRING, Name: STRING, Description: STRING}
        Building {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
        Storey {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
        Space {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
        Element {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
        Wall {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
        Window {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
        Door {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
        Slab {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
        Beam {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
        Column {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
        Railing {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
        Furniture {GlobalId: STRING, Name: STRING, Description: STRING, IFCType: STRING}
        Material {Name: STRING, Description: STRING}
        PropertySet {Name: STRING}
        Property {Name: STRING, Value: STRING}

        Relationship properties:
        CONTAINS {}
        DEFINES {}
        HAS_PROPERTY_SET {}
        HAS_PROPERTY {}
        IS_MADE_OF {}
        CONNECTED_TO {}
        BOUNDED_BY {}
        ADJACENT_TO {}

        The relationships:
        (:Project)-[:CONTAINS]->(:Site)
        (:Site)-[:CONTAINS]->(:Building)
        (:Building)-[:CONTAINS]->(:Storey)
        (:Storey)-[:CONTAINS]->(:Space)
        (:Space)-[:CONTAINS]->(:Element)
        (:Space)-[:CONTAINS]->(:Wall)
        (:Space)-[:CONTAINS]->(:Door)
        (:Space)-[:CONTAINS]->(:Window)
        (:Space)-[:CONTAINS]->(:Furniture)
        (:Element)-[:HAS_PROPERTY_SET]->(:PropertySet)
        (:PropertySet)-[:HAS_PROPERTY]->(:Property)
        (:Element)-[:IS_MADE_OF]->(:Material)
        (:Wall)-[:IS_MADE_OF]->(:Material)
        (:Wall)-[:CONNECTED_TO]->(:Wall)
        (:Space)-[:ADJACENT_TO]->(:Space)
        (:Wall)-[:BOUNDED_BY]->(:Space)
        """
        
        try:
            # Create the Text2Cypher retriever
            retriever = Text2CypherRetriever(
                driver=self.driver,
                llm=self.llm,
                neo4j_schema=building_schema
            )
            logger.info("Successfully initialized Text2Cypher retriever")
            return retriever
        except Exception as e:
            logger.error(f"Failed to initialize Text2Cypher retriever: {e}")
            raise RuntimeError(f"Could not initialize Text2Cypher retriever: {e}")
    
    def _initialize_multihop_retriever(self):
        """Initialize the MultihopRetriever for complex multi-step queries."""
        try:
            # Create the MultihopRetriever
            retriever = MultihopRetriever(
                driver=self.driver,
                llm=self.llm
            )
            logger.info("Successfully initialized MultihopRetriever")
            return retriever
        except Exception as e:
            logger.error(f"Failed to initialize MultihopRetriever: {e}")
            logger.warning("Falling back to standard Text2Cypher retriever")
            return None
    
    def _detect_multihop_query(self, query: str) -> bool:
        """
        Detect if a query requires multi-hop reasoning.
        
        Args:
            query: The user's query text
            
        Returns:
            True if the query likely requires multi-hop reasoning, False otherwise
        """
        # Keywords that suggest multi-hop relationships
        multihop_indicators = [
            "adjacent to", "connected to", "nearest", "between", "path", 
            "route", "sequence", "connected", "linked", "relationship between",
            "and then", "followed by", "through", "via", "across",
            "that have", "that contain", "with properties", "that are also",
            "relation", "connection", "journey", "traverse"
        ]
        
        # Check for common multi-step query patterns
        query_lower = query.lower()
        for indicator in multihop_indicators:
            if indicator in query_lower:
                logger.info(f"Detected potential multi-hop query: '{indicator}' in '{query}'")
                return True
        
        # Check for multiple entity types in the same query
        entity_types = [
            "room", "space", "wall", "door", "window", "floor", "material", 
            "storey", "building", "beam", "column", "slab", "furniture"
        ]
        
        entity_count = sum(1 for entity in entity_types if entity in query_lower)
        if entity_count >= 2:
            logger.info(f"Detected potential multi-hop query: {entity_count} entity types in '{query}'")
            return True
            
        return False
    
    def query(self, query_text: str, use_multihop: Optional[bool] = None) -> Dict[str, Any]:
        """
        Execute a query against the IFC knowledge graph.
        
        Args:
            query_text: The user's natural language query
            use_multihop: Force use of multihop retriever (True) or standard retriever (False)
                        If None, auto-detect based on query complexity
            
        Returns:
            Dictionary containing the query results and metadata
        """
        logger.info(f"Processing query: {query_text}")
        
        # Determine whether to use multi-hop retrieval
        should_use_multihop = use_multihop
        
        # If not explicitly specified, auto-detect if query needs multi-hop reasoning
        if use_multihop is None and self.config["retrieval"].get("multihop_detection", True):
            should_use_multihop = self._detect_multihop_query(query_text)
        
        # Override with multihop_enabled setting if use_multihop is None
        if use_multihop is None and not self.config["retrieval"].get("multihop_enabled", False):
            should_use_multihop = False
            
        # If multihop retriever is not available, fall back to standard retriever
        if should_use_multihop and self.multihop_retriever is None:
            logger.warning("Multihop retriever is not available, falling back to standard retriever")
            should_use_multihop = False
            
        # Select the appropriate retriever
        if should_use_multihop:
            logger.info("Using multi-hop retrieval strategy")
            retriever = self.multihop_retriever
        else:
            logger.info("Using standard text-to-cypher retrieval strategy")
            retriever = self.text2cypher_retriever
            
        # Update the RAG pipeline with the selected retriever
        self.rag.retriever = retriever
        
        # Add conversation history if enabled
        context = ""
        if self.context_enabled and self.conversation_history:
            context = "Previous conversation:\n"
            for i, (q, a) in enumerate(self.conversation_history[-self.max_history_length:]):
                context += f"Q{i+1}: {q}\nA{i+1}: {a}\n"
            context += "\nCurrent question: "
            
            # Adjust query format if context is added
            query_with_context = f"{context}{query_text}"
        else:
            query_with_context = query_text
        
        # Execute the query using the RAG pipeline's search method 
        # (previously named "query" - this is the API change we're fixing)
        logging.info(f"Query with context: {query_with_context}")
        response = self.rag.search(
            query_text=query_with_context
        )
        logging.info(f"Response: {response}")
        
        # Extract relevant information
        result = {
            "query": query_text,
            "answer": response.answer if hasattr(response, "answer") else str(response),
            "retrieval_strategy": "multihop" if should_use_multihop else "standard",
            "metadata": {}
        }
        
        # Add different metadata based on retriever type
        if should_use_multihop and hasattr(response, "intermediate_results"):
            result["metadata"]["intermediate_results"] = response.intermediate_results
            result["metadata"]["sub_queries"] = getattr(response, "sub_queries", [])
        else:
            # Add standard retriever metadata
            if hasattr(response, "retriever_result") and response.retriever_result is not None:
                retriever_result = response.retriever_result
                
                # Extract cypher query from metadata if available
                if hasattr(retriever_result, "metadata") and retriever_result.metadata:
                    metadata = retriever_result.metadata
                    if isinstance(metadata, dict) and "cypher" in metadata:
                        result["metadata"]["cypher_query"] = metadata["cypher"]
                
                # Extract sources from items if available
                if hasattr(retriever_result, "items"):
                    result["metadata"]["records"] = [{
                        "content": item.content if hasattr(item, "content") else "",
                        "metadata": item.metadata if hasattr(item, "metadata") else {}
                    } for item in retriever_result.items]
            
        # Add conversation context if enabled
        if self.context_enabled:
            self.add_to_conversation_history(query_text, result["answer"])
            
        return result
    
    def add_to_conversation_history(self, question: str, answer: str) -> None:
        """
        Add a question-answer pair to the conversation history.
        
        Args:
            question: The user's question
            answer: The system's answer (string or dict with 'answer' key)
        """
        # Handle both string answers and dict answers with 'answer' key
        answer_text = answer
        if isinstance(answer, dict) and "answer" in answer:
            answer_text = answer["answer"]
            
        self.conversation_history.append((question, answer_text))
        
        # Trim history if needed
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]
        
        logger.debug(f"Added to conversation history, new length: {len(self.conversation_history)}")
    
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
            enabled: Whether to enable conversation context
        """
        self.context_enabled = enabled
        if "conversation" not in self.config:
            self.config["conversation"] = {}
        self.config["conversation"]["enabled"] = enabled
        logger.info(f"Conversation context {'enabled' if enabled else 'disabled'}")
        
    def set_multihop_enabled(self, enabled: bool) -> None:
        """
        Enable or disable multihop retrieval globally.
        
        Args:
            enabled: Whether to enable multihop retrieval
        """
        if "retrieval" not in self.config:
            self.config["retrieval"] = {}
        self.config["retrieval"]["multihop_enabled"] = enabled
        logger.info(f"Multihop retrieval globally {'enabled' if enabled else 'disabled'}")
        
    def set_multihop_detection(self, enabled: bool) -> None:
        """
        Enable or disable automatic detection of queries that need multihop retrieval.
        
        Args:
            enabled: Whether to enable automatic detection
        """
        if "retrieval" not in self.config:
            self.config["retrieval"] = {}
        self.config["retrieval"]["multihop_detection"] = enabled
        logger.info(f"Automatic multihop detection {'enabled' if enabled else 'disabled'}")
    
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
        """
        Get current conversation settings.
        
        Returns:
            Dictionary of conversation settings
        """
        return {
            "context_enabled": self.context_enabled,
            "max_history_length": self.max_history_length,
            "history_entries": len(self.conversation_history),
            "multihop_enabled": self.config["retrieval"].get("multihop_enabled", False),
            "multihop_detection": self.config["retrieval"].get("multihop_detection", True)
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
    max_history_length: int = 10,
    multihop_enabled: bool = False,
    multihop_detection: bool = True
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
        multihop_enabled: Whether multi-hop retrieval is enabled by default
        multihop_detection: Whether to auto-detect multi-hop queries
        
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
            "include_graph_context": True,
            "multihop_enabled": multihop_enabled,
            "multihop_detection": multihop_detection
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