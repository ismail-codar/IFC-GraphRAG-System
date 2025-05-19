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
from typing import Dict, Any

from core import BIMConverseRAG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BIMConverseTest")

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
        "neo4j_password": os.environ.get("NEO4J_PASSWORD", "password"),
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
        bimconverse = BIMConverseRAG(config=config)
        
        # Print statistics (this will verify connection works)
        try:
            stats = bimconverse.get_statistics()
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
        
        # Test a query
        test_query = "What spaces are in this building?"
        logger.info(f"Testing query: '{test_query}'")
        
        result = bimconverse.query(test_query)
        
        # Print query results
        logger.info("Query Results:")
        logger.info(f"  Answer: {result['answer']}")
        logger.info(f"  Generated Cypher: {result['cypher_query']}")
        
        # Test conversation context
        if config['context_enabled']:
            # Test follow-up question
            followup_query = "How many of them are there?"
            logger.info(f"Testing follow-up query: '{followup_query}'")
            
            result = bimconverse.query(followup_query)
            
            # Print follow-up results
            logger.info("Follow-up Results:")
            logger.info(f"  Answer: {result['answer']}")
            logger.info(f"  Generated Cypher: {result['cypher_query']}")
            
            # Get context settings
            context_settings = bimconverse.get_context_settings()
            logger.info("Conversation Context Settings:")
            logger.info(f"  Enabled: {context_settings['enabled']}")
            logger.info(f"  Max History Length: {context_settings['max_history_length']}")
            logger.info(f"  Current History Length: {context_settings['current_history_length']}")
        
        # Close the connection
        bimconverse.close()
        logger.info("Test completed successfully")
        
    except Exception as e:
        logger.error(f"Error testing BIMConverseRAG: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_with_config() 