#!/usr/bin/env python
"""
Simplified test script for multihop reasoning in BIMConverse.

This script validates the MultihopRetriever code structure and API without 
requiring actual API access or a Neo4j database.
"""

import os
import sys
import json
import logging
import inspect
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

# Add the parent directory to the path
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MultihopTest")

# Create mock imports for testing
class MockDriver:
    def session(self):
        session = MagicMock()
        session.run.return_value = MagicMock()
        return session

class MockLLM:
    def generate(self, prompt):
        # Simple mock that returns different responses based on prompt content
        if "decompose" in prompt or "query_decomposition" in prompt:
            return """
            I'll break this down into the following steps:
            
            1. First, find the kitchen space
            2. Next, find spaces adjacent to the kitchen
            3. Then, count windows in each adjacent space
            4. Finally, filter spaces with more than 2 windows
            """
        elif "chain_of_thought" in prompt:
            return """
            Let me break this down step by step:
            
            Step 1: Find the kitchen
            ```
            MATCH (kitchen:Space)
            WHERE kitchen.Name CONTAINS 'Kitchen'
            ```
            
            Step 2: Find adjacent spaces
            ```
            MATCH (kitchen:Space)-[:ADJACENT_TO]-(adjacent:Space)
            WHERE kitchen.Name CONTAINS 'Kitchen'
            ```
            
            Step 3: Count windows and filter
            ```
            MATCH (kitchen:Space)-[:ADJACENT_TO]-(adjacent:Space)
            WHERE kitchen.Name CONTAINS 'Kitchen'
            WITH adjacent
            MATCH (adjacent)-[:BOUNDED_BY]->(window:Window)
            WITH adjacent, count(window) as window_count
            WHERE window_count > 2
            RETURN adjacent.Name, window_count
            ```
            """
        elif "context_accumulation" in prompt:
            return """
            Based on previous findings, I'll continue with:
            
            ```
            MATCH (kitchen:Space)-[:ADJACENT_TO]-(adjacent:Space)
            WHERE kitchen.Name CONTAINS 'Kitchen'
            WITH adjacent
            MATCH (adjacent)-[:BOUNDED_BY]->(window:Window)
            WITH adjacent, count(window) as window_count
            WHERE window_count > 2
            RETURN adjacent.Name, window_count
            ```
            """
        else:
            return """
            ```cypher
            MATCH (kitchen:Space)-[:ADJACENT_TO]-(adjacent:Space)
            WHERE kitchen.Name CONTAINS 'Kitchen'
            WITH adjacent
            MATCH (adjacent)-[:BOUNDED_BY]->(window:Window)
            WITH adjacent, count(window) as window_count
            WHERE window_count > 2
            RETURN adjacent.Name, window_count
            ```
            """

# Import MultihopRetriever for testing
try:
    from bimconverse.retrievers import MultihopRetriever
except ImportError as e:
    logger.error(f"Error importing MultihopRetriever: {e}")
    sys.exit(1)

class TestMultihopRetriever(unittest.TestCase):
    """Test the MultihopRetriever functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock driver and LLM
        self.driver = MockDriver()
        self.llm = MockLLM()
        
        # Create a MultihopRetriever instance with mocks
        self.retriever = MultihopRetriever(self.driver, self.llm)
    
    def test_decompose_query(self):
        """Test query decomposition functionality."""
        # Test a complex spatial query
        query = "Find all rooms adjacent to the kitchen that have more than 2 windows"
        sub_queries = self.retriever._decompose_query(query)
        
        # Verify we got multiple sub-queries
        self.assertTrue(len(sub_queries) > 0, "Should decompose into multiple sub-queries")
        
        # Log the decomposed sub-queries
        logger.info(f"Decomposed query into {len(sub_queries)} sub-queries:")
        for i, subq in enumerate(sub_queries):
            logger.info(f"  {i+1}. {subq}")
    
    def test_chain_of_thought_decomposition(self):
        """Test chain-of-thought decomposition."""
        # Test with a complex query
        query = "Find materials used in walls that are adjacent to spaces containing wooden furniture"
        sub_queries = self.retriever._chain_of_thought_decomposition(query)
        
        # Verify we got multiple reasoning steps
        self.assertTrue(len(sub_queries) > 0, "Should decompose into multiple reasoning steps")
        
        # Log the reasoning steps
        logger.info(f"Chain-of-thought produced {len(sub_queries)} reasoning steps:")
        for i, step in enumerate(sub_queries):
            logger.info(f"  {i+1}. {step}")
    
    def test_generate_cypher(self):
        """Test Cypher generation from natural language."""
        # Test simple query
        query = "What spaces are adjacent to the kitchen?"
        cypher = self.retriever._generate_cypher(query)
        
        # Verify we got a Cypher query
        self.assertTrue(len(cypher) > 0, "Should generate a valid Cypher query")
        self.assertTrue("MATCH" in cypher, "Cypher query should contain MATCH clause")
        
        # Log the generated Cypher
        logger.info(f"Generated Cypher: {cypher}")
        
        # Test with context accumulation
        context = "Step 1 found 1 kitchen space."
        cypher_with_context = self.retriever._generate_cypher(
            "Find spaces adjacent to the kitchen", 
            context
        )
        
        # Verify context affected the generation
        self.assertTrue(len(cypher_with_context) > 0, "Should generate a Cypher query with context")
        logger.info(f"Generated Cypher with context: {cypher_with_context}")
    
    def test_multihop_search(self):
        """Test the complete multihop search process."""
        # Patch the _execute_cypher method to return mock results
        with patch.object(self.retriever, '_execute_cypher', return_value=[
            {"space": {"Name": "Living Room"}, "window_count": 3},
            {"space": {"Name": "Dining Room"}, "window_count": 4}
        ]):
            # Test a complex query that requires multiple hops
            query = "Find all rooms adjacent to the kitchen that have more than 2 windows"
            result = self.retriever.search(query)
            
            # Verify result structure
            self.assertTrue(hasattr(result, "query"), "Result should have query attribute")
            self.assertTrue(hasattr(result, "sub_queries"), "Result should have sub_queries attribute")
            self.assertTrue(hasattr(result, "intermediate_results"), "Result should have intermediate_results attribute")
            
            # Log the result
            logger.info(f"Multihop search result for '{query}':")
            logger.info(f"  Answer: {result.answer}")
            logger.info(f"  Sub-queries: {len(result.sub_queries)}")
            logger.info(f"  Metadata: {result.metadata}")
    
    def test_search_method_compatibility(self):
        """Test compatibility of search method with GraphRAG interface."""
        # Test the search method matches GraphRAG expectations
        with patch.object(self.retriever, 'retrieve', return_value={
            "query": "test query",
            "sub_queries": ["step 1", "step 2"],
            "intermediate_results": [{"results": [{"data": "value"}]}],
            "accumulated_context": "context",
            "strategy": "multihop"
        }):
            # Call the search method
            result = self.retriever.search("test query")
            
            # Verify it has the expected attributes for GraphRAG compatibility
            self.assertTrue(hasattr(result, "answer"), "Result should have answer attribute")
            self.assertTrue(hasattr(result, "metadata"), "Result should have metadata attribute")
            
            # Check metadata
            self.assertEqual(result.metadata["multihop"], True, "Metadata should indicate multihop")
            self.assertEqual(result.metadata["num_steps"], 2, "Metadata should show correct number of steps")

def main():
    """Run the tests."""
    unittest.main()

if __name__ == "__main__":
    main() 