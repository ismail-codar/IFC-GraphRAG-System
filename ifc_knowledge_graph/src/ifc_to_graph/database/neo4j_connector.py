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
    Connector for Neo4j graph database.
    
    This class handles connections to Neo4j, provides methods to run queries,
    and includes performance monitoring.
    """
    
    def __init__(
        self, 
        uri: str, 
        username: str, 
        password: str, 
        database: Optional[str] = None,
        enable_monitoring: bool = False,
        monitoring_output_dir: Optional[str] = None
    ):
        """
        Initialize the Neo4j connector.
        
        Args:
            uri: URI for Neo4j server
            username: Neo4j username
            password: Neo4j password
            database: Optional database name
            enable_monitoring: Enable performance monitoring
            monitoring_output_dir: Directory to output performance reports
        """
        self.uri = uri
        self.auth = (username, password)
        self.database = database
        self.driver = None
        
        # Initialize performance monitoring
        self.performance_monitor = PerformanceMonitor(enabled=enable_monitoring)
        self.monitoring_output_dir = monitoring_output_dir
        
        # Connect to Neo4j
        self._connect()
    
    def _connect(self) -> None:
        """Connect to Neo4j database."""
        logger.info(f"Connecting to Neo4j database at {self.uri}")
        try:
            # Create the driver
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=self.auth,
                # Connection pool settings
                max_connection_lifetime=3600,  # 1 hour
                max_connection_pool_size=50,
                connection_acquisition_timeout=60  # 1 minute
            )
            
            # Verify connection works
            with self.driver.session(database=self.database) as session:
                session.run("RETURN 1")
            
            logger.info("Successfully connected to the Neo4j database")
            
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j database: {str(e)}")
            if self.driver:
                self.driver.close()
                self.driver = None
            raise
    
    def close(self) -> None:
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()
            self.driver = None
            logger.info("Neo4j database connection closed")
    
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
    
    def flatten_complex_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten complex parameter values that Neo4j can't handle.
        Neo4j only accepts primitive values (strings, numbers, booleans) or arrays of these.
        
        Args:
            params: Dictionary with possibly complex values
            
        Returns:
            Dictionary with only primitive values and arrays
        """
        flattened = {}
        
        for key, value in params.items():
            if value is None:
                # Skip None values
                continue
                
            if isinstance(value, (str, int, float, bool)):
                # Primitive types are allowed
                flattened[key] = value
            elif isinstance(value, (list, tuple)):
                # Lists/tuples of primitives are allowed
                primitive_list = []
                for item in value:
                    if isinstance(item, (str, int, float, bool)):
                        primitive_list.append(item)
                    else:
                        # Convert complex items to string representation
                        primitive_list.append(str(item))
                flattened[key] = primitive_list
            elif isinstance(value, dict):
                # Convert dict to string
                flattened[key] = str(value)
            else:
                # Convert other complex types to string
                flattened[key] = str(value)
                
        return flattened
    
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
            
        # Flatten any complex parameters Neo4j can't handle
        safe_parameters = self.flatten_complex_parameters(parameters)
        
        # Track memory if monitoring is enabled, but handle potential errors
        if self.performance_monitor and self.performance_monitor.enabled:
            try:
                self.performance_monitor.measure_memory("query_before", {
                    "query_type": "run_query",
                    "query_preview": query[:100] if query else ""
                })
            except Exception as e:
                logger.warning(f"Failed to measure memory before query: {str(e)}")
        
        with self.get_session() as session:
            try:
                # Record query context for monitoring
                context = {
                    "query_text": query,
                    "parameter_count": len(safe_parameters) if safe_parameters else 0
                }
                
                # Start timer manually only if monitoring is enabled
                stop_timer = None
                if self.performance_monitor and self.performance_monitor.enabled:
                    try:
                        stop_timer = self.performance_monitor.start_timer("run_query", context)
                    except Exception as e:
                        logger.warning(f"Failed to start timer: {str(e)}")
                
                # Execute query
                result = session.run(query, safe_parameters)
                records = [record.data() for record in result]
                
                # Record result context and stop timer only if monitoring is enabled
                if self.performance_monitor and self.performance_monitor.enabled and stop_timer:
                    try:
                        result_context = {
                            **context,
                            "record_count": len(records)
                        }
                        
                        # Stop timer with result context
                        try:
                            elapsed_ms = stop_timer()
                            
                            # Only log slow queries if we got a valid elapsed time
                            if elapsed_ms is not None and elapsed_ms > 1000:  # 1 second
                                logger.warning(f"Slow query ({elapsed_ms:.2f} ms): {query[:100]}...")
                        except Exception as timer_error:
                            logger.warning(f"Error processing timer result: {str(timer_error)}")
                        
                        # Record metrics about results
                        try:
                            self.performance_monitor.record_metric(
                                name="query_result_count",
                                value=len(records),
                                unit="records",
                                context=result_context
                            )
                        except Exception as metric_error:
                            logger.warning(f"Error recording result count metric: {str(metric_error)}")
                        
                        # Track memory after query
                        try:
                            self.performance_monitor.measure_memory("query_after", result_context)
                        except Exception as memory_error:
                            logger.warning(f"Error measuring memory after query: {str(memory_error)}")
                        
                    except Exception as e:
                        logger.warning(f"Error in performance monitoring: {str(e)}")
                
                return records
            
            except Exception as e:
                logger.error(f"Error executing query: {str(e)}")
                
                # Record error in performance metrics if monitoring is enabled
                if self.performance_monitor and self.performance_monitor.enabled:
                    try:
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
                    except Exception as mon_err:
                        logger.warning(f"Error recording performance metric: {str(mon_err)}")
                
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
                # Track memory before transaction if monitoring is enabled
                if self.performance_monitor and self.performance_monitor.enabled:
                    try:
                        self.performance_monitor.measure_memory("transaction_before")
                    except Exception as e:
                        logger.warning(f"Error measuring memory before transaction: {str(e)}")
                
                result = session.execute_write(work_function)
                
                # Track memory after transaction if monitoring is enabled
                if self.performance_monitor and self.performance_monitor.enabled:
                    try:
                        self.performance_monitor.measure_memory("transaction_after")
                    except Exception as e:
                        logger.warning(f"Error measuring memory after transaction: {str(e)}")
                
                return result
            
            except Exception as e:
                logger.error(f"Error in transaction: {str(e)}")
                
                # Record error if monitoring is enabled
                if self.performance_monitor and self.performance_monitor.enabled:
                    try:
                        self.performance_monitor.record_metric(
                            name="transaction_error",
                            value=1.0,
                            unit="count",
                            context={
                                "error_type": type(e).__name__,
                                "error_message": str(e)
                            }
                        )
                    except Exception as mon_err:
                        logger.warning(f"Error recording transaction error metric: {str(mon_err)}")
                
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
                # Track memory before read transaction if monitoring is enabled
                if self.performance_monitor and self.performance_monitor.enabled:
                    try:
                        self.performance_monitor.measure_memory("read_transaction_before")
                    except Exception as e:
                        logger.warning(f"Error measuring memory before read transaction: {str(e)}")
                
                result = session.execute_read(work_function)
                
                # Track memory after read transaction if monitoring is enabled
                if self.performance_monitor and self.performance_monitor.enabled:
                    try:
                        self.performance_monitor.measure_memory("read_transaction_after")
                    except Exception as e:
                        logger.warning(f"Error measuring memory after read transaction: {str(e)}")
                
                return result
            
            except Exception as e:
                logger.error(f"Error in read transaction: {str(e)}")
                
                # Record error if monitoring is enabled
                if self.performance_monitor and self.performance_monitor.enabled:
                    try:
                        self.performance_monitor.record_metric(
                            name="read_transaction_error",
                            value=1.0,
                            unit="count",
                            context={
                                "error_type": type(e).__name__,
                                "error_message": str(e)
                            }
                        )
                    except Exception as mon_err:
                        logger.warning(f"Error recording read transaction error metric: {str(mon_err)}")
                
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
        if self.performance_monitor and self.performance_monitor.enabled:
            try:
                self.performance_monitor.record_metric(
                    name="batch_size",
                    value=len(batch_data),
                    unit="items",
                    context={"query": query[:100] if query else ""}
                )
            except Exception as e:
                logger.warning(f"Error recording batch size metric: {str(e)}")
        
        # Track memory before batch
        if self.performance_monitor and self.performance_monitor.enabled:
            try:
                self.performance_monitor.measure_memory("batch_before", {
                    "batch_size": len(batch_data)
                })
            except Exception as e:
                logger.warning(f"Error measuring memory before batch: {str(e)}")
        
        with self.get_session() as session:
            try:
                for idx, data in enumerate(batch_data):
                    # Start timer for individual batch item
                    stop_item_timer = None
                    if self.performance_monitor and self.performance_monitor.enabled:
                        try:
                            stop_item_timer = self.performance_monitor.start_timer(
                                "batch_item", 
                                {"item_index": idx, "batch_size": len(batch_data)}
                            )
                        except Exception as e:
                            logger.warning(f"Error starting timer for batch item {idx}: {str(e)}")
                    
                    session.run(query, data)
                    
                    # Stop timer for individual batch item
                    if stop_item_timer:
                        try:
                            stop_item_timer()
                        except Exception as e:
                            logger.warning(f"Error stopping timer for batch item {idx}: {str(e)}")
                
                # Track memory after batch
                if self.performance_monitor and self.performance_monitor.enabled:
                    try:
                        self.performance_monitor.measure_memory("batch_after", {
                            "batch_size": len(batch_data)
                        })
                    except Exception as e:
                        logger.warning(f"Error measuring memory after batch: {str(e)}")
                
                logger.info(f"Successfully executed batch with {len(batch_data)} items")
            
            except Exception as e:
                logger.error(f"Error executing batch: {str(e)}")
                
                # Record error
                if self.performance_monitor and self.performance_monitor.enabled:
                    try:
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
                    except Exception as mon_err:
                        logger.warning(f"Error recording batch error metric: {str(mon_err)}")
                
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
            # Ensure we have a driver
            if not self.driver:
                logger.error("No Neo4j driver available for connection test")
                return False
                
            # Disable performance monitoring for the connection test to avoid potential issues
            original_enabled = False
            if hasattr(self, 'performance_monitor') and self.performance_monitor:
                original_enabled = self.performance_monitor.enabled
                self.performance_monitor.enabled = False
            
            try:
                # Use a very simple query that doesn't require any comparisons
                with self.get_session() as session:
                    # Direct session query without using run_query to avoid any additional issues
                    result = session.run("RETURN true AS connected")
                    record = result.single()
                    
                    # Check if we got a valid result with the expected field
                    if record and record.get("connected") is True:
                        logger.info("Connection test successful")
                        return True
                    else:
                        logger.warning(f"Connection test returned unexpected result: {record}")
                        return False
                
            finally:
                # Restore original monitoring state if we changed it
                if hasattr(self, 'performance_monitor') and self.performance_monitor:
                    self.performance_monitor.enabled = original_enabled
                
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
    
    def create_relationship(self, source_id, target_id, relationship_type, properties=None):
        """
        Create a relationship between nodes identified by their GlobalIds.
        Uses optimized query to avoid Cartesian product warnings.
        
        Args:
            source_id: GlobalId of the source node
            target_id: GlobalId of the target node
            relationship_type: Type of relationship to create
            properties: Optional dictionary of relationship properties
            
        Returns:
            relationship type if successful
        """
        # Import the query optimizer
        from .query_optimizer import optimize_node_connection_query
        
        # Get optimized query and parameters
        query, params = optimize_node_connection_query(source_id, target_id, relationship_type, properties)
        
        # Execute query with performance monitoring if enabled
        if self.performance_monitor and self.performance_monitor.enabled:
            # Use start_timer instead of measure_time context manager
            stop_timer = self.performance_monitor.start_timer("create_relationship")
            try:
                result = self.run_query(query, params)
                if stop_timer:
                    stop_timer()
                return result[0]["RelationType"] if result else None
            except Exception as e:
                if stop_timer:
                    stop_timer()
                raise
        else:
            result = self.run_query(query, params)
            return result[0]["RelationType"] if result else None
    
    def create_relationships_batch(self, relationship_batch):
        """
        Create multiple relationships in a batch operation.
        Uses optimized query to avoid Cartesian product warnings.
        
        Args:
            relationship_batch: List of dictionaries, each containing:
                source_id: GlobalId of source node
                target_id: GlobalId of target node
                type: Relationship type
                properties: Optional relationship properties
                
        Returns:
            Number of relationships created
        """
        if not relationship_batch:
            return 0
            
        # Import the query optimizer
        from .query_optimizer import optimize_batch_merge_query
        
        # Get optimized batch query and parameters
        query, params = optimize_batch_merge_query(relationship_batch)
        
        # Execute query with performance monitoring if enabled
        if self.performance_monitor and self.performance_monitor.enabled:
            # Use start_timer instead of measure_time context manager
            stop_timer = self.performance_monitor.start_timer("create_relationships_batch")
            try:
                result = self.run_query(query, params)
                if stop_timer:
                    stop_timer()
                return result[0]["count"] if result else 0
            except Exception as e:
                if stop_timer:
                    stop_timer()
                raise
        else:
            result = self.run_query(query, params)
            return result[0]["count"] if result else 0
    
    def run_transaction(
        self, 
        queries: List[Dict[str, Any]], 
        read_only: bool = False
    ) -> List[List[Dict[str, Any]]]:
        """
        Run multiple queries in a single transaction.
        
        Args:
            queries: List of dictionaries, each containing:
                - query: Cypher query string
                - parameters: Dictionary of query parameters (optional)
            read_only: Whether to use a read-only transaction
            
        Returns:
            List of result lists for each query
        """
        if not queries:
            return []
        
        try:
            with self.get_session() as session:
                if self.performance_monitor and self.performance_monitor.enabled:
                    # Start timing
                    stop_timer = self.performance_monitor.start_timer("transaction")
                
                # Execute transaction
                if read_only:
                    result = session.execute_read(
                        self._run_transaction_function, queries=queries
                    )
                else:
                    result = session.execute_write(
                        self._run_transaction_function, queries=queries
                    )
                
                if self.performance_monitor and self.performance_monitor.enabled:
                    # Stop timer if available
                    if stop_timer:
                        elapsed_time = stop_timer()
                    
                    # Record metrics
                    query_count = len(queries)
                    self.performance_monitor.record_metric(
                        name="transaction_query_count",
                        value=query_count,
                        unit="count"
                    )
                
                return result
        except Exception as e:
            logger.error(f"Transaction failed: {str(e)}")
            raise
    
    def _run_transaction_function(self, tx: Transaction, queries: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Execute multiple queries within a transaction.
        
        Args:
            tx: Neo4j transaction object
            queries: List of query dictionaries
            
        Returns:
            List of results for each query
        """
        results = []
        
        for query_dict in queries:
            query = query_dict["query"]
            parameters = query_dict.get("parameters", {})
            
            # Flatten any complex parameters
            safe_parameters = self.flatten_complex_parameters(parameters)
            
            # Execute query within transaction
            result = tx.run(query, safe_parameters)
            results.append([record.data() for record in result])
        
        return results 