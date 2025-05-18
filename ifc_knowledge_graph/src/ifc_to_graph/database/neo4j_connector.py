"""
Neo4j Connector Module

This module provides functionality to connect to and interact with the Neo4j database,
including session management and transaction handling.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from neo4j import GraphDatabase, Driver, Session, Transaction
from neo4j.exceptions import ServiceUnavailable, AuthError

# Configure logging
logger = logging.getLogger(__name__)


class Neo4jConnector:
    """
    Connector class for Neo4j database operations.
    Handles connection, session management, and transactions.
    """
    
    def __init__(self, uri: str, username: str, password: str, database: Optional[str] = None):
        """
        Initialize the Neo4j connector with connection parameters.
        
        Args:
            uri: The URI for Neo4j (e.g., 'neo4j://localhost:7687')
            username: The Neo4j username
            password: The Neo4j password
            database: Optional database name if not using the default
        """
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.driver = None
        
        # Connect to database
        self._connect()
        
    def _connect(self) -> None:
        """
        Establish a connection to the Neo4j database.
        Raises an exception if connection fails.
        """
        try:
            logger.info(f"Connecting to Neo4j database at {self.uri}")
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.username, self.password)
            )
            
            # Verify connection
            self.driver.verify_connectivity()
            logger.info("Successfully connected to the Neo4j database")
        
        except AuthError as e:
            logger.error(f"Authentication error connecting to Neo4j: {str(e)}")
            raise
        
        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable: {str(e)}")
            raise
        
        except Exception as e:
            logger.error(f"Error connecting to Neo4j: {str(e)}")
            raise
    
    def close(self) -> None:
        """Close the database connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j database connection closed")
            self.driver = None
    
    def get_session(self) -> Session:
        """
        Get a new Neo4j session.
        
        Returns:
            A new Neo4j session object
        """
        if not self.driver:
            raise RuntimeError("Not connected to Neo4j database")
        
        # Create session with specified database if provided
        if self.database:
            return self.driver.session(database=self.database)
        return self.driver.session()
    
    def run_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Run a Cypher query and return the results.
        
        Args:
            query: Cypher query string
            parameters: Dictionary of query parameters
            
        Returns:
            List of result records as dictionaries
        """
        if parameters is None:
            parameters = {}
        
        with self.get_session() as session:
            try:
                result = session.run(query, parameters)
                return [record.data() for record in result]
            
            except Exception as e:
                logger.error(f"Error executing query: {str(e)}")
                raise
    
    def execute_with_transaction(self, work_function: Callable[[Transaction], Any]) -> Any:
        """
        Execute operations within a transaction.
        
        Args:
            work_function: Function to execute within transaction
            
        Returns:
            Result from the work function
        """
        with self.get_session() as session:
            try:
                return session.execute_write(work_function)
            
            except Exception as e:
                logger.error(f"Error in transaction: {str(e)}")
                raise
    
    def execute_read_transaction(self, work_function: Callable[[Transaction], Any]) -> Any:
        """
        Execute read-only operations within a transaction.
        
        Args:
            work_function: Function to execute within read transaction
            
        Returns:
            Result from the work function
        """
        with self.get_session() as session:
            try:
                return session.execute_read(work_function)
            
            except Exception as e:
                logger.error(f"Error in read transaction: {str(e)}")
                raise
    
    def execute_batch(self, query: str, batch_data: List[Dict[str, Any]]) -> None:
        """
        Execute a query in batch mode for better performance with large data sets.
        
        Args:
            query: Cypher query string with parameter placeholders
            batch_data: List of parameter dictionaries for each batch item
        """
        if not batch_data:
            return
        
        with self.get_session() as session:
            try:
                for data in batch_data:
                    session.run(query, data)
                
                logger.info(f"Successfully executed batch with {len(batch_data)} items")
            
            except Exception as e:
                logger.error(f"Error executing batch: {str(e)}")
                raise
                
    def __enter__(self):
        """Support context manager protocol."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources when exiting context."""
        self.close() 