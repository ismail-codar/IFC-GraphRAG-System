#!/usr/bin/env python
"""
Test script for BIMConverse Core Module.

This script tests the core functionality of BIMConverse, specifically
the Text2CypherRetriever integration with Neo4j GraphRAG.
"""

import os
import sys
import json
import logging
import inspect
from typing import Dict, Any

from core import BIMConverseRAG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BIMConverseTest")

def debug_object(obj, prefix=""):
    """Helper function to inspect object attributes and methods."""
    if obj is None:
        return f"{prefix}Object is None"
    
    result = [f"{prefix}Type: {type(obj).__name__}"]
    
    # Get all attributes and methods
    for name in dir(obj):
        # Skip private attributes
        if name.startswith('_'):
            continue
        
        try:
            attr = getattr(obj, name)
            
            # Check if it's a method
            if inspect.ismethod(attr) or inspect.isfunction(attr):
                result.append(f"{prefix}{name}: <method>")
            else:
                # For attributes, get the value
                value_str = str(attr)
                if len(value_str) > 100:
                    value_str = value_str[:100] + "..."
                result.append(f"{prefix}{name}: {value_str}")
        except Exception as e:
            result.append(f"{prefix}{name}: <error: {str(e)}>")
    
    return "\n".join(result)

def test_with_config():
    """Test BIMConverseRAG with a test configuration."""
    # Check if OpenAI API key is set in environment
    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY environment variable not set")
        logger.info("Please set your OpenAI API key as an environment variable")
        sys.exit(1)
    
    # Create test configuration
    config = {
        "neo4j_uri": os.environ.get("NEO4J_URI", "neo4j://localhost:7687"),
        "neo4j_username": os.environ.get("NEO4J_USERNAME", "neo4j"),
        "neo4j_password": os.environ.get("NEO4J_PASSWORD", "test1234"),
        "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
        "context_enabled": True,
        "max_history": 5
    }
    
    logger.info("Testing BIMConverseRAG with configuration:")
    logger.info(f"  Neo4j URI: {config['neo4j_uri']}")
    logger.info(f"  Neo4j Username: {config['neo4j_username']}")
    logger.info(f"  Context Enabled: {config['context_enabled']}")
    logger.info(f"  Max History: {config['max_history']}")
    
    try:
        # Initialize BIMConverseRAG
        bimconverse = BIMConverseRAG(
            neo4j_uri=config['neo4j_uri'],
            neo4j_username=config['neo4j_username'],
            neo4j_password=config['neo4j_password'],
            openai_api_key=config['openai_api_key']
        )
        
        # Set conversation context settings
        bimconverse.set_context_enabled(config['context_enabled'])
        bimconverse.set_max_history_length(config['max_history'])
        
        # Print statistics
        try:
            stats = bimconverse.get_stats()
            logger.info("Knowledge Graph Statistics:")
            logger.info(f"  Nodes: {stats.get('nodes', 'N/A')}")
            logger.info(f"  Relationships: {stats.get('relationships', 'N/A')}")
            
            # Show top 5 node labels if available
            if 'labels' in stats:
                logger.info("  Top 5 Node Labels:")
                for label, count in list(stats.get('labels', {}).items())[:5]:
                    logger.info(f"    {label}: {count}")
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
        
        # Test a query with more detailed debugging
        test_query = "What spaces are in this building?"
        logger.info(f"Testing query: '{test_query}'")
        
        try:
            # Execute the query directly with the RAG API
            logger.info("Executing search directly with GraphRAG API...")
            response = bimconverse.rag.search(test_query)
            
            # Detailed inspection of response object
            logger.info("\nDEBUG RESPONSE OBJECT:")
            logger.info(debug_object(response))
            
            # Check for retriever_result attribute
            if hasattr(response, "retriever_result"):
                logger.info("\nDEBUG RETRIEVER RESULT:")
                logger.info(debug_object(response.retriever_result, prefix="  "))
                
                # Inspect items if available
                if hasattr(response.retriever_result, "items"):
                    for i, item in enumerate(response.retriever_result.items):
                        logger.info(f"\nDEBUG ITEM {i}:")
                        logger.info(debug_object(item, prefix="  "))
            
            # Now try our custom query method
            logger.info("\nExecuting query with custom BIMConverseRAG method...")
            result = bimconverse.query(test_query)
            
            # Print query results
            logger.info("Query Results:")
            logger.info(f"  Answer: {result['answer']}")
            logger.info(f"  Generated Cypher: {result.get('cypher_query', 'None')}")
            
            # Test chat history functionality
            logger.info("\nTesting follow-up query with conversation context...")
            followup_query = "How many of them are there?"
            follow_result = bimconverse.query(followup_query)
            
            logger.info("Follow-up Results:")
            logger.info(f"  Answer: {follow_result['answer']}")
            logger.info(f"  Generated Cypher: {follow_result.get('cypher_query', 'None')}")
            
            # Get context settings
            context_settings = bimconverse.get_conversation_settings()
            logger.info("Conversation Context Settings:")
            logger.info(f"  Enabled: {context_settings['enabled']}")
            logger.info(f"  Max History Length: {context_settings['max_history_length']}")
            logger.info(f"  Current History Length: {context_settings['current_history_length']}")
            
        except Exception as e:
            logger.error(f"Error testing query: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        # Close the connection
        bimconverse.close()
        logger.info("Test completed")
        
    except Exception as e:
        logger.error(f"Error testing BIMConverseRAG: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    test_with_config() 