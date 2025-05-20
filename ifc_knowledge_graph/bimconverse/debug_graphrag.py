#!/usr/bin/env python
"""
Debug script for Neo4j GraphRAG API.

This script tests the Neo4j GraphRAG API directly to understand the result structure.
"""

import os
import sys
import logging
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
logger = logging.getLogger("DebugGraphRAG")

def debug_api():
    """Debug the Neo4j GraphRAG API directly."""
    # Check if OpenAI API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    
    # Get Neo4j connection details
    neo4j_uri = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
    neo4j_username = os.environ.get("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD", "test1234")
    
    logger.info(f"Testing Neo4j GraphRAG API with URI: {neo4j_uri}")
    
    try:
        # Connect to Neo4j
        driver = GraphDatabase.driver(
            neo4j_uri, 
            auth=(neo4j_username, neo4j_password)
        )
        
        # Test the connection
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as count")
            count = result.single()["count"]
            logger.info(f"Connected to Neo4j database with {count} nodes")
        
        # Create embeddings provider
        embedder = OpenAIEmbeddings(
            model="text-embedding-3-large"
        )
        
        # Create the LLM
        llm = OpenAILLM(
            model_name="gpt-4o",
            model_params={"temperature": 0.1}
        )
        
        # Create the schema for the retriever
        building_schema = """
        Node properties:
        Project {GlobalId: STRING, Name: STRING}
        Site {GlobalId: STRING, Name: STRING}
        Building {GlobalId: STRING, Name: STRING}
        Storey {GlobalId: STRING, Name: STRING}
        Space {GlobalId: STRING, Name: STRING}
        Wall {GlobalId: STRING, Name: STRING}
        Window {GlobalId: STRING, Name: STRING}
        Door {GlobalId: STRING, Name: STRING}
        Furniture {GlobalId: STRING, Name: STRING}
        Material {Name: STRING}
        
        Relationship properties:
        CONTAINS {}
        DEFINES {}
        HAS_PROPERTY_SET {}
        HAS_PROPERTY {}
        IS_MADE_OF {}
        CONNECTED_TO {}
        
        The relationships:
        (:Project)-[:CONTAINS]->(:Site)
        (:Site)-[:CONTAINS]->(:Building)
        (:Building)-[:CONTAINS]->(:Storey)
        (:Storey)-[:CONTAINS]->(:Space)
        (:Space)-[:CONTAINS]->(:Wall)
        (:Space)-[:CONTAINS]->(:Door)
        (:Space)-[:CONTAINS]->(:Window)
        (:Space)-[:CONTAINS]->(:Furniture)
        """
        
        # Create the retriever
        logger.info("Creating Text2CypherRetriever")
        retriever = Text2CypherRetriever(
            driver=driver,
            llm=llm,
            neo4j_schema=building_schema
        )
        
        # Create the RAG
        logger.info("Creating GraphRAG")
        rag = GraphRAG(
            retriever=retriever,
            llm=llm
        )
        
        # Test query
        query = "What spaces are in this building?"
        logger.info(f"Testing query: '{query}'")
        
        # Execute the query
        response = rag.search(query)
        
        # Debug response object
        logger.info(f"Response type: {type(response).__name__}")
        logger.info(f"Response dir: {dir(response)}")
        
        # Access response attributes
        logger.info(f"Response answer: {response.answer if hasattr(response, 'answer') else 'No answer attribute'}")
        
        if hasattr(response, "retriever_result"):
            retriever_result = response.retriever_result
            logger.info(f"Retriever result type: {type(retriever_result).__name__}")
            logger.info(f"Retriever result dir: {dir(retriever_result)}")
            
            if hasattr(retriever_result, "metadata"):
                logger.info(f"Metadata: {retriever_result.metadata}")
            else:
                logger.info("No metadata attribute in retriever_result")
                
            if hasattr(retriever_result, "items"):
                logger.info(f"Items count: {len(retriever_result.items)}")
                
                for i, item in enumerate(retriever_result.items):
                    logger.info(f"Item {i} type: {type(item).__name__}")
                    logger.info(f"Item {i} dir: {dir(item)}")
                    
                    if hasattr(item, "content"):
                        logger.info(f"Item {i} content: {item.content}")
                    
                    if hasattr(item, "metadata"):
                        logger.info(f"Item {i} metadata: {item.metadata}")
        
        # Close connection
        driver.close()
        logger.info("Debug completed successfully")
        
    except Exception as e:
        logger.error(f"Error during debug: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    debug_api() 