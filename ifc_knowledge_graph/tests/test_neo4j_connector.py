"""
Tests for Neo4j connector and database operations.

This module contains tests for the Neo4j connector and database operations.
Note: These tests require a running Neo4j instance.
"""

import os
import sys
import unittest
from unittest.mock import patch, Mock

# Add the src directory to the Python path
src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
sys.path.insert(0, src_dir)

from ifc_to_graph.database import Neo4jConnector


class TestNeo4jConnector(unittest.TestCase):
    """Test cases for Neo4j connector."""
    
    @patch('ifc_to_graph.database.neo4j_connector.GraphDatabase')
    def test_connection(self, mock_graph_db):
        """Test database connection."""
        # Setup mock
        mock_driver = Mock()
        mock_graph_db.driver.return_value = mock_driver
        
        # Create connector
        connector = Neo4jConnector(
            uri="neo4j://localhost:7687",
            username="neo4j",
            password="password"
        )
        
        # Verify GraphDatabase.driver was called with correct parameters
        mock_graph_db.driver.assert_called_once_with(
            "neo4j://localhost:7687", 
            auth=("neo4j", "password")
        )
        
        # Verify connection was verified
        mock_driver.verify_connectivity.assert_called_once()
        
        # Verify driver is stored
        self.assertEqual(connector.driver, mock_driver)
    
    @patch('ifc_to_graph.database.neo4j_connector.GraphDatabase')
    def test_close(self, mock_graph_db):
        """Test closing database connection."""
        # Setup mock
        mock_driver = Mock()
        mock_graph_db.driver.return_value = mock_driver
        
        # Create and close connector
        connector = Neo4jConnector(
            uri="neo4j://localhost:7687",
            username="neo4j",
            password="password"
        )
        connector.close()
        
        # Verify driver.close was called
        mock_driver.close.assert_called_once()
        
        # Verify driver is set to None
        self.assertIsNone(connector.driver)
    
    @patch('ifc_to_graph.database.neo4j_connector.GraphDatabase')
    def test_get_session(self, mock_graph_db):
        """Test getting a session."""
        # Setup mock
        mock_driver = Mock()
        mock_session = Mock()
        mock_driver.session.return_value = mock_session
        mock_graph_db.driver.return_value = mock_driver
        
        # Create connector and get session
        connector = Neo4jConnector(
            uri="neo4j://localhost:7687",
            username="neo4j",
            password="password"
        )
        session = connector.get_session()
        
        # Verify session is created
        mock_driver.session.assert_called_once()
        self.assertEqual(session, mock_session)
    
    @patch('ifc_to_graph.database.neo4j_connector.GraphDatabase')
    def test_get_session_with_database(self, mock_graph_db):
        """Test getting a session with a specific database."""
        # Setup mock
        mock_driver = Mock()
        mock_session = Mock()
        mock_driver.session.return_value = mock_session
        mock_graph_db.driver.return_value = mock_driver
        
        # Create connector and get session with database
        connector = Neo4jConnector(
            uri="neo4j://localhost:7687",
            username="neo4j",
            password="password",
            database="testdb"
        )
        session = connector.get_session()
        
        # Verify session is created with database
        mock_driver.session.assert_called_once_with(database="testdb")
        self.assertEqual(session, mock_session)
    
    @patch('ifc_to_graph.database.neo4j_connector.GraphDatabase')
    def test_run_query(self, mock_graph_db):
        """Test running a query."""
        # Setup mock
        mock_driver = Mock()
        mock_session = Mock()
        mock_result = Mock()
        mock_record1 = Mock()
        mock_record2 = Mock()
        
        mock_record1.data.return_value = {"name": "Test1"}
        mock_record2.data.return_value = {"name": "Test2"}
        mock_result.__iter__.return_value = iter([mock_record1, mock_record2])
        
        mock_session.run.return_value = mock_result
        mock_session.__enter__.return_value = mock_session
        mock_driver.session.return_value = mock_session
        mock_graph_db.driver.return_value = mock_driver
        
        # Create connector and run query
        connector = Neo4jConnector(
            uri="neo4j://localhost:7687",
            username="neo4j",
            password="password"
        )
        result = connector.run_query(
            "MATCH (n) RETURN n.name as name",
            {"param": "value"}
        )
        
        # Verify session.run was called with correct parameters
        mock_session.run.assert_called_once_with(
            "MATCH (n) RETURN n.name as name",
            {"param": "value"}
        )
        
        # Verify result is correct
        self.assertEqual(result, [{"name": "Test1"}, {"name": "Test2"}])
    
    @patch('ifc_to_graph.database.neo4j_connector.GraphDatabase')
    def test_context_manager(self, mock_graph_db):
        """Test using the connector as a context manager."""
        # Setup mock
        mock_driver = Mock()
        mock_graph_db.driver.return_value = mock_driver
        
        # Use connector as context manager
        with Neo4jConnector(
            uri="neo4j://localhost:7687",
            username="neo4j",
            password="password"
        ) as connector:
            # Verify connection is established
            self.assertEqual(connector.driver, mock_driver)
        
        # Verify connection is closed after context
        mock_driver.close.assert_called_once()


if __name__ == '__main__':
    unittest.main() 