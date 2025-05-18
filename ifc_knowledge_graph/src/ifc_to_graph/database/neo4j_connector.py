"""
Neo4j Connector Module

This module provides functionality to connect to and interact with the Neo4j database,
including session management and transaction handling.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from neo4j import GraphDatabase, Driver, Session, Transaction
from neo4j.exceptions import ServiceUnavailable, AuthError

from .performance_monitor import PerformanceMonitor, timing_decorator

# Configure logging
logger = logging.getLogger(__name__)


class Neo4jConnector:
    """
    Connector class for Neo4j database operations.
    Handles connection, session management, and transactions.
    """
    
    def __init__(
        self, 
        uri: str, 
        username: str, 
        password: str, 
        database: Optional[str] = None,
        enable_monitoring: bool = False
    ):
        """
        Initialize the Neo4j connector with connection parameters.
        
        Args:
            uri: The URI for Neo4j (e.g., 'neo4j://localhost:7687')
            username: The Neo4j username
            password: The Neo4j password
            database: Optional database name if not using the default
            enable_monitoring: Whether to enable performance monitoring
        """
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.driver = None
        
        # Initialize performance monitor
        self.performance_monitor = PerformanceMonitor(enabled=enable_monitoring)
        
        # Connect to database
        self._connect()
        
    def _connect(self) -> None:
        """
        Establish a connection to the Neo4j database.
        Raises an exception if connection fails.
        """
        try:
            logger.info(f"Connecting to Neo4j database at {self.uri}")
            
            # Measure connection time
            stop_timer = self.performance_monitor.start_timer(
                "database_connection",
                {"uri": self.uri}
            )
            
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.username, self.password)
            )
            
            # Verify connection
            self.driver.verify_connectivity()
            
            # Record connection time
            stop_timer()
            
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
    
    @timing_decorator
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
        
        # Track memory before query
        self.performance_monitor.measure_memory("query_before", {
            "query_type": "run_query",
            "query_preview": query[:100] if query else ""
        })
        
        with self.get_session() as session:
            try:
                # Record query context for monitoring
                context = {
                    "query_text": query,
                    "parameter_count": len(parameters) if parameters else 0
                }
                
                # Start timer manually (decorator also times, but we want more context)
                stop_timer = self.performance_monitor.start_timer("run_query", context)
                
                # Execute query
                result = session.run(query, parameters)
                records = [record.data() for record in result]
                
                # Record result context
                result_context = {
                    **context,
                    "record_count": len(records)
                }
                
                # Stop timer with result context
                elapsed_ms = stop_timer()
                
                # Record metrics about results
                self.performance_monitor.record_metric(
                    name="query_result_count",
                    value=len(records),
                    unit="records",
                    context=result_context
                )
                
                # Track memory after query
                self.performance_monitor.measure_memory("query_after", result_context)
                
                # Log performance for slow queries
                if elapsed_ms > 1000:  # 1 second
                    logger.warning(f"Slow query ({elapsed_ms:.2f} ms): {query[:100]}...")
                
                return records
            
            except Exception as e:
                logger.error(f"Error executing query: {str(e)}")
                
                # Record error in performance metrics
                self.performance_monitor.record_metric(
                    name="query_error",
                    value=1.0,
                    unit="count",
                    context={
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "query_text": query
                    }
                )
                
                raise
    
    @timing_decorator
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
                # Track memory before transaction
                self.performance_monitor.measure_memory("transaction_before")
                
                result = session.execute_write(work_function)
                
                # Track memory after transaction
                self.performance_monitor.measure_memory("transaction_after")
                
                return result
            
            except Exception as e:
                logger.error(f"Error in transaction: {str(e)}")
                
                # Record error
                self.performance_monitor.record_metric(
                    name="transaction_error",
                    value=1.0,
                    unit="count",
                    context={
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    }
                )
                
                raise
    
    @timing_decorator
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
                # Track memory before read transaction
                self.performance_monitor.measure_memory("read_transaction_before")
                
                result = session.execute_read(work_function)
                
                # Track memory after read transaction
                self.performance_monitor.measure_memory("read_transaction_after")
                
                return result
            
            except Exception as e:
                logger.error(f"Error in read transaction: {str(e)}")
                
                # Record error
                self.performance_monitor.record_metric(
                    name="read_transaction_error",
                    value=1.0,
                    unit="count",
                    context={
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    }
                )
                
                raise
    
    @timing_decorator
    def execute_batch(self, query: str, batch_data: List[Dict[str, Any]]) -> None:
        """
        Execute a query in batch mode for better performance with large data sets.
        
        Args:
            query: Cypher query string with parameter placeholders
            batch_data: List of parameter dictionaries for each batch item
        """
        if not batch_data:
            return
        
        # Track batch metrics
        self.performance_monitor.record_metric(
            name="batch_size",
            value=len(batch_data),
            unit="items",
            context={"query": query[:100] if query else ""}
        )
        
        # Track memory before batch
        self.performance_monitor.measure_memory("batch_before", {
            "batch_size": len(batch_data)
        })
        
        with self.get_session() as session:
            try:
                for idx, data in enumerate(batch_data):
                    # Start timer for individual batch item
                    stop_item_timer = self.performance_monitor.start_timer(
                        "batch_item", 
                        {"item_index": idx, "batch_size": len(batch_data)}
                    )
                    
                    session.run(query, data)
                    
                    # Stop timer for individual batch item
                    stop_item_timer()
                
                # Track memory after batch
                self.performance_monitor.measure_memory("batch_after", {
                    "batch_size": len(batch_data)
                })
                
                logger.info(f"Successfully executed batch with {len(batch_data)} items")
            
            except Exception as e:
                logger.error(f"Error executing batch: {str(e)}")
                
                # Record error
                self.performance_monitor.record_metric(
                    name="batch_error",
                    value=1.0,
                    unit="count",
                    context={
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "batch_size": len(batch_data),
                        "query": query
                    }
                )
                
                raise
                
    def __enter__(self):
        """Support context manager protocol."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources when exiting context."""
        self.close()
        
    def test_connection(self) -> bool:
        """
        Test the connection to Neo4j database.
        
        Returns:
            bool: True if the connection is successful, False otherwise
        """
        try:
            # Simple query to test the connection
            result = self.run_query("RETURN 1 AS test")
            return result and len(result) > 0 and result[0].get("test") == 1
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def get_performance_report(self) -> str:
        """
        Get a performance report.
        
        Returns:
            String containing the performance report
        """
        return self.performance_monitor.summary_report()
    
    def export_performance_metrics(self, file_path: str) -> Dict[str, Any]:
        """
        Export performance metrics to a file.
        
        Args:
            file_path: Path to save the metrics
            
        Returns:
            Dictionary with metrics data
        """
        return self.performance_monitor.export_metrics(file_path) 